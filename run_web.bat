@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Create it first with:
    echo py -m venv .venv
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo.
echo Smart Greenhouse Web
echo ====================
echo.

for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    set "IP=%%A"
    goto :found
)

:found
if defined IP (
    set "IP=%IP: =%"
    echo LAN address: http://%IP%:8000
) else (
    echo LAN address: http://<LAPTOP-IP>:8000
)

echo Local address: http://127.0.0.1:8000
echo.
echo Keep this window open while the web server is running.
echo.

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

pause
