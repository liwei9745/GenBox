@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
color 0B
echo.
echo  ============================================
echo    Image Gen Studio v2 - Stopping...
echo  ============================================
echo.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8890 ^| findstr LISTENING') do (
    echo    Killing PID %%a...
    taskkill /PID %%a /F >nul 2>&1
)
echo.
echo  ============================================
echo    Server stopped.
echo  ============================================
echo.
timeout /t 2 /nobreak >nul
