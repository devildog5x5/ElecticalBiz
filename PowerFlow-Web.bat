@echo off
cd /d "%~dp0"
python main.py --web --browser
if errorlevel 1 pause
