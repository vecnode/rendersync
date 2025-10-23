// ============================================================================
// RENDERSYNC CORE - JAVASCRIPT FUNCTIONS
// ============================================================================

// ============================================================================
// PAGE INITIALIZATION
// ============================================================================

// Load workflows when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadComfyUIWorkflows();
    updateConnectionStatus(); // Fast connection status check
});



// ============================================================================
// CONNECTIONS CONSOLE FUNCTIONS
// ============================================================================

let connectionCount = 0;
let connections = new Map();
let currentConnectionId = null;
let selectedWorkflow = null;

// Register this page/tab as a connection when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Create unique connection ID for this tab
    currentConnectionId = `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Get comprehensive browser and system info
    const browserInfo = getBrowserInfo();
    const systemInfo = getSystemInfo();
    
    // Register this connection with the server
    addConnection('127.0.0.1:8080', browserInfo.name, systemInfo.platform, currentConnectionId, {
        userAgent: navigator.userAgent,
        screenResolution: `${screen.width}x${screen.height}`,
        language: navigator.language,
        machineType: systemInfo.machineType,
        timestamp: new Date().toISOString()
    });
});



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

function addConsoleEntryWithTime(message, type = 'connection-info', customTime) {
    const consoleLog = document.getElementById('connections-log');
    
    const entry = document.createElement('div');
    entry.className = `console-entry ${type}`;
    entry.innerHTML = `<span class="console-timestamp">[${customTime}]</span>${message}`;
    
    consoleLog.appendChild(entry);
    
    // Auto-scroll to bottom
    consoleLog.scrollTop = consoleLog.scrollHeight;
}

function addOllamaChatEntry(message, type = 'ollama-response') {
    const ollamaChatLog = document.getElementById('ollama-chat-log');
    const timestamp = new Date().toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = `ollama-chat-entry ${type}`;
    entry.innerHTML = `<span class="ollama-chat-timestamp">[${timestamp}]</span>${message}`;
    
    ollamaChatLog.appendChild(entry);
    
    // Auto-scroll to bottom with a small delay to ensure DOM is updated
    setTimeout(() => {
        ollamaChatLog.scrollTop = ollamaChatLog.scrollHeight;
    }, 10);
}


async function addConnection(ip, browser, os, connectionId = null, additionalData = {}) {
    const id = connectionId || `${ip}_${Date.now()}`;
    
    try {
        // Send connection to server with all data
        const response = await fetch('/api/connections', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                connectionId: id,
                ip: ip,
                browser: browser,
                os: os,
                timestamp: additionalData.timestamp || new Date().toISOString(),
                userAgent: additionalData.userAgent || navigator.userAgent,
                screenResolution: additionalData.screenResolution || `${screen.width}x${screen.height}`,
                language: additionalData.language || navigator.language,
                machineType: additionalData.machineType || 'Unknown'
            })
        });
        
        if (response.ok) {
            console.log(`Connection ${id} registered with server`);
        }
    } catch (error) {
        console.error('Failed to register connection with server:', error);
    }
}

async function loadConnections() {
    const button = document.getElementById('refresh-connections');
    const consoleLog = document.getElementById('connections-log');
    
    button.disabled = true;
    button.textContent = 'Refreshing';
    
    // Clear the console display
    consoleLog.innerHTML = '';
    
    try {
        // Fetch connections from server
        const response = await fetch('/api/connections');
        const data = await response.json();
        
        if (data.success) {
            // Display connections from server with detailed info
            data.connections.forEach(conn => {
                const userAgentShort = conn.userAgent.length > 50 ? 
                    conn.userAgent.substring(0, 50) + '...' : conn.userAgent;
                
                const connectedTime = new Date(conn.timestamp).toLocaleTimeString();
                const detailLine = `Client: ${conn.browser} from ${conn.ip} (${conn.os}) | UA: ${userAgentShort} | Res: ${conn.screenResolution} | Lang: ${conn.language} | Machine: ${conn.machineType}`;
                
                // Add entry with original connection timestamp
                addConsoleEntryWithTime(detailLine, 'connection-success', connectedTime);
            });
            
            connectionCount = data.connections.length;
            updateConnectionCount();
        } else {
            addConsoleEntry('Failed to load connections from server', 'connection-error');
        }
    } catch (error) {
        addConsoleEntry(`Error: ${error.message}`, 'connection-error');
    }
    
    button.disabled = false;
    button.textContent = 'Refresh Connections';
}

function getBrowserInfo() {
    const userAgent = navigator.userAgent;
    
    if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
        return { name: 'Chrome' };
    } else if (userAgent.includes('Firefox')) {
        return { name: 'Firefox' };
    } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
        return { name: 'Safari' };
    } else if (userAgent.includes('Edg')) {
        return { name: 'Edge' };
    } else if (userAgent.includes('Opera')) {
        return { name: 'Opera' };
    } else {
        return { name: 'Unknown Browser' };
    }
}

function getSystemInfo() {
    const userAgent = navigator.userAgent;
    const platform = navigator.platform;
    
    // Detect machine type
    let machineType = 'Unknown';
    
    if (userAgent.includes('Windows NT 10.0')) {
        // Check if it's Windows 11 (Windows NT 10.0 with build number >= 22000)
        const buildMatch = userAgent.match(/Windows NT 10\.0; Win64; x64/);
        if (buildMatch) {
            machineType = 'Windows 11 Desktop';
        } else {
            machineType = 'Windows 10 Desktop';
        }
    } else if (userAgent.includes('Windows NT 6.3')) {
        machineType = 'Windows 8.1 Desktop';
    } else if (userAgent.includes('Windows NT 6.1')) {
        machineType = 'Windows 7 Desktop';
    } else if (userAgent.includes('Mac OS X')) {
        machineType = 'macOS Desktop';
    } else if (userAgent.includes('Linux')) {
        machineType = 'Linux Desktop';
    } else if (userAgent.includes('Android')) {
        machineType = 'Android Mobile';
    } else if (userAgent.includes('iPhone') || userAgent.includes('iPad')) {
        machineType = 'iOS Mobile';
    }
    
    return {
        platform: platform,
        machineType: machineType
    };
}




function updateConnectionCount() {
    const countElement = document.getElementById('connection-count');
    countElement.textContent = `${connectionCount} connection${connectionCount !== 1 ? 's' : ''}`;
}





// ============================================================================
// GLOBAL BACKEND VARIABLES
// ============================================================================

// TODO here make the outputs of these loads


// ============================================================================
// UI INTERACTION FUNCTIONS
// ============================================================================

function toggleTerminalRowOnTable(terminalId) {
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
                terminalInfo += `<button onclick="toggleTerminalRowOnTable('${terminalId}')" style="font-size:10px; padding:1px 3px;">+</button><br>`;
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
    const ollamaChatLog = document.getElementById('ollama-chat-log');
    
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
    
    // Add user message to chat with timestamp
    addOllamaChatEntry(`User: ${query}`, 'user-message');
    
    // Clear input
    input.value = '';
    
    // Scroll to bottom immediately after user message
    setTimeout(() => {
        ollamaChatLog.scrollTop = ollamaChatLog.scrollHeight;
    }, 10);
    
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
        if (data.success) {
            addOllamaChatEntry(`${selectedModel}: ${data.response}`, 'ollama-response');
        } else {
            addOllamaChatEntry(`${selectedModel}: Error: ${data.error}`, 'error-message');
        }
        
        
    } catch (error) {
        // Add error message to chat
        addOllamaChatEntry(`Error: ${error.message}`, 'error-message');
        
    } finally {
        button.disabled = false;
        button.textContent = 'Query ollama';
        
        // Scroll to bottom after response
        setTimeout(() => {
            ollamaChatLog.scrollTop = ollamaChatLog.scrollHeight;
        }, 10);
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
                appInfo += `<button onclick="toggleButtonRunningAppAbout('${appId}')" style="font-size:10px; padding:1px 3px;">+</button><br>`;
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

function toggleButtonRunningAppAbout(appId) {
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

async function openComfyUIOutputFolder() {
    const button = document.getElementById('open-comfyui-output-folder');
    const rows = document.getElementById('comfyui-action-rows');
    
    button.disabled = true;
    button.textContent = 'Opening';
    rows.innerHTML = '<tr><td colspan="2">Getting ComfyUI output folder information</td></tr>';
    
    try {
        const response = await fetch('/api/comfyui-output-folder');
        const data = await response.json();
        
        if (data.error) {
            rows.innerHTML = `<tr><td colspan="2">Error: ${data.error}</td></tr>`;
            return;
        }
        
        if (data.success && data.output_folder) {
            // Display folder information in the table
            const rowData = [];
            rowData.push(['Output Folder', data.output_folder]);
            rowData.push(['ComfyUI Path', data.comfyui_path]);
            rowData.push(['Folder Exists', data.output_exists ? 'Yes' : 'No']);
            
            // Try to open the folder using the backend endpoint
            try {
                const openResponse = await fetch('/api/comfyui-open-output-folder', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const openData = await openResponse.json();
                
                if (openData.success) {
                    rowData.push(['Status', 'Folder opened successfully']);
                } else {
                    rowData.push(['Status', `Failed to open: ${openData.error}`]);
                }
            } catch (openError) {
                rowData.push(['Status', `Error opening folder: ${openError.message}`]);
            }
            
            // Display all data in table format
            if (rowData.length === 0) {
                rows.innerHTML = '<tr><td colspan="2">No folder data available</td></tr>';
            } else {
                rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
            }
            
        } else {
            rows.innerHTML = '<tr><td colspan="2">Failed to get ComfyUI output folder path</td></tr>';
        }
        
    } catch (error) {
        rows.innerHTML = `<tr><td colspan="2">Error opening ComfyUI output folder: ${error.message}</td></tr>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Open ComfyUI Output Folder';
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
// COMFYUI WORKFLOW MANAGEMENT FUNCTIONS
// ============================================================================

async function loadComfyUIWorkflows() {
    try {
        const response = await fetch('/api/workflows');
        const data = await response.json();
        
        const workflowRows = document.getElementById('workflow-rows');
        
        if (data.success && data.workflows.length > 0) {
            workflowRows.innerHTML = data.workflows.map(workflow => {
                const isSelected = selectedWorkflow === workflow.filename;
                const buttonStyle = isSelected 
                    ? 'padding: 4px 8px; font-size: 12px; background: #5a6268 !important; color: white !important; border: 1px solid black; border-radius: 3px;'
                    : 'padding: 4px 8px; font-size: 12px; background: #e9ecef !important; color: inherit !important; border: 1px solid black; border-radius: 3px;';
                const buttonText = isSelected ? 'Selected' : 'Select';
                
                const inspectorButtonStyle = 'padding: 4px 8px; font-size: 12px; border-radius: 3px;';
                
                return `<tr>
                    <td>${workflow.filename}</td>
                    <td><button onclick="selectComfyUIWorkflowButton('${workflow.filename}')" style="${buttonStyle}">${buttonText}</button></td>
                    <td><button onclick="openWorkflowInspector('${workflow.filename}')" style="${inspectorButtonStyle}">Inspector</button></td>
                </tr>`;
            }).join('');
        } else {
            workflowRows.innerHTML = '<tr><td colspan="3">No workflows found</td></tr>';
        }
    } catch (error) {
        console.error('Failed to load workflows:', error);
        document.getElementById('workflow-rows').innerHTML = '<tr><td colspan="3">Failed to load workflows</td></tr>';
    }
}



function selectComfyUIWorkflowButton(filename) {
    // Toggle selection - if already selected, deselect; otherwise select
    if (selectedWorkflow === filename) {
        selectedWorkflow = null;
    } else {
        selectedWorkflow = filename;
    }
    
    // Reload the workflow list to update button states
    loadComfyUIWorkflows();
}

function openWorkflowInspector(filename) {
    // Open a new tab with the workflow inspector
    const inspectorUrl = `/workflow-inspector?workflow=${encodeURIComponent(filename)}`;
    window.open(inspectorUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
}




async function uploadComfyUIWorkflow() {
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
            const workflowRows = document.getElementById('workflow-rows');
            const successRow = document.createElement('tr');
            successRow.className = 'upload-message';
            successRow.innerHTML = `<td colspan="2" style="color: #155724; background: #d4edda; border: 1px solid #28a745; padding: 8px; text-align: center;">Workflow '${data.filename}' uploaded successfully!</td>`;
            
            // Remove any existing messages
            const existingMessage = workflowRows.querySelector('.upload-message');
            if (existingMessage) {
                existingMessage.remove();
            }
            
            workflowRows.appendChild(successRow);
            
            // Remove message after 3 seconds
            setTimeout(() => {
                if (successRow.parentNode) {
                    successRow.remove();
                }
            }, 3000);
            
            loadComfyUIWorkflows(); // Refresh the list
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


// ============================================================================

async function submitComfyUIWorkflow() {
    const button = document.getElementById('submit-workflow');
    const rows = document.getElementById('comfyui-action-rows');
    
    // Check if a workflow is selected
    if (!selectedWorkflow) {
        alert('Please select a workflow first');
        return;
    }
    
    button.disabled = true;
    button.textContent = 'Submitting';
    rows.innerHTML = '<tr><td colspan="2">Submitting workflow to ComfyUI</td></tr>';
    
    try {
        // Load selected workflow from file
        const workflowPath = `/workflows/${selectedWorkflow}`;
        
        const response = await fetch(workflowPath);
        if (!response.ok) {
            throw new Error(`Failed to load workflow file: ${response.status}`);
        }
        
        const workflowData = await response.json();
        
        // Generate unique client ID and random seed
        const uniqueClientId = `rendersync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const randomSeed = Math.floor(Math.random() * 1000000000000000);
        
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
            rowData.push(['Seed', `${randomSeed} (random)`]);
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
// SERVER SHUTDOWN FUNCTIONS
// ============================================================================

async function shutdownServer() {
    if (confirm('Are you sure you want to shutdown the rendersync server? This will close the application.')) {
        try {
            const response = await fetch('/api/shutdown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('Server shutdown initiated. The application will close shortly.');
                // The server will terminate, so the page will become unresponsive
            } else {
                alert('Failed to shutdown server: ' + data.message);
            }
        } catch (error) {
            console.error('Failed to shutdown server:', error);
            alert('Failed to shutdown server. Please check the console for details.');
        }
    }
}

// ============================================================================
// CONNECTION CONTROL FUNCTIONS
// ============================================================================

async function loadConnectionStatus() {
    try {
        const response = await fetch('/api/connection-status');
        const data = await response.json();
        
        updateConnectionIndicator(data.connection_access_enabled);
        updateConnectionButton(data.connection_access_enabled);
        
    } catch (error) {
        console.error('Failed to load connection status:', error);
        updateConnectionIndicator(false);
    }
}

async function toggleConnectionAccess() {
    const button = document.getElementById('toggle-connections');
    const indicator = document.getElementById('connection-indicator');
    const statusText = document.getElementById('connection-status-text');
    
    // Get current status
    const currentStatus = indicator.style.backgroundColor === 'rgb(76, 175, 80)'; // Green color
    const action = currentStatus ? 'disable' : 'enable';
    
    button.disabled = true;
    button.textContent = 'Updating...';
    
    try {
        const response = await fetch('/api/connection-control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: action })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateConnectionIndicator(data.connection_access_enabled);
            updateConnectionButton(data.connection_access_enabled);
            
            // Show success message
            const originalText = statusText.textContent;
            statusText.textContent = data.message;
            setTimeout(() => {
                statusText.textContent = originalText;
            }, 3000);
        } else {
            alert(`Failed to ${action} connections: ${data.error}`);
        }
        
    } catch (error) {
        console.error(`Failed to ${action} connections:`, error);
        alert(`Failed to ${action} connections: ${error.message}`);
    } finally {
        button.disabled = false;
        updateConnectionButton(indicator.style.backgroundColor === 'rgb(76, 175, 80)');
    }
}

function updateConnectionIndicator(isEnabled) {
    const indicator = document.getElementById('connection-indicator');
    const statusText = document.getElementById('connection-status-text');
    
    if (isEnabled) {
        indicator.style.backgroundColor = '#4caf50'; // Green
        statusText.textContent = 'Enabled';
    } else {
        indicator.style.backgroundColor = '#f44336'; // Red
        statusText.textContent = 'Disabled';
    }
}

function updateConnectionButton(isEnabled) {
    const button = document.getElementById('toggle-connections');
    
    if (isEnabled) {
        button.textContent = 'Disable External Connections';
        button.style.backgroundColor = '#f44336';
        button.style.color = 'white';
    } else {
        button.textContent = 'Enable External Connections';
        button.style.backgroundColor = '#4caf50';
        button.style.color = 'white';
    }
}

async function loadServerInfo() {
    try {
        const response = await fetch('/api/server-info');
        const data = await response.json();
        
        const rows = document.getElementById('server-info-rows');
        
        const rowData = [];
        
        // Server information
        if (data.status) rowData.push(['Status', data.status]);
        if (data.service) rowData.push(['Service', data.service]);
        if (data.hostname) rowData.push(['Hostname', data.hostname]);
        if (data.local_ip) rowData.push(['Local IP', data.local_ip]);
        if (data.connection_status) rowData.push(['Connection Status', data.connection_status]);
        if (data.accessible_from_network !== undefined) rowData.push(['Network Access', data.accessible_from_network ? 'Enabled' : 'Disabled']);
        if (data.cors_enabled !== undefined) rowData.push(['CORS Enabled', data.cors_enabled ? 'Yes' : 'No']);
        
        // Port information
        if (data.port_info) {
            if (data.port_info.default_port) rowData.push(['Default Port', data.port_info.default_port]);
        }
        
        // Display all data
        if (rowData.length === 0) {
            rows.innerHTML = '<tr><td colspan="2">No server data available</td></tr>';
        } else {
            rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
        }
        
    } catch (error) {
        document.getElementById('server-info-rows').innerHTML = `<tr><td colspan="2">Error loading server info: ${error.message}</td></tr>`;
    }
}


// ============================================================================
// CONNECTION CONTROL FUNCTIONS
// ============================================================================

async function toggleConnectionAccess() {
    try {
        const button = document.getElementById('toggle-connections');
        const indicator = document.getElementById('connection-indicator');
        const statusText = document.getElementById('connection-status-text');
        
        // Show loading state immediately
        button.disabled = true;
        button.textContent = 'Updating';
        
        // Determine current state from button text
        const isCurrentlyEnabled = button.textContent.includes('Disable') || button.textContent.includes('Updating');
        
        const action = isCurrentlyEnabled ? 'disable' : 'enable';
        
        const response = await fetch('/api/connection-control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: action })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                // Update button text
                if (action === 'disable') {
                    button.textContent = 'Enable External Connections';
                    button.className = 'btn btn-outline-success';
                    
                    // Update indicator
                    indicator.style.backgroundColor = '#dc3545'; // Light red
                    statusText.textContent = 'Disabled';
                } else {
                    button.textContent = 'Disable External Connections';
                    button.className = 'btn btn-outline-danger';
                    
                    // Update indicator
                    indicator.style.backgroundColor = '#4caf50'; // Light green
                    statusText.textContent = 'Enabled';
                }
                
                console.log(result.message);
            } else {
                console.error('Failed to toggle connection access:', result.message);
            }
        } else {
            console.error('Failed to toggle connection access:', response.statusText);
        }
        
    } catch (error) {
        console.error('Error toggling connection access:', error);
    } finally {
        // Re-enable button
        button.disabled = false;
    }
}

// Fast connection status check (doesn't load heavy server info)
async function updateConnectionStatus() {
    try {
        const response = await fetch('/api/connection-status');
        const data = await response.json();
        
        const button = document.getElementById('toggle-connections');
        const indicator = document.getElementById('connection-indicator');
        const statusText = document.getElementById('connection-status-text');
        
        if (data.connection_access_enabled) {
            button.textContent = 'Disable External Connections';
            button.className = 'btn btn-outline-danger';
            indicator.style.backgroundColor = '#4caf50'; // Light green
            statusText.textContent = 'Enabled';
        } else {
            button.textContent = 'Enable External Connections';
            button.className = 'btn btn-outline-success';
            indicator.style.backgroundColor = '#dc3545'; // Light red
            statusText.textContent = 'Disabled';
        }
        
    } catch (error) {
        console.error('Error updating connection status:', error);
    }
}

// ============================================================================
// SYSTEM PAGE FUNCTIONS (Unified Table)
// ============================================================================

// Clear all results from the unified table
function clearSystemResults() {
    const rows = document.getElementById('system-results-rows');
    rows.innerHTML = '<tr><td colspan="2" class="text-center text-muted">Click any button above to load system information</td></tr>';
}

// Generic function to display data in the unified table
function displaySystemData(data, title) {
    const rows = document.getElementById('system-results-rows');
    
    if (!data || Object.keys(data).length === 0) {
        rows.innerHTML = `<tr><td colspan="2" class="text-center text-muted">No ${title} data available</td></tr>`;
        return;
    }
    
    const rowData = [];
    
    // Add data rows
    for (const [key, value] of Object.entries(data)) {
        if (value !== null && value !== undefined) {
            if (key === 'terminals' && Array.isArray(value)) {
                // Special handling for terminals array
                rowData.push([key, `${value.length} terminals found`]);
                
                // Add each terminal as a separate row with collapsible details
                value.forEach((terminal, index) => {
                    const terminalId = `terminal-${index}`;
                    const terminalSummary = `${terminal.icon} ${terminal.name} (PID: ${terminal.pid}) - ${terminal.status}`;
                    
                    rowData.push([
                        `Terminal ${index + 1}`,
                        `<div class="d-flex justify-content-between align-items-center">
                            <span>${terminalSummary}</span>
                            <button class="btn btn-xs btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#${terminalId}" aria-expanded="false" aria-controls="${terminalId}" style="font-size: 0.7rem; padding: 0.2rem 0.4rem;">
                                <i class="bi bi-chevron-down" style="font-size: 0.7rem;"></i>
                            </button>
                        </div>
                        <div class="collapse" id="${terminalId}" data-bs-parent="#system-results-rows">
                            <div class="card card-body py-2 mt-1">
                                <pre class="mb-0">${JSON.stringify(terminal, null, 2)}</pre>
                            </div>
                        </div>`
                    ]);
                });
            } else if (typeof value === 'object') {
                rowData.push([key, JSON.stringify(value, null, 2)]);
            } else {
                rowData.push([key, value.toString()]);
            }
        }
    }
    
    // Display all data
    rows.innerHTML = rowData.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join('');
}

// Load system information
async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system-info');
        const data = await response.json();
        displaySystemData(data, 'System Information');
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error loading system info: ${error.message}</td></tr>`;
    }
}

// Load terminal information
async function loadTerminalInfo() {
    try {
        const response = await fetch('/api/terminal-info');
        const data = await response.json();
        displaySystemData(data, 'Terminal Information');
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error loading terminal info: ${error.message}</td></tr>`;
    }
}

// Load apps running information
async function loadAppsRunningInfo() {
    try {
        const response = await fetch('/api/apps-running-info');
        const data = await response.json();
        displaySystemData(data, 'Apps Running Information');
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error loading apps running info: ${error.message}</td></tr>`;
    }
}

// Load network information
async function loadNetworkInfo() {
    try {
        const response = await fetch('/api/network-info');
        const data = await response.json();
        displaySystemData(data, 'Network Information');
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error loading network info: ${error.message}</td></tr>`;
    }
}

// Inspect port
async function inspectPort() {
    const portInput = document.getElementById('port-input');
    const port = portInput.value;
    
    if (!port) {
        alert('Please enter a port number');
        return;
    }
    
    try {
        const response = await fetch('/api/inspect-port', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ port: parseInt(port) })
        });
        
        const data = await response.json();
        displaySystemData(data, `Port ${port} Inspection`);
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error inspecting port: ${error.message}</td></tr>`;
    }
}

// Inspect PID
async function inspectPID() {
    const pidInput = document.getElementById('pid-input');
    const pid = pidInput.value;
    
    if (!pid) {
        alert('Please enter a PID number');
        return;
    }
    
    try {
        const response = await fetch('/api/inspect-pid', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pid: pid })
        });
        
        const data = await response.json();
        displaySystemData(data, `PID ${pid} Inspection`);
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error inspecting PID: ${error.message}</td></tr>`;
    }
}

// Ping IP
async function pingIP() {
    const pingInput = document.getElementById('ping-input');
    const pingPortInput = document.getElementById('ping-port-input');
    
    const target = pingInput.value;
    const port = pingPortInput.value;
    
    if (!target) {
        alert('Please enter an IP address or hostname');
        return;
    }
    
    try {
        const requestBody = { target: target };
        if (port) {
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
        displaySystemData(data, `Ping ${target}${port ? `:${port}` : ''}`);
    } catch (error) {
        document.getElementById('system-results-rows').innerHTML = `<tr><td colspan="2">Error pinging: ${error.message}</td></tr>`;
    }
}

// ============================================================================
// END OF RENDERSYNC CORE JAVASCRIPT
// ============================================================================
