@echo off
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title GenBox Launcher / GenBox 启动器

echo.
echo ========================================
echo   GenBox Launcher / GenBox 启动器
echo ========================================
echo.

:: Clear PYTHONPATH to avoid pollution
set PYTHONPATH=

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found / 未找到 Python，请安装 Python 3.10+
    echo Download / 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check dependencies
echo Checking dependencies / 检查依赖...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies / 安装依赖...
    pip install -r requirements.txt
)

:: Run environment check
echo.
echo Running environment check / 检查运行环境...
python check_env.py

:: Start service
echo.
echo Starting GenBox / 启动 GenBox...
echo Access / 访问: http://localhost:8891
echo Press Ctrl+C to stop / 按 Ctrl+C 停止
echo.
python main.py

pause
