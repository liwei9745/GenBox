# GenBox v2.5.0 - 扩展中心、双语体验与可验证发布

> 这是一次覆盖产品体验、远程服务管理、安全边界和发布基础设施的重大更新。

## 最值得关注的变化

### 1. 扩展中心正式进入主界面

GenBox 现在提供面向非开发者的远程服务管理流程：

- 保存并管理多个 VPS 目标。
- 确认 SSH 主机指纹，执行只读环境发现。
- 为 chatgpt2api 生成隔离部署计划并部署独立实例。
- 配置和验证 Tailscale 私网链路。
- 查看已部署实例、控制台/API 地址和运行状态。
- 默认仅本次显示管理密钥，也可明确选择保存在本机加密凭证库。

现有生产 chatgpt2api 实例在整个开发流程中保持只读；开发与验收使用独立目录、端口、容器、Compose 项目和凭证。

### 2. GenBox 与 chatgpt2api 的连接基础

- 保留 GenBox 主动发起的远程 Pull，可把兼容实例图片导入本地媒体库。
- 新增认证、幂等的 GenBox Push 接收端，支持来源身份、SHA-256 校验、内容去重和导入回执。
- 网络向导可以准备本机与 VPS 的私网连接并保存最终目标 URL。

> [!NOTE]
> chatgpt2api 发送端的单图自动 Push、批量和定时增量 Push、确认后源图清理尚未端到端完成。这些能力不会在本版本中被描述为可用。

### 3. 全新的双语与新手体验

- 中文和 English 改为固定翻译键，不再扫描页面文字做运行时替换。
- Dashboard、Images、Video、Media Library、History、Extensions 使用统一三行标题体系。
- 四段式新手引导依次介绍首次创作、GenBox 能力、chatgpt2api 和连接价值。
- Dashboard 语言选择会更新 `?lang=` 并保留当前路由。
- 新手引导始终可以从 Sidebar 和 Dock 重新打开。

### 4. 创作工作台与视觉系统升级

- 图片和视频支持单模型工作台与多模型并排对比。
- 图片提示词卡与视频输入统一为“标题 → 输入 → 全宽主操作”。
- 图片工作台增加可折叠工具栏和任务监视器。
- 媒体库、历史和 Extensions 标题统一，导航使用同一套线性图标。
- 提供 10 套协调主题，深色主题覆盖页面、卡片、输入框、Dock 与侧栏。

### 5. 发布包可以被实际验证

感谢 [@yukkcat](https://github.com/yukkcat) 在 [PR #4](https://github.com/liwei9745/GenBox/pull/4) 中提出 Docker Compose 一键部署包方案。本版本在此基础上补齐：

- Compose 默认拉取 `ghcr.io/liwei9745/genbox`，无需本地构建源码。
- Docker 发布包使用独立生产环境模板，不复用开发端口配置。
- Windows、macOS、Linux 客户端在 CI 中构建后会实际启动并检查 HTTP 端点。
- 修复 Windows 客户端首次启动时 GBK 控制台输出 Emoji 导致的崩溃。
- 发布包附带 `SHA256SUMS.txt`。
- 运行依赖、测试依赖和 PyInstaller 构建依赖分离并锁定。

## 下载文件

| 文件 | 用途 |
|---|---|
| `GenBox-Windows.zip` | Windows 开箱客户端 |
| `GenBox-macOS.zip` | macOS 客户端 |
| `GenBox-Linux-x64.zip` | Linux/VPS 客户端 |
| `GenBox-Docker-Compose-v2.5.0.zip` | Docker Compose 一键部署包 |
| `SHA256SUMS.txt` | 所有发布文件的 SHA-256 校验值 |

## 安装与升级

### 桌面客户端

解压平台压缩包并运行可执行文件。客户端无需安装 Python，默认访问：

```text
http://localhost:8891
```

### Docker Compose

```bash
cp .env.example .env
docker compose pull
docker compose up -d
```

远程访问前，请在 `.env` 中把 `ALLOWED_ORIGINS` 设置为实际 HTTPS 或私网 URL。运行数据保存在 `./storage`，升级前请备份该目录。

### 从旧版本升级

> [!IMPORTANT]
> v2.4.1 及更早的 Windows EXE 更新器会误选 ZIP，并尝试覆盖正在运行的自身文件。这次不能依赖旧版的“在线更新”：请手动下载 `GenBox-Windows.zip`，退出旧版后解压替换可执行文件。v2.5.0 已修复资产选择和退出后替换流程，后续版本可使用新的在线更新链路。

1. 备份 `.env`、`storage/providers.json`、媒体库和其他运行数据。
2. 不要用发布包覆盖现有 `storage/`。
3. 源码 Git 用户必须先保存本地修改；旧更新器使用 `git reset --hard` 跟随当前远程分支。
4. 旧 Docker 用户先下载新的 Docker Compose 包，保留 `.env` 和 `storage/`，再执行 `docker compose pull && docker compose up -d`。旧 Compose 中的本地 `build` 配置无法通过应用内按钮迁移为 GHCR 镜像。
5. 启动后检查模型设置、媒体库、管理员登录和远程同步配置。

## 安全说明

- 不要分享 `.env`、`storage/`、凭证库、原始日志或用户媒体。
- 管理员密钥与每个 Push 来源密钥相互独立。
- Tailscale Auth Key、Push Key 和 GenBox 管理员密钥不会保存在浏览器存储中。
- 源图片默认不删除；后续清理必须同时满足认证回执、SHA-256 匹配和用户明确选择。
- chatgpt2api 是第三方逆向研究项目，存在账号受限风险，不要使用重要账号测试。

## 验证摘要

- 76 项本地自动化测试通过，包括发布资产选择、Windows 退出后替换脚本、打包客户端控制台输出和公开截图引用。
- 中文和 English 主路由及新手引导通过桌面、窄屏和手机视口检查。
- 全新隔离 Python 环境完成依赖安装与测试。
- Windows PyInstaller 客户端成功构建并通过真实 HTTP 启动冒烟检查。
- Docker Compose 发布包结构和生产环境模板通过自动化测试。

## 已知限制

- chatgpt2api 发送端 Push、批量/定时同步和安全源图清理仍在后续阶段。
- 扩展部署任务在进程重启后的持久恢复仍需完善。
- NetBird 与 Cloudflare Tunnel 尚未达到与 Tailscale 相同的完整验收状态。
- v2.4.1 及更早的 Windows EXE 到 v2.5.0 需要一次手动升级；旧 Docker Compose 需要手动迁移配置。
- 最新 Starlette 测试客户端提示未来将迁移到 `httpx2`；当前运行和测试不受影响。

完整状态和验收证据见 [`docs/STATUS.md`](docs/STATUS.md)。
