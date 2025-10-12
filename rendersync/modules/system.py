# rendersync/modules/system.py
# This module is supposed to interact with the OS and the Computer running the platform
# For a network module refer to rendersync/modules/network.py, this one should be about:
# Hardware inspection, Computer Specs, Application PID, Application Memory, GPU, RAM, ROM, etc.


# Default Python Modules
import os
import platform
import subprocess
import sys
import socket
import time

# Third-party Modules
import psutil


def get_system_info_data():
    """Get system information as dictionary for web display."""
    try:
        data = {}
        
        # OS Information
        data['os'] = f"{platform.system()} {platform.release()}"
        data['architecture'] = platform.machine()
        data['architecture_bits'] = f"{platform.architecture()[0].split('bit')[0]}bit"
        data['platform'] = platform.platform()
        data['hostname'] = platform.node()
        data['python_version'] = platform.python_version()
        data['python_path'] = os.path.abspath(sys.executable)
        data['python_command'] = f"python -m rendersync.main"
        data['cpu'] = platform.processor().split(',')[0]
        
        # GPU Information
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split('\n')[0]
                if gpu_info:
                    parts = gpu_info.split(', ')
                    gpu_name = parts[0]
                    gpu_memory = parts[1] if len(parts) > 1 else "Unknown"
                    data['gpu'] = f"{gpu_name}, {gpu_memory} MB"
                else:
                    data['gpu'] = "Not detected"
            else:
                data['gpu'] = "Not available"
        except Exception:
            data['gpu'] = "Not available"
        
        # Memory Information
        data['ram'] = f"{psutil.virtual_memory().total // (1024**3)} GB Total"
        data['rom'] = f"{psutil.disk_usage('/').total // (1024**3)} GB Total"
        
        # Application Information
        try:
            current_process = psutil.Process()
            data['app_pid'] = str(current_process.pid)
            data['app_memory'] = f"{current_process.memory_info().rss // (1024*1024)} MB"
        except Exception:
            data['app_pid'] = "N/A"
            data['app_memory'] = "N/A"
        
            
        return data
        
    except Exception as e:
        return {"error": f"Error getting system info: {e}"}


def inspect_pid_data(pid_str):
    """Inspect a process by PID and return data for web display."""
    try:
        if not pid_str.strip():
            return {"error": "Please enter a PID number"}
            
        pid_int = int(pid_str)
        
        try:
            process = psutil.Process(pid_int)
            data = {}
            
            # Basic process info
            data['pid'] = process.pid
            data['name'] = process.name()
            data['status'] = process.status()
            data['cpu_percent'] = f"{process.cpu_percent(interval=0.1):.1f}%"
            data['memory_mb'] = f"{process.memory_info().rss // (1024*1024)} MB"
            data['create_time'] = process.create_time()
            
            # Command line
            try:
                cmdline = process.cmdline()
                if cmdline:
                    data['command'] = ' '.join(cmdline)
                else:
                    data['command'] = "N/A"
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                data['command'] = "Access denied"
            
            # Network connections
            try:
                connections = process.connections()
                if connections:
                    data['network_connections'] = []
                    for i, conn in enumerate(connections[:10]):  # Limit to first 10 connections
                        local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
                        remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                        data['network_connections'].append({
                            'local': local_addr,
                            'remote': remote_addr,
                            'status': conn.status,
                            'type': conn.type.name
                        })
                    if len(connections) > 10:
                        data['total_connections'] = len(connections)
                else:
                    data['network_connections'] = []
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                data['network_connections'] = "Access denied"
            except Exception as e:
                data['network_connections'] = f"Error: {e}"
            
            # Open files
            try:
                open_files = process.open_files()
                if open_files:
                    data['open_files'] = []
                    for file in open_files[:5]:  # Show first 5
                        data['open_files'].append(file.path)
                    if len(open_files) > 5:
                        data['total_open_files'] = len(open_files)
                else:
                    data['open_files'] = []
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                data['open_files'] = "Access denied"
            except Exception as e:
                data['open_files'] = f"Error: {e}"
            
            return data
                
        except psutil.NoSuchProcess:
            return {"error": f"Process {pid_int} not found"}
        except psutil.AccessDenied:
            return {"error": f"Access denied to process {pid_int}"}
        except Exception as e:
            return {"error": f"Error inspecting process: {e}"}
            
    except ValueError:
        return {"error": f"'{pid_str}' is not a valid PID"}
    except Exception as e:
        return {"error": f"Error: {e}"}


def ping_ip_data(ip_or_hostname, port=None, timeout=3, count=1):
    """Ping an IP address or hostname and optionally check a specific port."""
    try:
        if not ip_or_hostname.strip():
            return {"error": "Please enter an IP address or hostname"}
        
        results = {
            'target': ip_or_hostname,
            'port': port,
            'ping_results': [],
            'port_results': [],
            'summary': {}
        }
        
        # ICMP Ping (if available)
        ping_success = False
        ping_times = []
        
        try:
            # Try to ping using system ping command
            if sys.platform == "win32":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), ip_or_hostname]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(timeout), ip_or_hostname]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            end_time = time.time()
            
            if result.returncode == 0:
                ping_success = True
                # Parse ping times from output
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if 'time=' in line.lower() or 'time<' in line.lower():
                        # Extract time values
                        import re
                        time_match = re.search(r'time[<=](\d+(?:\.\d+)?)', line.lower())
                        if time_match:
                            ping_times.append(float(time_match.group(1)))
                
                if not ping_times:
                    # Fallback: estimate from total time
                    ping_times = [(end_time - start_time) * 1000]
                
                results['ping_results'] = ping_times
                results['summary']['ping_success'] = True
                results['summary']['ping_avg_time'] = sum(ping_times) / len(ping_times) if ping_times else 0
            else:
                results['summary']['ping_success'] = False
                results['summary']['ping_error'] = "Host unreachable"
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            results['summary']['ping_success'] = False
            results['summary']['ping_error'] = f"Ping failed: {str(e)}"
        
        # Port check (if specified)
        if port:
            try:
                port_int = int(port)
                if 1 <= port_int <= 65535:
                    results['port'] = port_int
                    
                    # Check if port is open
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    
                    start_time = time.time()
                    result = sock.connect_ex((ip_or_hostname, port_int))
                    end_time = time.time()
                    connection_time = (end_time - start_time) * 1000
                    
                    sock.close()
                    
                    if result == 0:
                        results['port_results'].append({
                            'port': port_int,
                            'status': 'open',
                            'response_time': round(connection_time, 2)
                        })
                        results['summary']['port_open'] = True
                        results['summary']['port_response_time'] = round(connection_time, 2)
                    else:
                        results['port_results'].append({
                            'port': port_int,
                            'status': 'closed',
                            'response_time': round(connection_time, 2)
                        })
                        results['summary']['port_open'] = False
                        results['summary']['port_response_time'] = round(connection_time, 2)
                else:
                    results['summary']['port_error'] = "Port must be between 1 and 65535"
            except ValueError:
                results['summary']['port_error'] = f"'{port}' is not a valid port number"
            except Exception as e:
                results['summary']['port_error'] = f"Port check failed: {str(e)}"
        
        # DNS Resolution check
        try:
            resolved_ip = socket.gethostbyname(ip_or_hostname)
            results['summary']['dns_resolved'] = True
            results['summary']['resolved_ip'] = resolved_ip
        except socket.gaierror:
            results['summary']['dns_resolved'] = False
            results['summary']['dns_error'] = "DNS resolution failed"
        
        return results
        
    except Exception as e:
        return {"error": f"Ping failed: {str(e)}"}


def ping_multiple_ips_data(ip_list, port=None, timeout=2):
    """Ping multiple IPs sequentially (no threading)."""
    try:
        if not ip_list or not isinstance(ip_list, list):
            return {"error": "Please provide a list of IPs to ping"}
        
        results = {
            'targets': ip_list,
            'port': port,
            'scan_results': [],
            'summary': {
                'total_targets': len(ip_list),
                'successful_pings': 0,
                'open_ports': 0,
                'scan_duration': 0
            }
        }
        
        start_time = time.time()
        
        # Ping each IP sequentially (no threading)
        for ip in ip_list:
            try:
                result = ping_ip_data(ip, port, timeout, 1)
                results['scan_results'].append({
                    'ip': ip,
                    'result': result
                })
                
                # Update summary
                if not result.get('error'):
                    if result.get('summary', {}).get('ping_success'):
                        results['summary']['successful_pings'] += 1
                    if result.get('summary', {}).get('port_open'):
                        results['summary']['open_ports'] += 1
                        
            except Exception as e:
                results['scan_results'].append({
                    'ip': ip,
                    'result': {'error': f"Ping failed: {str(e)}"}
                })
        
        end_time = time.time()
        results['summary']['scan_duration'] = round(end_time - start_time, 2)
        
        return results
        
    except Exception as e:
        return {"error": f"Multi-ping failed: {str(e)}"}

