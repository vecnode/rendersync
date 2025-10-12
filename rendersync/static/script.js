// ============================================================================
// RENDERSYNC CORE - JAVASCRIPT FUNCTIONS
// ============================================================================

// ============================================================================
// SYSTEM INFORMATION FUNCTIONS
// ============================================================================

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system-info');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('system-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        document.getElementById('system-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error loading system info: ${error.message}</td></tr>`;
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
            document.getElementById('network-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        document.getElementById('network-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error loading network info: ${error.message}</td></tr>`;
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
            document.getElementById('terminal-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        document.getElementById('terminal-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error loading terminal info: ${error.message}</td></tr>`;
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
        rows.innerHTML = '<tr><td colspan="2" style="color: red;">Please enter a port number</td></tr>';
        return;
    }
    
    if (port < 1 || port > 65535) {
        rows.innerHTML = '<tr><td colspan="2" style="color: red;">Port must be between 1 and 65535</td></tr>';
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Inspecting';
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Inspecting port ' + port + '</td></tr>';
    
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
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error inspecting port: ${error.message}</td></tr>`;
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
        rows.innerHTML = '<tr><td colspan="2" style="color: red;">Please enter a PID number</td></tr>';
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Inspecting';
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Inspecting PID ' + pid + '</td></tr>';
    
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
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error inspecting PID: ${error.message}</td></tr>`;
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
        rows.innerHTML = '<tr><td colspan="2" style="color: red;">Please enter an IP address or hostname</td></tr>';
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Pinging';
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Pinging ' + target + (port ? ':' + port : '') + '</td></tr>';
    
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
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error pinging: ${error.message}</td></tr>`;
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
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Inspecting Ollama installation</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-status');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error inspecting Ollama: ${error.message}</td></tr>`;
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
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Stopping Ollama processes</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error stopping Ollama: ${error.message}</td></tr>`;
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
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Starting Ollama process</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error starting Ollama: ${error.message}</td></tr>`;
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
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Getting Ollama models</td></tr>';
    
    try {
        const response = await fetch('/api/ollama-models');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error getting models: ${error.message}</td></tr>`;
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
            document.getElementById('apps-running-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        document.getElementById('apps-running-info-rows').innerHTML = `<tr><td colspan="2" style="color: red;">Error loading apps info: ${error.message}</td></tr>`;
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
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Inspecting ComfyUI installation</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-status');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        if (data.port_8188) {
            rowData.push(['Port 8188', 'In use']);
        } else {
            rowData.push(['Port 8188', 'Not in use']);
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error inspecting ComfyUI: ${error.message}</td></tr>`;
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
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Stopping ComfyUI processes</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error stopping ComfyUI: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Stop comfyui';
    }
}

async function startComfyUI() {
    const button = document.getElementById('start-comfyui');
    const rows = document.getElementById('comfyui-action-rows');
    
    button.disabled = true;
    button.textContent = 'Starting';
    rows.innerHTML = '<tr><td colspan="2" style="color: blue;">Starting ComfyUI process</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error: ${data.error}</td></tr>`;
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
        rows.innerHTML = `<tr><td colspan="2" style="color: red;">Error starting ComfyUI: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Start comfyui';
    }
}

// ============================================================================
// END OF RENDERSYNC CORE JAVASCRIPT
// ============================================================================
