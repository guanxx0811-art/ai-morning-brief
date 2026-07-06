@echo off
cd /d "%~dp0"

echo Starting AI Morning Brief...
echo.

echo Waiting for server to start...
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
ping -n 5 127.0.0.1 >nul

echo Opening browser...
start http://localhost:8000

echo.
echo Server is running. Close this window to stop.
pause >nul
taskkill /F /IM python.exe 2>nul