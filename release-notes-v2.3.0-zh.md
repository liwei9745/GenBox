- **Windows**: 双击 `GenBox.exe` 启动（建议先运行 `check_env.py` 检查环境）
- **macOS**: 解压后运行 `./GenBox-macOS`（需执行 `xattr -c GenBox-macOS` 去隔离）
- **Linux**: 解压后运行 `./GenBox-Linux-x64`

### 快速开始

1. 确保 Python 3.10+ 已安装
2. 下载对应平台的 zip 包
3. 解压后运行：
   ```bash
   # Windows
   GenBox.exe

   # macOS/Linux
   ./GenBox-macOS  # 或 ./GenBox-Linux-x64
   ```

### 环境配置

首次运行会进入**交互式配置向导**：
- 选择运行模式：本地开发 / VPS 生产 / Docker
- 配置 API Keys（支持 OpenAI、Claude、Gemini 等 13 个服务商）
- 可选配置代理

### 更新日志 v2.3.0

**安全加固**
- 密钥脱敏：Provider API Keys 返回时自动掩码（如 `sk-a****12c`）
- SSRF 防护：拦截内网 IP 请求，防止端口扫描
- CSRF 防护：Origin/Referer 校验中间件
- CSP 增强：更严格的 Content-Security-Policy

**自动更新系统**
- 一键检查更新：`/api/update/check`
- GitHub 镜像加速：支持 6 个国内镜像源
- 自动修复：检测并修复损坏的安装
- Docker 适配：容器环境自动检测与提示

**生产模式升级**
- 首次运行向导：3 种运行模式（本地/VPS/Docker）
- 管理员认证：VPS 部署强制设置密钥
- 安全头部：CSP + CSRF + 认证中间件

**配置增强**
- 逐服务商代理：`skip_proxy: true` 跳过特定服务商的代理
- 配置文件：`config/settings.yaml` 详细注释
- 环境变量：`.env.example` 文档完善

### 系统要求

- Python 3.10 或更高版本
- 无需安装依赖（exe 已打包）

### 已知问题

- Windows 杀毒软件可能误报（PyInstaller 通病）
- macOS 首次运行需执行 `xattr -c` 去隔离
- Linux 需要 `libgl1` 依赖（GUI 模式）

### 相关链接

- [GitHub 仓库](https://github.com/liwei9745/GenBox)
- [问题反馈](https://github.com/liwei9745/GenBox/issues)
- [配置文档](https://github.com/liwei9745/GenBox/blob/main/README.md)

### 密钥重置

如需重置管理员密钥，删除 `config/settings.yaml` 文件，重启服务后首次运行向导会提示重新设置：

```bash
# Windows
del config\settings.yaml

# macOS/Linux
rm config/settings.yaml
```
