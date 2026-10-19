@echo off
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
REM run as a module: gateway.py uses package-relative imports
python -m gateway.gateway
pause
