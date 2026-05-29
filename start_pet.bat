@echo off
cd /d "%~dp0"
start /b "" pythonw main.py >nul 2>&1
exit
