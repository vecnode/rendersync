# ============================================================================
# RENDERSYNC SERVER
# ============================================================================

import subprocess
import sys
import os
import socket
import psutil

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .modules.system import get_system_info_data, inspect_pid_data, ping_ip_data, ping_multiple_ips_data
from .modules.network import get_network_info_data
from .modules.interaction import inspect_port
from .modules.utilities import track_spawned_process, check_application_timeout, cleanup_processes, get_application_status, get_terminal_info, get_apps_running_info
from .modules.ollama import OllamaManager, OllamaClient
from .modules.comfyui import ComfyUIManager
from .comfy_api import ComfyUIClient, load_workflow_from_file


# ================================================================================
# RENDERSYNC API ENDPOINTS
# ================================================================================
# Core System Endpoints
# --------------------------------------------------------------------------------
# GET    /health                     Health check and system status
# GET    /                           Serve main interface
# GET    /static/*                   Static assets (js, css, images)
#
# System Information & Diagnostics 
# --------------------------------------------------------------------------------
# GET    /api/system-info            Full system specifications and capabilities
# GET    /api/network-info           Network interfaces, IPs and connectivity data
# GET    /api/apps-running-info      Running processes and resource utilization
# GET    /api/terminal-info          Active terminal sessions and shell info
#
# Process & Port Management
# --------------------------------------------------------------------------------
# POST   /api/inspect-port           Analyze port status and bound processes
# POST   /api/inspect-pid            Process details and resource consumption
# POST   /api/ping                   Network connectivity test to single target
# POST   /api/ping-multiple          Parallel connectivity testing to multiple targets
#
# Ollama Integration 
# --------------------------------------------------------------------------------
# POST   /api/ollama-start           Launch Ollama service (Windows)
# GET    /api/ollama-models          List available language models
# POST   /api/ollama-chat            Send message to active Ollama model
#
# ComfyUI Integration
# --------------------------------------------------------------------------------
# GET    /api/comfyui-status         ComfyUI installation and runtime status
# POST   /api/comfyui-stop           Terminate ComfyUI processes
# POST   /api/comfyui-start          Launch ComfyUI service (Windows)
# POST   /api/comfyui-submit-workflow Submit workflow to ComfyUI
# GET    /api/comfyui-queue          Get ComfyUI queue status
# GET    /api/comfyui-history/{prompt_id} Get workflow execution history
# POST   /api/comfyui-interrupt      Interrupt current ComfyUI execution
# GET    /api/comfyui-system-stats   Get ComfyUI system statistics
# GET    /workflows/{filename}       Serve workflow JSON files
#
# ================================================================================




# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class PortInspectionRequest(BaseModel):
    port: int

class PIDInspectionRequest(BaseModel):
    pid: str

class PingRequest(BaseModel):
    target: str
    port: int = None
    timeout: int = 3

class MultiPingRequest(BaseModel):
    targets: list
    port: int = None
    timeout: int = 2


# ============================================================================
# PORT MANAGEMENT SYSTEM FOR RENDER FARMS
# ============================================================================

# Optimal ports for render farms and professional installations
RENDER_FARM_PORTS = [
    8080,   # Standard HTTP alternative (most common in render farms)
    8000,   # Development standard
    8081,   # Common render farm port
    8082,   # Secondary render service
    3000,   # Node.js standard (many render tools use this)
    5000,   # Flask standard
    9000,   # Common render farm port
    8888,   # Jupyter/development standard
    8001,   # Alternative development port
    8083,   # Tertiary render service
    7000,   # Common render farm port
]

DEFAULT_PORT = 8080  # Best choice for render farms


def find_available_port(start_port=None):
    """Find the best available port for render farm operations."""
    if start_port is None:
        start_port = DEFAULT_PORT
    
    # Check if start_port is in our preferred list
    if start_port in RENDER_FARM_PORTS:
        ports_to_try = [start_port] + [p for p in RENDER_FARM_PORTS if p != start_port]
    else:
        ports_to_try = [start_port] + RENDER_FARM_PORTS
    
    for port in ports_to_try:
        if is_port_available(port):
            print(f"\033[92mPORTMANAGER\033[0m Selected port {port} for render farm operations")
            return port
    
    # Fallback: find any available port
    for port in range(8000, 9000):
        if is_port_available(port):
            print(f"\033[92mPORTMANAGER\033[0m Fallback: Using port {port}")
            return port
    
    raise RuntimeError("No available ports found in range 8000-8999")


def is_port_available(port):
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
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
        'preferred_ports': RENDER_FARM_PORTS,
        'default_port': DEFAULT_PORT,
        'port_usage': {}
    }
    
    # Check usage of preferred ports
    for port in RENDER_FARM_PORTS[:5]:  # Check first 5 ports
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
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="rendersync core", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def _startup() -> None:
    print("rendersync server starting")
    
    # Secure port for render farm operations
    try:
        secured_port = secure_port_for_render_farm()
        print(f"\033[92mPORTMANAGER\033[0m Render farm server secured on port {secured_port}")
    except Exception as e:
        print(f"\033[92mPORTMANAGER\033[0m Failed to secure port: {e}")
        print(f"\033[92mPORTMANAGER\033[0m Continuing with default port configuration")
    
    # Check for timeout on startup
    if check_application_timeout():
        print("Server startup terminated due to timeout")
        return

@app.on_event("shutdown")
async def _shutdown() -> None:
    print("rendersync server shutting down")
    cleanup_processes()

@app.get("/")
async def root():
    """Serve the main HTML page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": "Local LLM Server API", "docs": "/docs"}

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon to prevent 404 errors."""
    return Response(content="", media_type="image/x-icon")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    """Handle Chrome DevTools metadata request."""
    return {"version": "1.0", "name": "rendersync"}

@app.get("/api/system-info")
async def system_info():
    """Get system information."""
    return get_system_info_data()

@app.get("/api/network-info")
async def network_info():
    """Get network information."""
    return get_network_info_data()

@app.get("/api/terminal-info")
async def terminal_info():
    """Get terminal information."""
    return get_terminal_info()





@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "rendersync"}


@app.get("/api/process-status")
async def process_status():
    """Get process management status."""
    return get_application_status()


@app.get("/api/port-info")
async def port_info():
    """Get port management information."""
    return get_port_info()


@app.post("/api/inspect-port")
async def inspect_port_endpoint(request: PortInspectionRequest):
    """Inspect a specific port and return detailed information."""
    try:
        result = inspect_port(request.port)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Port inspection failed: {str(e)}")


@app.post("/api/inspect-pid")
async def inspect_pid_endpoint(request: PIDInspectionRequest):
    """Inspect a specific PID and return detailed process information."""
    try:
        result = inspect_pid_data(request.pid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PID inspection failed: {str(e)}")


@app.post("/api/ping-ip")
async def ping_ip_endpoint(request: PingRequest):
    """Ping an IP address or hostname and optionally check a specific port."""
    try:
        result = ping_ip_data(request.target, request.port, request.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping failed: {str(e)}")


@app.post("/api/ping-multiple")
async def ping_multiple_endpoint(request: MultiPingRequest):
    """Ping multiple IPs sequentially for network scanning."""
    try:
        result = ping_multiple_ips_data(request.targets, request.port, request.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-ping failed: {str(e)}")


@app.get("/api/ollama-status")
async def ollama_status():
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
                client = OllamaClient("http://127.0.0.1:11434")
                health = await client.health()
                result["api_responding"] = health
            except Exception as e:
                result["api_responding"] = False
                result["api_error"] = str(e)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama inspection failed: {str(e)}")


@app.post("/api/ollama-stop")
async def ollama_stop():
    """Stop all Ollama processes running on the system."""
    try:
        manager = OllamaManager()
        result = manager.stop_all_ollama_processes()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop Ollama processes: {str(e)}")


@app.post("/api/ollama-start")
async def ollama_start():
    """Start Ollama on Windows 10/11 as if double-clicked by user."""
    try:
        manager = OllamaManager()
        result = manager.start_ollama_windows()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Ollama: {str(e)}")


@app.get("/api/ollama-models")
async def ollama_models():
    """Get available Ollama models."""
    try:
        manager = OllamaManager()
        result = await manager.get_ollama_models()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Ollama models: {str(e)}")


@app.post("/api/ollama-chat")
async def ollama_chat(request: dict):
    """Send a chat message to Ollama."""
    try:
        message = request.get("message", "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        client = OllamaClient("http://127.0.0.1:11434")
        result = await client.simple_chat(message)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chat with Ollama: {str(e)}")


@app.get("/api/comfyui-status")
async def comfyui_status():
    """Get ComfyUI installation and running status."""
    try:
        manager = ComfyUIManager()
        result = manager.get_status()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ComfyUI inspection failed: {str(e)}")


@app.post("/api/comfyui-stop")
async def comfyui_stop():
    """Stop all ComfyUI processes running on the system."""
    try:
        manager = ComfyUIManager()
        result = manager.stop_all_comfyui_processes()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop ComfyUI processes: {str(e)}")


@app.post("/api/comfyui-start")
async def comfyui_start():
    """Start ComfyUI on Windows."""
    try:
        manager = ComfyUIManager()
        result = manager.start_comfyui_windows()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start ComfyUI: {str(e)}")


@app.get("/api/apps-running-info")
async def apps_running_info():
    """Get information about running applications similar to Task Manager."""
    try:
        result = get_apps_running_info()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get apps running info: {str(e)}")


@app.post("/api/comfyui-submit-workflow")
async def comfyui_submit_workflow(request: dict):
    """Submit a workflow to ComfyUI for execution."""
    try:
        workflow_data = request.get("workflow")
        base_url = request.get("base_url")  # None means auto-detect
        
        if not workflow_data:
            raise HTTPException(status_code=400, detail="Workflow data is required")
        
        client = ComfyUIClient(base_url)
        result = await client.submit_workflow(workflow_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit workflow: {str(e)}")


@app.get("/api/comfyui-queue")
async def comfyui_queue(request: Request):
    """Get ComfyUI queue status."""
    try:
        base_url = request.query_params.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.get_queue_status()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@app.get("/api/comfyui-history/{prompt_id}")
async def comfyui_history(prompt_id: str, request: Request):
    """Get workflow execution history."""
    try:
        base_url = request.query_params.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.get_history(prompt_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")



@app.get("/workflows/{filename}")
async def serve_workflow(filename: str):
    """Serve workflow JSON files."""
    workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
    file_path = os.path.join(workflows_dir, filename)
    
    if os.path.exists(file_path) and filename.endswith('.json'):
        return FileResponse(file_path, media_type="application/json")
    else:
        raise HTTPException(status_code=404, detail="Workflow file not found")


@app.post("/api/comfyui-interrupt")
async def comfyui_interrupt(request: dict):
    """Interrupt current ComfyUI execution."""
    try:
        base_url = request.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.interrupt_execution()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to interrupt execution: {str(e)}")


@app.get("/api/comfyui-system-stats")
async def comfyui_system_stats(request: Request):
    """Get ComfyUI system statistics."""
    try:
        base_url = request.query_params.get("base_url")  # None means auto-detect
        client = ComfyUIClient(base_url)
        result = await client.get_system_stats()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


