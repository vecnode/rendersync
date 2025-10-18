import asyncio
import subprocess
import psutil
import socket
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

import shutil
import os
from ..config import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL, OLLAMA_GENERATION_OPTIONS

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        """Check if Ollama service is healthy."""
        url = f"{self.base_url}/api/tags"
        timeout = httpx.Timeout(1.0, connect=1.0)  # Reduced timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                r = await client.get(url)
                r.raise_for_status()
                return True
            except Exception:
                return False

    async def ensure_model(self, model: str) -> None:
        """No-throw attempt to ensure model exists by checking tags.
        If missing, try to pull it (non-fatal if this fails)."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:  # Reduced timeout
                tags = await client.get(f"{self.base_url}/api/tags")
                present = False
                if tags.status_code == 200:
                    data = tags.json()
                    for m in data.get("models", []):
                        if m.get("name") == model:
                            present = True
                            break
                if not present:
                    # Attempt to pull; stream progress, but don't block the server forever.
                    # If it fails, requests to /chat will still return a clear error from Ollama.
                    async with client.stream("POST", f"{self.base_url}/api/pull", json={"name": model}) as resp:
                        async for _ in resp.aiter_bytes():
                            pass
        except Exception:
            # Non-fatal; proceed.
            return

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] | None = None,
        stream: bool = False,
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """Send chat request to Ollama."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        if not stream:
            async with httpx.AsyncClient(timeout=None) as client:
                r = await client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                return r.json()
        else:
            async def gen() -> AsyncGenerator[Dict[str, Any], None]:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as r:
                        r.raise_for_status()
                        async for line in r.aiter_lines():
                            if not line:
                                continue
                            try:
                                yield json.loads(line)
                            except Exception:
                                # If a line isn't valid JSON, skip it.
                                continue
            return gen()
    
    async def simple_chat(self, message: str, model: str = None) -> dict:
        """Send a simple chat message to Ollama and return the response."""
        try:
            # First check if Ollama is responding
            if not await self.health():
                return {
                    "success": False,
                    "error": "Ollama not running",
                    "response": "Ollama is not running. Please start Ollama first using the 'Start ollama' button."
                }
            
            # Get available models
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    tags_response = await client.get(f"{self.base_url}/api/tags")
                    if tags_response.status_code != 200:
                        return {
                            "success": False,
                            "error": "Failed to get available models",
                            "response": f"Cannot connect to Ollama API (Status: {tags_response.status_code})"
                        }
                    
                    data = tags_response.json()
                    models = data.get("models", [])
                    
                    if not models:
                        return {
                            "success": False,
                            "error": "No models available",
                            "response": "No models found. Please install a model first using 'Get ollama Models' to see available models."
                        }
                    
                    # Use provided model, or try default model, or fallback to first available
                    if model:
                        # Check if provided model is available
                        model_available = False
                        for m in models:
                            if m["name"] == model:
                                model_available = True
                                break
                        
                        if model_available:
                            model_name = model
                            logger.info(f"Using selected model: {model_name}")
                        else:
                            # Provided model not available, fallback to default
                            model_name = OLLAMA_DEFAULT_MODEL
                            logger.warning(f"Selected model '{model}' not available, trying default: {model_name}")
                    else:
                        # No model provided, use default
                        model_name = OLLAMA_DEFAULT_MODEL
                        logger.info(f"No model specified, using default: {model_name}")
                    
                    # Check if chosen model is available
                    model_available = False
                    for m in models:
                        if m["name"] == model_name:
                            model_available = True
                            break
                    
                    # If chosen model not available, use first available
                    if not model_available:
                        model_name = models[0]["name"]
                        logger.info(f"Chosen model not available, using first available: {model_name}")
                    
                except httpx.ConnectError:
                    return {
                        "success": False,
                        "error": "Connection failed",
                        "response": "Cannot connect to Ollama. Please make sure Ollama is running and try again."
                    }
                except httpx.TimeoutException:
                    return {
                        "success": False,
                        "error": "Connection timeout",
                        "response": "Ollama is taking too long to respond. Please try again."
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"API error: {str(e)}",
                        "response": f"Error getting models: {str(e)}"
                    }
            
            # Send chat message
            try:
                messages = [{"role": "user", "content": message}]
                response = await self.chat(model_name, messages, options=OLLAMA_GENERATION_OPTIONS, stream=False)
                
                if response and "message" in response:
                    return {
                        "success": True,
                        "response": response["message"]["content"],
                        "model": model_name
                    }
                else:
                    return {
                        "success": False,
                        "error": "Invalid response from Ollama",
                        "response": f"Unexpected response format: {str(response)}"
                    }
                    
            except httpx.ConnectError:
                return {
                    "success": False,
                    "error": "Connection failed during chat",
                    "response": "Lost connection to Ollama during chat. Please check if Ollama is still running."
                }
            except httpx.TimeoutException:
                return {
                    "success": False,
                    "error": "Chat timeout",
                    "response": "Ollama is taking too long to respond to your message. Please try again."
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Chat error: {str(e)}",
                    "response": f"Error during chat: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error in simple_chat: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"Unexpected error: {str(e)}"
            }


class OllamaManager:
    """Manager for Ollama process lifecycle and model management."""
    
    def __init__(self):
        self.ollama_process: Optional[subprocess.Popen] = None
        self.ollama_pid: Optional[int] = None
        self.is_external_process = False
        self.base_url = OLLAMA_BASE_URL
        
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use by trying to bind to it."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return False
        except OSError:
            return True
            
    def find_ollama_process(self) -> Optional[int]:
        """Find existing Ollama process by checking for processes listening on port 11434."""
        try:
            # Get all network connections
            connections = psutil.net_connections(kind='tcp')
            
            # Find processes listening on port 11434
            for conn in connections:
                if conn.laddr.port == 11434 and conn.status == 'LISTEN':
                    return conn.pid
                    
        except Exception as e:
            logger.warning(f"Error finding Ollama process: {e}")
            
        return None
        
    def is_ollama_responding(self) -> bool:
        """Check if Ollama is responding on its API endpoint."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)  # Faster timeout
                result = s.connect_ex(('127.0.0.1', 11434))
                return result == 0
        except Exception:
            return False
            
    def find_ollama_installation(self) -> Optional[str]:
        """Find Ollama installation directory."""
        try:
            import shutil
            
            # First try to find ollama executable in PATH
            ollama_path = shutil.which("ollama")
            if ollama_path:
                # Get the directory containing the executable
                install_dir = os.path.dirname(ollama_path)
                if os.path.exists(install_dir):
                    return install_dir
            
            # Check if we're on Windows 11
            is_windows_11 = False
            if os.name == 'nt':  # Windows
                try:
                    import platform
                    version = platform.version()
                    # Windows 11 has build number >= 22000
                    if version and int(version.split('.')[2]) >= 22000:
                        is_windows_11 = True
                except:
                    pass
            
            # Common installation paths for current user
            if is_windows_11:
                possible_paths = [
                    os.path.normpath(os.path.expanduser("~/ollama")),
                    os.path.normpath(os.path.expanduser("~/Ollama")),
                    os.path.normpath(os.path.expanduser("~/Desktop/ollama")),
                    os.path.normpath(os.path.expanduser("~/Desktop/Ollama")),
                    os.path.normpath(os.path.expanduser("~/Documents/ollama")),
                    os.path.normpath(os.path.expanduser("~/Documents/Ollama")),
                    os.path.normpath(os.path.expanduser("~/AppData/Local/Programs/Ollama")),  # Windows default
                    os.path.normpath(os.path.expanduser("~/Applications/Ollama.app/Contents/MacOS")),  # macOS
                    os.path.join(os.getcwd(), "ollama"),
                    os.path.join(os.getcwd(), "Ollama"),
                ]
            else:
                possible_paths = [
                    os.path.expanduser("~/ollama"),
                    os.path.expanduser("~/Ollama"),
                    os.path.expanduser("~/Desktop/ollama"),
                    os.path.expanduser("~/Desktop/Ollama"),
                    os.path.expanduser("~/Documents/ollama"),
                    os.path.expanduser("~/Documents/Ollama"),
                    os.path.expanduser("~/AppData/Local/Programs/Ollama"),  # Windows default
                    os.path.expanduser("~/Applications/Ollama.app/Contents/MacOS"),  # macOS
                    os.path.join(os.getcwd(), "ollama"),
                    os.path.join(os.getcwd(), "Ollama"),
                ]
            
            # Windows-specific: Check Program Files
            if os.name == 'nt':  # Windows
                try:
                    import winreg
                    # Check common Windows installation locations
                    windows_paths = [
                        os.path.expanduser("~/AppData/Local/Programs/Ollama"),
                        "C:/Program Files/Ollama",
                        "C:/Program Files (x86)/Ollama",
                    ]
                    possible_paths.extend(windows_paths)
                except ImportError:
                    pass
            
            # Check each possible path
            for path in possible_paths:
                if os.path.exists(path):
                    # Look for ollama executable in this directory
                    ollama_exe = os.path.join(path, "ollama.exe" if os.name == 'nt' else "ollama")
                    if os.path.exists(ollama_exe):
                        return path
                    
                    # Also check subdirectories
                    try:
                        for item in os.listdir(path):
                            item_path = os.path.join(path, item)
                            if os.path.isdir(item_path):
                                ollama_exe = os.path.join(item_path, "ollama.exe" if os.name == 'nt' else "ollama")
                                if os.path.exists(ollama_exe):
                                    return item_path
                    except (OSError, PermissionError):
                        continue
                        
        except Exception as e:
            logger.warning(f"Error finding Ollama installation: {e}")
            
        return None
            
    async def ensure_ollama_running(self) -> bool:
        """Ensure Ollama is running, either by finding existing process or starting new one."""
        try:
            # Fast check: Is Ollama already responding?
            if self.is_ollama_responding():
                logger.info("Ollama is already running and responding")
                # Find the process ID for tracking
                existing_pid = self.find_ollama_process()
                if existing_pid:
                    self.ollama_pid = existing_pid
                    self.is_external_process = True
                return True
                
            # Slower check: Is port in use by something else?
            if self.is_port_in_use(11434):
                # Port is in use, try to find the process
                existing_pid = self.find_ollama_process()
                if existing_pid:
                    logger.info(f"Found existing Ollama process (PID: {existing_pid})")
                    self.ollama_pid = existing_pid
                    self.is_external_process = True
                    return True
                
            # No existing process found, start a new one
            logger.info("Starting new Ollama process")
            self.ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.ollama_pid = self.ollama_process.pid
            self.is_external_process = False
            
            # Wait for Ollama to start (max 10 seconds)
            for _ in range(20):
                await asyncio.sleep(0.5)
                if self.is_ollama_responding():
                    logger.info(f"Ollama started successfully (PID: {self.ollama_pid})")
                    return True
                    
            # If we get here, Ollama failed to start
            logger.error("Ollama failed to start within 10 seconds")
            self.cleanup()
            return False
            
        except Exception as e:
            logger.error(f"Error ensuring Ollama is running: {e}")
            self.cleanup()
            return False
            
    def cleanup(self):
        """Clean up Ollama process if we started it."""
        try:
            if self.ollama_process and not self.is_external_process:
                logger.info(f"Terminating Ollama process (PID: {self.ollama_pid})")
                self.ollama_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.ollama_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Ollama process didn't terminate gracefully, forcing kill")
                    self.ollama_process.kill()
                    
            self.ollama_process = None
            self.ollama_pid = None
            self.is_external_process = False
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    async def load_model(self, model_name: str) -> bool:
        """Load a model into Ollama memory."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First check if model is already loaded by trying a simple request
                try:
                    test_response = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": model_name,
                            "messages": [{"role": "user", "content": "test"}],
                            "stream": False
                        },
                        timeout=5.0
                    )
                    if test_response.status_code == 200:
                        logger.info(f"Model {model_name} is already loaded")
                        return True
                except Exception:
                    pass
                
                # Model not loaded, pull it
                logger.info(f"Loading model {model_name}...")
                pull_response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    timeout=60.0
                )
                
                if pull_response.status_code == 200:
                    logger.info(f"Model {model_name} loaded successfully")
                    return True
                else:
                    logger.error(f"Failed to load model {model_name}: {pull_response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get current Ollama status."""
        # Check if Ollama is installed
        install_path = self.find_ollama_installation()
        installed = install_path is not None
        
        # Find Ollama process
        pid = self.find_ollama_process()
        
        result = {
            "installed": installed,
            "running": self.is_ollama_responding(),
            "pid": pid,
            "is_external": self.is_external_process,
            "port_in_use": self.is_port_in_use(11434)
        }
        
        if installed:
            result["location"] = install_path
            
        return result
    
    def stop_all_ollama_processes(self) -> dict:
        """Stop all Ollama processes running on the system."""
        stopped_processes = []
        errors = []
        
        try:
            # Find all processes with 'ollama' in the name
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    cmdline = proc_info.get('cmdline', [])
                    
                    # Check if it's an ollama process
                    is_ollama = 'ollama' in proc_name
                    
                    # Only check cmdline if it's not None and not empty
                    if cmdline and isinstance(cmdline, list):
                        is_ollama = is_ollama or any('ollama' in str(arg).lower() for arg in cmdline)
                    
                    if is_ollama:
                        pid = proc_info['pid']
                        logger.info(f"Found Ollama process: {proc_name} (PID: {pid})")
                        
                        try:
                            # Try graceful termination first
                            proc.terminate()
                            
                            # Wait for graceful shutdown
                            try:
                                proc.wait(timeout=3)
                                stopped_processes.append({
                                    'pid': pid,
                                    'name': proc_name,
                                    'method': 'terminate'
                                })
                                logger.info(f"Gracefully terminated Ollama process {pid}")
                            except psutil.TimeoutExpired:
                                # Force kill if it doesn't terminate gracefully
                                proc.kill()
                                stopped_processes.append({
                                    'pid': pid,
                                    'name': proc_name,
                                    'method': 'kill'
                                })
                                logger.info(f"Force killed Ollama process {pid}")
                                
                        except psutil.NoSuchProcess:
                            # Process already gone
                            stopped_processes.append({
                                'pid': pid,
                                'name': proc_name,
                                'method': 'already_terminated'
                            })
                        except psutil.AccessDenied:
                            errors.append(f"Access denied for process {pid} ({proc_name})")
                        except Exception as e:
                            errors.append(f"Error stopping process {pid}: {str(e)}")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process disappeared or we can't access it
                    continue
                except Exception as e:
                    errors.append(f"Error checking process: {str(e)}")
                    continue
            
            # Also clean up our own managed process
            if self.ollama_process and not self.is_external_process:
                try:
                    self.ollama_process.terminate()
                    self.ollama_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.ollama_process.kill()
                except Exception:
                    pass
                self.cleanup()
            
            return {
                "success": True,
                "stopped_processes": stopped_processes,
                "total_stopped": len(stopped_processes),
                "errors": errors,
                "message": f"Stopped {len(stopped_processes)} Ollama processes"
            }
            
        except Exception as e:
            logger.error(f"Error stopping Ollama processes: {e}")
            return {
                "success": False,
                "stopped_processes": stopped_processes,
                "total_stopped": len(stopped_processes),
                "errors": errors + [str(e)],
                "message": f"Error stopping processes: {str(e)}"
            }
    
    def start_ollama_windows(self) -> dict:
        """Start Ollama on Windows 10/11 with unlimited memory and terminal window."""
        try:
            
            # Check if Ollama is already running
            if self.is_ollama_responding():
                return {
                    "success": True,
                    "already_running": True,
                    "pid": self.find_ollama_process(),
                    "message": "Ollama is already running"
                }
            
            # Find Ollama executable
            ollama_path = shutil.which("ollama")
            if not ollama_path:
                return {
                    "success": False,
                    "error": "Ollama not found in PATH. Please install Ollama first.",
                    "message": "Ollama installation not found"
                }
            
            # Start Ollama process with unlimited memory configuration
            try:
                logger.info(f"Starting Ollama with unlimited memory: {ollama_path} serve")
                
                # Create a PowerShell command that sets unlimited memory and starts Ollama
                if os.name == 'nt':  # Windows
                    # Use PowerShell to set environment variables and start Ollama
                    powershell_cmd = f'''
                    Write-Host "=== RENDERSYNC OLLAMA MODULE ===" -ForegroundColor Green
                    Write-Host "Starting Ollama with unlimited memory" -ForegroundColor Yellow
                    Write-Host "Server will run until this window is closed" -ForegroundColor Cyan
                    Write-Host "=================================" -ForegroundColor Green
                    Write-Host ""
                    
                    # Set unlimited memory environment variables
                    $env:OLLAMA_NUM_CTX = "0"  # Unlimited context
                    $env:OLLAMA_NUM_THREAD = "0"  # Auto-detect threads
                    $env:OLLAMA_NUM_GPU = "0"  # Auto-detect GPU
                    $env:OLLAMA_MAX_LOADED_MODELS = "0"  # Unlimited models
                    $env:OLLAMA_MAX_QUEUE = "0"  # Unlimited queue
                    
                    # Start Ollama serve
                    & "{ollama_path}" serve
                    '''
                    
                    # Start PowerShell with the command
                    self.ollama_process = subprocess.Popen(
                        ["powershell", "-NoExit", "-Command", powershell_cmd],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:  # Linux/macOS
                    # Set environment variables and start Ollama
                    env = os.environ.copy()
                    env.update({
                        'OLLAMA_NUM_CTX': '0',  # Unlimited context
                        'OLLAMA_NUM_THREAD': '0',  # Auto-detect threads
                        'OLLAMA_NUM_GPU': '0',  # Auto-detect GPU
                        'OLLAMA_MAX_LOADED_MODELS': '0',  # Unlimited models
                        'OLLAMA_MAX_QUEUE': '0',  # Unlimited queue
                    })
                    
                    self.ollama_process = subprocess.Popen(
                        [ollama_path, "serve"],
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                
                self.ollama_pid = self.ollama_process.pid
                self.is_external_process = False
                
                logger.info(f"Started Ollama process with unlimited memory (PID: {self.ollama_pid})")
                
                return {
                    "success": True,
                    "already_running": False,
                    "pid": self.ollama_pid,
                    "path": ollama_path,
                    "method": "terminal",
                    "message": f"Ollama started with unlimited memory (PID: {self.ollama_pid})"
                }
                
            except Exception as e:
                logger.error(f"Error starting Ollama: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to start Ollama: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error in start_ollama_windows: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error starting Ollama: {str(e)}"
            }
    
    async def get_ollama_models(self) -> dict:
        """Get available Ollama models from the system - optimized for speed."""
        try:
            import subprocess
            import os
            
            # Fast check: Try API first with shorter timeout
            if self.is_ollama_responding():
                try:
                    import httpx
                    
                    async with httpx.AsyncClient(timeout=2.0) as client:  # Much shorter timeout
                        response = await client.get(f"{self.base_url}/api/tags")
                        if response.status_code == 200:
                            data = response.json()
                            models = data.get("models", [])
                            if models:
                                return {
                                    "success": True,
                                    "method": "api",
                                    "models": models,
                                    "total_models": len(models),
                                    "message": f"Found {len(models)} models via API"
                                }
                except Exception as e:
                    logger.warning(f"API method failed: {e}")
            
            # Fast fallback: Check models directory directly (much faster than ollama list)
            models_dir = os.path.expanduser("~/.ollama/models")
            if os.path.exists(models_dir):
                try:
                    models = []
                    for item in os.listdir(models_dir):
                        if os.path.isdir(os.path.join(models_dir, item)):
                            # Get model info from directory
                            model_name = item
                            model_path = os.path.join(models_dir, item)
                            
                            # Try to get size
                            try:
                                total_size = 0
                                for root, dirs, files in os.walk(model_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        total_size += os.path.getsize(file_path)
                                
                                # Convert to human readable
                                if total_size > 1024**3:
                                    size_str = f"{total_size / (1024**3):.1f} GB"
                                elif total_size > 1024**2:
                                    size_str = f"{total_size / (1024**2):.1f} MB"
                                else:
                                    size_str = f"{total_size / 1024:.1f} KB"
                            except:
                                size_str = "Unknown"
                            
                            models.append({
                                "name": model_name,
                                "size": size_str,
                                "id": "Unknown",
                                "modified_at": "Unknown"
                            })
                    
                    if models:
                        return {
                            "success": True,
                            "method": "directory_scan",
                            "models": models,
                            "total_models": len(models),
                            "message": f"Found {len(models)} models via directory scan"
                        }
                except Exception as e:
                    logger.warning(f"Directory scan failed: {e}")
            
            # Last resort: Use command line with shorter timeout
            ollama_path = shutil.which("ollama")
            if not ollama_path:
                return {
                    "success": False,
                    "error": "Ollama not found in PATH and no models directory found",
                    "message": "Cannot get models - Ollama not available"
                }
            
            try:
                # Run 'ollama list' command with shorter timeout
                result = subprocess.run(
                    [ollama_path, "list"],
                    capture_output=True,
                    text=True,
                    timeout=5  # Much shorter timeout
                )
                
                if result.returncode == 0:
                    models = []
                    lines = result.stdout.strip().split('\n')
                    
                    # Parse the output (skip header line)
                    for line in lines[1:]:
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 2:
                                model_name = parts[0]
                                model_size = parts[1] if len(parts) > 1 else "Unknown"
                                model_id = parts[2] if len(parts) > 2 else "Unknown"
                                
                                models.append({
                                    "name": model_name,
                                    "size": model_size,
                                    "id": model_id,
                                    "modified_at": parts[3] if len(parts) > 3 else "Unknown"
                                })
                    
                    return {
                        "success": True,
                        "method": "command_line",
                        "models": models,
                        "total_models": len(models),
                        "message": f"Found {len(models)} models via command line"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Command failed: {result.stderr}",
                        "message": "Failed to get models via command line"
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "Command timed out",
                    "message": "Command timed out while getting models"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Error running ollama list: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error in get_ollama_models: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error getting models: {str(e)}"
            }
    


# Convenience functions for easy access
def create_ollama_client(base_url: str = OLLAMA_BASE_URL) -> OllamaClient:
    """Create a new OllamaClient instance."""
    return OllamaClient(base_url)


def create_ollama_manager() -> OllamaManager:
    """Create a new OllamaManager instance."""
    return OllamaManager()


