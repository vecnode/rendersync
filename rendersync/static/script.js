// ============================================================================
// RENDERSYNC CORE - JAVASCRIPT FUNCTIONS
// ============================================================================

// ============================================================================
// PAGE INITIALIZATION
// ============================================================================

// Load workflows when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadWorkflows();
});

// ============================================================================

// ============================================================================
// SYSTEM INFORMATION FUNCTIONS
// ============================================================================

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system-info');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('system-info-rows').innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rows = document.getElementById('system-info-rows');
        
        // Automatically display all data fields
        const rowData = [];
        
        // Basic system info
        if (data.os) rowData.push(['OS', data.os]);
        if (data.platform) rowData.push(['Platform', data.platform]);
        if (data.architecture) rowData.push(['Architecture', data.architecture]);
        if (data.architecture_bits) rowData.push(['Architecture Bits', data.architecture_bits]);
        if (data.hostname) rowData.push(['Hostname', data.hostname]);
        
        // Python info
        if (data.python_version) rowData.push(['Python Version', data.python_version]);
        if (data.python_path) rowData.push(['Python Path', data.python_path]);
        if (data.python_command) rowData.push(['Python Command', data.python_command]);
        
        // Hardware info
        if (data.cpu) rowData.push(['CPU', data.cpu]);
        if (data.gpu) rowData.push(['GPU', data.gpu]);
        if (data.ram) rowData.push(['RAM', data.ram]);
        if (data.rom) rowData.push(['Storage', data.rom]);
        
        // Application info
        if (data.app_pid) rowData.push(['App PID', data.app_pid]);
        if (data.app_memory) rowData.push(['App Memory', data.app_memory]);
        
        // Process info
        if (data.processes) {
            rowData.push(['Total Processes', data.processes]);
        }
        if (data.processes_running) {
            rowData.push(['Running Processes', data.processes_running]);
        }
        
        // System uptime
        if (data.uptime) {
            rowData.push(['System Uptime', data.uptime]);
        }
        
        // Load averages (Unix)
        if (data.load_avg) {
            rowData.push(['Load Average', data.load_avg]);
        }
        
        // Disk usage
        if (data.disk_usage) {
            rowData.push(['Disk Usage', data.disk_usage]);
        }
        
        // Network interfaces
        if (data.network_interfaces) {
            rowData.push(['Network Interfaces', data.network_interfaces]);
        }
        
        // Display all data
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No system data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
    } catch (error) {
        document.getElementById('system-info-rows').innerHTML = `<tr><td colspan="2">Error loading system info: ${error.message}</td></tr>`;
    }
}

// ============================================================================
// NETWORK INFORMATION FUNCTIONS
// ============================================================================

async function loadNetworkInfo() {
    try {
        const response = await fetch('/api/network-info');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('network-info-rows').innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rows = document.getElementById('network-info-rows');
        
        // Automatically display all data fields
        const rowData = [];
        
        // Basic network info
        if (data.local_ip) rowData.push(['Local IP', data.local_ip]);
        if (data.gateway) rowData.push(['Gateway', data.gateway]);
        if (data.network_range) rowData.push(['Network Range', data.network_range]);
        if (data.hostname) rowData.push(['Hostname', data.hostname]);
        if (data.fqdn) rowData.push(['FQDN', data.fqdn]);
        
        // Network status
        if (data.network_status) {
            const status = data.network_status;
            if (status.internet_connected !== undefined) rowData.push(['Internet Connected', status.internet_connected ? 'Yes' : 'No']);
            if (status.dns_working !== undefined) rowData.push(['DNS Working', status.dns_working ? 'Yes' : 'No']);
            if (status.local_network !== undefined) rowData.push(['Local Network', status.local_network ? 'Yes' : 'No']);
        }
        
        // Render ports
        if (data.render_ports && data.render_ports.length > 0) {
            rowData.push(['Render Ports Open', data.render_ports.join(', ')]);
        }
        
        // Active hosts
        if (data.active_hosts_count !== undefined) rowData.push(['Active Hosts Count', data.active_hosts_count]);
        if (data.active_hosts && data.active_hosts.length > 0) {
            rowData.push(['Active Hosts', data.active_hosts.join(', ')]);
        }
        
        // Network hardware
        if (data.network_hardware) {
            const hw = data.network_hardware;
            if (hw.total_adapters !== undefined) rowData.push(['Total Adapters', hw.total_adapters]);
            if (hw.active_adapters !== undefined) rowData.push(['Active Adapters', hw.active_adapters]);
            if (hw.wifi_adapters !== undefined) rowData.push(['WiFi Adapters', hw.wifi_adapters]);
            if (hw.ethernet_adapters !== undefined) rowData.push(['Ethernet Adapters', hw.ethernet_adapters]);
            
            // Adapter details
            if (hw.adapters && hw.adapters.length > 0) {
                hw.adapters.forEach((adapter, index) => {
                    rowData.push([`Adapter ${index + 1}`, `${adapter.name} (${adapter.type}) - ${adapter.status} - ${adapter.speed}`]);
                });
            }
        }
        
        // Global IP
        if (data.global_ip) {
            rowData.push(['Global IP', data.global_ip]);
        }
        
        // Router information
        if (data.router_info) {
            const router = data.router_info;
            if (router.ip) rowData.push(['Router IP', router.ip]);
            if (router.mac) rowData.push(['Router MAC', router.mac]);
            if (router.brand) rowData.push(['Router Brand', router.brand]);
            if (router.model) rowData.push(['Router Model', router.model]);
            if (router.manufacturer) rowData.push(['Router Manufacturer', router.manufacturer]);
        }
        
        // Connected devices
        if (data.connected_devices && data.connected_devices.length > 0) {
            rowData.push(['Connected Devices Count', data.connected_devices.length]);
            data.connected_devices.forEach((device, index) => {
                rowData.push([`Device ${index + 1}`, `${device.hostname} (${device.type}) - ${device.ip} - ${device.mac}`]);
            });
        }
        
        // Display all data
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No network data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
    } catch (error) {
        document.getElementById('network-info-rows').innerHTML = `<tr><td colspan="2">Error loading network info: ${error.message}</td></tr>`;
    }
}

// ============================================================================
// TERMINAL INFORMATION FUNCTIONS
// ============================================================================

async function loadTerminalInfo() {
    try {
        const response = await fetch('/api/terminal-info');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('terminal-info-rows').innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rows = document.getElementById('terminal-info-rows');
        
        // Automatically display all data fields
        const rowData = [];
        
        // Basic terminal info
        if (data.platform) rowData.push(['Platform', data.platform]);
        if (data.total_terminals !== undefined) rowData.push(['Total Terminals', data.total_terminals]);
        if (data.active_terminals !== undefined) rowData.push(['Active Terminals', data.active_terminals]);
        
        // Individual terminal details
        if (data.terminals && data.terminals.length > 0) {
            data.terminals.forEach((terminal, index) => {
                const statusIcon = terminal.is_active ? '🟢' : '🔴';
                const uptime = Math.floor(terminal.uptime_seconds / 60) + 'm ' + (terminal.uptime_seconds % 60) + 's';
                const terminalId = `terminal-${index}`;
                
                let terminalInfo = `${terminal.name} (${terminal.type}) - ${statusIcon} ${terminal.status} `;
                terminalInfo += `<button onclick="toggleTerminal('${terminalId}')" style="font-size:10px; padding:1px 3px;">+</button><br>`;
                terminalInfo += `<div id="${terminalId}" style="display:none;">`;
                terminalInfo += `└─ PID: ${terminal.pid}<br>`;
                terminalInfo += `└─ Description: ${terminal.description}<br>`;
                terminalInfo += `└─ Running: ${terminal.command_line}<br>`;
                terminalInfo += `└─ Last Commands: ${terminal.last_commands}<br>`;
                terminalInfo += `└─ Start Time: ${terminal.start_time}<br>`;
                terminalInfo += `└─ Uptime: ${uptime}`;
                terminalInfo += `</div>`;
                
                // Check if this terminal is running this app
                const isRunningThisApp = terminal.command_line && 
                    (terminal.command_line.includes('rendersync') || 
                     terminal.command_line.includes('python') && terminal.command_line.includes('main.py'));
                
                const rowStyle = isRunningThisApp ? 'style="background-color: #d4edda;"' : '';
                rowData.push([`${terminal.icon} Terminal ${index + 1}`, terminalInfo, rowStyle]);
            });
        } else {
            rowData.push(['Terminals Found', 'No terminals detected']);
        }
        
        // Display all data
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No terminal data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => {
                if (row.length === 3) {
                    return `<tr ${row[2]}><td>${row[0]}</td><td>${row[1]}</td></tr>`;
                } else {
                    return `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`;
                }
            }).join('');
        }
    } catch (error) {
        document.getElementById('terminal-info-rows').innerHTML = `<tr><td colspan="2">Error loading terminal info: ${error.message}</td></tr>`;
    }
}

// ============================================================================
// UI INTERACTION FUNCTIONS
// ============================================================================

function toggleTerminal(terminalId) {
    const element = document.getElementById(terminalId);
    const parentDiv = element.parentElement;
    const button = parentDiv.querySelector('button');
    
    if (element.style.display === 'none' || element.style.display === '') {
        element.style.display = 'block';
        button.textContent = '-';
    } else {
        element.style.display = 'none';
        button.textContent = '+';
    }
}

function toggleModule(moduleId) {
    const element = document.getElementById(moduleId);
    const button = element.previousElementSibling.querySelector('button');
    
    if (element.style.display === 'none') {
        element.style.display = 'block';
        button.textContent = '-';
    } else {
        element.style.display = 'none';
        button.textContent = '+';
    }
}

// ============================================================================
// PORT INSPECTION FUNCTIONS
// ============================================================================

async function inspectPort() {
    const portInput = document.getElementById('port-input');
    const button = document.getElementById('inspect-port');
    const rows = document.getElementById('port-inspection-rows');
    
    const port = portInput.value.trim();
    if (!port) {
        rows.innerHTML = '<tr><td colspan="2">Please enter a port number</td></tr>';
        return;
    }
    
    if (port < 1 || port > 65535) {
        rows.innerHTML = '<tr><td colspan="2">Port must be between 1 and 65535</td></tr>';
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Inspecting';
    rows.innerHTML = '<tr><td colspan="2">Inspecting port ' + port + '</td></tr>';
    
    try {
        const response = await fetch('/api/inspect-port', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ port: parseInt(port) })
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
        } else {
            const rowData = [];
            
            // Basic port status
            rowData.push(['Port', data.port]);
            rowData.push(['Port Open', data.is_open ? 'Yes' : 'No']);
            rowData.push(['Port Listening', data.is_listening ? 'Yes' : 'No']);
            
            // Process information
            if (data.process_info) {
                rowData.push(['Process PID', data.process_info.pid]);
                rowData.push(['Process Name', data.process_info.name]);
                rowData.push(['Process Command', data.process_info.cmdline]);
                rowData.push(['Process Status', data.process_info.status]);
                if (data.process_info.cpu_percent !== undefined) {
                    rowData.push(['CPU Usage', data.process_info.cpu_percent + '%']);
                }
                if (data.process_info.memory_info) {
                    rowData.push(['Memory Usage', Math.round(data.process_info.memory_info.rss / 1024 / 1024) + ' MB']);
                }
            }
            
            // Connection information
            if (data.connection_info && data.connection_info.length > 0) {
                data.connection_info.forEach((conn, index) => {
                    rowData.push([`Connection ${index + 1}`, `${conn.local_address} -> ${conn.remote_address} (${conn.status})`]);
                });
            }
            
            // Network connections
            if (data.network_connections && data.network_connections.length > 0) {
                data.network_connections.forEach((conn, index) => {
                    rowData.push([`Network ${index + 1}`, `${conn.family} ${conn.type} - ${conn.local_address} -> ${conn.remote_address} (${conn.status})`]);
                });
            }
            
            // Display all data in table format
            if (rowData.length === 0) {
                rows.innerHTML = '<tr><td colspan="2">No port data available</td></tr>';
            } else {
                rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
            }
        }
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error inspecting port: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Inspect Port';
    }
}

// ============================================================================
// PID INSPECTION FUNCTIONS
// ============================================================================

async function inspectPID() {
    const pidInput = document.getElementById('pid-input');
    const button = document.getElementById('inspect-pid');
    const rows = document.getElementById('pid-inspection-rows');
    
    const pid = pidInput.value.trim();
    if (!pid) {
        rows.innerHTML = '<tr><td colspan="2">Please enter a PID number</td></tr>';
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Inspecting';
    rows.innerHTML = '<tr><td colspan="2">Inspecting PID ' + pid + '</td></tr>';
    
    try {
        const response = await fetch('/api/inspect-pid', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pid: pid })
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
        } else {
            const rowData = [];
            
            // Basic process info
            rowData.push(['PID', data.pid]);
            rowData.push(['Name', data.name]);
            rowData.push(['Status', data.status]);
            rowData.push(['CPU Percent', data.cpu_percent]);
            rowData.push(['Memory', data.memory_mb]);
            rowData.push(['Create Time', new Date(data.create_time * 1000).toLocaleString()]);
            rowData.push(['Command', data.command]);
            
            // Network connections
            if (data.network_connections && Array.isArray(data.network_connections)) {
                if (data.network_connections.length > 0) {
                    data.network_connections.forEach((conn, index) => {
                        rowData.push([`Connection ${index + 1}`, `${conn.local} -> ${conn.remote} (${conn.status}, ${conn.type})`]);
                    });
                    if (data.total_connections) {
                        rowData.push(['Total Connections', data.total_connections]);
                    }
                } else {
                    rowData.push(['Network Connections', 'No connections found']);
                }
            } else if (data.network_connections) {
                rowData.push(['Network Connections', data.network_connections]);
            }
            
            // Open files
            if (data.open_files && Array.isArray(data.open_files)) {
                if (data.open_files.length > 0) {
                    data.open_files.forEach((file, index) => {
                        rowData.push([`Open File ${index + 1}`, file]);
                    });
                    if (data.total_open_files) {
                        rowData.push(['Total Open Files', data.total_open_files]);
                    }
                } else {
                    rowData.push(['Open Files', 'No files found']);
                }
            } else if (data.open_files) {
                rowData.push(['Open Files', data.open_files]);
            }
            
            // Display all data in table format
            if (rowData.length === 0) {
                rows.innerHTML = '<tr><td colspan="2">No PID data available</td></tr>';
            } else {
                rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
            }
        }
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error inspecting PID: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Inspect PID';
    }
}

// ============================================================================
// PING FUNCTIONS
// ============================================================================

async function pingIP() {
    const pingInput = document.getElementById('ping-input');
    const portInput = document.getElementById('ping-port-input');
    const button = document.getElementById('ping-ip');
    const rows = document.getElementById('ping-results-rows');
    
    const target = pingInput.value.trim();
    const port = portInput.value.trim();
    
    if (!target) {
        rows.innerHTML = '<tr><td colspan="2">Please enter an IP address or hostname</td></tr>';
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Pinging';
    rows.innerHTML = '<tr><td colspan="2">Pinging ' + target + (port ? ':' + port : '') + '</td></tr>';
    
    try {
        const requestBody = {
            target: target,
            timeout: 3
        };
        
        if (port && port !== '') {
            requestBody.port = parseInt(port);
        }
        
        const response = await fetch('/api/ping-ip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
        } else {
            const rowData = [];
            
            // Basic target info
            rowData.push(['Target', data.target]);
            if (data.port) {
                rowData.push(['Port', data.port]);
            }
            
            // DNS Resolution
            if (data.summary.dns_resolved !== undefined) {
                rowData.push(['DNS Resolved', data.summary.dns_resolved ? 'Yes' : 'No']);
                if (data.summary.resolved_ip) {
                    rowData.push(['Resolved IP', data.summary.resolved_ip]);
                }
                if (data.summary.dns_error) {
                    rowData.push(['DNS Error', data.summary.dns_error]);
                }
            }
            
            // Ping Results
            if (data.summary.ping_success !== undefined) {
                rowData.push(['Ping Success', data.summary.ping_success ? 'Yes' : 'No']);
                if (data.summary.ping_avg_time !== undefined) {
                    rowData.push(['Average Ping Time', data.summary.ping_avg_time.toFixed(2) + ' ms']);
                }
                if (data.ping_results && data.ping_results.length > 0) {
                    rowData.push(['Ping Times', data.ping_results.map(t => t.toFixed(2) + 'ms').join(', ')]);
                }
                if (data.summary.ping_error) {
                    rowData.push(['Ping Error', data.summary.ping_error]);
                }
            }
            
            // Port Results
            if (data.port && data.summary.port_open !== undefined) {
                rowData.push(['Port Open', data.summary.port_open ? 'Yes' : 'No']);
                if (data.summary.port_response_time !== undefined) {
                    rowData.push(['Port Response Time', data.summary.port_response_time + ' ms']);
                }
                if (data.summary.port_error) {
                    rowData.push(['Port Error', data.summary.port_error]);
                }
            }
            
            // Display all data in table format
            if (rowData.length === 0) {
                rows.innerHTML = '<tr><td colspan="2">No ping data available</td></tr>';
            } else {
                rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
            }
        }
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error pinging: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Ping IP';
    }
}


// ============================================================================
// MARKDOWN RENDERING FUNCTIONS
// ============================================================================

function renderMarkdown(text) {
    if (!text) return '';
    
    // Escape HTML first to prevent XSS
    let html = text.replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;');
    
    // Convert code blocks (```code```)
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Convert inline code (`code`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Convert bold (**text**)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic (*text*)
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert URLs to clickable links
    html = html.replace(/(https?:\/\/[^\s<>"']+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    return html;
}

// ============================================================================
// OLLAMA INSPECTION FUNCTIONS
// ============================================================================

async function inspectOllama() {
    const button = document.getElementById('inspect-ollama');
    const rows = document.getElementById('ollama-info-rows');
    
    button.disabled = true;
    button.textContent = 'Inspecting';
    rows.innerHTML = '<tr><td colspan="2">Inspecting Ollama installation</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-status');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Installation status
        if (data.installed) {
            rowData.push(['Installation Status', 'Installed']);
            rowData.push(['Location', data.location]);
            if (data.version) {
                rowData.push(['Version', data.version]);
            }
        } else {
            rowData.push(['Installation Status', 'Not installed']);
            rowData.push(['Installation', '<a href="https://ollama.ai" target="_blank">https://ollama.ai</a>']);
        }
        
        // Running status
        if (data.running) {
            rowData.push(['Service Status', 'Running']);
            if (data.pid) {
                rowData.push(['Process ID', data.pid]);
            }
            if (data.api_responding !== undefined) {
                if (data.api_responding) {
                    rowData.push(['API Status', 'Responding']);
                } else {
                    rowData.push(['API Status', 'Not responding']);
                    if (data.api_error) {
                        rowData.push(['API Error', data.api_error]);
                    }
                }
            }
        } else {
            rowData.push(['Service Status', 'Not running']);
            if (data.installed) {
                rowData.push(['Start Command', 'ollama serve']);
            }
        }
        
        // Port status
        if (data.port_11434) {
            rowData.push(['Port 11434', 'In use']);
        } else {
            rowData.push(['Port 11434', 'Not in use']);
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No Ollama data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error inspecting Ollama: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Inspect ollama';
    }
}

async function stopOllama() {
    const button = document.getElementById('stop-ollama');
    const rows = document.getElementById('ollama-action-rows');
    
    button.disabled = true;
    button.textContent = 'Stopping';
    rows.innerHTML = '<tr><td colspan="2">Stopping Ollama processes</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Show results
        if (data.success) {
            if (data.total_stopped > 0) {
                rowData.push(['Output', `Successfully stopped ${data.total_stopped} Ollama process${data.total_stopped > 1 ? 'es' : ''}`]);
                
                if (data.stopped_processes && data.stopped_processes.length > 0) {
                    data.stopped_processes.forEach((proc, index) => {
                        const method = proc.method === 'terminate' ? 'Graceful' : 
                                      proc.method === 'kill' ? 'Force kill' : 'Already stopped';
                        rowData.push([`Process ${index + 1}`, `PID ${proc.pid} (${proc.name}) - ${method}`]);
                    });
                }
            } else {
                rowData.push(['Output', 'No Ollama processes were running to stop']);
            }
            
            if (data.errors && data.errors.length > 0) {
                rowData.push(['Warnings', data.errors.join('; ')]);
            }
        } else {
            rowData.push(['Output', 'Failed to stop processes']);
            rowData.push(['Message', data.message]);
            if (data.errors && data.errors.length > 0) {
                rowData.push(['Errors', data.errors.join('; ')]);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No stop data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error stopping Ollama: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Stop ollama';
    }
}

async function startOllama() {
    const button = document.getElementById('start-ollama');
    const rows = document.getElementById('ollama-action-rows');
    
    button.disabled = true;
    button.textContent = 'Starting';
    rows.innerHTML = '<tr><td colspan="2">Starting Ollama process</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Show results
        if (data.success) {
            if (data.already_running) {
                rowData.push(['Output', 'Ollama is already running']);
                if (data.pid) {
                    rowData.push(['Process ID', data.pid]);
                }
            } else {
                rowData.push(['Output', 'Ollama started successfully']);
                if (data.pid) {
                    rowData.push(['Process ID', data.pid]);
                }
                if (data.path) {
                    rowData.push(['Executable', data.path]);
                }
            }
            
            if (data.message) {
                rowData.push(['Status', data.message]);
            }
        } else {
            rowData.push(['Output', 'Failed to start Ollama']);
            if (data.error) {
                rowData.push(['Error', data.error]);
            }
            if (data.message) {
                rowData.push(['Message', data.message]);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No start data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error starting Ollama: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Start ollama';
    }
}

async function getOllamaModels() {
    const button = document.getElementById('get-models');
    const rows = document.getElementById('ollama-action-rows');
    
    button.disabled = true;
    button.textContent = 'Getting Models';
    rows.innerHTML = '<tr><td colspan="2">Getting Ollama models</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-models');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Show results
        if (data.success) {
            rowData.push(['Output', `Found ${data.total_models} Ollama models`]);
            rowData.push(['Method', data.method === 'api' ? 'API' : 'Command Line']);
            
            // Populate dropdown with models
            const modelSelect = document.getElementById('ollama-model-select');
            modelSelect.innerHTML = '<option value="">Select Model</option>';
            
            if (data.models && data.models.length > 0) {
                data.models.forEach((model, index) => {
                    const modelInfo = `${model.name} (${model.size || 'Unknown size'})`;
                    rowData.push([`Model ${index + 1}`, modelInfo]);
                    
                    // Add to dropdown
                    const option = document.createElement('option');
                    option.value = model.name;
                    option.textContent = model.name;
                    modelSelect.appendChild(option);
                });
            } else {
                rowData.push(['Models', 'No models found']);
            }
            
            if (data.message) {
                rowData.push(['Status', data.message]);
            }
        } else {
            rowData.push(['Output', 'Failed to get models']);
            if (data.error) {
                rowData.push(['Error', data.error]);
            }
            if (data.message) {
                rowData.push(['Message', data.message]);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No model data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error getting models: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Get ollama Models';
    }
}

async function queryOllama() {
    const input = document.getElementById('ollama-query-input');
    const modelSelect = document.getElementById('ollama-model-select');
    const button = document.getElementById('query-ollama');
    const chatDiv = document.getElementById('ollama-chat');
    
    const query = input.value.trim();
    const selectedModel = modelSelect.value;
    
    if (!query) {
        alert('Please enter a question for Ollama');
        return;
    }
    
    if (!selectedModel) {
        alert('Please select a model from the dropdown');
        return;
    }
    
    // Disable button and show loading
    button.disabled = true;
    button.textContent = 'Querying';
    
    // Add user message to chat
    const userMessage = document.createElement('div');
    userMessage.innerHTML = `<strong>User (${selectedModel}):</strong> ${query}`;
    chatDiv.appendChild(userMessage);
    
    // Clear input
    input.value = '';
    
    // Scroll to bottom
    chatDiv.scrollTop = chatDiv.scrollHeight;
    
    try {
        const response = await fetch('/api/ollama-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: query, model: selectedModel })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add Ollama response to chat
        const ollamaMessage = document.createElement('div');
        
        if (data.success) {
            ollamaMessage.innerHTML = `<strong>Ollama:</strong> ${renderMarkdown(data.response)}`;
        } else {
            ollamaMessage.innerHTML = `<strong>Ollama:</strong> Error: ${data.error}`;
        }
        
        chatDiv.appendChild(ollamaMessage);
        
        
    } catch (error) {
        // Add error message to chat
        const errorMessage = document.createElement('div');
        errorMessage.innerHTML = `Error: ${error.message}`;
        chatDiv.appendChild(errorMessage);
        
    } finally {
        button.disabled = false;
        button.textContent = 'Query ollama';
        
        // Scroll to bottom
        chatDiv.scrollTop = chatDiv.scrollHeight;
    }
}

// ============================================================================
// APPS RUNNING INFORMATION FUNCTIONS
// ============================================================================

async function loadAppsRunningInfo() {
    try {
        const response = await fetch('/api/apps-running-info');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('apps-running-info-rows').innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rows = document.getElementById('apps-running-info-rows');
        
        // Automatically display all data fields
        const rowData = [];
        
        // Basic apps info
        if (data.total_apps !== undefined) rowData.push(['Total Apps', data.total_apps]);
        if (data.gui_apps !== undefined) rowData.push(['GUI Apps', data.gui_apps]);
        if (data.background_apps !== undefined) rowData.push(['Background Apps', data.background_apps]);
        
        // Individual app details
        if (data.apps && data.apps.length > 0) {
            data.apps.forEach((app, index) => {
                const statusIcon = app.is_running ? '🟢' : '🔴';
                const appId = `app-${index}`;
                
                let appInfo = `${app.name} (${app.type}) - ${statusIcon} ${app.status} `;
                appInfo += `<button onclick="toggleApp('${appId}')" style="font-size:10px; padding:1px 3px;">+</button><br>`;
                appInfo += `<div id="${appId}" style="display:none;">`;
                appInfo += `└─ PID: ${app.pid}<br>`;
                appInfo += `└─ Description: ${app.description}<br>`;
                appInfo += `└─ Command: ${app.command_line}<br>`;
                appInfo += `└─ CPU: ${app.cpu_percent}%<br>`;
                appInfo += `└─ Memory: ${app.memory_mb} MB<br>`;
                appInfo += `└─ Start Time: ${app.start_time}<br>`;
                appInfo += `└─ User: ${app.username}`;
                appInfo += `</div>`;
                
                // Check if this is a system-critical app
                const isSystemApp = app.name && 
                    (app.name.toLowerCase().includes('system') || 
                     app.name.toLowerCase().includes('windows') ||
                     app.name.toLowerCase().includes('explorer'));
                
                const rowStyle = isSystemApp ? 'style="background-color: #fff3cd;"' : '';
                rowData.push([`${app.icon} App ${index + 1}`, appInfo, rowStyle]);
            });
        } else {
            rowData.push(['Apps Found', 'No apps detected']);
        }
        
        // Display all data
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No apps data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => {
                if (row.length === 3) {
                    return `<tr ${row[2]}><td>${row[0]}</td><td>${row[1]}</td></tr>`;
                } else {
                    return `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`;
                }
            }).join('');
        }
    } catch (error) {
        document.getElementById('apps-running-info-rows').innerHTML = `<tr><td colspan="2">Error loading apps info: ${error.message}</td></tr>`;
    }
}

function toggleApp(appId) {
    const element = document.getElementById(appId);
    const parentDiv = element.parentElement;
    const button = parentDiv.querySelector('button');
    
    if (element.style.display === 'none' || element.style.display === '') {
        element.style.display = 'block';
        button.textContent = '-';
    } else {
        element.style.display = 'none';
        button.textContent = '+';
    }
}

// ============================================================================
// COMFYUI INSPECTION FUNCTIONS
// ============================================================================

async function inspectComfyUI() {
    const button = document.getElementById('inspect-comfyui');
    const rows = document.getElementById('comfyui-info-rows');
    
    button.disabled = true;
    button.textContent = 'Inspecting';
    rows.innerHTML = '<tr><td colspan="2">Inspecting ComfyUI installation</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-status');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Installation status
        if (data.installed) {
            rowData.push(['Installation Status', 'Installed']);
            rowData.push(['Location', data.location]);
            if (data.version) {
                rowData.push(['Version', data.version]);
            }
        } else {
            rowData.push(['Installation Status', 'Not installed']);
            rowData.push(['Installation', '<a href="https://github.com/comfyanonymous/ComfyUI" target="_blank">https://github.com/comfyanonymous/ComfyUI</a>']);
        }
        
        // Running status
        if (data.running) {
            rowData.push(['Service Status', 'Running']);
            if (data.pid) {
                rowData.push(['Process ID', data.pid]);
            }
            if (data.api_responding !== undefined) {
                if (data.api_responding) {
                    rowData.push(['API Status', 'Responding']);
                } else {
                    rowData.push(['API Status', 'Not responding']);
                    if (data.api_error) {
                        rowData.push(['API Error', data.api_error]);
                    }
                }
            }
        } else {
            rowData.push(['Service Status', 'Not running']);
            if (data.installed) {
                rowData.push(['Start Command', 'python main.py']);
            }
        }
        
        // Port status
        if (data.port_in_use) {
            rowData.push([`Port ${data.port}`, 'In use']);
            rowData.push(['ComfyUI URL', data.base_url]);
        } else {
            rowData.push([`Port ${data.port}`, 'Not in use']);
        }
        
        // ComfyUI folder path
        if (data.location) {
            rowData.push(['ComfyUI Folder', data.location]);
        }
        
        // Models information
        if (data.models_found) {
            rowData.push(['Models Found', 'Yes']);
            
            // Display model types and their paths
            if (data.model_types && Object.keys(data.model_types).length > 0) {
                Object.entries(data.model_types).forEach(([type, path]) => {
                    rowData.push([`${type} Models`, path]);
                });
            }
            
            // Display model folders with file counts
            if (data.model_folders && data.model_folders.length > 0) {
                data.model_folders.forEach((folder, index) => {
                    const fileInfo = `${folder.file_count} files`;
                    const exampleFiles = folder.files.length > 0 ? ` (e.g., ${folder.files.join(', ')})` : '';
                    rowData.push([`Model Folder ${index + 1}`, `${folder.path} - ${fileInfo}${exampleFiles}`]);
                });
            }
        } else {
            rowData.push(['Models Found', 'No']);
            if (data.models_error) {
                rowData.push(['Models Error', data.models_error]);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No ComfyUI data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error inspecting ComfyUI: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Inspect comfyui';
    }
}

async function stopComfyUI() {
    const button = document.getElementById('stop-comfyui');
    const rows = document.getElementById('comfyui-action-rows');
    
    button.disabled = true;
    button.textContent = 'Stopping';
    rows.innerHTML = '<tr><td colspan="2">Stopping ComfyUI processes</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Show results
        if (data.success) {
            if (data.total_stopped > 0) {
                rowData.push(['Output', `Successfully stopped ${data.total_stopped} ComfyUI process${data.total_stopped > 1 ? 'es' : ''}`]);
                
                if (data.stopped_processes && data.stopped_processes.length > 0) {
                    data.stopped_processes.forEach((proc, index) => {
                        const method = proc.method === 'terminate' ? 'Graceful' : 
                                      proc.method === 'kill' ? 'Force kill' : 'Already stopped';
                        rowData.push([`Process ${index + 1}`, `PID ${proc.pid} (${proc.name}) - ${method}`]);
                    });
                }
            } else {
                rowData.push(['Output', 'No ComfyUI processes were running to stop']);
            }
            
            if (data.errors && data.errors.length > 0) {
                rowData.push(['Warnings', data.errors.join('; ')]);
            }
        } else {
            rowData.push(['Output', 'Failed to stop processes']);
            rowData.push(['Message', data.message]);
            if (data.errors && data.errors.length > 0) {
                rowData.push(['Errors', data.errors.join('; ')]);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No stop data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error stopping ComfyUI: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Stop ALL ComfyUI';
    }
}

async function startComfyUI() {
    const button = document.getElementById('start-comfyui');
    const rows = document.getElementById('comfyui-action-rows');
    
    button.disabled = true;
    button.textContent = 'Starting';
    rows.innerHTML = '<tr><td colspan="2">Starting ComfyUI process</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        const rowData = [];
        
        // Show results
        if (data.success) {
            if (data.already_running) {
                rowData.push(['Output', 'ComfyUI is already running']);
                if (data.pid) {
                    rowData.push(['Process ID', data.pid]);
                }
            } else {
                rowData.push(['Output', 'ComfyUI started successfully']);
                if (data.pid) {
                    rowData.push(['Process ID', data.pid]);
                }
                if (data.path) {
                    rowData.push(['Executable', data.path]);
                }
            }
            
            if (data.message) {
                rowData.push(['Status', data.message]);
            }
        } else {
            rowData.push(['Output', 'Failed to start ComfyUI']);
            if (data.error) {
                rowData.push(['Error', data.error]);
            }
            if (data.message) {
                rowData.push(['Message', data.message]);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No start data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error starting ComfyUI: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Start ComfyUI';
    }
}

// ============================================================================
// CONNECTIONS CONSOLE FUNCTIONS
// ============================================================================

let connectionCount = 0;
let connections = new Map();

function loadConnections() {
    const button = document.getElementById('refresh-connections');
    const status = document.getElementById('core-status');
    
    button.disabled = true;
    button.textContent = 'Refreshing...';
    status.textContent = 'Loading connection data...';
    
    // Simulate loading connections (in a real implementation, this would fetch from the server)
    setTimeout(() => {
        addConsoleEntry('Refreshing connection list...', 'connection-info');
        
        // Add some sample connections for demonstration
        if (connectionCount === 0) {
            addConnection('127.0.0.1:8080', 'Chrome', 'Windows 11');
            addConnection('127.0.0.1:8081', 'Edge', 'Windows 11');
        }
        
        updateConnectionCount();
        status.textContent = `Active: ${connectionCount} connections`;
        
        button.disabled = false;
        button.textContent = 'Refresh Connections';
    }, 1000);
}

function addConnection(ip, browser, os) {
    const connectionId = `${ip}_${Date.now()}`;
    connections.set(connectionId, {
        ip: ip,
        browser: browser,
        os: os,
        timestamp: new Date(),
        status: 'active'
    });
    
    connectionCount++;
    addConsoleEntry(`New connection: ${browser} from ${ip} (${os})`, 'connection-new');
}

function removeConnection(connectionId) {
    if (connections.has(connectionId)) {
        const conn = connections.get(connectionId);
        connections.delete(connectionId);
        connectionCount--;
        addConsoleEntry(`Connection lost: ${conn.browser} from ${conn.ip}`, 'connection-lost');
    }
}

function addConsoleEntry(message, type = 'connection-info') {
    const consoleLog = document.getElementById('connections-log');
    const timestamp = new Date().toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = `console-entry ${type}`;
    entry.innerHTML = `<span class="console-timestamp">[${timestamp}]</span>${message}`;
    
    consoleLog.appendChild(entry);
    
    // Auto-scroll to bottom
    consoleLog.scrollTop = consoleLog.scrollHeight;
}

function clearConnections() {
    const consoleLog = document.getElementById('connections-log');
    consoleLog.innerHTML = '<div class="console-entry">Console cleared. Waiting for connections</div>';
    
    connections.clear();
    connectionCount = 0;
    updateConnectionCount();
    
    const status = document.getElementById('core-status');
    status.textContent = 'Console cleared';
}

function updateConnectionCount() {
    const countElement = document.getElementById('connection-count');
    countElement.textContent = `${connectionCount} connection${connectionCount !== 1 ? 's' : ''}`;
}

// Simulate periodic connection updates
function startConnectionMonitoring() {
    setInterval(() => {
        // In a real implementation, this would check actual server connections
        // For now, we'll just update the status
        const status = document.getElementById('core-status');
        if (status.textContent.includes('Initializing')) {
            status.textContent = `Monitoring ${connectionCount} connections`;
        }
    }, 5000);
}

// Initialize connection monitoring when page loads
document.addEventListener('DOMContentLoaded', function() {
    startConnectionMonitoring();
});

// ============================================================================
// WORKFLOW MANAGEMENT FUNCTIONS
// ============================================================================

async function loadWorkflows() {
    try {
        const response = await fetch('/api/workflows');
        const data = await response.json();
        
        const workflowList = document.getElementById('workflow-list');
        
        if (data.success && data.workflows.length > 0) {
            workflowList.innerHTML = data.workflows.map(workflow => `
                <div style="padding: 8px; border: 1px solid black; border-radius: 4px; margin-bottom: 8px; background: #f9f9f9; display: flex; justify-content: space-between; align-items: center;">
                    <div style="color: #333;">${workflow.filename}</div>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="showWorkflowInfo('${workflow.filename}')" style="padding: 4px 8px; font-size: 12px; background: #e9ecef; border: 1px solid black; border-radius: 3px;">Info</button>
                        <button onclick="selectWorkflow('${workflow.filename}')" style="padding: 4px 8px; font-size: 12px; background: #e9ecef; border: 1px solid black; border-radius: 3px;">Select</button>
                    </div>
                </div>
            `).join('');
        } else {
            workflowList.innerHTML = '<div style="color: #888; font-size: 12px;">No workflows found</div>';
        }
    } catch (error) {
        console.error('Failed to load workflows:', error);
        document.getElementById('workflow-list').innerHTML = '<div font-size: 12px;">Failed to load workflows</div>';
    }
}

function openWorkflowDialog() {
    document.getElementById('workflow-file-input').click();
}

async function uploadWorkflow() {
    const fileInput = document.getElementById('workflow-file-input');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    if (!file.name.endsWith('.json')) {
        alert('Please select a JSON file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/workflows/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show green success message
            const workflowList = document.getElementById('workflow-list');
            const successDiv = document.createElement('div');
            successDiv.style.color = '#155724'; // Dark green text
            successDiv.style.fontSize = '12px';
            successDiv.style.marginTop = '10px';
            successDiv.style.padding = '8px';
            successDiv.style.border = '1px solid #28a745';
            successDiv.style.borderRadius = '4px';
            successDiv.style.background = '#d4edda';
            successDiv.textContent = `✅ Workflow '${data.filename}' uploaded successfully!`;
            
            // Remove any existing messages
            const existingMessage = workflowList.querySelector('.upload-message');
            if (existingMessage) {
                existingMessage.remove();
            }
            
            successDiv.className = 'upload-message';
            workflowList.appendChild(successDiv);
            
            // Remove message after 3 seconds
            setTimeout(() => {
                if (successDiv.parentNode) {
                    successDiv.remove();
                }
            }, 3000);
            
            loadWorkflows(); // Refresh the list
        } else {
            alert(`Upload failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed: ' + error.message);
    }
    
    // Clear the input
    fileInput.value = '';
}

function selectWorkflow(filename) {
    const workflowList = document.getElementById('workflow-list');
    const buttons = workflowList.querySelectorAll('button');
    
    // Check if this workflow is already selected
    const isCurrentlySelected = window.selectedWorkflow === filename;
    
    if (isCurrentlySelected) {
        // Deselect - clear selection
        window.selectedWorkflow = null;
        buttons.forEach(btn => {
            btn.textContent = 'Select';
            btn.style.background = '#e9ecef';
            btn.style.color = '#000';
            btn.style.border = '1px solid #ccc';
        });
        console.log('Deselected workflow');
    } else {
        // Select this workflow - deselect all others first
        window.selectedWorkflow = filename;
        buttons.forEach(btn => {
            btn.textContent = 'Select';
            btn.style.background = '#e9ecef';
            btn.style.color = '#000';
            btn.style.border = '1px solid #ccc';
        });
        
        // Highlight the selected one with green
        event.target.textContent = 'Selected';
        event.target.style.background = '#28a745'; // Green
        event.target.style.color = 'white';
        event.target.style.border = '1px solid #28a745';
        
        console.log(`Selected workflow: ${filename}`);
    }
}

// ============================================================================

async function submitWorkflow() {
    const button = document.getElementById('submit-workflow');
    const rows = document.getElementById('comfyui-action-rows');
    
    // Check if a workflow is selected
    if (!window.selectedWorkflow) {
        alert('Please select a workflow first');
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Submitting';
    rows.innerHTML = '<tr><td colspan="2">Submitting workflow to ComfyUI</td></tr>';
    
    try {
        // Load selected workflow from file
        const workflowPath = `/workflows/${window.selectedWorkflow}`;
        
        const response = await fetch(workflowPath);
        if (!response.ok) {
            throw new Error(`Failed to load workflow file: ${response.status}`);
        }
        
        const workflowData = await response.json();
        
        // Generate unique client ID and get seed (deterministic or random)
        const uniqueClientId = `rendersync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Get seed from input or generate random
        const seedInput = document.getElementById('seed-input');
        const inputSeed = seedInput.value.trim();
        const randomSeed = inputSeed ? parseInt(inputSeed) : Math.floor(Math.random() * 1000000000000000);
        
        // Submit the workflow to ComfyUI
        const submitResponse = await fetch('/api/comfyui-submit-workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                workflow: workflowData,
                client_id: uniqueClientId,
                random_seed: randomSeed
            })
        });
        
        const result = await submitResponse.json();
        
        const rowData = [];
        
        if (result.success) {
            rowData.push(['Output', 'Workflow submitted successfully']);
            rowData.push(['Prompt ID', result.prompt_id]);
            rowData.push(['Client ID', uniqueClientId]);
            rowData.push(['Seed', `${randomSeed} ${inputSeed ? '(deterministic)' : '(random)'}`]);
            rowData.push(['Status', 'Queued for execution']);
            rowData.push(['ComfyUI URL', '<a href="http://127.0.0.1:8188" target="_blank">http://127.0.0.1:8188</a>']);
        } else {
            rowData.push(['Output', 'Failed to submit workflow']);
            rowData.push(['Error', result.error]);
            if (result.connection_error) {
                rowData.push(['Note', 'Make sure ComfyUI is running on port 8188']);
            }
        }
        
        // Display all data in table format
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No submission data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error submitting workflow: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Submit Workflow';
    }
}

// ============================================================================
// WORKFLOW INFO MODAL FUNCTIONS
// ============================================================================

async function showWorkflowInfo(filename) {
    try {
        // Show loading state
        const modal = document.getElementById('workflow-info-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        
        modalTitle.textContent = `Workflow Information: ${filename}`;
        modalBody.innerHTML = '<div style="text-align: center; padding: 20px;">Loading workflow information...</div>';
        modal.style.display = 'flex';
        
        // Fetch workflow data
        const response = await fetch(`/workflows/${filename}`);
        if (!response.ok) {
            throw new Error(`Failed to load workflow: ${response.status}`);
        }
        
        const workflowData = await response.json();
        
        // Extract and format workflow information
        const info = extractWorkflowInfo(workflowData);
        
        // Display the information
        modalBody.innerHTML = formatWorkflowInfo(info);
        
    } catch (error) {
        console.error('Failed to load workflow info:', error);
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `<div style="color: red; padding: 20px;">Error loading workflow information: ${error.message}</div>`;
    }
}

function extractWorkflowInfo(workflowData) {
    const info = {
        filename: 'Unknown',
        nodes: [],
        models: [],
        general: {}
    };
    
    // Extract general information
    if (workflowData.id) info.general.id = workflowData.id;
    if (workflowData.version) info.general.version = workflowData.version;
    if (workflowData.last_node_id) info.general.lastNodeId = workflowData.last_node_id;
    if (workflowData.last_link_id) info.general.lastLinkId = workflowData.last_link_id;
    
    // Extract node information
    if (workflowData.nodes && Array.isArray(workflowData.nodes)) {
        info.nodes = workflowData.nodes.map(node => ({
            id: node.id,
            type: node.type,
            name: node.properties?.['Node name for S&R'] || node.type,
            inputs: node.inputs?.length || 0,
            outputs: node.outputs?.length || 0,
            widgets: node.widgets_values || []
        }));
    }
    
    // Extract model information
    if (workflowData.nodes && Array.isArray(workflowData.nodes)) {
        workflowData.nodes.forEach(node => {
            if (node.type === 'CheckpointLoaderSimple' && node.properties?.models) {
                node.properties.models.forEach(model => {
                    info.models.push({
                        name: model.name,
                        url: model.url,
                        directory: model.directory
                    });
                });
            }
        });
    }
    
    return info;
}

function formatWorkflowInfo(info) {
    let html = '<div>';
    
    // General Information
    html += '<h4>General Information</h4>';
    html += '<ul>';
    if (info.general.id) html += `<li><strong>ID:</strong> <code>${info.general.id}</code></li>`;
    if (info.general.version) html += `<li><strong>Version:</strong> ${info.general.version}</li>`;
    if (info.general.lastNodeId) html += `<li><strong>Last Node ID:</strong> ${info.general.lastNodeId}</li>`;
    if (info.general.lastLinkId) html += `<li><strong>Last Link ID:</strong> ${info.general.lastLinkId}</li>`;
    html += '</ul>';
    
    // Models
    if (info.models.length > 0) {
        html += '<h4>Models</h4>';
        html += '<ul>';
        info.models.forEach(model => {
            html += `<li><strong>${model.name}</strong>`;
            if (model.directory) html += ` (${model.directory})`;
            html += '</li>';
        });
        html += '</ul>';
    }
    
    // Nodes
    if (info.nodes.length > 0) {
        html += '<h4>Nodes</h4>';
        html += '<ul>';
        info.nodes.forEach(node => {
            html += `<li><strong>${node.name}</strong> (ID: ${node.id})`;
            html += `<br><small>Type: <code>${node.type}</code> | Inputs: ${node.inputs} | Outputs: ${node.outputs}</small>`;
            if (node.widgets && node.widgets.length > 0) {
                html += `<br><small>Widgets: ${node.widgets.join(', ')}</small>`;
            }
            html += '</li>';
        });
        html += '</ul>';
    }
    
    html += '</div>';
    return html;
}

function closeWorkflowInfo() {
    const modal = document.getElementById('workflow-info-modal');
    modal.style.display = 'none';
}


// ============================================================================
// END OF RENDERSYNC CORE JAVASCRIPT
// ============================================================================
