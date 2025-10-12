# Default Python Modules
import os
import platform
import subprocess
import textwrap
import time
import signal
import psutil
import logging
from typing import List, Dict, Any
from datetime import datetime


# ============================================================================
# DISK AND FILE SYSTEM UTILITIES
# ============================================================================

def get_current_disk_drive() -> str:
    """Get the current disk drive (e.g., C:\\) where the application is running."""
    try:
        # Get the current working directory
        current_path = os.getcwd()
        
        # Extract the drive letter (e.g., "C:" from "C:\Users\...")
        if platform.system() == "Windows":
            # On Windows, get the drive letter
            drive = os.path.splitdrive(current_path)[0]
            if drive:
                return drive + "\\"
            else:
                # Fallback: try to get from environment
                return os.environ.get('SystemDrive', 'C:') + "\\"
        else:
            # On Unix-like systems, return root directory
            return "/"
            
    except Exception as e:
        # Fallback to default drive
        return "C:\\" if platform.system() == "Windows" else "/"


def get_powershell_history_file_path() -> str:
    """Get the PowerShell history file path for all Windows versions."""
    try:
        # Get user profile directory
        user_profile = os.path.expanduser("~")
        
        # Possible PowerShell history locations (in order of preference)
        possible_paths = [
            # Windows 10/11 with PSReadLine (most common)
            os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Windows", "PowerShell", "PSReadLine", "ConsoleHost_history.txt"),
            # Windows 10/11 alternative location
            os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Windows", "PowerShell", "PSReadLine", "Microsoft.PowerShell_profile.ps1"),
            # Windows 7/8/Server versions
            os.path.join(user_profile, "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1"),
            # Legacy PowerShell locations
            os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "PowerShell", "PSReadLine", "ConsoleHost_history.txt"),
            # PowerShell Core locations
            os.path.join(user_profile, "Documents", "PowerShell", "Microsoft.PowerShell_profile.ps1"),
        ]
        
        # Check each possible path
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If no file found, return the most likely location for error reporting
        return possible_paths[0]
        
    except Exception:
        # Fallback to default location
        return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "PowerShell", "PSReadLine", "ConsoleHost_history.txt")


# ============================================================================
# POWERSHELL AND COMMAND HISTORY UTILITIES
# ============================================================================

def get_powershell_history(limit: int = 50) -> str:
    """Get the last N commands from PowerShell history on Windows (cross-platform compatible)."""
    try:
        # Only work on Windows
        if platform.system() != "Windows":
            return "PowerShell history is only available on Windows"
        
        # Get the correct history file path
        history_file = get_powershell_history_file_path()
        
        if not os.path.exists(history_file):
            return f"PowerShell history file not found at: {history_file}"
        
        # Read the history file with multiple encoding attempts
        lines = []
        encodings = ['utf-8', 'utf-16', 'cp1252', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(history_file, 'r', encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue
        
        if not lines:
            return f"Could not read PowerShell history file: {history_file}"
        
        # Get the last N lines (most recent commands)
        recent_commands = lines[-limit:] if len(lines) >= limit else lines
        
        # Format the output
        history_text = f"Last {len(recent_commands)} PowerShell Commands:\n"
        history_text += f"Source: {history_file}\n"
        history_text += "=" * 50 + "\n"
        
        for i, command in enumerate(recent_commands, 1):
            command = command.strip()
            if command:  # Skip empty lines
                history_text += f"{i:2d}. {command}\n"
        
        return history_text
        
    except Exception as e:
        return f"Error retrieving PowerShell history: {str(e)}"


# ============================================================================
# TEXT AND UI UTILITIES
# ============================================================================

def wrap_text(text: str, max_width: int = 80) -> str:
    """Wrap text to fit within container width."""
    return textwrap.fill(text, width=max_width, break_long_words=True, break_on_hyphens=False)


def open_with_os(file_path) -> None:
    """Open file/folder with OS default application."""
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(file_path)
        elif system == "Darwin":  # macOS
            os.system(f"open '{file_path}'")
        else:  # Linux and others
            os.system(f"xdg-open '{file_path}'")
    except Exception as e:
        raise Exception(f"Failed to open {file_path}: {e}")


# ============================================================================
# PROCESS MANAGEMENT SYSTEM
# ============================================================================
class ProcessManager:
    """Cross-platform process management for tracking and terminating spawned processes."""
    
    def __init__(self):
        self.tracked_processes = []
        self.start_time = time.time()
        self.max_load_time = 20  # seconds
        self.parent_pid = os.getpid()
        
    def track_process(self, process):
        """Track a spawned process."""
        if process and hasattr(process, 'pid'):
            self.tracked_processes.append({
                'pid': process.pid,
                'start_time': time.time(),
                'process': process
            })
            print(f"[ProcessManager] Tracking process PID: {process.pid}")
    
    def get_spawned_processes(self):
        """Get all processes spawned by this application."""
        spawned = []
        try:
            current_process = psutil.Process(self.parent_pid)
            children = current_process.children(recursive=True)
            
            for child in children:
                try:
                    # Check if it's a terminal/PowerShell process
                    if self._is_terminal_process(child):
                        spawned.append({
                            'pid': child.pid,
                            'name': child.name(),
                            'cmdline': ' '.join(child.cmdline()) if child.cmdline() else '',
                            'create_time': child.create_time(),
                            'status': child.status()
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"[ProcessManager] Error getting spawned processes: {e}")
        
        return spawned
    
    def _is_terminal_process(self, process):
        """Check if process is a terminal/PowerShell/command prompt."""
        try:
            name = process.name().lower()
            cmdline = ' '.join(process.cmdline()).lower() if process.cmdline() else ''
            
            # Windows terminal processes
            if platform.system() == "Windows":
                terminal_names = [
                    'powershell.exe', 'cmd.exe', 'pwsh.exe', 'wt.exe', 'conhost.exe',
                    'powershell_ise.exe', 'powershell_ise.exe', 'wsl.exe', 'bash.exe',
                    'ubuntu.exe', 'debian.exe', 'kali.exe', 'opensuse.exe', 'sles.exe',
                    'windows-terminal.exe', 'terminal.exe', 'hyper.exe', 'alacritty.exe',
                    'wezterm.exe', 'tabby.exe', 'terminus.exe', 'fltterm.exe'
                ]
                return any(term in name for term in terminal_names)
            
            # Unix/Linux terminal processes
            else:
                terminal_names = ['bash', 'sh', 'zsh', 'fish', 'dash', 'ksh', 'csh', 'tcsh']
                terminal_terms = ['terminal', 'xterm', 'gnome-terminal', 'konsole', 'alacritty']
                return (any(term in name for term in terminal_names) or 
                       any(term in cmdline for term in terminal_terms))
        except Exception:
            return False
    
    def check_load_timeout(self):
        """Check if application has been loading too long."""
        elapsed = time.time() - self.start_time
        if elapsed > self.max_load_time:
            print(f"\n[ProcessManager] APPLICATION LOAD TIMEOUT ({elapsed:.1f}s > {self.max_load_time}s)")
            print("[ProcessManager] Terminating all spawned processes...")
            self.terminate_all_processes()
            return True
        return False
    
    def terminate_all_processes(self):
        """Terminate all tracked and spawned processes."""
        terminated_count = 0
        
        # Terminate tracked processes first
        for proc_info in self.tracked_processes[:]:
            try:
                if proc_info['process'].poll() is None:  # Still running
                    print(f"[ProcessManager] Terminating tracked process PID: {proc_info['pid']}")
                    self._terminate_process(proc_info['process'])
                    terminated_count += 1
            except Exception as e:
                print(f"[ProcessManager] Error terminating tracked process {proc_info['pid']}: {e}")
        
        # Terminate all spawned terminal processes
        spawned = self.get_spawned_processes()
        for proc_info in spawned:
            try:
                process = psutil.Process(proc_info['pid'])
                if process.is_running():
                    print(f"[ProcessManager] Terminating spawned process: {proc_info['name']} (PID: {proc_info['pid']})")
                    self._terminate_process(process)
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"[ProcessManager] Could not terminate process {proc_info['pid']}: {e}")
        
        print(f"[ProcessManager] Terminated {terminated_count} processes")
        return terminated_count
    
    def _terminate_process(self, process):
        """Safely terminate a process with fallback methods."""
        try:
            # Try graceful termination first
            if platform.system() == "Windows":
                process.terminate()
                time.sleep(1)
                if process.is_running():
                    process.kill()
            else:
                process.terminate()
                time.sleep(1)
                if process.is_running():
                    process.kill()
        except Exception as e:
            print(f"[ProcessManager] Error terminating process {process.pid}: {e}")
    
    def get_process_status(self):
        """Get current status of all tracked processes."""
        status = {
            'parent_pid': self.parent_pid,
            'elapsed_time': time.time() - self.start_time,
            'tracked_count': len(self.tracked_processes),
            'spawned_count': len(self.get_spawned_processes()),
            'timeout_warning': self.check_load_timeout()
        }
        return status
    
    def cleanup(self):
        """Clean up all tracked processes on exit."""
        print("[ProcessManager] Cleaning up processes...")
        self.terminate_all_processes()


# Global process manager instance
_process_manager = ProcessManager()


def get_process_manager():
    """Get the global process manager instance."""
    return _process_manager


def track_spawned_process(process):
    """Track a spawned process globally."""
    _process_manager.track_process(process)


def check_application_timeout():
    """Check if application should be terminated due to timeout."""
    return _process_manager.check_load_timeout()


def terminate_all_spawned_processes():
    """Terminate all processes spawned by this application."""
    return _process_manager.terminate_all_processes()


def get_application_status():
    """Get current application process status."""
    return _process_manager.get_process_status()


def cleanup_processes():
    """Clean up all processes on application exit."""
    _process_manager.cleanup()


def get_terminal_info():
    """Get comprehensive information about all open terminals and their processes."""
    try:
        terminal_info = {
            'total_terminals': 0,
            'active_terminals': 0,
            'terminals': [],
            'platform': platform.system()
        }
        
        if platform.system() == "Windows":
            terminal_info.update(_get_windows_terminals())
        else:
            terminal_info.update(_get_unix_terminals())
        
        return terminal_info
        
    except Exception as e:
        return {"error": f"Error getting terminal info: {e}"}


def _get_windows_terminals():
    """Get Windows terminal information."""
    terminals = []
    terminal_processes = []
    
    try:
        # Windows terminal process names and their characteristics
        terminal_configs = {
            'powershell.exe': {
                'name': 'PowerShell',
                'type': 'Shell',
                'icon': '🔷',
                'description': 'Windows PowerShell'
            },
            'pwsh.exe': {
                'name': 'PowerShell Core',
                'type': 'Shell',
                'icon': '🔷',
                'description': 'PowerShell Core (Cross-platform)'
            },
            'cmd.exe': {
                'name': 'Command Prompt',
                'type': 'Shell',
                'icon': '⚫',
                'description': 'Windows Command Prompt'
            },
            'wt.exe': {
                'name': 'Windows Terminal',
                'type': 'Terminal',
                'icon': '🪟',
                'description': 'Windows Terminal (Modern)'
            },
            'windows-terminal.exe': {
                'name': 'Windows Terminal',
                'type': 'Terminal',
                'icon': '🪟',
                'description': 'Windows Terminal (Legacy)'
            },
            'conhost.exe': {
                'name': 'Console Host',
                'type': 'Host',
                'icon': '🖥️',
                'description': 'Windows Console Host'
            },
            'wsl.exe': {
                'name': 'WSL',
                'type': 'Subsystem',
                'icon': '🐧',
                'description': 'Windows Subsystem for Linux'
            },
            'bash.exe': {
                'name': 'Bash (WSL)',
                'type': 'Shell',
                'icon': '🐧',
                'description': 'Bash Shell (WSL)'
            },
            'ubuntu.exe': {
                'name': 'Ubuntu (WSL)',
                'type': 'Distribution',
                'icon': '🐧',
                'description': 'Ubuntu on WSL'
            },
            'debian.exe': {
                'name': 'Debian (WSL)',
                'type': 'Distribution',
                'icon': '🐧',
                'description': 'Debian on WSL'
            },
            'kali.exe': {
                'name': 'Kali (WSL)',
                'type': 'Distribution',
                'icon': '🐧',
                'description': 'Kali Linux on WSL'
            },
            'opensuse.exe': {
                'name': 'openSUSE (WSL)',
                'type': 'Distribution',
                'icon': '🐧',
                'description': 'openSUSE on WSL'
            },
            'hyper.exe': {
                'name': 'Hyper',
                'type': 'Terminal',
                'icon': '⚡',
                'description': 'Hyper Terminal'
            },
            'alacritty.exe': {
                'name': 'Alacritty',
                'type': 'Terminal',
                'icon': '⚡',
                'description': 'Alacritty Terminal'
            },
            'wezterm.exe': {
                'name': 'WezTerm',
                'type': 'Terminal',
                'icon': '⚡',
                'description': 'WezTerm Terminal'
            },
            'tabby.exe': {
                'name': 'Tabby',
                'type': 'Terminal',
                'icon': '⚡',
                'description': 'Tabby Terminal'
            },
            'terminus.exe': {
                'name': 'Terminus',
                'type': 'Terminal',
                'icon': '⚡',
                'description': 'Terminus Terminal'
            },
            'fltterm.exe': {
                'name': 'Fluent Terminal',
                'type': 'Terminal',
                'icon': '⚡',
                'description': 'Fluent Terminal'
            }
        }
        
        # Scan all processes for terminals
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status', 'cwd', 'exe']):
            try:
                proc_info = proc.info
                proc_name = proc_info['name'].lower()
                
                # Check if this is a terminal process
                if proc_name in terminal_configs:
                    config = terminal_configs[proc_name]
                    
                    # Get additional process details
                    try:
                        process = psutil.Process(proc_info['pid'])
                        cpu_percent = process.cpu_percent()
                        memory_info = process.memory_info()
                        create_time = process.create_time()
                        
                        # Get working directory
                        try:
                            cwd = process.cwd()
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            cwd = "Access Denied"
                        
                        # Get command line arguments
                        cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else 'N/A'
                        
                        # Get last few commands (fast approach)
                        last_commands = _get_last_commands_fast(proc_info['pid'])
                        
                        # Determine if it's actively running
                        is_active = proc_info['status'] in ['running', 'sleeping']
                        
                        terminal_data = {
                            'pid': proc_info['pid'],
                            'name': config['name'],
                            'type': config['type'],
                            'icon': config['icon'],
                            'description': config['description'],
                            'status': proc_info['status'],
                            'is_active': is_active,
                            'cpu_percent': round(cpu_percent, 1),
                            'memory_mb': round(memory_info.rss / 1024 / 1024, 1),
                            'working_directory': cwd,
                            'command_line': cmdline,
                            'last_commands': last_commands,
                            'start_time': time.strftime('%H:%M:%S', time.localtime(create_time)),
                            'uptime_seconds': int(time.time() - create_time)
                        }
                        
                        terminals.append(terminal_data)
                        terminal_processes.append(proc_info['pid'])
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process disappeared or access denied
                        terminal_data = {
                            'pid': proc_info['pid'],
                            'name': config['name'],
                            'type': config['type'],
                            'icon': config['icon'],
                            'description': config['description'],
                            'status': 'Access Denied',
                            'is_active': False,
                            'cpu_percent': 0,
                            'memory_mb': 0,
                            'working_directory': 'Access Denied',
                            'command_line': 'Access Denied',
                            'start_time': 'Unknown',
                            'uptime_seconds': 0
                        }
                        terminals.append(terminal_data)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort terminals by PID
        terminals.sort(key=lambda x: x['pid'])
        
        return {
            'total_terminals': len(terminals),
            'active_terminals': len([t for t in terminals if t['is_active']]),
            'terminals': terminals
        }
        
    except Exception as e:
        return {"error": f"Error scanning Windows terminals: {e}"}


def _get_last_commands_fast(pid):
    """Get last few commands for a terminal process (fast approach)."""
    try:
        # For Windows, try to get PowerShell history if it's a PowerShell process
        if platform.system() == "Windows":
            # Check if this might be a PowerShell process
            try:
                process = psutil.Process(pid)
                if 'powershell' in process.name().lower():
                    # Try to get recent PowerShell history
                    history_file = get_powershell_history_file_path()
                    if os.path.exists(history_file):
                        try:
                            with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                # Get last 3 commands
                                recent_commands = [line.strip() for line in lines[-3:] if line.strip()]
                                if recent_commands:
                                    return ' ; '.join(recent_commands)
                        except Exception:
                            pass
            except Exception:
                pass
        
        # Fallback: return a simple indicator
        return "History not available"
        
    except Exception:
        return "History not available"


def _get_unix_terminals():
    """Get Unix/Linux terminal information (placeholder implementation)."""
    # Placeholder for Linux/Unix terminal detection
    return {
        'total_terminals': 0,
        'active_terminals': 0,
        'terminals': [],
        'note': 'Linux/Unix terminal detection not yet implemented'
    }


def monitor_application_startup():
    """Monitor application startup and terminate if it takes too long."""
    print(f"[ProcessManager] Starting application monitoring (max {_process_manager.max_load_time}s)")
    
    # Check timeout every 2 seconds
    while True:
        if _process_manager.check_load_timeout():
            print("[ProcessManager] Application terminated due to timeout")
            break
        
        time.sleep(2)
        
        # If we've been running for more than 30 seconds, stop monitoring
        if time.time() - _process_manager.start_time > 30:
            print("[ProcessManager] Application startup monitoring complete")
            break


# ============================================================================
# RUNNING APPLICATIONS INFORMATION
# ============================================================================

def get_apps_running_info() -> Dict[str, Any]:
    """Get information about running applications similar to Task Manager."""
    try:
        apps = []
        gui_apps = 0
        background_apps = 0
        
        # Get all running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 
                                        'create_time', 'status', 'username', 'exe']):
            try:
                proc_info = proc.info
                
                # Skip system processes that are not user applications
                if not proc_info['name'] or proc_info['name'] in ['System', 'Idle', 'Registry']:
                    continue
                
                # Get process details
                pid = proc_info['pid']
                name = proc_info['name'] or 'Unknown'
                cmdline = proc_info['cmdline'] or []
                cpu_percent = proc_info['cpu_percent'] or 0
                memory_info = proc_info['memory_info']
                create_time = proc_info['create_time']
                status = proc_info['status'] or 'Unknown'
                username = proc_info['username'] or 'Unknown'
                exe = proc_info['exe'] or ''
                
                # Calculate memory usage in MB
                memory_mb = round(memory_info.rss / 1024 / 1024, 1) if memory_info else 0
                
                # Determine if it's a GUI application
                is_gui = False
                app_type = 'Background'
                icon = '🔧'
                
                # Check for GUI applications
                if exe:
                    exe_lower = exe.lower()
                    if any(gui_indicator in exe_lower for gui_indicator in [
                        'explorer.exe', 'chrome.exe', 'firefox.exe', 'edge.exe', 'notepad.exe',
                        'wordpad.exe', 'calc.exe', 'mspaint.exe', 'winword.exe', 'excel.exe',
                        'powerpnt.exe', 'outlook.exe', 'teams.exe', 'discord.exe', 'spotify.exe',
                        'vlc.exe', 'obs64.exe', 'obs32.exe', 'steam.exe', 'epicgameslauncher.exe',
                        'photoshop.exe', 'illustrator.exe', 'afterfx.exe', 'premiere.exe',
                        'blender.exe', 'maya.exe', '3dsmax.exe', 'unity.exe', 'unreal.exe',
                        'code.exe', 'devenv.exe', 'notepad++.exe', 'sublime_text.exe',
                        'atom.exe', 'pycharm64.exe', 'idea64.exe', 'webstorm64.exe',
                        'comfyui', 'ollama', 'python.exe', 'node.exe', 'npm.exe'
                    ]):
                        is_gui = True
                        app_type = 'GUI'
                        icon = '🖥️'
                
                # Check for system applications
                if any(sys_indicator in name.lower() for sys_indicator in [
                    'system', 'windows', 'microsoft', 'svchost', 'winlogon', 'csrss',
                    'lsass', 'services', 'dwm', 'explorer'
                ]):
                    app_type = 'System'
                    icon = '⚙️'
                
                # Check for development tools
                if any(dev_indicator in name.lower() for dev_indicator in [
                    'python', 'node', 'npm', 'git', 'docker', 'compose', 'kubernetes',
                    'code', 'devenv', 'pycharm', 'idea', 'webstorm', 'sublime', 'atom',
                    'comfyui', 'ollama', 'rendersync'
                ]):
                    app_type = 'Development'
                    icon = '💻'
                
                # Format command line
                command_line = ' '.join(cmdline) if cmdline else exe
                if len(command_line) > 100:
                    command_line = command_line[:100] + '...'
                
                # Format start time
                try:
                    start_time = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    start_time = 'Unknown'
                
                # Determine if running
                is_running = status.lower() in ['running', 'sleeping']
                
                # Create app info
                app_info = {
                    'pid': pid,
                    'name': name,
                    'type': app_type,
                    'is_running': is_running,
                    'status': status,
                    'description': f"{name} - {app_type} Application",
                    'command_line': command_line,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'start_time': start_time,
                    'username': username,
                    'icon': icon
                }
                
                apps.append(app_info)
                
                # Count app types
                if is_gui:
                    gui_apps += 1
                else:
                    background_apps += 1
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process disappeared or we can't access it
                continue
            except Exception as e:
                logging.warning(f"Error processing process: {e}")
                continue
        
        # Sort apps by memory usage (descending) and then by name
        apps.sort(key=lambda x: (-x['memory_mb'], x['name']))
        
        # Limit to top 50 apps to avoid overwhelming the UI
        apps = apps[:50]
        
        return {
            'total_apps': len(apps),
            'gui_apps': gui_apps,
            'background_apps': background_apps,
            'apps': apps
        }
        
    except Exception as e:
        logging.error(f"Error getting apps running info: {e}")
        return {
            'error': str(e),
            'total_apps': 0,
            'gui_apps': 0,
            'background_apps': 0,
            'apps': []
        }


