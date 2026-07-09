@echo off
chcp 65001 >nul 2>&1
title GenBox Launcher

echo.
echo ========================================
echo   GenBox Launcher
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found, please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check dependencies
echo Checking dependencies...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

:: Run environment check
echo.
echo Running environment check...
python check_env.py

:: Start service
echo.
echo Starting GenBox...
echo Access: http://localhost:8891
echo Press Ctrl+C to stop
echo.
python main.py

pause
