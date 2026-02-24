<p align="center">
  <img src="assets/shadow-nexus.png" alt="Shadow Nexus Banner"/>
</p>




# 🕶️ SHADOW-NEXUS

> _"From Shadow Nexus APT with love ;)"_

**Shadow-Nexus** is a next-generation adversary simulation framework that brings together automation, AI, and real-world offensive tradecraft. Built for demos, research, and red team simulations, it offers a modular Command and Control (C2) system with stealth agents capable of persistence, credential harvesting, and lateral movement analysis—powered by AI.

⚠️ **For authorized environments only.** This project is intended strictly for ethical use in controlled, permissioned labs. Do not deploy this in real-world systems without explicit consent.

---

## ✨ Features

- 🕵️‍♂️ **Stealth Agent (Windows/Linux)**  
  - Initial recon (system, user, network & scheduled tasks)  
  - Optional persistence (registry keys or scheduled tasks)  
  - AWS credential discovery (file system + env vars)  
  - Automated lateral movement suggestions via GPT  
  - Obfuscated payload execution

- 🧠 **AI-Assisted Analysis**  
  - One-click intelligence analysis of each task output  
  - “Attacker’s perspective” narratives for SOC & demo use  
  - Uses OpenAI’s GPT for parsing and summarizing raw output

- 🌐 **C2 Dashboard**  
  - Web-based interface to monitor and control agents  
  - Live feed of tasks and results  
  - Agent ID fingerprinting & per-task targeting  

---

## 📦 Structure

```bash
shadow-nexus/
├── agent/                  # Advanced agent codebase
├── utils/                  # Exfil server        
├── server/                 # Flask C2 backend + dashboard
├── llm_responses/          # Auto-generated AI output storage
├── stealth_wrapper.py      # (optional) PyInstaller wrapper
├── README.md               # This file
├── INSTALL.md              # Install instructions
