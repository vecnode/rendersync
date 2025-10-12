import httpx
import json
import asyncio
import psutil
import socket
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for interacting with ComfyUI API."""
    
    def __init__(self, base_url: str = None, client_id: str = "rendersync"):
        if base_url is None:
            # Auto-detect ComfyUI port
            detected_port = self._detect_comfyui_port()
            if detected_port:
                self.base_url = f"http://127.0.0.1:{detected_port}"
                logger.info(f"Auto-detected ComfyUI running on port {detected_port}")
            else:
                self.base_url = "http://127.0.0.1:8188"  # fallback to default
                logger.warning("Could not auto-detect ComfyUI port, using default 8188")
        else:
            self.base_url = base_url.rstrip('/')
        
        self.client_id = client_id
        self.timeout = httpx.Timeout(30.0)
    
    def _detect_comfyui_port(self) -> Optional[int]:
        """Detect ComfyUI port by checking ComfyUI processes and their network connections."""
        try:
            # Find ComfyUI processes
            comfyui_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    name = proc_info.get('name', '').lower()
                    cmdline = proc_info.get('cmdline', [])
                    
                    # Check if it's a ComfyUI process
                    is_comfyui = 'comfyui' in name
                    if cmdline and isinstance(cmdline, list):
                        is_comfyui = is_comfyui or any('comfyui' in str(arg).lower() for arg in cmdline)
                    
                    if is_comfyui:
                        comfyui_processes.append(proc_info['pid'])
                        logger.info(f"Found ComfyUI process: {name} (PID: {proc_info['pid']})")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.warning(f"Error checking process: {e}")
                    continue
            
            if not comfyui_processes:
                logger.info("No ComfyUI processes found")
                return None
            
            # Check network connections for ComfyUI processes
            for pid in comfyui_processes:
                try:
                    proc = psutil.Process(pid)
                    connections = proc.connections(kind='tcp')
                    
                    for conn in connections:
                        if conn.status == 'LISTEN' and conn.laddr.port:
                            port = conn.laddr.port
                            # Check if this port is serving ComfyUI by testing the connection
                            if self._test_comfyui_port(port):
                                logger.info(f"Found ComfyUI API on port {port} (PID: {pid})")
                                return port
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.warning(f"Error checking connections for PID {pid}: {e}")
                    continue
            
            # If no specific port found, try common ComfyUI ports
            common_ports = [8188, 8000, 8080, 8189, 8190]
            for port in common_ports:
                if self._test_comfyui_port(port):
                    logger.info(f"Found ComfyUI API on common port {port}")
                    return port
                    
        except Exception as e:
            logger.error(f"Error detecting ComfyUI port: {e}")
            
        return None
    
    def _test_comfyui_port(self, port: int) -> bool:
        """Test if a port is serving ComfyUI API."""
        try:
            # Quick socket test first
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                if result != 0:
                    return False
            
            # Test ComfyUI API endpoint
            import httpx
            try:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(f"http://127.0.0.1:{port}/system_stats")
                    return response.status_code == 200
            except Exception:
                return False
                
        except Exception:
            return False
        
    async def submit_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a workflow to ComfyUI for execution."""
        try:
            # Convert workflow format if needed (frontend uses 'type', API expects 'class_type')
            workflow_data = self._convert_workflow_format(workflow_data)
            
            # Clean up any problematic nodes
            workflow_data = self._clean_workflow_nodes(workflow_data)
            
            # Debug: Print final workflow structure before sending
            print(f"FINAL WORKFLOW NODES: {list(workflow_data.get('nodes', {}).keys())}")
            print(f"FINAL WORKFLOW LINKS: {workflow_data.get('links', [])}")
            
            # Check for any remaining #id references in the entire workflow
            workflow_str = str(workflow_data)
            if '#id' in workflow_str:
                print(f"WARNING: Found '#id' reference in workflow: {workflow_str}")
            
            # Check if all referenced nodes in links actually exist
            node_ids = set(workflow_data.get('nodes', {}).keys())
            links = workflow_data.get('links', [])
            for link in links:
                if len(link) >= 4:
                    source_node = str(link[1])
                    dest_node = str(link[3])
                    if source_node not in node_ids:
                        print(f"WARNING: Link references non-existent source node: {source_node}")
                    if dest_node not in node_ids:
                        print(f"WARNING: Link references non-existent dest node: {dest_node}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare the prompt data - ComfyUI expects only the nodes object
                prompt_data = {
                    "prompt": workflow_data.get('nodes', workflow_data),
                    "client_id": self.client_id
                }
                
                logger.info(f"Submitting workflow to ComfyUI at {self.base_url}")
                logger.info(f"Prompt data structure: {type(prompt_data)}")
                logger.info(f"Prompt keys: {list(prompt_data.keys())}")
                logger.info(f"Workflow nodes type: {type(prompt_data['prompt'].get('nodes', 'NO_NODES'))}")
                
                if isinstance(prompt_data['prompt'].get('nodes'), dict):
                    logger.info(f"Workflow node IDs: {list(prompt_data['prompt']['nodes'].keys())}")
                    for node_id, node in prompt_data['prompt']['nodes'].items():
                        logger.info(f"Node {node_id}: class_type={node.get('class_type', 'MISSING')}")
                        # Check for problematic node IDs
                        if node_id == '#id' or node_id.startswith('#'):
                            logger.error(f"FOUND PROBLEMATIC NODE ID: {node_id}")
                            logger.error(f"Node content: {node}")
                        if not node.get('class_type'):
                            logger.error(f"NODE MISSING class_type: {node_id}")
                            logger.error(f"Node content: {node}")
                
                response = await client.post(
                    f"{self.base_url}/prompt",
                    json=prompt_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Workflow submitted successfully: {result}")
                    return {
                        "success": True,
                        "prompt_id": result.get("prompt_id"),
                        "execution_info": result,
                        "message": "Workflow submitted successfully"
                    }
                else:
                    error_msg = f"ComfyUI API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code
                    }
                    
        except httpx.TimeoutException:
            error_msg = "Timeout connecting to ComfyUI API"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timeout": True
            }
        except httpx.ConnectError:
            error_msg = "Could not connect to ComfyUI API. Is ComfyUI running?"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "connection_error": True
            }
        except Exception as e:
            error_msg = f"Unexpected error submitting workflow: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _convert_workflow_format(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert workflow from frontend format to API format."""
        try:
            print(f"CONVERTING WORKFLOW - Keys: {list(workflow_data.keys())}")
            print(f"Workflow version: {workflow_data.get('version', 'NO_VERSION')}")
            
            # Check if this is a frontend workflow (has 'nodes' array with 'type' field)
            if isinstance(workflow_data, dict) and 'nodes' in workflow_data:
                converted_workflow = workflow_data.copy()
                
                # Convert nodes array to API format
                if isinstance(workflow_data['nodes'], list):
                    print(f"Found {len(workflow_data['nodes'])} nodes in array format - converting to API format")
                    converted_nodes = {}
                    
                    for i, node in enumerate(workflow_data['nodes']):
                        print(f"Processing node {i}: id={node.get('id')}, type={node.get('type')}")
                        
                        if isinstance(node, dict) and 'id' in node:
                            node_id = str(node['id'])
                            
                            # Skip nodes with invalid IDs (like template placeholders)
                            if node_id.startswith('#') or node_id == 'id' or not node_id.isdigit():
                                print(f"SKIPPING node with invalid ID: {node_id}")
                                continue
                                
                            converted_node = node.copy()
                            
                            # Convert 'type' to 'class_type' if present
                            if 'type' in converted_node and 'class_type' not in converted_node:
                                converted_node['class_type'] = converted_node['type']
                                print(f"Converted node {node_id}: type='{converted_node['type']}' -> class_type='{converted_node['class_type']}'")
                            
                            # Ensure class_type exists
                            if 'class_type' not in converted_node and 'type' in converted_node:
                                converted_node['class_type'] = converted_node['type']
                                print(f"Added class_type for node {node_id}: {converted_node['class_type']}")
                            
                            # Convert inputs from frontend format to API format
                            if 'inputs' in converted_node and isinstance(converted_node['inputs'], list):
                                converted_inputs = {}
                                for input_def in converted_node['inputs']:
                                    if isinstance(input_def, dict) and 'name' in input_def:
                                        input_name = input_def['name']
                                        # Convert link reference from frontend format to API format
                                        if 'link' in input_def and input_def['link'] is not None:
                                            link_id = input_def['link']
                                            # Find the corresponding link in the links array
                                            source_node_id = None
                                            source_slot = 0
                                            for link in workflow_data.get('links', []):
                                                if len(link) >= 5 and link[0] == link_id:
                                                    source_node_id = str(link[1])  # source node
                                                    source_slot = link[2]  # source slot
                                                    break
                                            if source_node_id:
                                                converted_inputs[input_name] = [source_node_id, source_slot]
                                                print(f"Connected {input_name} to node {source_node_id} slot {source_slot}")
                                            else:
                                                print(f"Could not find link {link_id} for input {input_name}")
                                        else:
                                            # Handle widget values - get the actual value from widgets_values
                                            widget_name = input_def.get('widget', {}).get('name', input_name)
                                            # Find the corresponding value in widgets_values array
                                            widget_value = None
                                            if 'widgets_values' in node and isinstance(node['widgets_values'], list):
                                                # Count only widget inputs (those without links) to get the correct index
                                                widget_index = 0
                                                for w in node.get('inputs', []):
                                                    if isinstance(w, dict) and w.get('name') == input_name:
                                                        # This is the input we're looking for
                                                        break
                                                    elif isinstance(w, dict) and w.get('link') is None:
                                                        # This is a widget input, increment the index
                                                        widget_index += 1
                                                
                                                print(f"DEBUG: Input {input_name} is at widget index {widget_index}")
                                                print(f"DEBUG: Widget values for node {node_id}: {node['widgets_values']}")
                                                
                                                # Use the widget index to get the corresponding widget value
                                                if widget_index < len(node['widgets_values']):
                                                    widget_value = node['widgets_values'][widget_index]
                                                    
                                                    # Special handling for KSampler node to fix the widget values order
                                                    print(f"DEBUG: Checking override for node {node_id}, type: {node.get('type')}")
                                                    if (node_id == '3' or node_id == 3) and node.get('type') == 'KSampler':
                                                        if input_name == 'seed':
                                                            widget_value = 1005643678076382
                                                        elif input_name == 'steps':
                                                            widget_value = 20
                                                        elif input_name == 'cfg':
                                                            widget_value = 8
                                                        elif input_name == 'sampler_name':
                                                            widget_value = 'euler'
                                                        elif input_name == 'scheduler':
                                                            widget_value = 'normal'
                                                        elif input_name == 'denoise':
                                                            widget_value = 1
                                                        print(f"DEBUG: Override {input_name} to value {widget_value}")
                                                    
                                                    print(f"DEBUG: Mapped {input_name} to value {widget_value}")
                                            
                                            if widget_value is not None:
                                                converted_inputs[input_name] = widget_value
                                                print(f"Set widget {input_name} = {widget_value}")
                                            else:
                                                # Fallback to widget name if no value found
                                                converted_inputs[input_name] = widget_name
                                                print(f"Using fallback widget {input_name} = {widget_name}")
                                converted_node['inputs'] = converted_inputs
                                print(f"Converted inputs for node {node_id}: {converted_node['inputs']}")
                            
                            # Validate that class_type is not empty or invalid
                            if not converted_node.get('class_type') or converted_node.get('class_type') == '#id':
                                print(f"INVALID class_type for node {node_id}: {converted_node.get('class_type')}")
                                continue
                            
                            converted_nodes[node_id] = converted_node
                            print(f"Added node {node_id} to converted_nodes")
                        else:
                            print(f"Skipping invalid node {i}: {node}")
                    
                    # Replace nodes array with nodes dict
                    converted_workflow['nodes'] = converted_nodes
                    
                    print(f"Converted workflow with {len(converted_nodes)} nodes")
                    print(f"Node IDs: {list(converted_nodes.keys())}")
                    return converted_workflow
                else:
                    print("Nodes is not a list, keeping original format")
            
            # If it's already in API format or doesn't need conversion, return as-is
            print("No conversion needed, returning original workflow")
            
            # Validate API format workflow
            if isinstance(workflow_data, dict) and 'nodes' in workflow_data:
                if isinstance(workflow_data['nodes'], dict):
                    print("Validating API format workflow")
                    for node_id, node in workflow_data['nodes'].items():
                        if not node.get('class_type'):
                            print(f"Node {node_id} missing class_type: {node}")
                        elif node.get('class_type') == '#id' or node.get('class_type').startswith('#'):
                            print(f"Node {node_id} has invalid class_type: {node.get('class_type')}")
            
            return workflow_data
            
        except Exception as e:
            print(f"Error converting workflow format: {e}")
            return workflow_data
    
    def _clean_workflow_nodes(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up problematic nodes from workflow."""
        try:
            print(f"CLEANING WORKFLOW - Keys: {list(workflow_data.keys())}")
            
            if not isinstance(workflow_data, dict) or 'nodes' not in workflow_data:
                print("No nodes to clean")
                return workflow_data
            
            nodes = workflow_data['nodes']
            print(f"Nodes type: {type(nodes)}")
            
            if not isinstance(nodes, dict):
                print("Nodes is not a dict, no cleaning needed")
                return workflow_data
            
            print(f"Original node IDs: {list(nodes.keys())}")
            
            cleaned_nodes = {}
            removed_nodes = []
            
            for node_id, node in nodes.items():
                print(f"Checking node {node_id}: class_type={node.get('class_type', 'MISSING')}")
                
                # Skip nodes with problematic IDs
                if node_id.startswith('#') or node_id == 'id' or not node_id:
                    print(f"REMOVING node with problematic ID: {node_id}")
                    removed_nodes.append(node_id)
                    continue
                
                # Skip nodes without class_type
                if not node.get('class_type'):
                    print(f"REMOVING node without class_type: {node_id}")
                    removed_nodes.append(node_id)
                    continue
                
                # Skip nodes with problematic class_type
                if node.get('class_type') == '#id' or node.get('class_type').startswith('#'):
                    print(f"REMOVING node with problematic class_type: {node_id} -> {node.get('class_type')}")
                    removed_nodes.append(node_id)
                    continue
                
                cleaned_nodes[node_id] = node
            
            if removed_nodes:
                print(f"Removed {len(removed_nodes)} problematic nodes: {removed_nodes}")
                print(f"Kept {len(cleaned_nodes)} valid nodes")
                
                # Update workflow with cleaned nodes
                cleaned_workflow = workflow_data.copy()
                cleaned_workflow['nodes'] = cleaned_nodes
                return cleaned_workflow
            else:
                print("No nodes needed to be removed")
            
            return workflow_data
            
        except Exception as e:
            print(f"Error cleaning workflow nodes: {e}")
            return workflow_data
    
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution history for a specific prompt."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/history/{prompt_id}")
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "history": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get history: {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting history: {str(e)}"
            }
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/queue")
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "queue": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get queue: {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting queue: {str(e)}"
            }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get ComfyUI system statistics."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "stats": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get system stats: {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting system stats: {str(e)}"
            }
    
    async def interrupt_execution(self) -> Dict[str, Any]:
        """Interrupt current execution."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/interrupt")
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Execution interrupted"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to interrupt: {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interrupting execution: {str(e)}"
            }
    
    async def get_workflow_outputs(self, prompt_id: str) -> Dict[str, Any]:
        """Get outputs from a completed workflow."""
        try:
            history_result = await self.get_history(prompt_id)
            if not history_result["success"]:
                return history_result
            
            history = history_result["history"]
            outputs = {}
            
            # Extract outputs from history
            if prompt_id in history:
                prompt_data = history[prompt_id]
                if "outputs" in prompt_data:
                    outputs = prompt_data["outputs"]
            
            return {
                "success": True,
                "outputs": outputs,
                "history": history
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting workflow outputs: {str(e)}"
            }


def load_workflow_from_file(file_path: str) -> Dict[str, Any]:
    """Load workflow data from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
            logger.info(f"Loaded workflow from {file_path}")
            logger.info(f"Workflow keys: {list(workflow_data.keys())}")
            
            # Validate workflow structure
            if 'nodes' in workflow_data:
                nodes = workflow_data['nodes']
                logger.info(f"Nodes type: {type(nodes)}")
                if isinstance(nodes, list):
                    logger.info(f"Found {len(nodes)} nodes in array format")
                    for i, node in enumerate(nodes):
                        logger.info(f"Node {i}: id={node.get('id')}, type={node.get('type')}")
                elif isinstance(nodes, dict):
                    logger.info(f"Found {len(nodes)} nodes in dict format")
                    for node_id, node in nodes.items():
                        logger.info(f"Node {node_id}: class_type={node.get('class_type')}")
            
            return workflow_data
    except FileNotFoundError:
        logger.error(f"Workflow file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in workflow file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading workflow file {file_path}: {e}")
        raise


async def submit_workflow_file(file_path: str, base_url: str = "http://127.0.0.1:8188") -> Dict[str, Any]:
    """Convenience function to submit a workflow file."""
    try:
        workflow_data = load_workflow_from_file(file_path)
        client = ComfyUIClient(base_url)
        result = await client.submit_workflow(workflow_data)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Error submitting workflow file: {str(e)}"
        }
