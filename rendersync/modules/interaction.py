# Default Python Modules
import socket
import subprocess
import platform
import psutil


def inspect_port(port):
    """Inspect a specific port and return detailed information instantly."""
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            return {"error": "Port must be between 1 and 65535"}
        
        result = {
            'port': port,
            'is_open': False,
            'is_listening': False,
            'process_info': None,
            'connection_info': None,
            'network_connections': []
        }
        
        # Check if port is open locally (instant)
        result['is_open'] = _check_port_open(port)
        
        # Check if port is listening (instant)
        result['is_listening'] = _check_port_listening(port)
        
        # Get process information if port is in use (instant)
        if result['is_listening']:
            result['process_info'] = _get_process_using_port(port)
        
        # Get connection information (instant)
        result['connection_info'] = _get_connection_info(port)
        
        # Get network connections (instant)
        result['network_connections'] = _get_network_connections(port)
        
        return result
        
    except ValueError:
        return {"error": "Invalid port number"}
    except Exception as e:
        return {"error": f"Error inspecting port: {e}"}


def _check_port_open(port):
    """Check if a port is open locally - instant."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.01)  # Ultra-fast timeout
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False


def _check_port_listening(port):
    """Check if a port is listening."""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return True
        return False
    except Exception:
        return False


def _get_process_using_port(port):
    """Get process information for a port."""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    process = psutil.Process(conn.pid)
                    return {
                        'pid': conn.pid,
                        'name': process.name(),
                        'cmdline': ' '.join(process.cmdline()),
                        'status': process.status(),
                        'cpu_percent': process.cpu_percent(),
                        'memory_info': process.memory_info()._asdict(),
                        'create_time': process.create_time()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return {'pid': conn.pid, 'name': 'Unknown', 'error': 'Access denied'}
        return None
    except Exception:
        return None


def _get_connection_info(port):
    """Get detailed connection information for a port."""
    try:
        connections = []
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                conn_info = {
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                    'status': conn.status,
                    'pid': conn.pid
                }
                connections.append(conn_info)
        return connections
    except Exception:
        return []


def _get_network_connections(port):
    """Get network connections related to the port."""
    try:
        connections = []
        for conn in psutil.net_connections():
            if conn.laddr.port == port or (conn.raddr and conn.raddr.port == port):
                conn_info = {
                    'family': 'IPv4' if conn.family == socket.AF_INET else 'IPv6',
                    'type': 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP',
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                    'status': conn.status,
                    'pid': conn.pid
                }
                connections.append(conn_info)
        return connections
    except Exception:
        return []




def ping_host(host):
    """Ping a host and return detailed information."""
    try:
        # Determine ping command based on OS
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "4", host]
        else:
            cmd = ["ping", "-c", "4", host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        ping_info = {
            'host': host,
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None,
            'packets_sent': 0,
            'packets_received': 0,
            'packet_loss': 0,
            'response_times': []
        }
        
        # Parse ping output for statistics
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'packets transmitted' in line.lower() or 'packets sent' in line.lower():
                    # Extract packet statistics
                    import re
                    numbers = re.findall(r'\d+', line)
                    if len(numbers) >= 2:
                        ping_info['packets_sent'] = int(numbers[0])
                        ping_info['packets_received'] = int(numbers[1])
                        if len(numbers) >= 3:
                            ping_info['packet_loss'] = int(numbers[2])
                elif 'time=' in line.lower() or 'time<' in line.lower():
                    # Extract response times
                    import re
                    time_match = re.search(r'time[<=](\d+(?:\.\d+)?)', line)
                    if time_match:
                        ping_info['response_times'].append(float(time_match.group(1)))
        
        return ping_info
        
    except subprocess.TimeoutExpired:
        return {"error": "Ping timeout", "host": host}
    except Exception as e:
        return {"error": f"Ping failed: {e}", "host": host}


def get_processes_by_name(process_name):
    """Get processes by name with detailed information."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'cpu_percent', 'memory_info', 'create_time']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else 'N/A',
                        'status': proc.info['status'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_info': proc.info['memory_info']._asdict() if proc.info['memory_info'] else None,
                        'create_time': proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            'process_name': process_name,
            'count': len(processes),
            'processes': processes
        }
        
    except Exception as e:
        return {"error": f"Error getting processes: {e}"}
