@echo off
chcp 65001 >nul 2>&1
title GenBox 启动器

echo.
echo ========================================
echo   GenBox 启动器
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
echo 正在检查依赖...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

:: 运行环境检查
echo.
echo 正在运行环境检查...
python check_env.py

:: 启动服务
echo.
echo 正在启动 GenBox...
echo 启动后请访问: http://localhost:8891
echo 按 Ctrl+C 停止服务
echo.
python main.py

pause
