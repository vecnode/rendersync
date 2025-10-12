import asyncio
import subprocess
import psutil
import socket
import json
import logging
import os
import shutil
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class ComfyUIManager:
    """Manager for ComfyUI process lifecycle and status management."""
    
    def __init__(self):
        self.comfyui_process: Optional[subprocess.Popen] = None
        self.comfyui_pid: Optional[int] = None
        self.is_external_process = False
        self.base_url = "http://127.0.0.1:8188"
        
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use by checking network connections."""
        try:
            # Get all network connections
            connections = psutil.net_connections(kind='tcp')
            
            # Check if any process is listening on the port
            for conn in connections:
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    logger.info(f"Port {port} is in use by PID {conn.pid}")
                    return True
                    
            return False
        except Exception as e:
            logger.warning(f"Error checking port {port}: {e}")
            # Fallback to socket binding method
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return False
            except OSError:
                return True
            
    def find_comfyui_process(self) -> Optional[int]:
        """Find existing ComfyUI process by checking for processes listening on port 8188 or ComfyUI.exe."""
        try:
            logger.info("Searching for ComfyUI processes")
            
            # First check for processes listening on port 8188
            connections = psutil.net_connections(kind='tcp')
            logger.info(f"Checking {len(connections)} network connections for port 8188")
            
            for conn in connections:
                if conn.laddr.port == 8188 and conn.status == 'LISTEN':
                    logger.info(f"Found process listening on port 8188: PID {conn.pid}")
                    return conn.pid
            
            # Also check for ComfyUI.exe processes directly
            logger.info("Checking all processes for ComfyUI")
            comfyui_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    name = proc_info['name'] or ''
                    exe = proc_info['exe'] or ''
                    
                    # Check if it's a ComfyUI process
                    if name and 'comfyui' in name.lower():
                        comfyui_processes.append(f"{name} (PID {proc_info['pid']})")
                        logger.info(f"Found ComfyUI process: {name} (PID {proc_info['pid']})")
                        return proc_info['pid']
                    
                    # Also check executable path
                    if exe and 'comfyui' in exe.lower():
                        comfyui_processes.append(f"{name} (PID {proc_info['pid']}) - {exe}")
                        logger.info(f"Found ComfyUI executable: {name} (PID {proc_info['pid']}) - {exe}")
                        return proc_info['pid']
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.warning(f"Error checking process: {e}")
                    continue
            
            logger.info(f"ComfyUI process search complete. Found {len(comfyui_processes)} potential matches: {comfyui_processes}")
                    
        except Exception as e:
            logger.warning(f"Error finding ComfyUI process: {e}")
            
        return None
        
    def is_comfyui_responding(self) -> bool:
        """Check if ComfyUI is responding on its API endpoint."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)  # Faster timeout
                result = s.connect_ex(('127.0.0.1', 8188))
                return result == 0
        except Exception:
            return False
            
    def find_comfyui_installation(self) -> Optional[str]:
        """Find ComfyUI installation directory."""
        try:
            # Common installation paths for current user
            possible_paths = [
                os.path.expanduser("~/ComfyUI"),
                os.path.expanduser("~/comfyui"),
                os.path.expanduser("~/Desktop/ComfyUI"),
                os.path.expanduser("~/Desktop/comfyui"),
                os.path.expanduser("~/Documents/ComfyUI"),
                os.path.expanduser("~/Documents/comfyui"),
                os.path.join(os.getcwd(), "ComfyUI"),
                os.path.join(os.getcwd(), "comfyui"),
            ]
            
            # Windows-specific: Check all user directories
            if os.name == 'nt':  # Windows
                try:
                    # Get all user directories from C:\Users
                    users_dir = "C:\\Users"
                    if os.path.exists(users_dir):
                        for user_name in os.listdir(users_dir):
                            user_path = os.path.join(users_dir, user_name)
                            if os.path.isdir(user_path):
                                # Add common ComfyUI locations for each user
                                user_comfyui_paths = [
                                    os.path.join(user_path, "ComfyUI"),
                                    os.path.join(user_path, "comfyui"),
                                    os.path.join(user_path, "Desktop", "ComfyUI"),
                                    os.path.join(user_path, "Desktop", "comfyui"),
                                    os.path.join(user_path, "Documents", "ComfyUI"),
                                    os.path.join(user_path, "Documents", "comfyui"),
                                    # AppData locations for installed ComfyUI
                                    os.path.join(user_path, "AppData", "Local", "Programs", "ComfyUI"),
                                    os.path.join(user_path, "AppData", "Local", "ComfyUI"),
                                    os.path.join(user_path, "AppData", "Roaming", "ComfyUI"),
                                ]
                                possible_paths.extend(user_comfyui_paths)
                except Exception as e:
                    logger.warning(f"Error scanning user directories: {e}")
            
            # Also check current directory and subdirectories
            current_dir = os.getcwd()
            try:
                for root, dirs, files in os.walk(current_dir):
                    for dir_name in dirs:
                        if dir_name.lower() in ['comfyui', 'comfy_ui']:
                            possible_paths.append(os.path.join(root, dir_name))
            except Exception as e:
                logger.warning(f"Error walking current directory: {e}")
            
            # Check each possible path
            for path in possible_paths:
                if os.path.exists(path):
                    # Check if it's a ComfyUI installation by looking for main.py OR ComfyUI.exe
                    main_py = os.path.join(path, "main.py")
                    comfyui_exe = os.path.join(path, "ComfyUI.exe")
                    
                    # Check for Python-based ComfyUI installation
                    if os.path.exists(main_py):
                        # Additional check: look for ComfyUI-specific files
                        comfyui_files = ["nodes.py", "web", "models"]
                        comfyui_found = any(os.path.exists(os.path.join(path, f)) for f in comfyui_files)
                        if comfyui_found:
                            logger.info(f"Found ComfyUI Python installation at: {path}")
                            return path
                    
                    # Check for executable-based ComfyUI installation
                    elif os.path.exists(comfyui_exe):
                        logger.info(f"Found ComfyUI executable installation at: {path}")
                        return path
                    
                    # Check for ComfyUI directory structure without main.py (portable/installed version)
                    elif any(os.path.exists(os.path.join(path, f)) for f in ["web", "models", "nodes"]):
                        logger.info(f"Found ComfyUI directory structure at: {path}")
                        return path
                            
        except Exception as e:
            logger.warning(f"Error finding ComfyUI installation: {e}")
            
        return None
        
    def get_comfyui_version(self, install_path: str) -> Optional[str]:
        """Get ComfyUI version from installation."""
        try:
            # Try to get version from main.py or other files
            main_py_path = os.path.join(install_path, "main.py")
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for version patterns
                    import re
                    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                    if version_match:
                        return version_match.group(1)
            
            # Try to get version from git if it's a git repository
            try:
                result = subprocess.run(
                    ["git", "describe", "--tags", "--always"],
                    cwd=install_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
                
            # Try to get version from requirements.txt or other files
            req_path = os.path.join(install_path, "requirements.txt")
            if os.path.exists(req_path):
                with open(req_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for ComfyUI version in requirements
                    import re
                    version_match = re.search(r'ComfyUI[>=]+([0-9.]+)', content, re.IGNORECASE)
                    if version_match:
                        return version_match.group(1)
                        
        except Exception as e:
            logger.warning(f"Error getting ComfyUI version: {e}")
            
        return None

    def get_comfyui_models_info(self, install_path: str) -> dict:
        """Get ComfyUI models and their folder paths."""
        try:
            models_info = {
                "models_found": False,
                "model_folders": [],
                "model_types": {}
            }
            
            if not install_path:
                return models_info
            
            # Common ComfyUI model directories
            model_dirs = [
                "models",
                "models/checkpoints",
                "models/loras", 
                "models/controlnet",
                "models/vae",
                "models/embeddings",
                "models/upscale_models",
                "models/clip_vision",
                "models/ipadapter",
                "models/unet",
                "models/diffusers",
                "models/animediff",
                "models/svd",
                "models/instantid",
                "models/face_restore",
                "models/segment_anything",
                "models/ultralytics",
                "models/rembg",
                "models/background_removal",
                "models/depth_anything",
                "models/midas",
                "models/lineart",
                "models/softedge",
                "models/openpose",
                "models/canny",
                "models/normal",
                "models/segmentation",
                "models/sketch",
                "models/scribble",
                "models/tile",
                "models/blur",
                "models/inpaint",
                "models/outpaint",
                "models/refiner",
                "models/style",
                "models/pose",
                "models/face",
                "models/hand",
                "models/body",
                "models/clothing",
                "models/accessories",
                "models/backgrounds",
                "models/environments",
                "models/characters",
                "models/objects",
                "models/textures",
                "models/materials",
                "models/lighting",
                "models/effects",
                "models/filters",
                "models/transitions",
                "models/animations",
                "models/videos",
                "models/audio",
                "models/data",
                "models/configs",
                "models/presets",
                "models/templates",
                "models/examples",
                "models/samples",
                "models/test",
                "models/temp",
                "models/cache",
                "models/logs",
                "models/backup",
                "models/archive"
            ]
            
            # Check each model directory
            for model_dir in model_dirs:
                full_path = os.path.join(install_path, model_dir)
                if os.path.exists(full_path):
                    try:
                        # Count files in directory
                        files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
                        if files:
                            models_info["model_folders"].append({
                                "path": full_path,
                                "name": model_dir,
                                "file_count": len(files),
                                "files": files[:5]  # First 5 files as examples
                            })
                            
                            # Categorize by model type
                            if "checkpoints" in model_dir.lower():
                                models_info["model_types"]["Checkpoints"] = full_path
                            elif "lora" in model_dir.lower():
                                models_info["model_types"]["LoRAs"] = full_path
                            elif "controlnet" in model_dir.lower():
                                models_info["model_types"]["ControlNet"] = full_path
                            elif "vae" in model_dir.lower():
                                models_info["model_types"]["VAE"] = full_path
                            elif "embeddings" in model_dir.lower():
                                models_info["model_types"]["Embeddings"] = full_path
                            elif "upscale" in model_dir.lower():
                                models_info["model_types"]["Upscale"] = full_path
                            elif "clip" in model_dir.lower():
                                models_info["model_types"]["CLIP"] = full_path
                            elif "ipadapter" in model_dir.lower():
                                models_info["model_types"]["IP-Adapter"] = full_path
                            elif "unet" in model_dir.lower():
                                models_info["model_types"]["UNet"] = full_path
                            elif "diffusers" in model_dir.lower():
                                models_info["model_types"]["Diffusers"] = full_path
                            elif "animediff" in model_dir.lower():
                                models_info["model_types"]["AnimeDiff"] = full_path
                            elif "svd" in model_dir.lower():
                                models_info["model_types"]["SVD"] = full_path
                            elif "instantid" in model_dir.lower():
                                models_info["model_types"]["InstantID"] = full_path
                            elif "face" in model_dir.lower():
                                models_info["model_types"]["Face"] = full_path
                            elif "pose" in model_dir.lower():
                                models_info["model_types"]["Pose"] = full_path
                            elif "depth" in model_dir.lower():
                                models_info["model_types"]["Depth"] = full_path
                            elif "normal" in model_dir.lower():
                                models_info["model_types"]["Normal"] = full_path
                            elif "segmentation" in model_dir.lower():
                                models_info["model_types"]["Segmentation"] = full_path
                            elif "sketch" in model_dir.lower():
                                models_info["model_types"]["Sketch"] = full_path
                            elif "canny" in model_dir.lower():
                                models_info["model_types"]["Canny"] = full_path
                            elif "lineart" in model_dir.lower():
                                models_info["model_types"]["LineArt"] = full_path
                            elif "softedge" in model_dir.lower():
                                models_info["model_types"]["SoftEdge"] = full_path
                            elif "openpose" in model_dir.lower():
                                models_info["model_types"]["OpenPose"] = full_path
                            elif "inpaint" in model_dir.lower():
                                models_info["model_types"]["Inpaint"] = full_path
                            elif "outpaint" in model_dir.lower():
                                models_info["model_types"]["Outpaint"] = full_path
                            elif "refiner" in model_dir.lower():
                                models_info["model_types"]["Refiner"] = full_path
                            elif "style" in model_dir.lower():
                                models_info["model_types"]["Style"] = full_path
                            elif "hand" in model_dir.lower():
                                models_info["model_types"]["Hand"] = full_path
                            elif "body" in model_dir.lower():
                                models_info["model_types"]["Body"] = full_path
                            elif "clothing" in model_dir.lower():
                                models_info["model_types"]["Clothing"] = full_path
                            elif "accessories" in model_dir.lower():
                                models_info["model_types"]["Accessories"] = full_path
                            elif "backgrounds" in model_dir.lower():
                                models_info["model_types"]["Backgrounds"] = full_path
                            elif "environments" in model_dir.lower():
                                models_info["model_types"]["Environments"] = full_path
                            elif "characters" in model_dir.lower():
                                models_info["model_types"]["Characters"] = full_path
                            elif "objects" in model_dir.lower():
                                models_info["model_types"]["Objects"] = full_path
                            elif "textures" in model_dir.lower():
                                models_info["model_types"]["Textures"] = full_path
                            elif "materials" in model_dir.lower():
                                models_info["model_types"]["Materials"] = full_path
                            elif "lighting" in model_dir.lower():
                                models_info["model_types"]["Lighting"] = full_path
                            elif "effects" in model_dir.lower():
                                models_info["model_types"]["Effects"] = full_path
                            elif "filters" in model_dir.lower():
                                models_info["model_types"]["Filters"] = full_path
                            elif "transitions" in model_dir.lower():
                                models_info["model_types"]["Transitions"] = full_path
                            elif "animations" in model_dir.lower():
                                models_info["model_types"]["Animations"] = full_path
                            elif "videos" in model_dir.lower():
                                models_info["model_types"]["Videos"] = full_path
                            elif "audio" in model_dir.lower():
                                models_info["model_types"]["Audio"] = full_path
                            elif "data" in model_dir.lower():
                                models_info["model_types"]["Data"] = full_path
                            elif "configs" in model_dir.lower():
                                models_info["model_types"]["Configs"] = full_path
                            elif "presets" in model_dir.lower():
                                models_info["model_types"]["Presets"] = full_path
                            elif "templates" in model_dir.lower():
                                models_info["model_types"]["Templates"] = full_path
                            elif "examples" in model_dir.lower():
                                models_info["model_types"]["Examples"] = full_path
                            elif "samples" in model_dir.lower():
                                models_info["model_types"]["Samples"] = full_path
                            elif "test" in model_dir.lower():
                                models_info["model_types"]["Test"] = full_path
                            elif "temp" in model_dir.lower():
                                models_info["model_types"]["Temp"] = full_path
                            elif "cache" in model_dir.lower():
                                models_info["model_types"]["Cache"] = full_path
                            elif "logs" in model_dir.lower():
                                models_info["model_types"]["Logs"] = full_path
                            elif "backup" in model_dir.lower():
                                models_info["model_types"]["Backup"] = full_path
                            elif "archive" in model_dir.lower():
                                models_info["model_types"]["Archive"] = full_path
                            else:
                                models_info["model_types"]["Other"] = full_path
                                
                    except Exception as e:
                        logger.warning(f"Error reading model directory {full_path}: {e}")
                        continue
            
            models_info["models_found"] = len(models_info["model_folders"]) > 0
            return models_info
            
        except Exception as e:
            logger.error(f"Error getting ComfyUI models info: {e}")
            return {
                "models_found": False,
                "model_folders": [],
                "model_types": {},
                "error": str(e)
            }

    def get_status(self) -> dict:
        """Get current ComfyUI status."""
        try:
            # Check if ComfyUI is installed
            install_path = self.find_comfyui_installation()
            installed = install_path is not None
            
            # Find ComfyUI process first (most reliable indicator)
            pid = self.find_comfyui_process()
            
            # Check if ComfyUI is running based on process detection
            running = pid is not None
            
            # Check port status
            port_8188 = self.is_port_in_use(8188)
            
            # If we found a process but port 8188 is not in use, check other common ports
            if running and not port_8188:
                # Check other common ComfyUI ports
                for port in [8189, 8190, 8080, 8000]:
                    if self.is_port_in_use(port):
                        logger.info(f"ComfyUI found running on port {port} instead of 8188")
                        port_8188 = True
                        break
            
            result = {
                "installed": installed,
                "running": running,
                "pid": pid,
                "port_8188": port_8188,
                "is_external": False
            }
            
            if installed:
                result["location"] = install_path
                version = self.get_comfyui_version(install_path)
                if version:
                    result["version"] = version
                
                # Get models information
                models_info = self.get_comfyui_models_info(install_path)
                if models_info["models_found"]:
                    result["models_found"] = True
                    result["model_folders"] = models_info["model_folders"]
                    result["model_types"] = models_info["model_types"]
                else:
                    result["models_found"] = False
                    if "error" in models_info:
                        result["models_error"] = models_info["error"]
            
            # If running, try to get API status
            if running:
                try:
                    # Try a simple API call to check if it's responding
                    import httpx
                    import asyncio
                    
                    async def check_api():
                        try:
                            async with httpx.AsyncClient(timeout=2.0) as client:
                                response = await client.get(f"{self.base_url}/system_stats")
                                return response.status_code == 200
                        except Exception:
                            return False
                    
                    # Check if there's already an event loop running
                    try:
                        loop = asyncio.get_running_loop()
                        # If we're in an async context, we can't use run_until_complete
                        # Just skip the API check to avoid the error
                        result["api_responding"] = None
                        result["api_error"] = "Cannot check API status in async context"
                    except RuntimeError:
                        # No event loop running, safe to create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            api_responding = loop.run_until_complete(check_api())
                            result["api_responding"] = api_responding
                        finally:
                            loop.close()
                        
                except Exception as e:
                    result["api_responding"] = False
                    result["api_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting ComfyUI status: {e}")
            return {
                "installed": False,
                "running": False,
                "pid": None,
                "port_8188": False,
                "error": str(e)
            }
    
    def stop_all_comfyui_processes(self) -> dict:
        """Stop all ComfyUI processes running on the system."""
        stopped_processes = []
        errors = []
        
        try:
            # Find all processes with 'comfyui' in the name
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    cmdline = proc_info.get('cmdline', [])
                    
                    # Check if it's a ComfyUI process
                    is_comfyui = 'comfyui' in proc_name
                    
                    # Only check cmdline if it's not None and not empty
                    if cmdline and isinstance(cmdline, list):
                        is_comfyui = is_comfyui or any('comfyui' in str(arg).lower() for arg in cmdline)
                    
                    if is_comfyui:
                        pid = proc_info['pid']
                        logger.info(f"Found ComfyUI process: {proc_name} (PID: {pid})")
                        
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
                                logger.info(f"Gracefully terminated ComfyUI process {pid}")
                            except psutil.TimeoutExpired:
                                # Force kill if it doesn't terminate gracefully
                                proc.kill()
                                stopped_processes.append({
                                    'pid': pid,
                                    'name': proc_name,
                                    'method': 'kill'
                                })
                                logger.info(f"Force killed ComfyUI process {pid}")
                                
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
            
            return {
                "success": True,
                "stopped_processes": stopped_processes,
                "total_stopped": len(stopped_processes),
                "errors": errors,
                "message": f"Stopped {len(stopped_processes)} ComfyUI processes"
            }
            
        except Exception as e:
            logger.error(f"Error stopping ComfyUI processes: {e}")
            return {
                "success": False,
                "stopped_processes": stopped_processes,
                "total_stopped": len(stopped_processes),
                "errors": errors + [str(e)],
                "message": f"Error stopping processes: {str(e)}"
            }
    
    def find_comfyui_executable(self) -> Optional[str]:
        """Find ComfyUI executable specifically for starting the application."""
        try:
            # First check if ComfyUI is already running and get its executable path
            pid = self.find_comfyui_process()
            if pid:
                try:
                    proc = psutil.Process(pid)
                    exe_path = proc.exe()
                    if exe_path and 'comfyui' in exe_path.lower():
                        logger.info(f"Found running ComfyUI executable: {exe_path}")
                        return exe_path
                except Exception as e:
                    logger.warning(f"Error getting executable path for PID {pid}: {e}")
            
            # Check common Windows installation paths for ComfyUI.exe
            possible_exe_paths = []
            
            # Windows-specific: Check all user directories for ComfyUI.exe
            if os.name == 'nt':  # Windows
                try:
                    # Get all user directories from C:\Users
                    users_dir = "C:\\Users"
                    if os.path.exists(users_dir):
                        for user_name in os.listdir(users_dir):
                            user_path = os.path.join(users_dir, user_name)
                            if os.path.isdir(user_path):
                                # Add common ComfyUI executable locations for each user
                                user_exe_paths = [
                                    os.path.join(user_path, "AppData", "Local", "Programs", "ComfyUI", "ComfyUI.exe"),
                                    os.path.join(user_path, "AppData", "Local", "ComfyUI", "ComfyUI.exe"),
                                    os.path.join(user_path, "AppData", "Roaming", "ComfyUI", "ComfyUI.exe"),
                                    os.path.join(user_path, "ComfyUI", "ComfyUI.exe"),
                                    os.path.join(user_path, "comfyui", "ComfyUI.exe"),
                                    os.path.join(user_path, "Desktop", "ComfyUI", "ComfyUI.exe"),
                                    os.path.join(user_path, "Desktop", "comfyui", "ComfyUI.exe"),
                                    os.path.join(user_path, "Documents", "ComfyUI", "ComfyUI.exe"),
                                    os.path.join(user_path, "Documents", "comfyui", "ComfyUI.exe"),
                                ]
                                possible_exe_paths.extend(user_exe_paths)
                except Exception as e:
                    logger.warning(f"Error scanning user directories for executable: {e}")
            
            # Check each possible executable path
            for exe_path in possible_exe_paths:
                if os.path.exists(exe_path):
                    logger.info(f"Found ComfyUI executable: {exe_path}")
                    return exe_path
            
            # Also check current directory and subdirectories
            current_dir = os.getcwd()
            try:
                for root, dirs, files in os.walk(current_dir):
                    for file in files:
                        if file.lower() == 'comfyui.exe':
                            exe_path = os.path.join(root, file)
                            logger.info(f"Found ComfyUI executable in current directory: {exe_path}")
                            return exe_path
            except Exception as e:
                logger.warning(f"Error walking current directory for executable: {e}")
            
            logger.warning("No ComfyUI executable found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding ComfyUI executable: {e}")
            return None

    def start_comfyui_windows(self) -> dict:
        """Start ComfyUI on Windows."""
        try:
            # Check if ComfyUI is already running
            existing_pid = self.find_comfyui_process()
            if existing_pid:
                return {
                    "success": True,
                    "already_running": True,
                    "pid": existing_pid,
                    "message": "ComfyUI is already running"
                }
            
            # Find ComfyUI executable
            comfyui_exe = self.find_comfyui_executable()
            if not comfyui_exe:
                return {
                    "success": False,
                    "error": "ComfyUI executable not found. Please install ComfyUI first.",
                    "message": "ComfyUI executable not found"
                }
            
            # Start ComfyUI executable
            try:
                logger.info(f"Starting ComfyUI executable: {comfyui_exe}")
                
                if os.name == 'nt':  # Windows
                    # Create a PowerShell command that starts ComfyUI in a new window
                    powershell_cmd = f'''
                    Write-Host "=== RENDERSYNC COMFYUI MODULE ===" -ForegroundColor Green
                    Write-Host "Starting ComfyUI with full functionality" -ForegroundColor Yellow
                    Write-Host "ComfyUI will run until this window is closed" -ForegroundColor Cyan
                    Write-Host "Web interface: http://127.0.0.1:8000" -ForegroundColor Magenta
                    Write-Host "=================================" -ForegroundColor Green
                    Write-Host ""
                    
                    # Start ComfyUI executable
                    & "{comfyui_exe}"
                    '''
                    
                    # Start PowerShell with the command
                    self.comfyui_process = subprocess.Popen(
                        ["powershell", "-NoExit", "-Command", powershell_cmd],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:  # Linux/macOS
                    self.comfyui_process = subprocess.Popen(
                        [comfyui_exe],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                
                self.comfyui_pid = self.comfyui_process.pid
                self.is_external_process = False
                
                logger.info(f"Started ComfyUI executable (PID: {self.comfyui_pid})")
                
                return {
                    "success": True,
                    "already_running": False,
                    "pid": self.comfyui_pid,
                    "path": comfyui_exe,
                    "method": "executable",
                    "message": f"ComfyUI started successfully (PID: {self.comfyui_pid})"
                }
                
            except Exception as e:
                logger.error(f"Error starting ComfyUI executable: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to start ComfyUI executable: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error in start_comfyui_windows: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error starting ComfyUI: {str(e)}"
            }


# Convenience functions for easy access
def create_comfyui_manager() -> ComfyUIManager:
    """Create a new ComfyUIManager instance."""
    return ComfyUIManager()
