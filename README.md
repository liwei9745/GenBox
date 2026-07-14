# GenBox - 本地优先的 AI 创作与媒体管理工作台

[![CI](https://github.com/liwei9745/GenBox/actions/workflows/build.yml/badge.svg)](https://github.com/liwei9745/GenBox/actions/workflows/build.yml)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue?logo=docker)](https://github.com/liwei9745/GenBox/pkgs/container/genbox)
[![Python](https://img.shields.io/badge/Python-3.12-yellow?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/github/license/liwei9745/GenBox)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/liwei9745/GenBox/pulls)

GenBox 把图片生成、视频生成、提示词辅助、媒体库、历史记录和远程服务管理放在一个本地 Web 工作台中。它既可以作为桌面客户端运行，也可以部署在 NAS、VPS 或 Docker 中。

> [!IMPORTANT]
> **v2.5.0 是一次重大体验与基础设施更新。**
> 本次新增扩展中心、chatgpt2api 引导部署与私网连接、双语界面、四段式新手引导、统一页面标题、加密凭证库和新的发布构建链路。GenBox 已具备远程 Pull 同步和认证幂等的 Push 接收端基础；chatgpt2api 发送端自动 Push、批量/定时搬运与确认后清理仍属于后续阶段，本文不会把它们描述为已完成。

**当前稳定版：v2.5.0** · [版本说明](release-notes-v2.5.0-zh.md) · [更新历史](CHANGELOG.md) · [全部 Releases](https://github.com/liwei9745/GenBox/releases)

![GenBox 系统看板](screenshots/sanitized/01-dashboard.png)

> 看板截图中的主机名、容量和运行统计为明确标注的演示数据，不对应真实设备。

## 本次重大更新

### 扩展中心与 chatgpt2api

![GenBox 扩展中心](screenshots/sanitized/03-extension-center.png)

- 图形化完成 VPS 目标保存、SSH 主机指纹确认、只读环境发现、部署计划和隔离实例部署。
- 提供 Tailscale 私网准备、连通性验证、服务地址交付和已部署实例管理。
- 支持从兼容 chatgpt2api 实例主动 Pull 图片到本地媒体库。
- GenBox Push 接收端已实现来源认证、SHA-256、幂等与去重；发送端工作仍未端到端完成。
- 管理密钥默认仅本次显示，也可以由用户明确选择保存在本机加密凭证库中。

### 创作工作台与媒体管理

- 图片和视频支持单模型工作台与多模型并排对比。
- 图片支持文生图、图生图、变体、超分辨率和多图结果管理。
- 视频支持文生视频、图生视频与关键帧流程。
- 媒体库支持筛选、排序、搜索、批量操作、历史回看和提示词复用。
- 提示词辅助可把自然语言意图整理为更适合模型的提示词。

### 双语、主题与新手引导

![GenBox 新手引导](screenshots/sanitized/04-onboarding.png)

- 中文和 English 使用固定翻译键，模型名、用户提示词、密钥和原始日志保持原样。
- Dashboard、Images、Video、Media Library、History 和 Extensions 使用统一三行标题体系。
- 新手引导按“首次创作 → GenBox 能力 → chatgpt2api 介绍 → 为什么连接 GenBox”组织。
- 10 套协调主题、统一线性图标、可折叠创作工具栏和自动隐藏 Dock。

### 发布与安全

- Windows、macOS、Linux 客户端使用固定构建依赖，并在 GitHub Actions 中实际启动冒烟验证。
- Docker Compose 发布包默认拉取 GHCR 镜像，解压、配置 `.env` 后即可启动。
- 每次 Release 附带 SHA-256 校验文件。
- 敏感运行数据、真实环境地址、凭证、原始日志和未脱敏截图不进入发布包。

## 快速开始

### 桌面客户端

前往 [Releases](https://github.com/liwei9745/GenBox/releases/latest) 下载对应平台压缩包。客户端已经包含 Python 运行环境。

| 平台 | 发布包 | 启动方式 |
|---|---|---|
| Windows | `GenBox-Windows.zip` | 解压后双击 `GenBox.exe` |
| macOS | `GenBox-macOS.zip` | `chmod +x GenBox-macOS && xattr -c GenBox-macOS && ./GenBox-macOS` |
| Linux | `GenBox-Linux-x64.zip` | `chmod +x GenBox-Linux-x64 && ./GenBox-Linux-x64` |

浏览器未自动打开时，访问 `http://localhost:8891`。首次启动会引导你选择运行模式并生成管理员密钥，请把密钥保存在密码管理器中。

### Docker Compose

下载 `GenBox-Docker-Compose-v2.5.0.zip`，解压后：

```bash
cp .env.example .env
docker compose pull
docker compose up -d
```

默认访问 `http://localhost:8891`。首次管理员密钥可通过 `docker compose logs genbox` 查看一次，并会写回挂载的 `.env`；运行数据保存在当前目录的 `storage/`。远程访问前必须把 `.env` 中的 `ALLOWED_ORIGINS` 改为实际 HTTPS 或私网地址。

### 源码运行

```bash
git clone https://github.com/liwei9745/GenBox.git
cd GenBox
python -m venv .venv

# Windows
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py

# macOS / Linux
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

源码开发默认使用 `.env.example` 中的 `8892`；发布客户端和 Docker 默认使用 `8891`。

## 使用路径

1. 在“模型设置”中添加至少一个图片或视频 Provider。
2. 在图片或视频工作台输入提示词并生成内容。
3. 在媒体库和历史记录中筛选、查看和复用结果。
4. 需要远程服务时，再进入“扩展中心”配置独立实例与私网连接。

![GenBox 多模型图片工作台](screenshots/sanitized/02-generate-workspace.png)

## chatgpt2api 与 GenBox 的关系

可以把 chatgpt2api 理解为放在远程服务器上的创作站，把 GenBox 理解为自己的作品仓库：

- chatgpt2api 负责把已经实现的 ChatGPT 官网能力整理为兼容 API，并管理账号、代理、调用日志和远程图片。
- GenBox 负责本地创作入口、长期媒体保存、分类检索、历史与提示词复用，以及服务部署和连接管理。
- 当前可以由 GenBox 引导部署、建立私网并主动 Pull 图片。
- 后续自动 Push、批量/定时同步和安全清理完成后，远程作品搬运会进一步自动化。

chatgpt2api 属于第三方逆向研究项目，存在账号受限风险。请阅读其项目声明，不要使用重要或高价值账号测试。

## 安全边界

- 不要把 `.env`、`storage/`、凭证库、日志、用户媒体或真实配置提交到 Git。
- 生产 chatgpt2api 实例在开发期间只读；新功能必须使用隔离开发实例。
- GenBox 管理员密钥与每个 Push 来源密钥相互独立。
- 源图片默认保留；只有匹配 SHA-256 的认证成功回执和明确用户选择才能允许后续清理。
- 浏览器不会提交任意远程 shell 命令，部署命令由后端固定适配器生成。

## 文档入口

| 文档 | 用途 | 更新方式 |
|---|---|---|
| [产品定义](docs/PRODUCT.md) | 产品目标、用户旅程和范围 | 稳定，产品方向变化时更新 |
| [架构](docs/ARCHITECTURE.md) | 仓库边界、部署与同步架构 | 稳定，架构变化时更新 |
| [决策记录](docs/DECISIONS.md) | 已接受的安全与技术决策 | 追加 ADR，不覆盖历史 |
| [当前状态](docs/STATUS.md) | 已验证事实、阻塞项与下一步 | 随开发持续更新 |
| [路线图](docs/ROADMAP.md) | 阶段、交付物和验收标准 | 阶段状态变化时更新 |
| [文档维护规则](docs/DOCUMENTATION-MAP.md) | 哪些文档置顶、冻结或滚动维护 | 文档体系变化时更新 |

## 开发与测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --check static/js/i18n.js
node --check static/js/app-all.js
```

桌面客户端构建依赖见 `requirements-build.txt`。发布工作流会构建三平台客户端、启动实际 HTTP 冒烟检查、生成 Docker Compose 包并输出 `SHA256SUMS.txt`。

## 项目状态

- 已完成：本地创作与媒体管理、远程 Pull、扩展中心基础、隔离部署、私网流程、Push 接收端基础、双语与新手引导。
- 尚未完成：chatgpt2api 发送端单图 Push、批量和定时增量 Push、确认后源图清理、干净仓库重新部署验收与上游交付。

详细证据和限制请查看 [docs/STATUS.md](docs/STATUS.md)。

## 社区与致谢

- [GitHub Issues](https://github.com/liwei9745/GenBox/issues)
- [QQ 交流群](https://qm.qq.com/q/yegwCqJisS)
- [yukkcat/chatgpt2api](https://github.com/yukkcat/chatgpt2api)

GenBox 使用 FastAPI、原生 HTML/CSS/JavaScript、Pillow、AsyncSSH 和其他开源组件构建。感谢所有上游项目和贡献者。

## License

[MIT](LICENSE)
