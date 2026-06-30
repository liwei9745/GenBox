@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Image Gen Studio v2
color 0B
cd /d "%~dp0"

if "%1"=="--reset-admin" (
    echo.
    echo  [Admin Reset] 正在重置管理密钥...
    python main.py --reset-admin
    echo.
    pause
    exit /b
)

echo.
echo  ============================================
echo    Image Gen Studio v2 - Starting...
echo    Port: 8890
echo    URL:  http://localhost:8890
echo  ============================================
echo.
python main.py
pause
