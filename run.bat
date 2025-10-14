@echo off
REM rendersync launcher batch file
REM This batch file runs the PowerShell script run.ps1

echo Starting rendersync
echo.

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available on this system
    echo Please install PowerShell or run run.ps1 directly
    pause
    exit /b 1
)

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1"

REM If we get here, the PowerShell script has finished
echo.
echo rendersync has finished running
pause
