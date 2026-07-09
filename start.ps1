# GenBox PowerShell 启动器
# 支持自动检查环境和启动服务

$ErrorActionPreference = "Stop"

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
Write-Header "GenBox 启动器"

# 检查 Python
Write-Host ""
Write-Host "检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Check "Python" $true $pythonVersion
} catch {
    Write-Check "Python" $false "未找到，请安装 Python 3.10+"
    Write-Host "  下载: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按 Enter 退出"
    exit 1
}

# 检查依赖
Write-Host ""
Write-Host "检查依赖..." -ForegroundColor Yellow
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
    Write-Check "依赖" $false "缺少: $($missing -join ', ')"
    Write-Host "  正在安装依赖..." -ForegroundColor Yellow
    pip install -r requirements.txt
} else {
    Write-Check "依赖" $true "所有必需模块已安装"
}

# 检查端口
Write-Host ""
Write-Host "检查端口..." -ForegroundColor Yellow
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
    Write-Check "端口 $port" $true "可用"
} else {
    Write-Check "端口 $port" $false "已被占用"
    Write-Host "  解决方案:" -ForegroundColor Yellow
    Write-Host "    1. 关闭占用端口的程序" -ForegroundColor Gray
    Write-Host "    2. 或设置环境变量: `$env:PORT=其他端口" -ForegroundColor Gray
}

# 检查配置
Write-Host ""
Write-Host "检查配置..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Check ".env" $true "存在"
} else {
    Write-Check ".env" $false "不存在"
    Write-Host "  正在从模板创建..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Check ".env" $true "已创建"
    }
}

# 运行环境检查
Write-Host ""
Write-Host "运行详细环境检查..." -ForegroundColor Yellow
python check_env.py

# 启动服务
Write-Header "启动 GenBox"
Write-Host "  访问地址: http://localhost:$port" -ForegroundColor Green
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host ""
python main.py

Read-Host "按 Enter 退出"
