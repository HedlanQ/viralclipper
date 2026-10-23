@echo off
title ViralClipper - AI Video Clip Generator
cd /d "%~dp0backend"

echo =======================================================
echo          ⚡ Welcome to ViralClipper ⚡
echo   AI-Powered Viral Video Clipper ^& Dead-Air Remover
echo =======================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Python not found in PATH. Please install Python 3.10+.
        pause
        exit /b 1
    )
    echo [2/3] Installing dependencies...
    venv\Scripts\pip.exe install -r requirements.txt
)

echo [3/3] Starting ViralClipper Web App...
echo.
echo Application will be available at: http://localhost:8000
echo.

start "" "http://localhost:8000"
venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload

pause
