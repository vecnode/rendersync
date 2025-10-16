# rendersync
# ================================================================================
# Main launcher script - handles .venv setup and FastAPI server startup
# This script creates .venv if missing, installs requirements, and starts the server
# ================================================================================

$ErrorActionPreference = "Stop"

# Color functions
function Write-Info { param($msg) Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "==> $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "==> $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "==> $msg" -ForegroundColor Red }

Write-Info "rendersync"
Write-Info "================"

# Get the project root directory (where this script is located)
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# System checks
Write-Info "System checks"
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$osName = $osInfo.Caption
$osVersion = $osInfo.Version
$osBuild = $osInfo.BuildNumber

# Detect Windows version
if ($osName -like "*Windows 11*") {
    Write-Success "Windows 11 detected" 
    Write-Success "Windows 11 Build $osBuild"
    Write-Success "Windows 11 Version $osVersion"
    
    # Windows 11 specific checks
    $win11Features = @()
    
    # Check for Windows 11 features
    try {
        $tpm = Get-CimInstance -Namespace "root\cimv2\security\microsofttpm" -ClassName Win32_Tpm -ErrorAction SilentlyContinue
        if ($tpm) { $win11Features += "TPM 2.0" }
    } catch {}
    
    try {
        $secureBoot = Confirm-SecureBootUEFI -ErrorAction SilentlyContinue
        if ($secureBoot) { $win11Features += "Secure Boot" }
    } catch {}
    
    try {
        $hyperV = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue
        if ($hyperV.State -eq "Enabled") { $win11Features += "Hyper-V" }
    } catch {}
    
    try {
        $wsl = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -ErrorAction SilentlyContinue
        if ($wsl.State -eq "Enabled") { $win11Features += "WSL" }
    } catch {}
    
    if ($win11Features.Count -gt 0) {
        Write-Success "Advanced features: $($win11Features -join ', ')"
    }
    
} else {
    Write-Error "Windows 11 required - rendersync was not tested on $osName"
    Write-Host "`nPress any key to exit" -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# System capabilities check
Write-Info "System capabilities"
try {
    $cpu = Get-CimInstance -ClassName Win32_Processor
    $ram = Get-CimInstance -ClassName Win32_ComputerSystem
    $gpu = Get-CimInstance -ClassName Win32_VideoController | Where-Object { $_.Name -notlike "*Basic*" -and $_.Name -notlike "*Standard*" }
    
    Write-Success "CPU: $($cpu.Name.Trim())"
    Write-Success "RAM: $([math]::Round($ram.TotalPhysicalMemory / 1GB, 1)) GB"
    
    if ($gpu) {
        Write-Success "GPU: $($gpu.Name.Trim())"
        if ($gpu.AdapterRAM) {
            $gpuRam = [math]::Round($gpu.AdapterRAM / 1GB, 1)
            Write-Success "VRAM: $gpuRam GB"
        }
    }
} catch {
    Write-Warning "System info unavailable"
}

# Check if venv exists, create if missing
$venvActivate = "$projectRoot\.venv\Scripts\Activate.ps1"
if (-Not (Test-Path $venvActivate)) {
    Write-Info "Virtual environment not found. Creating .venv"
    
    # Create virtual environment
    Write-Info "Creating Python virtual environment"
    python -m venv "$projectRoot\.venv"
    
    if (-Not (Test-Path $venvActivate)) {
        Write-Error "Failed to create virtual environment"
        Write-Host "`nPress any key to exit" -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }
    
    # Activate venv and install requirements
    Write-Info "Activating virtual environment and installing requirements"
    & $venvActivate
    
    # Upgrade pip first using the recommended method
    Write-Info "Upgrading pip to latest version"
    python -m pip install --upgrade pip
    
    # Install requirements
    Write-Info "Installing project requirements"
    pip install -r "$projectRoot\requirements.txt"
    
    Write-Success "Virtual environment created and requirements installed"
}

# Function to cleanup on exit
function Cleanup {
    Write-Info "Shutting down"
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Success "Cleanup complete"
}

# Register cleanup on script exit
trap { Cleanup; break }

# Start server in a new window so we can see output
Write-Info "Starting FastAPI server"
$serverProcess = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; & '$venvActivate'; python -m uvicorn rendersync.main:app --host 127.0.0.1 --port 8080 --workers 1" -PassThru

# Wait for server to start
Write-Info "Waiting for server to start"
$maxAttempts = 15
$attempt = 0
do {
    Start-Sleep -Seconds 1
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Success "Server is ready"
            
            Write-Info "Launching web interface"
            $browsers = @(
                @{ name = "Microsoft Edge"; path = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" },
                @{ name = "Google Chrome"; path = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe" },
                @{ name = "Google Chrome (x86)"; path = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe" },
                @{ name = "Mozilla Firefox"; path = "${env:ProgramFiles}\Mozilla Firefox\firefox.exe" },
                @{ name = "Mozilla Firefox (x86)"; path = "${env:ProgramFiles(x86)}\Mozilla Firefox\firefox.exe" }
            )
            
            $browserLaunched = $false
            foreach ($browser in $browsers) {
                if (Test-Path $browser.path) {
                    try {
                        Start-Process -FilePath $browser.path -ArgumentList "http://127.0.0.1:8080" -ErrorAction SilentlyContinue
                        Write-Success "Launched $($browser.name)"
                        $browserLaunched = $true
                        break
                    } catch {
                        Write-Warning "Failed to launch $($browser.name)"
                    }
                }
            }
            
            if (-not $browserLaunched) {
                Write-Warning "No supported browser found. Please open http://127.0.0.1:8080 manually"
            }
            
            Write-Success "Server started successfully. Closing launcher window"
            Start-Sleep -Seconds 2
            exit 0
        }
    } catch {
        if ($attempt -eq 5) {
            Write-Warning "Server taking longer than expected to start"
        }
        if ($attempt -ge $maxAttempts) {
            Write-Error "Server failed to start within $maxAttempts seconds"
            Write-Info "Check the server window for error messages"
            Cleanup
            Write-Host "`nPress any key to exit" -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            exit 1
        }
    }
} while ($true)


