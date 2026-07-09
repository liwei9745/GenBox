## GenBox v2.0.0-test.6

> 一站式 AI 创作平台 - 桌面客户端测试版

---

## 下载说明

### Windows
| 文件 | 说明 |
|------|------|
| `GenBox.exe` | 双击运行，自动打开浏览器 |

**使用方法：**
1. 下载 `GenBox.exe`
2. 双击运行
3. 浏览器自动打开 `http://localhost:8891`
4. 首次运行会自动生成管理员密钥

**注意事项：**
- 首次运行需要允许防火墙访问
- 如遇 Windows Defender 警告，点击"仍要运行"

---

### macOS
| 文件 | 说明 |
|------|------|
| `GenBox-macOS` | 命令行运行 |

**使用方法：**
```bash
# 1. 下载后赋予执行权限
chmod +x GenBox-macOS

# 2. 运行
./GenBox-macOS

# 3. 浏览器自动打开 http://localhost:8891
```

**注意事项：**
- 首次运行需要在「系统设置 > 隐私与安全性」中允许
- 如提示"无法验证开发者"，点击"仍要打开"

---

### Linux (桌面版)
| 文件 | 说明 |
|------|------|
| `GenBox-Linux` | 命令行运行 |

**使用方法：**
```bash
# 1. 下载后赋予执行权限
chmod +x GenBox-Linux

# 2. 运行
./GenBox-Linux

# 3. 浏览器自动打开 http://localhost:8891
```

---

### Linux (服务器/无头版)
| 文件 | 说明 |
|------|------|
| `GenBox-Linux` | 适用于无显示器的服务器 |

**使用方法：**
```bash
# 1. 上传到服务器
scp GenBox-Linux user@server:/path/to/

# 2. SSH 登录服务器
ssh user@server

# 3. 赋予执行权限
chmod +x GenBox-Linux

# 4. 后台运行
nohup ./GenBox-Linux > genbox.log 2>&1 &

# 5. 从其他设备浏览器访问
http://服务器IP:8891
```

**注意事项：**
- 需要安装 ffmpeg：`sudo apt install ffmpeg`
- 确保防火墙开放 8891 端口
- 配置文件在可执行文件同目录的 `.env`

---

## 环境变量配置

在可执行文件同目录创建 `.env` 文件：

```bash
# 运行模式
APP_MODE=dev          # dev=免认证, prod=需要管理员密钥

# API 配置
GPT_IMAGE_API_KEY=your-key
GEMINI_API_KEY=your-key
```

---

## 已知问题

- Linux 服务器版需要手动安装 ffmpeg
- macOS 首次运行需要手动允许安全权限
- Windows 可能触发 Defender 警告

---

## 更新日志

### v2.0.0-test.6 (2026-07-09)
- 修复 macOS 和 Linux 文件名冲突
- 修复无头 Linux 服务器兼容性

### v2.0.0-test.1 (2026-07-09)
- 初始测试版发布
- 支持 Windows / macOS / Linux 三平台

---

**测试反馈：** 请在 Issues 中报告问题
