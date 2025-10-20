# rendersync Client - Get Server Info
# ================================================================================
# PowerShell script to connect to rendersync server and get server information
# Usage: .\get-server-info.ps1 [server_ip] [port]
# ================================================================================

param(
    [string]$ServerIP = "127.0.0.1",
    [int]$Port = 8080
)

# Color functions for better output
function Write-Info { param($msg) Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "==> $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "==> $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "==> $msg" -ForegroundColor Red }

Write-Info "rendersync Client - Server Info"
Write-Info "==============================="
Write-Info "Connecting to: http://$ServerIP`:$Port/api/server-info"

try {
    # Make the HTTP request to the server-info endpoint
    $response = Invoke-RestMethod -Uri "http://$ServerIP`:$Port/api/server-info" -Method GET -TimeoutSec 10
    
    Write-Success "Connection successful!"
    Write-Host ""
    
    # Display the server information in a formatted way
    Write-Host "Server Information:" -ForegroundColor Yellow
    Write-Host "==================" -ForegroundColor Yellow
    Write-Host "Status: $($response.status)" -ForegroundColor Green
    Write-Host "Service: $($response.service)" -ForegroundColor Green
    Write-Host "Hostname: $($response.hostname)" -ForegroundColor White
    Write-Host "Local IP: $($response.local_ip)" -ForegroundColor White
    Write-Host "Connection Status: $($response.connection_status)" -ForegroundColor $(if($response.connection_status -eq "enabled") { "Green" } else { "Red" })
    Write-Host "Network Accessible: $($response.accessible_from_network)" -ForegroundColor $(if($response.accessible_from_network) { "Green" } else { "Red" })
    Write-Host "CORS Enabled: $($response.cors_enabled)" -ForegroundColor $(if($response.cors_enabled) { "Green" } else { "Red" })
    
    # Display port information if available
    if ($response.port_info) {
        Write-Host ""
        Write-Host "Port Information:" -ForegroundColor Yellow
        Write-Host "================" -ForegroundColor Yellow
        $response.port_info.PSObject.Properties | ForEach-Object {
            Write-Host "$($_.Name): $($_.Value)" -ForegroundColor White
        }
    }
    
    Write-Host ""
    Write-Success "Server info retrieved successfully!"
    
} catch {
    Write-Error "Failed to connect to server: $($_.Exception.Message)"
    Write-Warning "Make sure the rendersync server is running and accessible at http://$ServerIP`:$Port"
    Write-Warning "You can also try different IP addresses if connecting from another machine on the network"
    exit 1
}
