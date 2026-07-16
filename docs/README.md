# GenBox 文档矩阵 / Documentation Matrix

这里是 README 之外的完整文档入口。普通用户从“使用与升级”开始；部署者、集成开发者和项目贡献者可以直接进入对应区域。

This is the documentation hub beyond the main README. Start with usage and upgrades, or jump directly to operations, integration, or development.

## 使用与升级 / Usage and Upgrades

| 文档 | 适合谁 | 主要内容 |
|---|---|---|
| [中文 README](../README.md) / [English README](../README_EN.md) | 第一次接触 GenBox 的用户 | 项目定位、界面、下载选择、3 分钟启动 |
| [v2.5.0 中文发布说明](../release-notes-v2.5.0-zh.md) / [English](../release-notes-v2.5.0.md) | 安装或升级用户 | 下载哪个文件、如何启动、升级风险、主要变化与修复 |
| [CHANGELOG](../CHANGELOG.md) | 想快速查看版本变化的用户 | 按版本记录新增、改进和修复 |
| [许可证与第三方声明](../LICENSE) / [Third-party notices](../THIRD_PARTY_NOTICES.md) | 分发者、贡献者和合规审查者 | GPLv3-only 条款、依赖与资产来源记录 |
| [GitHub Releases](https://github.com/liwei9745/GenBox/releases) | 下载发布包的用户 | 客户端、Docker Compose 包和 SHA-256 校验文件 |

## 高级使用与部署 / Advanced Usage and Operations

| 文档 | 适合谁 | 主要内容 |
|---|---|---|
| [开发与发布生命周期](DEVELOPMENT-LIFECYCLE.md) | NAS、VPS、Docker 部署者和发布维护者 | 隔离环境、脱敏、构建、验证、发布与回滚门槛 |
| [架构说明](ARCHITECTURE.md) | 高级用户和维护者 | 模块边界、运行方式、扩展中心与同步架构 |
| [安全与技术决策](DECISIONS.md) | 安全审查者和维护者 | 已接受的凭证、网络、同步与删除安全决策 |
| [当前状态](STATUS.md) | 需要了解真实完成度的人 | 已验证能力、限制、阻塞项、测试证据和下一步 |

## chatgpt2api 集成 / chatgpt2api Integration

| 文档 | 适合谁 | 主要内容 |
|---|---|---|
| [跨项目集成协议](INTEGRATION.md) | GenBox 与 chatgpt2api 开发者 | 身份认证、Push/Pull、回执、幂等和删除条件 |
| [Push 集成设计](chatgpt2api-push-integration.md) | 后续发送端开发者 | 发送端工作拆分、批量/定时传输和安全清理设计 |
| [扩展部署契约](extensions-deployment-contract.md) | 扩展适配器开发者 | VPS 发现、部署计划、网络准备、交付与回滚边界 |
| [新手引导 UI 契约](ONBOARDING-UI-CONTRACT.md) | 产品与前端维护者 | 标题系统、能力介绍和 onboarding 信息顺序 |

## 项目开发 / Project Development

| 文档 | 适合谁 | 主要内容 |
|---|---|---|
| [AGENTS.md](../AGENTS.md) | AI Agent 和贡献者 | 仓库规则、安全边界、开发流程和完成门槛 |
| [产品定义](PRODUCT.md) | 产品维护者 | 用户、目标、核心旅程和非目标 |
| [路线图](ROADMAP.md) | 贡献者和维护者 | 阶段顺序、交付物和验收标准 |
| [文档维护规则](DOCUMENTATION-MAP.md) | 文档维护者 | 哪些文档置顶、滚动更新或随 Release 冻结 |
| [HANDOFF](../HANDOFF.md) | 下一位开发者或会话 | 当前主要目标、风险和恢复工作指引 |

## 信息应该放在哪里？ / Where Should Information Go?

- 面向第一次使用者的稳定信息放在 README。
- 某个版本的下载、升级、变化和已知问题放在对应 Release Notes。
- 持续变化的真实进度和验证证据放在 `STATUS.md`。
- 长期架构和安全选择放在 `ARCHITECTURE.md` 与 `DECISIONS.md`。
- 阶段目标和验收条件放在 `ROADMAP.md` 与专题契约中。
- 临时会话记录、真实地址、凭证、日志和未脱敏截图不进入公开文档。
