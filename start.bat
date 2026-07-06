@echo off
cd /d "%~dp0"
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
timeout /t 3 /nobreak >nul
start http://localhost:8000
echo Press any key to stop...
pause >nul
taskkill /F /IM python.exe 2>nul