# GenBox PowerShell 启动器
# 支持自动检查环境和启动服务

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Check {
    param([string]$Name, [bool]$Status, [string]$Detail = "")
    if ($Status) {
        Write-Host "  ✅ $Name" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $Name" -ForegroundColor Red
    }
    if ($Detail) {
        Write-Host "      $Detail" -ForegroundColor Gray
    }
}

# 主程序
Clear-Host
Write-Header "GenBox Launcher / GenBox 启动器"

# 检查 Python
Write-Host ""
Write-Host "Check Python / 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Check "Python" $true $pythonVersion
} catch {
    Write-Check "Python" $false "Not found / 未找到; install Python 3.10+ / 请安装 Python 3.10+"
    Write-Host "  Download / 下载: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit / 按 Enter 退出"
    exit 1
}

# 检查依赖
Write-Host ""
Write-Host "Check dependencies / 检查依赖..." -ForegroundColor Yellow
$required = @("fastapi", "uvicorn", "httpx", "aiofiles", "PIL", "psutil", "dotenv")
$missing = @()
foreach ($mod in $required) {
    try {
        python -c "import $mod" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $missing += $mod }
    } catch {
        $missing += $mod
    }
}

if ($missing.Count -gt 0) {
    Write-Check "Dependencies / 依赖" $false "Missing / 缺少: $($missing -join ', ')"
    Write-Host "  Installing dependencies / 正在安装依赖..." -ForegroundColor Yellow
    pip install -r requirements.txt
} else {
    Write-Check "Dependencies / 依赖" $true "All required modules installed / 所有必需模块已安装"
}

# 检查端口
Write-Host ""
Write-Host "Check port / 检查端口..." -ForegroundColor Yellow
$port = 8891
$portAvailable = $true
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("127.0.0.1", $port)
    $conn.Close()
    $portAvailable = $false
} catch {
    $portAvailable = $true
}

if ($portAvailable) {
    Write-Check "Port $port / 端口 $port" $true "Available / 可用"
} else {
    Write-Check "Port $port / 端口 $port" $false "Already in use / 已被占用"
    Write-Host "  Solutions / 解决方案:" -ForegroundColor Yellow
    Write-Host "    1. Close the process using this port / 关闭占用端口的程序" -ForegroundColor Gray
    Write-Host "    2. Set another port in the environment / 设置其他端口" -ForegroundColor Gray
}

# 检查配置
Write-Host ""
Write-Host "Check configuration / 检查配置..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Check ".env" $true "Present / 存在"
} else {
    Write-Check ".env" $false "Missing / 不存在"
    Write-Host "  Creating from template / 正在从模板创建..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Check ".env" $true "Created / 已创建"
    }
}

# 运行环境检查
Write-Host ""
Write-Host "Run detailed environment check / 运行详细环境检查..." -ForegroundColor Yellow
python check_env.py

# 启动服务
Write-Header "Start GenBox / 启动 GenBox"
Write-Host "  URL / 访问地址: http://localhost:$port" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop / 按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host ""
python main.py

Read-Host "Press Enter to exit / 按 Enter 退出"
