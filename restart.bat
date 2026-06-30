@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
color 0B
echo.
echo  ============================================
echo    Image Gen Studio v2 - Restarting...
echo  ============================================
echo.
cd /d "%~dp0"

echo  [1/2] Stopping old process...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8890 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo  [2/2] Starting new process...
start "" python main.py
echo.
echo  ============================================
echo    Server restarted on http://localhost:8890
echo  ============================================
echo.
timeout /t 3 /nobreak >nul
