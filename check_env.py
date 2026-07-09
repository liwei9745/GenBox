"""
GenBox 环境检查脚本
用于诊断启动失败问题
"""
import os
import sys
import platform
import subprocess
import socket
import json
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def print_check(name, status, detail=""):
    icon = "✅" if status else "❌"
    print(f"  {icon} {name}")
    if detail:
        print(f"      {detail}")

def check_python():
    print_header("Python 环境")
    version = sys.version_info
    print_check("Python 版本", True, f"{version.major}.{version.minor}.{version.micro}")
    print_check("Python 路径", True, sys.executable)
    
    # 检查关键依赖
    required = ["fastapi", "uvicorn", "httpx", "aiofiles", "PIL", "psutil", "dotenv"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    
    if missing:
        print_check("关键依赖", False, f"缺少: {', '.join(missing)}")
        print("      解决方案: pip install -r requirements.txt")
    else:
        print_check("关键依赖", True, "所有必需模块已安装")

def check_port(port=8891):
    print_header(f"端口检查 (默认: {port})")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    
    if result == 0:
        print_check(f"端口 {port}", False, "已被占用")
        print("      解决方案:")
        print(f"        1. 关闭占用端口的程序")
        print(f"        2. 或设置环境变量: set PORT=其他端口")
    else:
        print_check(f"端口 {port}", True, "可用")

def check_config():
    print_header("配置文件")
    env_file = Path(".env")
    config_dir = Path("config")
    
    if env_file.exists():
        print_check(".env 文件", True, "存在")
        # 检查关键配置
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "ADMINKEY=" in content and not content.split("ADMINKEY=")[1].split("\n")[0].strip():
                print_check("ADMINKEY 配置", False, "未设置")
            else:
                print_check("ADMINKEY 配置", True)
    else:
        print_check(".env 文件", False, "不存在")
        print("      解决方案: 复制 .env.example 为 .env 并配置")
    
    if config_dir.exists():
        providers_file = config_dir / "providers.json"
        if providers_file.exists():
            print_check("providers.json", True, "存在")
        else:
            print_check("providers.json", False, "不存在")
    else:
        print_check("config 目录", False, "不存在")

def check_storage():
    print_header("存储目录")
    dirs = ["storage", "storage/gallery", "storage/videos", "storage/temp"]
    for d in dirs:
        path = Path(d)
        if path.exists():
            print_check(d, True)
        else:
            print_check(d, False, "目录不存在，将自动创建")

def check_system():
    print_header("系统信息")
    print_check("操作系统", True, f"{platform.system()} {platform.release()}")
    print_check("架构", True, platform.machine())
    print_check("用户名", True, os.getenv("USERNAME", os.getenv("USER", "Unknown")))

def check_dependencies():
    print_header("系统依赖")
    
    # 检查 FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        print_check("FFmpeg", True, "已安装")
    except FileNotFoundError:
        print_check("FFmpeg", False, "未安装 (视频功能需要)")
        print("      下载: https://ffmpeg.org/download.html")
    except subprocess.TimeoutExpired:
        print_check("FFmpeg", True, "已安装 (版本检查超时)")

def main():
    print("\n" + "="*60)
    print("  GenBox 环境检查工具")
    print("  用于诊断启动失败问题")
    print("="*60)
    
    check_system()
    check_python()
    check_port()
    check_config()
    check_storage()
    check_dependencies()
    
    print_header("诊断完成")
    print("  如果有 ❌ 标记的问题，请按照解决方案修复后重试。")
    print("  如需帮助，请将此输出提交到 GitHub Issues。")
    print()

if __name__ == "__main__":
    main()
    input("\n按 Enter 键退出...")
