# ViralClipper Launcher for PowerShell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\backend"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         ⚡ Welcome to ViralClipper ⚡" -ForegroundColor Yellow
Write-Host "  AI-Powered Viral Video Clipper & Dead-Air Remover" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "[1/3] Creating Python virtual environment..." -ForegroundColor White
    python -m venv venv
    Write-Host "[2/3] Installing dependencies..." -ForegroundColor White
    .\venv\Scripts\pip.exe install -r requirements.txt
}

Write-Host "[3/3] Starting ViralClipper Web App..." -ForegroundColor Green
Write-Host "Open your browser at: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

Start-Process "http://localhost:8000"
& ".\venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload
