# ============================================================================
# RENDERSYNC CORE SERVER
# ============================================================================
# Main FastAPI application for render farm management and AI integration

# ============================================================================
# CORE IMPORTS
# ============================================================================
# Standard library imports for system operations
import subprocess  
import sys         
import os          
import socket      
import psutil      
import json        

# FastAPI framework imports for web API functionality
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ============================================================================
# MODULE IMPORTS
# ============================================================================
# System monitoring and diagnostics modules
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
# PROFESSIONAL PORT MANAGEMENT SYSTEM FOR RENDER FARMS
# ============================================================================

RENDER_FARM_PORTS = [
    8080,   # Standard HTTP alternative
    8000,   # Development standard
    8081,   # Common render farm port
    8082,   # Secondary render service
    3000,   # Node.js standard
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
# CONNECTION TRACKING
# ============================================================================
# Global Browser connection tracking

active_connections = {}

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
    # Server startup: secures port, checks timeout, initializes render farm operations
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
    # Server shutdown: cleans up processes, terminates gracefully
    print("rendersync server shutting down")
    cleanup_processes()

@app.get("/")
async def root():
    # Main page: serves index.html from static directory, fallback to API info
    """Serve the main HTML page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": "Local LLM Server API", "docs": "/docs"}

@app.get("/favicon.ico")
async def favicon():
    # Favicon: returns empty response to prevent 404 errors
    """Serve favicon to prevent 404 errors."""
    return Response(content="", media_type="image/x-icon")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    # Chrome DevTools: returns metadata for Chrome developer tools integration
    """Handle Chrome DevTools metadata request."""
    return {"version": "1.0", "name": "rendersync"}

@app.get("/api/system-info")
async def system_info():
    # System info: no input, returns complete system specifications and hardware data
    """Get system information."""
    return get_system_info_data()

@app.get("/api/network-info")
async def network_info():
    # Network info: no input, returns network interfaces, IPs and connectivity data
    """Get network information."""
    return get_network_info_data()

@app.get("/api/terminal-info")
async def terminal_info():
    # Terminal info: no input, returns active terminal sessions and shell information
    """Get terminal information."""
    return get_terminal_info()





@app.get("/health")
async def health():
    # Health check: no input, returns simple status confirmation
    """Simple health check endpoint."""
    return {"status": "ok", "service": "rendersync"}


@app.get("/api/process-status")
async def process_status():
    # Process status: no input, returns process management status and tracked processes
    """Get process management status."""
    return get_application_status()


@app.get("/api/port-info")
async def port_info():
    # Port info: no input, returns port management information and availability
    """Get port management information."""
    return get_port_info()


@app.post("/api/inspect-port")
async def inspect_port_endpoint(request: PortInspectionRequest):
    # Port inspection: takes port number, returns detailed port status and bound processes
    """Inspect a specific port and return detailed information."""
    try:
        result = inspect_port(request.port)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Port inspection failed: {str(e)}")


@app.post("/api/inspect-pid")
async def inspect_pid_endpoint(request: PIDInspectionRequest):
    # PID inspection: takes process ID, returns detailed process information and resource usage
    """Inspect a specific PID and return detailed process information."""
    try:
        result = inspect_pid_data(request.pid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PID inspection failed: {str(e)}")


@app.post("/api/ping-ip")
async def ping_ip_endpoint(request: PingRequest):
    # Single ping: takes target IP/hostname and optional port, returns connectivity test results
    """Ping an IP address or hostname and optionally check a specific port."""
    try:
        result = ping_ip_data(request.target, request.port, request.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping failed: {str(e)}")


@app.post("/api/ping-multiple")
async def ping_multiple_endpoint(request: MultiPingRequest):
    # Multi ping: takes list of targets and optional port, returns parallel connectivity test results
    """Ping multiple IPs sequentially for network scanning."""
    try:
        result = ping_multiple_ips_data(request.targets, request.port, request.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-ping failed: {str(e)}")


@app.get("/api/ollama-status")
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
async def ollama_models():
    # Ollama models: no input, returns list of available language models and their status
    """Get available Ollama models."""
    try:
        manager = OllamaManager()
        result = await manager.get_ollama_models()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Ollama models: {str(e)}")


@app.post("/api/connections")
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


@app.get("/api/comfyui-status")
async def comfyui_status():
    # ComfyUI status: no input, returns installation status, running state and port information
    """Get ComfyUI installation and running status."""
    try:
        manager = ComfyUIManager()
        result = manager.get_status()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ComfyUI inspection failed: {str(e)}")


@app.post("/api/comfyui-stop")
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
async def apps_running_info():
    # Apps info: no input, returns running processes and resource utilization (Task Manager style)
    """Get information about running applications similar to Task Manager."""
    try:
        result = get_apps_running_info()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get apps running info: {str(e)}")


@app.post("/api/comfyui-submit-workflow")
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



@app.get("/api/workflows")
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


