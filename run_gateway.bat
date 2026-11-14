
@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Virtual environment not found.
    pause
    exit /b 1
)

echo Checking WebSocket...
"%PYTHON%" -c "import websocket; print('WebSocket OK')"

if errorlevel 1 (
    echo WebSocket dependency is missing.
    pause
    exit /b 1
)

echo Starting Gateway...
"%PYTHON%" -m gateway.gateway

pause
