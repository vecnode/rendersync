# ============================================================================
# RENDERSYNC CORE SERVER
# ============================================================================
# Main FastAPI application for management

# ============================================================================
# CORE IMPORTS
# ============================================================================
import subprocess  
import sys         
import os          
import socket      
import psutil      
import json        

# FastAPI framework imports for web API functionality
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ============================================================================
# MODULE IMPORTS
# ============================================================================
from .modules.system import get_system_info_data, inspect_pid_data, ping_ip_data, ping_multiple_ips_data
from .modules.network import get_network_info_data
from .modules.network import inspect_port

# Utility modules for process management and system operations
from .modules.utilities import track_spawned_process, check_application_timeout, cleanup_processes, get_application_status, get_terminal_info, get_apps_running_info

# AI service integration modules
from .modules.ollama import OllamaManager, OllamaClient
from .modules.comfyui import ComfyUIManager

from .comfy_api import ComfyUIClient, load_workflow_from_file
from .config import OLLAMA_BASE_URL


# ================================================================================
# RENDERSYNC API ENDPOINTS DOCUMENTATION
# ================================================================================
# Complete API endpoint reference organized by functionality




# ============================================================================
# PYDANTIC DATA MODELS
# ============================================================================
# Request validation models for API endpoints

class PortInspectionRequest(BaseModel):
    port: int  # Port number to inspect

class PIDInspectionRequest(BaseModel):
    pid: str  # Process ID to inspect

class PingRequest(BaseModel):
    target: str      # Target IP address or hostname
    port: int = None  # Optional port for TCP ping
    timeout: int = 3  # Timeout in seconds

class MultiPingRequest(BaseModel):
    targets: list    # List of target IPs/hostnames
    port: int = None  # Optional port for TCP ping
    timeout: int = 2  # Timeout in seconds


# ============================================================================
# PORT MANAGEMENT SYSTEM
# ============================================================================

RENDERSYNC_PORTS = [
    8080,   
    8000,   
    8081,   
    8082,   
    3000,   
    5000,   
    9000,   
    8888,   
    8001,   
    8083,   
    7000,   
]

DEFAULT_PORT = 8080


def find_available_port(start_port=None):
    """Find the best available port."""
    if start_port is None:
        start_port = DEFAULT_PORT
    
    # Check if start_port is in our preferred list
    if start_port in RENDERSYNC_PORTS:
        ports_to_try = [start_port] + [p for p in RENDERSYNC_PORTS if p != start_port]
    else:
        ports_to_try = [start_port] + RENDERSYNC_PORTS
    
    for port in ports_to_try:
        if is_port_available(port):
            print(f"\033[92mPORTMANAGER\033[0m Selected port {port}")
            return port
    
    # Fallback: find any available port in the professional range
    for port in range(8000, 9000):
        if is_port_available(port):
            print(f"\033[92mPORTMANAGER\033[0m Fallback: Using port {port}")
            return port
    
    raise RuntimeError("No available ports found in range 8000-8999")


def is_port_available(port):
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # 1 second timeout for quick checking
            result = s.bind(('', port))
            return True
    except (OSError, socket.error):
        return False


def kill_processes_on_port(port):
    """Kill all processes using the specified port."""
    killed_count = 0
    
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Check if process has connections on our port
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"\033[92mPORTMANAGER\033[0m Killing process {proc.name()} (PID: {proc.pid}) using port {port}")
                        
                        # Try graceful termination first
                        proc.terminate()
                        
                        # Force kill if still running (no delay needed)
                        if proc.is_running():
                            proc.kill()
                        
                        killed_count += 1
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        print(f"\033[92mPORTMANAGER\033[0m Error killing processes on port {port}: {e}")
    
    if killed_count > 0:
        print(f"\033[92mPORTMANAGER\033[0m Killed {killed_count} processes using port {port}")
        # No delay needed - processes terminate immediately
    
    return killed_count


def secure_port_for_render_farm(port=None):
    """Secure a port for render farm operations by killing conflicting processes."""
    if port is None:
        port = find_available_port()
    
    print(f"\033[92mPORTMANAGER\033[0m Securing port {port} for render farm operations")
    
    # Kill any processes using this port
    killed = kill_processes_on_port(port)
    
    # Verify port is now available
    if is_port_available(port):
        print(f"\033[92mPORTMANAGER\033[0m Port {port} secured successfully")
        return port
    else:
        print(f"\033[92mPORTMANAGER\033[0m Port {port} still in use, trying next available port")
        return find_available_port(port + 1)


def get_port_info():
    """Get information about port usage and availability."""
    info = {
        'preferred_ports': RENDERSYNC_PORTS,
        'default_port': DEFAULT_PORT,
        'port_usage': {}
    }
    
    # Check usage of preferred ports
    for port in RENDERSYNC_PORTS[:5]:  # Check first 5 ports
        info['port_usage'][port] = {
            'available': is_port_available(port),
            'processes': []
        }
        
        # Find processes using this port
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    connections = proc.connections()
                    for conn in connections:
                        if conn.laddr.port == port:
                            info['port_usage'][port]['processes'].append({
                                'pid': proc.pid,
                                'name': proc.name()
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
    
    return info


# ============================================================================
# CONNECTION TRACKING AND CONTROL
# ============================================================================
# Global Browser connection tracking and access control

active_connections = {}
connection_access_enabled = True  # Global flag to control external connections

# Initialize application directories by discovering installations
def discover_app_directories():
    """Discover and return application installation directories."""
    ollama_path = None
    comfyui_path = None
    
    # Discover Ollama installation
    try:
        ollama_manager = OllamaManager()
        ollama_path = ollama_manager.find_ollama_installation()
    except Exception as e:
        print(f"\033[93mError discovering Ollama: {e}\033[0m")
    
    # Discover ComfyUI installation
    try:
        comfyui_manager = ComfyUIManager()
        comfyui_path = comfyui_manager.find_comfyui_installation()
    except Exception as e:
        print(f"\033[93mError discovering ComfyUI: {e}\033[0m")
    
    return ollama_path, comfyui_path


ollama_app_directory, comfyui_app_directory = discover_app_directories()



# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="rendersync core", version="0.1.0")

# ============================================================================
# CONNECTION CONTROL HELPER
# ============================================================================
# 
# ENDPOINT CATEGORIZATION:
# 
# @private_endpoint - Internal rendersync endpoints (always accessible from localhost)
#   - /api/connection-control (enable/disable external access)
#   - /api/connection-status (check current status)
#   - /api/shutdown (terminate server)
#   - Static files and web interface
#
# @public_endpoint - External API endpoints (controlled by connection_access_enabled)
#   - /api/process-status (system information)
#   - /api/inspect-port (port inspection)
#   - /api/ping-ip (network testing)
#   - Any endpoint meant for external applications
#
# USAGE:
#   - Private endpoints: Always work, even when external connections disabled
#   - Public endpoints: Blocked for external IPs when connection_access_enabled = False
#   - Localhost: Always allowed for both types
#
# ============================================================================

def check_connection_access(request: Request):
    """Check if external connections are allowed. Always allow localhost."""
    client_ip = request.client.host if request.client else "unknown"
    
    # Always allow localhost for management
    if client_ip in ["127.0.0.1", "::1", "localhost"]:
        return True
    
    # Check if external connections are enabled
    return connection_access_enabled

def require_connection_access(func):
    """Decorator to check connection access for endpoints."""
    async def wrapper(*args, **kwargs):
        # Find the Request object in the arguments
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if request and not check_connection_access(request):
            raise HTTPException(status_code=403, detail="External connections disabled")
        
        return await func(*args, **kwargs)
    return wrapper

def public_endpoint(func):
    """Decorator for public endpoints that should be controlled by connection_access_enabled."""
    async def wrapper(*args, **kwargs):
        # Find the Request object in the arguments
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        # If no Request found in args, try to get it from kwargs
        if not request:
            request = kwargs.get('request')
        
        if request and not check_connection_access(request):
            raise HTTPException(status_code=403, detail="External connections disabled")
        
        return await func(*args, **kwargs)
    return wrapper

def private_endpoint(func):
    """Decorator for private endpoints that are only for internal rendersync use."""
    # Private endpoints don't need connection checks - they're internal only
    return func

# ============================================================================
# MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================================
# SERVER LIFECYCLE EVENTS
# ============================================================================


@app.on_event("startup")
async def _startup() -> None:
    # Server startup: secures port, checks timeout, initializes render farm operations
    print("rendersync server starting")
    
    # Display discovered application installations
    global ollama_app_directory, comfyui_app_directory
    
    print("\033[96mApplication installations discovered:\033[0m")
    
    if ollama_app_directory:
        print(f"\033[92mOllama found at: {ollama_app_directory}\033[0m")
    else:
        print("\033[91mOllama installation not found\033[0m")
    
    if comfyui_app_directory:
        print(f"\033[92mComfyUI found at: {comfyui_app_directory}\033[0m")
    else:
        print("\033[91mComfyUI installation not found\033[0m")
    
    # Secure port for render farm operations
    try:
        secured_port = secure_port_for_render_farm()
        print(f"\033[92mPORTMANAGER\033[0m Rendersync server secured on port {secured_port}")
    except Exception as e:
        print(f"\033[92mPORTMANAGER\033[0m Failed to secure port: {e}")
        print(f"\033[92mPORTMANAGER\033[0m Continuing with default port")
    
    # Check for timeout on startup
    if check_application_timeout():
        print("Server startup terminated due to timeout")
        return

@app.on_event("shutdown")
async def _shutdown() -> None:
    # Server shutdown: cleans up processes, terminates gracefully
    print("rendersync server shutting down")
    cleanup_processes()


# ============================================================================
# CORE APPLICATION ENDPOINTS
# ============================================================================

@app.get("/")
@private_endpoint
async def root(request: Request):
    # Main page: serves index.html from static directory, fallback to API info
    """Serve the main HTML page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": "rendersync", "docs": "/docs"}

@app.get("/favicon.ico")
@private_endpoint
async def favicon(request: Request):
    # Favicon: returns empty response to prevent 404 errors
    """Serve favicon to prevent 404 errors."""
    return Response(content="", media_type="image/x-icon")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
@private_endpoint
async def chrome_devtools(request: Request):
    # Chrome DevTools: returns metadata for Chrome developer tools integration
    """Handle Chrome DevTools metadata request."""
    return {"version": "1.0", "name": "rendersync"}


# ============================================================================
# SYSTEM INFORMATION ENDPOINTS
# ============================================================================

@app.get("/api/system-info")
@private_endpoint
async def system_info():
    # System info: no input, returns complete system specifications and hardware data
    """Get system information."""
    return get_system_info_data()

@app.get("/api/network-info")
@private_endpoint
async def network_info():
    # Network info: no input, returns network interfaces, IPs and connectivity data
    """Get network information."""
    return get_network_info_data()

@app.get("/api/terminal-info")
@private_endpoint
async def terminal_info():
    # Terminal info: no input, returns active terminal sessions and shell information
    """Get terminal information."""
    return get_terminal_info()





# ============================================================================
# NETWORK AND INSPECTION ENDPOINTS
# ============================================================================

@app.get("/health")
@private_endpoint
async def health():
    # Health check: no input, returns simple status confirmation
    """Simple health check endpoint."""
    return {"status": "ok", "service": "rendersync"}

@app.get("/api/server-info")
@private_endpoint
async def server_info():
    # Server info: no input, returns server details and network accessibility
    """Get server information and network details."""
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    port_info = get_port_info()
    
    return {
        "status": "running",
        "service": "rendersync",
        "hostname": hostname,
        "local_ip": local_ip,
        "port_info": port_info,
        "accessible_from_network": connection_access_enabled,
        "cors_enabled": True,
        "connection_status": "enabled" if connection_access_enabled else "disabled"
    }

@app.post("/api/shutdown")
@private_endpoint
async def shutdown_server():
    """Shutdown the rendersync server."""
    try:
        # Schedule shutdown after response is sent
        import asyncio
        asyncio.create_task(delayed_shutdown())
        
        return {
            "success": True,
            "message": "Server shutdown initiated",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shutdown failed: {str(e)}")

async def delayed_shutdown():
    """Delayed shutdown to allow response to be sent."""
    await asyncio.sleep(1)  # Give time for response to be sent
    print("\033[91mShutting down rendersync server...\033[0m")
    import os
    os._exit(0)  # Force exit the process
@app.post("/api/connection-control")
@private_endpoint
async def connection_control(request: dict):
    # Connection control: takes action (enable/disable), controls external connection access
    """Enable or disable external connections to the server."""
    global connection_access_enabled
    
    try:
        action = request.get("action", "").strip().lower()
        
        if action == "enable":
            connection_access_enabled = True
            status = "enabled"
            message = "External connections enabled"
        elif action == "disable":
            connection_access_enabled = False
            status = "disabled"
            message = "External connections disabled"
        else:
            raise HTTPException(status_code=400, detail="Action must be 'enable' or 'disable'")
        
        return {
            "success": True,
            "action": action,
            "status": status,
            "message": message,
            "connection_access_enabled": connection_access_enabled,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection control failed: {str(e)}")

@app.get("/api/connection-status")
@private_endpoint
async def connection_status():
    # Connection status: no input, returns current connection control status
    """Get current connection control status."""
    return {
        "connection_access_enabled": connection_access_enabled,
        "status": "enabled" if connection_access_enabled else "disabled",
        "active_connections_count": len(active_connections),
        "message": "External connections allowed" if connection_access_enabled else "External connections blocked"
    }




@app.get("/api/process-status")
@public_endpoint
async def process_status(request: Request):
    # Process status: no input, returns process management status and tracked processes
    """Get process management status."""
    return get_application_status()


@app.get("/api/port-info")
@private_endpoint
async def port_info(request: Request):
    # Port info: no input, returns port management information and availability
    """Get port management information."""
    return get_port_info()


@app.post("/api/inspect-port")
@private_endpoint
async def inspect_port_endpoint(request: PortInspectionRequest, http_request: Request):
    # Port inspection: takes port number, returns detailed port status and bound processes
    """Inspect a specific port and return detailed information."""
    try:
        result = inspect_port(request.port)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Port inspection failed: {str(e)}")


@app.post("/api/inspect-pid")
@private_endpoint
async def inspect_pid_endpoint(request: PIDInspectionRequest):
    # PID inspection: takes process ID, returns detailed process information and resource usage
    """Inspect a specific PID and return detailed process information."""
    try:
        result = inspect_pid_data(request.pid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PID inspection failed: {str(e)}")


@app.post("/api/ping-ip")
@private_endpoint
async def ping_ip_endpoint(request: PingRequest, http_request: Request):
    # Single ping: takes target IP/hostname and optional port, returns connectivity test results
    """Ping an IP address or hostname and optionally check a specific port."""
    
    # Check connection access
    if not check_connection_access(http_request):
        raise HTTPException(status_code=403, detail="External connections disabled")
    
    try:
        result = ping_ip_data(request.target, request.port, request.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping failed: {str(e)}")


@app.post("/api/ping-multiple")
@private_endpoint
async def ping_multiple_endpoint(request: MultiPingRequest):
    # Multi ping: takes list of targets and optional port, returns parallel connectivity test results
    """Ping multiple IPs sequentially for network scanning."""
    try:
        result = ping_multiple_ips_data(request.targets, request.port, request.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-ping failed: {str(e)}")


# ============================================================================
# OLLAMA AI SERVICE ENDPOINTS
# ============================================================================

@app.get("/api/ollama-status")
@private_endpoint
async def ollama_status():
    # Ollama status: no input, returns installation status, version, running state and API health
    """Get Ollama installation and running status."""
    try:
        import shutil
        import subprocess
        import os
        
        result = {
            "installed": False,
            "location": None,
            "version": None,
            "running": False,
            "pid": None,
            "port_11434": False,
            "error": None
        }
        
        # Check if ollama is installed
        ollama_path = shutil.which("ollama")
        if ollama_path:
            result["installed"] = True
            result["location"] = ollama_path
            
            # Get version
            try:
                version_output = subprocess.run(["ollama", "version"], 
                                              capture_output=True, text=True, timeout=5)
                if version_output.returncode == 0:
                    result["version"] = version_output.stdout.strip()
            except Exception as e:
                result["version"] = f"Error getting version: {str(e)}"
        
        # Check if Ollama is running
        manager = OllamaManager()
        status = manager.get_status()
        result["running"] = status["running"]
        result["pid"] = status["pid"]
        result["port_11434"] = status["port_in_use"]
        
        # If running, try to get more details
        if result["running"]:
            try:
                client = OllamaClient(OLLAMA_BASE_URL)
                health = await client.health()
                result["api_responding"] = health
            except Exception as e:
                result["api_responding"] = False
                result["api_error"] = str(e)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama inspection failed: {str(e)}")


@app.post("/api/ollama-stop")
@private_endpoint
async def ollama_stop():
    # Ollama stop: no input, terminates all Ollama processes and returns termination results
    """Stop all Ollama processes running on the system."""
    try:
        manager = OllamaManager()
        result = manager.stop_all_ollama_processes()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop Ollama processes: {str(e)}")


@app.post("/api/ollama-start")
@private_endpoint
async def ollama_start():
    # Ollama start: no input, launches Ollama service on Windows and returns startup results
    """Start Ollama on Windows 10/11 as if double-clicked by user."""
    try:
        manager = OllamaManager()
        result = manager.start_ollama_windows()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Ollama: {str(e)}")


@app.get("/api/ollama-models")
@private_endpoint
async def ollama_models():
    # Ollama models: no input, returns list of available language models and their status
    """Get available Ollama models."""
    try:
        manager = OllamaManager()
        result = await manager.get_ollama_models()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Ollama models: {str(e)}")


# ============================================================================
# CONNECTION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/connections")
@private_endpoint
async def register_connection(request: dict):
    """Register a new browser connection."""
    try:
        connection_id = request.get("connectionId")
        ip = request.get("ip")
        browser = request.get("browser")
        os = request.get("os")
        timestamp = request.get("timestamp")
        user_agent = request.get("userAgent")
        screen_resolution = request.get("screenResolution")
        language = request.get("language")
        machine_type = request.get("machineType")
        
        if not all([connection_id, ip, browser, os]):
            raise HTTPException(status_code=400, detail="Missing required connection data")
        
        # Store connection globally with all details
        active_connections[connection_id] = {
            "ip": ip,
            "browser": browser,
            "os": os,
            "timestamp": timestamp,
            "userAgent": user_agent,
            "screenResolution": screen_resolution,
            "language": language,
            "machineType": machine_type,
            "status": "active"
        }
        
        return {"success": True, "message": f"Connection {connection_id} registered"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register connection: {str(e)}")

@app.get("/api/connections")
@private_endpoint
async def get_connections():
    """Get all active connections."""
    try:
        connections = []
        for conn_id, conn_data in active_connections.items():
            if conn_data["status"] == "active":
                connections.append({
                    "connectionId": conn_id,
                    "ip": conn_data["ip"],
                    "browser": conn_data["browser"],
                    "os": conn_data["os"],
                    "timestamp": conn_data["timestamp"],
                    "userAgent": conn_data.get("userAgent", ""),
                    "screenResolution": conn_data.get("screenResolution", ""),
                    "language": conn_data.get("language", ""),
                    "machineType": conn_data.get("machineType", "Unknown")
                })
        
        return {"success": True, "connections": connections}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {str(e)}")

@app.post("/api/ollama-chat")
@private_endpoint
async def ollama_chat(request: dict):
    # Ollama chat: takes message text and model, sends to Ollama API and returns AI response
    """Send a chat message to Ollama."""
    try:
        message = request.get("message", "").strip()
        model = request.get("model", "").strip()
        
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        client = OllamaClient(OLLAMA_BASE_URL)
        result = await client.simple_chat(message, model)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chat with Ollama: {str(e)}")


# ============================================================================
# COMFYUI INTEGRATION ENDPOINTS
# ============================================================================

@app.get("/api/comfyui-status")
@private_endpoint
async def comfyui_status():
    # ComfyUI status: no input, returns installation status, running state and port information
    """Get ComfyUI installation and running status."""
    try:
        manager = ComfyUIManager()
        result = manager.get_status()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ComfyUI inspection failed: {str(e)}")


@app.get("/api/comfyui-output-folder")
@private_endpoint
async def comfyui_output_folder():
    # ComfyUI output folder: no input, returns the path to ComfyUI output folder
    """Get ComfyUI output folder path."""
    try:
        global comfyui_app_directory
        
        if not comfyui_app_directory:
            # Try to discover ComfyUI installation if not already found
            manager = ComfyUIManager()
            comfyui_path = manager.find_comfyui_installation()
            if not comfyui_path:
                return {"error": "ComfyUI installation not found"}
            comfyui_app_directory = comfyui_path
        
        # Standard ComfyUI output folder is "output" in the ComfyUI directory
        output_folder = os.path.join(comfyui_app_directory, "output")
        
        return {
            "success": True,
            "comfyui_path": comfyui_app_directory,
            "output_folder": output_folder,
            "output_exists": os.path.exists(output_folder)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ComfyUI output folder: {str(e)}")


@app.post("/api/comfyui-open-output-folder")
@private_endpoint
async def comfyui_open_output_folder():
    # ComfyUI open output folder: no input, opens the ComfyUI output folder in file manager
    """Open ComfyUI output folder in system file manager."""
    try:
        global comfyui_app_directory
        
        if not comfyui_app_directory:
            # Try to discover ComfyUI installation if not already found
            manager = ComfyUIManager()
            comfyui_path = manager.find_comfyui_installation()
            if not comfyui_path:
                return {"error": "ComfyUI installation not found"}
            comfyui_app_directory = comfyui_path
        
        # Standard ComfyUI output folder is "output" in the ComfyUI directory
        output_folder = os.path.join(comfyui_app_directory, "output")
        
        # Open folder in system file manager
        if os.name == 'nt':  # Windows
            result = subprocess.run(['explorer', output_folder], capture_output=True, text=True)
            # Explorer returns non-zero exit status even on success, so we check if folder exists
            # and also check if the command executed without major errors
            if os.path.exists(output_folder) and result.returncode <= 1:  # 0 or 1 are both "success" for explorer
                return {
                    "success": True,
                    "message": "Folder opened successfully",
                    "output_folder": output_folder
                }
            elif not os.path.exists(output_folder):
                return {"error": f"Folder does not exist: {output_folder}"}
            else:
                return {"error": f"Failed to open folder: explorer returned exit code {result.returncode}"}
        elif os.name == 'posix':  # macOS and Linux
            if sys.platform == 'darwin':  # macOS
                result = subprocess.run(['open', output_folder], check=True)
            else:  # Linux
                result = subprocess.run(['xdg-open', output_folder], check=True)
            
            return {
                "success": True,
                "message": "Folder opened successfully",
                "output_folder": output_folder
            }
        
    except subprocess.CalledProcessError as e:
        return {"error": f"Failed to open folder: {str(e)}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open ComfyUI output folder: {str(e)}")


@app.get("/api/ollama-directory")
@private_endpoint
async def ollama_directory():
    # Ollama directory: no input, returns the path to Ollama installation directory
    """Get Ollama installation directory path."""
    try:
        global ollama_app_directory
        
        if not ollama_app_directory:
            # Try to discover Ollama installation if not already found
            manager = OllamaManager()
            ollama_path = manager.find_ollama_installation()
            if not ollama_path:
                return {"error": "Ollama installation not found"}
            ollama_app_directory = ollama_path
        
        return {
            "success": True,
            "ollama_path": ollama_app_directory,
            "directory_exists": os.path.exists(ollama_app_directory)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Ollama directory: {str(e)}")


@app.post("/api/comfyui-stop")
@private_endpoint
async def comfyui_stop():
    # ComfyUI stop: no input, terminates all ComfyUI processes and returns termination results
    """Stop all ComfyUI processes running on the system."""
    try:
        manager = ComfyUIManager()
        result = manager.stop_all_comfyui_processes()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop all ComfyUI processes: {str(e)}")


@app.post("/api/comfyui-start")
@private_endpoint
async def comfyui_start():
    # ComfyUI start: no input, launches ComfyUI service on Windows and returns startup results
    """Start ComfyUI on Windows."""
    try:
        manager = ComfyUIManager()
        result = manager.start_comfyui_windows()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start ComfyUI: {str(e)}")


@app.get("/api/apps-running-info")
@private_endpoint
async def apps_running_info():
    # Apps info: no input, returns running processes and resource utilization (Task Manager style)
    """Get information about running applications similar to Task Manager."""
    try:
        result = get_apps_running_info()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get apps running info: {str(e)}")


@app.post("/api/comfyui-submit-workflow")
@private_endpoint
async def comfyui_submit_workflow(request: dict):
    # Workflow submit: takes workflow data, client_id and seed, submits to ComfyUI and returns execution results
    """Submit a workflow to ComfyUI for execution."""
    try:
        workflow_data = request.get("workflow")
        base_url = request.get("base_url")  # None means auto-detect
        client_id = request.get("client_id")  # Custom client ID
        random_seed = request.get("random_seed")  # Random seed for variation
        
        if not workflow_data:
            raise HTTPException(status_code=400, detail="Workflow data is required")
        
        client = ComfyUIClient(base_url, client_id)
        result = await client.submit_workflow(workflow_data, random_seed)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit workflow: {str(e)}")


@app.get("/api/comfyui-queue")
@private_endpoint
async def comfyui_queue(request: Request):
    # ComfyUI queue: takes optional base_url query param, returns queue status and pending jobs
    """Get ComfyUI queue status."""
    try:
        base_url = request.query_params.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.get_queue_status()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@app.get("/api/comfyui-history/{prompt_id}")
@private_endpoint
async def comfyui_history(prompt_id: str, request: Request):
    # ComfyUI history: takes prompt_id from URL path and optional base_url query, returns workflow execution history
    """Get workflow execution history."""
    try:
        base_url = request.query_params.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.get_history(prompt_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")



# ============================================================================
# WORKFLOW MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/workflows")
@private_endpoint
async def list_workflows():
    # Workflow list: no input, returns list of available workflow JSON files
    """List all available workflow files."""
    try:
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
        workflows = []
        
        if os.path.exists(workflows_dir):
            for filename in os.listdir(workflows_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(workflows_dir, filename)
                    file_size = os.path.getsize(file_path)
                    workflows.append({
                        'filename': filename,
                        'size': file_size,
                        'path': f"/workflows/{filename}"
                    })
        
        return {
            "success": True,
            "workflows": workflows,
            "count": len(workflows)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")

@app.get("/workflows/{filename}")
@private_endpoint
async def get_workflow(filename: str):
    # Workflow file: takes filename, returns workflow JSON content
    """Get a specific workflow file."""
    try:
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
        file_path = os.path.join(workflows_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Workflow file '{filename}' not found")
        
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are allowed")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse and return as JSON
        workflow_data = json.loads(content)
        return workflow_data
        
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load workflow: {str(e)}")

@app.post("/api/workflows/upload")
async def upload_workflow(request: Request):
    # Workflow upload: takes multipart file upload, saves JSON workflow to workflows directory
    """Upload a new workflow JSON file."""
    try:
        form = await request.form()
        file = form.get("file")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are allowed")
        
        # Read file content
        content = await file.read()
        
        # Validate JSON
        try:
            json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        
        # Save to workflows directory
        workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
        os.makedirs(workflows_dir, exist_ok=True)
        
        file_path = os.path.join(workflows_dir, file.filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"Workflow '{file.filename}' uploaded successfully",
            "filename": file.filename,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload workflow: {str(e)}")


@app.post("/api/comfyui-interrupt")
@private_endpoint
async def comfyui_interrupt(request: dict):
    # ComfyUI interrupt: takes optional base_url, interrupts current execution and returns interrupt results
    """Interrupt current ComfyUI execution."""
    try:
        base_url = request.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.interrupt_execution()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to interrupt execution: {str(e)}")


@app.get("/api/comfyui-system-stats")
@private_endpoint
async def comfyui_system_stats(request: Request):
    # ComfyUI stats: takes optional base_url query param, returns system statistics and performance metrics
    """Get ComfyUI system statistics."""
    try:
        base_url = request.query_params.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.get_system_stats()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


# ============================================================================
# WORKFLOW INSPECTOR ENDPOINTS
# ============================================================================

@app.get("/workflow-inspector")
@private_endpoint
async def workflow_inspector(request: Request):
    """Workflow Inspector: Interactive workflow analysis and debugging tool."""
    try:
        workflow_name = request.query_params.get("workflow")
        if not workflow_name:
            raise HTTPException(status_code=400, detail="Workflow parameter is required")
        
        # Check if workflow file exists
        workflow_path = f"rendersync/workflows/{workflow_name}"
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow file not found: {workflow_name}")
        
        # Serve the static HTML file
        return FileResponse("rendersync/static/workflow-inspector.html")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load workflow inspector: {str(e)}")


@app.get("/api/workflow-info")
@private_endpoint
async def workflow_info(request: Request):
    """Get workflow file information."""
    try:
        workflow_name = request.query_params.get("workflow")
        if not workflow_name:
            raise HTTPException(status_code=400, detail="Workflow parameter is required")
        
        workflow_path = f"rendersync/workflows/{workflow_name}"
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow file not found: {workflow_name}")
        
        # Get file stats
        stat = os.stat(workflow_path)
        
        return {
            "filename": workflow_name,
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
            "created": stat.st_ctime
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow info: {str(e)}")


