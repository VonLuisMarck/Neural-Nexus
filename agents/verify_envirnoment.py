#!/usr/bin/env python3
# verify_environment.py - Environment verification script
import sys
import subprocess
import platform
import os

def check_requirements():
    print("Checking requirements...")
    try:
        import pkg_resources
        
        # Read requirements
        with open('requirements.txt') as f:
            requirements = f.read().splitlines()
        
        # Filter out comments and empty lines
        requirements = [r.strip() for r in requirements if r.strip() and not r.startswith('#')]
        
        # Check each requirement
        missing = []
        for req in requirements:
            try:
                pkg_resources.require(req)
            except pkg_resources.DistributionNotFound:
                missing.append(req)
        
        if missing:
            print("Missing requirements:")
            for req in missing:
                print(f"  - {req}")
            print("\nInstall with: pip install -r requirements.txt")
            return False
        
        print("All requirements satisfied!")
        return True
    
    except Exception as e:
        print(f"Error checking requirements: {e}")
        return False

def check_environment():
    print(f"Checking environment...")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Check for PyInstaller
    try:
        subprocess.run(["pyinstaller", "--version"], 
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("PyInstaller: Installed")
    except:
        print("PyInstaller: Not found (needed for agent compilation)")
    
    # Check directory permissions
    try:
        test_file = os.path.join(os.getcwd(), ".test_write_permission")
        with open(test_file, 'w') as f:
            f.write("test")
        os.unlink(test_file)
        print("Directory permissions: Write access OK")
    except:
        print("Directory permissions: Cannot write to current directory")
    

if __name__ == "__main__":
    print("GenAI-Enhanced C2 Framework - Environment Check")
    print("=" * 50)
    check_environment()
    print("\n" + "=" * 50)
    check_requirements()
    print("=" * 50)
