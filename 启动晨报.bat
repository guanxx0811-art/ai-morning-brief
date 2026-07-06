@echo off
chcp 65001 >nul
title AI 晨报网站

echo ========================================
echo   AI 晨报网站 — 正在启动...
echo ========================================
echo.

cd /d "%~dp0"
echo 工作目录: %CD%
echo.

echo [1/2] 启动服务...
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

echo.
echo [2/2] 等待服务启动...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   服务已启动！
echo   访问地址: http://localhost:8000
echo ========================================
echo.
echo 提示：关闭此窗口将停止服务
echo.

start http://localhost:8000

echo 按任意键停止服务...
pause >nul
taskkill /F /IM python.exe 2>nul
echo 服务已停止
timeout /t 2 >nul