# Default Python Modules
import socket
import subprocess
import platform
import signal
import functools
import psutil


def timeout_handler(signum, frame):
    """Handle timeout signals."""
    raise TimeoutError("Operation timed out")


def safe_execute(func, timeout=5, default=None):
    """Safely execute a function with timeout protection."""
    try:
        if hasattr(signal, 'SIGALRM'):  # Unix systems
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            try:
                result = func()
                return result
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:  # Windows systems
            return func()
    except (TimeoutError, Exception):
        return default


def get_network_info_data():
    """Get fast network information for render farm analysis."""
    try:
        data = {}
        
        # Get basic network info with error handling and timeouts
        data['local_ip'] = safe_execute(_get_local_ip, timeout=2, default="127.0.0.1")
        data['gateway'] = safe_execute(_get_gateway, timeout=3, default=None)
        data['network_range'] = safe_execute(lambda: _get_network_range(data['local_ip']), timeout=3, default=None)
        
        # Get hostname info with timeout protection
        data['hostname'] = safe_execute(socket.gethostname, timeout=1, default="Unknown")
        data['fqdn'] = safe_execute(socket.getfqdn, timeout=1, default="Unknown")
        
        # Get network status and hardware info with timeouts
        data['render_ports'] = safe_execute(_quick_render_port_check, timeout=2, default=[])
        data['network_status'] = safe_execute(_get_basic_network_status, timeout=2, default={'internet_connected': False, 'dns_working': False, 'local_network': False})
        data['network_hardware'] = safe_execute(_get_network_hardware, timeout=5, default={'adapters': [], 'total_adapters': 0, 'active_adapters': 0, 'wifi_adapters': 0, 'ethernet_adapters': 0})
        data['active_hosts_count'] = safe_execute(lambda: _quick_active_hosts_count(data['local_ip']), timeout=2, default=0)
        
        # Router and connected devices information with timeouts
        data['router_info'] = safe_execute(_get_router_info, timeout=5, default={'ip': None, 'mac': None, 'model': 'Unknown', 'brand': 'Unknown', 'manufacturer': 'Unknown'})
        data['connected_devices'] = safe_execute(_get_connected_devices, timeout=8, default=[])
        data['global_ip'] = safe_execute(_get_global_ip, timeout=1, default="Unknown")
        
        return data
        
    except Exception as e:
        return {"error": f"Error getting network info: {e}"}


def _get_local_ip():
    """Get the local IP address."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"


def _get_gateway():
    """Get the default gateway quickly."""
    try:
        if platform.system() == "Windows":
            # Fast Windows route command
            result = subprocess.run(['route', 'print', '0.0.0.0'], 
                                      capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if '0.0.0.0' in line and 'Gateway' not in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]
        else:
            # Fast Unix route command
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                      capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'default via' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]
    except Exception:
        pass
    return None


def _get_network_range(local_ip):
    """Get the network range for the local IP quickly."""
    try:
        if platform.system() == "Windows":
            # Fast Windows ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if local_ip in line:
                        # Look for subnet mask in next few lines
                        for j in range(i+1, min(i+5, len(lines))):
                            if 'Subnet Mask' in lines[j]:
                                mask_line = lines[j]
                                if ':' in mask_line:
                                    mask = mask_line.split(':')[1].strip()
                                    cidr = _mask_to_cidr(mask)
                                    if cidr:
                                        return f"{local_ip}/{cidr}"
        else:
            # Fast Unix ip command
            result = subprocess.run(['ip', 'route', 'get', '1.1.1.1'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'src' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'src' and i+1 < len(parts):
                                src_ip = parts[i+1]
                                # Estimate /24 for most home networks
                                return f"{src_ip}/24"
    except Exception:
        pass
    return None


def _mask_to_cidr(mask):
    """Convert subnet mask to CIDR notation."""
    try:
        parts = mask.split('.')
        if len(parts) == 4:
            binary = ''.join(format(int(part), '08b') for part in parts)
            return str(binary.count('1'))
    except Exception:
        pass
    return None


def _quick_render_port_check():
    """Quick check of common render farm ports."""
    render_ports = [8080, 8000, 8081, 3000, 5000, 9000]
    open_ports = []
    
    for port in render_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)  # Fast timeout
                result = sock.connect_ex(('127.0.0.1', port))
                if result == 0:
                    open_ports.append(port)
        except Exception:
            pass
    
    return sorted(open_ports)


def _get_basic_network_status():
    """Get basic network connectivity status."""
    status = {
        'internet_connected': False,
        'dns_working': False,
        'local_network': False
    }
    
    try:
        # Test internet connectivity with faster timeout
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)  # Faster timeout
            result = sock.connect_ex(('8.8.8.8', 53))
            status['internet_connected'] = (result == 0)
        
        # Test DNS resolution with timeout
        try:
            socket.setdefaulttimeout(0.5)
            socket.gethostbyname('google.com')
            status['dns_working'] = True
        except Exception:
            pass
        finally:
            socket.setdefaulttimeout(None)
        
        # Test local network
        local_ip = _get_local_ip()
        if local_ip and local_ip != "127.0.0.1":
            status['local_network'] = True
            
    except Exception:
        pass
    
    return status


def _get_network_hardware():
    """Get network hardware information quickly."""
    hardware = {
        'adapters': [],
        'total_adapters': 0,
        'active_adapters': 0,
        'wifi_adapters': 0,
        'ethernet_adapters': 0
    }
    
    try:
        if platform.system() == "Windows":
            # Fast Windows network adapter info
            result = subprocess.run(['powershell', '-Command', 
                'Get-NetAdapter | Select-Object Name, InterfaceDescription, LinkSpeed, Status | ConvertTo-Json'], 
                capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0 and result.stdout.strip():
                import json
                try:
                    adapters = json.loads(result.stdout)
                    if not isinstance(adapters, list):
                        adapters = [adapters]
                    
                    for adapter in adapters:
                        adapter_info = {
                            'name': adapter.get('Name', 'Unknown'),
                            'description': adapter.get('InterfaceDescription', 'Unknown'),
                            'speed': adapter.get('LinkSpeed', 'Unknown'),
                            'status': adapter.get('Status', 'Unknown'),
                            'type': 'Unknown'
                        }
                        
                        # Determine adapter type
                        desc = adapter_info['description'].lower()
                        if 'wireless' in desc or 'wifi' in desc or '802.11' in desc:
                            adapter_info['type'] = 'WiFi'
                            hardware['wifi_adapters'] += 1
                        elif 'ethernet' in desc or 'gigabit' in desc or 'lan' in desc:
                            adapter_info['type'] = 'Ethernet'
                            hardware['ethernet_adapters'] += 1
                        
                        # Count active adapters
                        if adapter_info['status'] == 'Up':
                            hardware['active_adapters'] += 1
                        
                        hardware['adapters'].append(adapter_info)
                        hardware['total_adapters'] += 1
                        
                except json.JSONDecodeError:
                    pass
        else:
            # Fast Unix network interface info
            result = subprocess.run(['ip', 'link', 'show'], 
                capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                current_adapter = None
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith(' ') and ':' in line:
                        if current_adapter:
                            hardware['adapters'].append(current_adapter)
                            hardware['total_adapters'] += 1
                            if current_adapter['status'] == 'Up':
                                hardware['active_adapters'] += 1
                        
                        # Parse interface name and status
                        parts = line.split(':')
                        if len(parts) >= 2:
                            name = parts[1].strip()
                            status = 'Up' if 'UP' in line else 'Down'
                            
                            # Determine type
                            adapter_type = 'Unknown'
                            if 'wlan' in name or 'wifi' in name:
                                adapter_type = 'WiFi'
                                hardware['wifi_adapters'] += 1
                            elif 'eth' in name or 'en' in name:
                                adapter_type = 'Ethernet'
                                hardware['ethernet_adapters'] += 1
                            
                            current_adapter = {
                                'name': name,
                                'description': f"Network interface {name}",
                                'speed': 'Unknown',
                                'status': status,
                                'type': adapter_type
                            }
                
                # Add the last adapter
                if current_adapter:
                    hardware['adapters'].append(current_adapter)
                    hardware['total_adapters'] += 1
                    if current_adapter['status'] == 'Up':
                        hardware['active_adapters'] += 1
                        
    except Exception:
        pass
    
    return hardware


def _quick_active_hosts_count(local_ip):
    """Quick count of active hosts in the network."""
    try:
        # Extract network base (e.g., 192.168.1 from 192.168.1.100)
        base = '.'.join(local_ip.split('.')[:-1])
        
        # Test only the most common IPs (very fast)
        common_ips = [
            f"{base}.1",    # Gateway
            f"{base}.2",    # Common server
            f"{base}.100",  # Common workstation
            f"{base}.254",  # Common device
        ]
        
        active_count = 0
        for ip in common_ips:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)  # Fast timeout
                    result = sock.connect_ex((ip, 80))  # Try HTTP port
                    if result == 0:
                        active_count += 1
            except Exception:
                pass
        
        return active_count
        
    except Exception:
        return 0


def _get_global_ip():
    """Get the global/public IP address using local methods only."""
    try:
        # Use local network information to determine if we have internet
        # but don't make external API calls for security
        local_ip = _get_local_ip()
        if local_ip and local_ip != "127.0.0.1":
            # We have a local network connection
            # Return a placeholder indicating we're connected but not exposing external IP
            return "Connected (External IP hidden for security)"
        else:
            return "No external connection"
            
    except Exception:
        pass
    return "Unknown"


def _get_router_info():
    """Get router information including model, brand, and IP."""
    router_info = {
        'ip': None,
        'mac': None,
        'model': 'Unknown',
        'brand': 'Unknown',
        'manufacturer': 'Unknown'
    }
    
    try:
        # Get gateway IP (router IP)
        gateway = _get_gateway()
        if gateway:
            router_info['ip'] = gateway
            
            # Try to get router MAC address
            if platform.system() == "Windows":
                result = subprocess.run(['arp', '-a', gateway], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if gateway in line and 'dynamic' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                router_info['mac'] = parts[1]
                                break
            else:
                result = subprocess.run(['arp', '-n', gateway], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if gateway in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                router_info['mac'] = parts[2]
                                break
            
            # Try to identify router brand/model from MAC address
            if router_info['mac']:
                router_info.update(_identify_router_from_mac(router_info['mac']))
            
            # Try to get router info via SNMP or HTTP
            router_info.update(_get_router_details(gateway))
            
    except Exception:
        pass
    
    return router_info


def _identify_router_from_mac(mac_address):
    """Identify router brand/model from MAC address OUI."""
    try:
        # Common router OUI prefixes
        oui_prefixes = {
            '00:50:56': {'brand': 'VMware', 'model': 'Virtual Router'},
            '00:0C:29': {'brand': 'VMware', 'model': 'Virtual Router'},
            '00:1C:42': {'brand': 'Parallels', 'model': 'Virtual Router'},
            '08:00:27': {'brand': 'Oracle', 'model': 'VirtualBox'},
            '00:15:5D': {'brand': 'Microsoft', 'model': 'Hyper-V'},
            '00:16:3E': {'brand': 'Xen', 'model': 'Virtual Router'},
            '52:54:00': {'brand': 'QEMU', 'model': 'Virtual Router'},
            '00:1B:21': {'brand': 'Intel', 'model': 'Wireless Router'},
            '00:1F:33': {'brand': 'Cisco', 'model': 'Router'},
            '00:26:08': {'brand': 'Cisco', 'model': 'Router'},
            'B8:27:EB': {'brand': 'Raspberry Pi', 'model': 'Foundation'},
            'DC:A6:32': {'brand': 'Raspberry Pi', 'model': 'Foundation'},
            'E4:5F:01': {'brand': 'Raspberry Pi', 'model': 'Foundation'},
        }
        
        mac_oui = mac_address[:8].upper()
        if mac_oui in oui_prefixes:
            return oui_prefixes[mac_oui]
        
        # Try to detect common router brands by MAC patterns
        if mac_address.startswith(('00:1B:21', '00:1F:33', '00:26:08')):
            return {'brand': 'Cisco', 'model': 'Router'}
        elif mac_address.startswith(('B8:27:EB', 'DC:A6:32', 'E4:5F:01')):
            return {'brand': 'Raspberry Pi', 'model': 'Foundation'}
        elif mac_address.startswith(('00:50:56', '00:0C:29')):
            return {'brand': 'VMware', 'model': 'Virtual Router'}
            
    except Exception:
        pass
    
    return {'brand': 'Unknown', 'model': 'Unknown'}


def _get_router_details(router_ip):
    """Get additional router details using local methods only."""
    details = {}
    
    try:
        # Use local network information to identify common router brands
        # based on MAC address patterns and local network behavior
        # No external HTTP requests
        
        # Common router brands can be identified by MAC address OUI
        # This is done in _identify_router_from_mac function
        
        # Additional local detection could be added here if needed
        # but we avoid external API calls for security and privacy
        pass
        
    except Exception:
        pass
    
    return details


def _get_connected_devices():
    """Get list of devices connected to the router."""
    devices = []
    
    try:
        if platform.system() == "Windows":
            # Get ARP table for connected devices
            result = subprocess.run(['arp', '-a'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'dynamic' in line.lower() and '192.168.' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            ip = parts[0]
                            mac = parts[1]
                            if ip and mac and ip != '0.0.0.0':
                                device_info = {
                                    'ip': ip,
                                    'mac': mac,
                                    'hostname': 'Unknown',
                                    'vendor': 'Unknown',
                                    'type': 'Unknown'
                                }
                                
                                # Try to get hostname
                                try:
                                    hostname = socket.gethostbyaddr(ip)[0]
                                    device_info['hostname'] = hostname
                                except Exception:
                                    pass
                                
                                # Identify device type by hostname patterns
                                hostname_lower = device_info['hostname'].lower()
                                if any(keyword in hostname_lower for keyword in ['phone', 'mobile', 'android', 'iphone']):
                                    device_info['type'] = 'Mobile Device'
                                elif any(keyword in hostname_lower for keyword in ['laptop', 'notebook', 'macbook']):
                                    device_info['type'] = 'Laptop'
                                elif any(keyword in hostname_lower for keyword in ['desktop', 'pc', 'computer']):
                                    device_info['type'] = 'Desktop'
                                elif any(keyword in hostname_lower for keyword in ['printer', 'print']):
                                    device_info['type'] = 'Printer'
                                elif any(keyword in hostname_lower for keyword in ['tv', 'smart-tv', 'roku', 'fire']):
                                    device_info['type'] = 'Smart TV'
                                elif any(keyword in hostname_lower for keyword in ['router', 'gateway', 'ap']):
                                    device_info['type'] = 'Router/AP'
                                else:
                                    device_info['type'] = 'Unknown Device'
                                
                                devices.append(device_info)
        else:
            # Unix/Linux ARP table
            result = subprocess.run(['arp', '-a'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '(' in line and ')' in line and 'at' in line:
                        # Parse format: hostname (192.168.1.1) at aa:bb:cc:dd:ee:ff
                        import re
                        ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', line)
                        mac_match = re.search(r'at ([0-9a-f:]{17})', line)
                        hostname_match = re.search(r'^([^(]+)', line)
                        
                        if ip_match and mac_match:
                            device_info = {
                                'ip': ip_match.group(1),
                                'mac': mac_match.group(1),
                                'hostname': hostname_match.group(1).strip() if hostname_match else 'Unknown',
                                'vendor': 'Unknown',
                                'type': 'Unknown'
                            }
                            
                            # Identify device type
                            hostname_lower = device_info['hostname'].lower()
                            if any(keyword in hostname_lower for keyword in ['phone', 'mobile', 'android', 'iphone']):
                                device_info['type'] = 'Mobile Device'
                            elif any(keyword in hostname_lower for keyword in ['laptop', 'notebook', 'macbook']):
                                device_info['type'] = 'Laptop'
                            elif any(keyword in hostname_lower for keyword in ['desktop', 'pc', 'computer']):
                                device_info['type'] = 'Desktop'
                            elif any(keyword in hostname_lower for keyword in ['printer', 'print']):
                                device_info['type'] = 'Printer'
                            elif any(keyword in hostname_lower for keyword in ['tv', 'smart-tv', 'roku', 'fire']):
                                device_info['type'] = 'Smart TV'
                            elif any(keyword in hostname_lower for keyword in ['router', 'gateway', 'ap']):
                                device_info['type'] = 'Router/AP'
                            else:
                                device_info['type'] = 'Unknown Device'
                            
                            devices.append(device_info)
                            
    except Exception:
        pass

    return devices


# ============================================================================
# INTERACTION FUNCTIONS (merged from interaction.py)
# ============================================================================

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


