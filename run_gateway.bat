@echo off
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python gateway\gateway.py
pause
