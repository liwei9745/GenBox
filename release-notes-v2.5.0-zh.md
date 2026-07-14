# GenBox v2.5.0 - 更容易上手，也更适合长期使用

> 多模型创作、扩展中心、双语新手引导和新的发布流程集中到同一个稳定版本。

## 先下载哪个？

| 你的设备 | 推荐下载 | 下载后怎么做 |
|---|---|---|
| Windows 10/11 | [GenBox-Windows.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-Windows.zip) | 解压后双击 `GenBox.exe` |
| macOS | [GenBox-macOS.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-macOS.zip) | 解压后运行 `GenBox-macOS` |
| Linux | [GenBox-Linux-x64.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-Linux-x64.zip) | 解压并添加执行权限 |
| NAS / VPS / Docker | [GenBox-Docker-Compose-v2.5.0.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/GenBox-Docker-Compose-v2.5.0.zip) | 解压、配置 `.env`、启动 Compose |

桌面压缩包已经包含运行环境，不需要安装 Python。启动后访问：

```text
http://localhost:8891
```

`GenBox.exe`、`GenBox-macOS` 和 `GenBox-Linux-x64` 是供在线更新器使用的独立文件；第一次下载更推荐使用 ZIP。

## 3 分钟开始使用

1. 下载并解压对应平台的 ZIP。
2. 启动 GenBox；浏览器没有自动打开时访问 `http://localhost:8891`。
3. 在“模型设置”中添加一个可用的模型服务地址、模型名和 API Key。
4. 进入“图片生成”，选择模型并输入提示词。

> [!IMPORTANT]
> **从 v2.4.1 或更早的 Windows 版本升级时，请不要使用旧版在线更新。** 旧更新器可能选中 ZIP 并尝试覆盖正在运行的程序。请退出旧版，手动下载 `GenBox-Windows.zip` 并解压替换一次。v2.5.0 已修复后续版本使用的更新流程。

## 这次更新带来了什么？

| 多模型图片工作台 | 扩展中心 |
|---|---|
| ![GenBox 多模型图片工作台](screenshots/sanitized/02-generate-workspace.png) | ![GenBox 扩展中心](screenshots/sanitized/03-extension-center.png) |

### 创作体验

- 图片和视频都支持单模型工作台与多模型并排对比。
- 图片工作台加入可折叠创作工具和任务监视器。
- 媒体库、历史记录和提示词复用继续保留在本地工作流中。
- 10 套主题、统一线性图标和自动隐藏 Dock 让页面更整洁。

### 小白上手

- 中文和 English 使用稳定的固定翻译，不再扫描页面文字临时替换。
- 新手引导按“第一次创作、GenBox 能做什么、chatgpt2api 是什么、为什么连接”组织。
- Dashboard、Images、Video、Media Library、History 和 Extensions 使用统一标题与说明。

### 扩展中心

- 图形化保存 VPS、确认 SSH 主机指纹并执行只读环境发现。
- 为独立 chatgpt2api 实例生成固定部署计划。
- 引导准备和验证 Tailscale 私网连接。
- 管理服务地址、运行状态和用户明确选择保存的本机加密凭证。

## 修复了什么？

- 修复 Windows 首次启动时，GBK 控制台无法输出部分 Unicode 字符导致的崩溃。
- 修复在线更新器误选 ZIP，以及运行中程序无法安全替换自身的问题。
- 修复视频 Provider 初始化时序导致的模型列表加载失败。
- 修复部分深色主题仍出现白色主面板的问题。
- 修复页面路由、返回/前进、刷新后工作台状态不能稳定恢复的问题。
- 发布流程现在会实际启动 Windows、macOS 和 Linux 客户端并检查 HTTP 服务。

## Docker 快速启动

```bash
cp .env.example .env
docker compose pull
docker compose up -d
```

运行数据保存在 `storage/`。远程访问前必须设置管理员密钥，并把 `ALLOWED_ORIGINS` 改为实际 HTTPS 或私网地址。

## 从旧版本升级

1. 备份 `.env`、`storage/providers.json`、媒体库和其他 `storage/` 数据。
2. 不要用发布包覆盖现有 `storage/`。
3. v2.4.1 及更早 Windows 版本按上方说明手动升级一次。
4. 旧 Docker 用户保留 `.env` 和 `storage/`，改用新的 Compose 包，再执行 `docker compose pull && docker compose up -d`。
5. 启动后检查模型设置、媒体库、管理员登录和远程同步配置。

## 当前限制

- chatgpt2api 发送端的生成后自动 Push、批量/定时同步和确认后清理仍未端到端完成。
- 扩展部署任务在进程重启后的持久恢复仍需完善。
- NetBird 与 Cloudflare Tunnel 尚未达到与 Tailscale 相同的完整验收状态。
- chatgpt2api 是第三方逆向研究项目，存在账号受限风险，不要使用重要账号测试。

<details>
<summary><strong>安全、校验和与发布验证</strong></summary>

- 所有发布文件的 SHA-256 位于 [SHA256SUMS.txt](https://github.com/liwei9745/GenBox/releases/download/v2.5.0/SHA256SUMS.txt)。
- 管理员密钥、Push 来源密钥和 Tailscale 授权信息相互独立。
- 源图片默认保留；未来清理必须有认证回执、匹配 SHA-256 和用户明确选择。
- 三平台客户端由 GitHub Actions 构建，并在发布前执行真实 HTTP 启动冒烟检查。
- Docker Compose 包默认拉取 `ghcr.io/liwei9745/genbox`，不需要本地构建源码。

</details>

<details>
<summary><strong>开发者与完整变更资料</strong></summary>

- [更新记录](CHANGELOG.md)
- [当前状态与验证证据](docs/STATUS.md)
- [文档矩阵](docs/README.md)
- [全部发布文件](https://github.com/liwei9745/GenBox/releases/tag/v2.5.0)

</details>

感谢 [@yukkcat](https://github.com/yukkcat) 在 [PR #4](https://github.com/liwei9745/GenBox/pull/4) 中提出 GHCR Docker Compose 发布包方案。
