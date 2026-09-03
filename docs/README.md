# GenBox 文档矩阵 / Documentation Matrix

这里是 README 之外的文档入口。当前稳定发布版是 **v2.6.6**（2026-09-03）。
普通用户从“安装、启动与升级”开始；开发者按专题进入合同；带日期的阶段
证据仅用于审计和追溯。

This is the documentation hub beyond the main README. The current stable
release is **v2.6.6** (2026-09-03). Start with installation and usage; use the
topic contracts for development; treat dated phase evidence as historical.

## 安装、启动与升级 / Install, Start, and Upgrade

| 文档 | 类型 | 主要内容 |
|---|---|---|
| [中文 README](../README.md) / [English README](../README_EN.md) | 用户入口 | 项目定位、界面、下载选择和首次启动 |
| [客户端快速开始](CLIENT-QUICKSTART.md) | 用户指南 | Windows、macOS、Linux 独立客户端启动、首次配置和数据位置 |
| [Docker 快速开始](DOCKER-QUICKSTART.md) | 部署指南 | Compose 配置、管理员密钥、启动、状态检查和更新 |
| [v2.6.6 中文发布说明](../release-notes-v2.6.6-zh.md) / [English](../release-notes-v2.6.6.md) | 已冻结发布记录 | 精细编辑 V4、客户端与 Docker 修复、验证范围和已知边界 |
| [当前发布说明指针](../RELEASE_NOTES.md) | 滚动入口 | 指向最新稳定版的中英文发布说明 |
| [CHANGELOG](../CHANGELOG.md) | 版本索引 | 按版本记录用户可见的新增、改进、修复和安全变化 |
| [GitHub Releases v2.6.6](https://github.com/liwei9745/GenBox/releases/tag/v2.6.6) | 下载入口 | 客户端、Docker Compose、源码包和 `SHA256SUMS.txt` |
| [许可证](../LICENSE) / [第三方声明](../THIRD_PARTY_NOTICES.md) | 合规文档 | GPLv3-only 条款与依赖、资产来源记录 |

## 精细编辑 V4 / Precision Edit V4

| 文档或入口 | 面向读者 | 使用方式与边界 |
|---|---|---|
| [人物抠图模型手动安装指南](CUTOUT-MODEL-GUIDE.md) | Windows、macOS、Linux 和 Docker 用户 | `u2net_human_seg.onnx` 的用途、固定大小/摘要、手动安装路径、上游来源和非商业使用边界 |
| [v2.6.6 中文发布说明](../release-notes-v2.6.6-zh.md) / [English](../release-notes-v2.6.6.md) | 使用者 | 查看精细编辑、尺寸扩展、结果对比、本地抠图/细化的发布范围与限制；工作台内的“文档说明”是完整操作入口 |
| [Precision Edit V4 研究与合同](precision-edit-v4-research.md) | 开发者与审查者 | 提交包约束、尺寸策略、标注交互、模型能力授权、抠图状态与测试矩阵 |
| [当前验证状态](STATUS.md) | 审计者 | 查看最新的本地测试、用户确认、未验证项和恢复点 |

**当前边界：** v2.6.6 已发布精细编辑工作台及其本地、打包与安全回归证据，
但 ONNX 抠图模型不随包分发。因模型来源和商业使用权利仍为 **UNVERIFIED**，
生产联网下载/安装仍禁用。v2.6.6 发布验证也未包含真实 Provider 请求、
真实抠图模型推理或 Provider 端到端验收。

## 产品、架构与当前计划 / Product, Architecture, and Current Plan

| 文档 | 类型 | 拥有的信息 |
|---|---|---|
| [产品定义](PRODUCT.md) | 稳定定义 | 目标用户、产品目标、主要旅程、范围和非目标 |
| [架构说明](ARCHITECTURE.md) | 稳定定义 | GenBox/chatgpt2api 仓库边界、扩展部署、网络、Push/Pull 和密钥架构 |
| [技术与安全决策](DECISIONS.md) | ADR 记录 | 已接受、被取代或仍在约束实现的持久决策 |
| [当前状态](STATUS.md) | 滚动事实 | 有日期的验证证据、阻塞项、范围边界和下一步 |
| [路线图](ROADMAP.md) | 验收计划 | 阶段顺序、交付物、专题合同和验收标准 |

## 集成、部署与开发合同 / Integration, Deployment, and Development Contracts

| 文档 | 主题 | 定义的边界 |
|---|---|---|
| [跨项目集成协议](INTEGRATION.md) | GenBox + chatgpt2api | Push/Pull 责任、认证、回执、幂等、批量/定时和源图删除条件 |
| [Push 集成设计](chatgpt2api-push-integration.md) | 发送端与接收端 | Push v1 请求/回执、共享服务层、重试、调度和删除门禁 |
| [扩展部署契约](extensions-deployment-contract.md) | 扩展中心 | VPS 发现、部署计划、交付信息、回滚与资源所有权 |
| [部署安全合同](deployment-invariants.md) | 远程执行 | 字段分类、证据、所有权、副作用和失败关闭规则 |
| [开发与发布生命周期](DEVELOPMENT-LIFECYCLE.md) | 环境与发布门禁 | 生产只读、隔离开发副本、脱敏、清洁重部署与上游交付 |
| [发布打包合同](RELEASE-PACKAGING.md) | 发布维护 | 不可变 Git 源码包、Docker 同镜像验证、许可证边车和发布检查 |
| [新手引导 UI 契约](ONBOARDING-UI-CONTRACT.md) | 产品与前端 | onboarding 标题、能力介绍和信息顺序 |
| [消息通道契约](message-channel-contract.md) | 未来通道适配器 | 通知、Bot 指令、绑定、回调、鉴权和能力范围 |
| [AGENTS.md](../AGENTS.md) | 仓库协作 | 事实纪律、安全边界、开发流程和完成门槛 |

## 历史证据与恢复材料 / Historical Evidence and Resume Material

以下文档记录某个时点、阶段或运行的证据。它们可用于追溯，但不代替
[`STATUS.md`](STATUS.md) 的当前状态，也不会自动把本地测试、模拟测试或 UI 占位符
升级为真实端到端能力。

| 文档 | 证据类型 | 使用注意 |
|---|---|---|
| [P4 单图 Push 本地证据](P4-SINGLE-IMAGE-PUSH-LOCAL-EVIDENCE.md) | 日期化本地证据 | 只证明文档内标注的本地范围 |
| [Phase 5 隔离验收证据](PHASE5-EVIDENCE-2026-08-01.md) | 阶段验收记录 | 保留当时环境、步骤与边界 |
| [Phase 7 本地预检](PHASE7-LOCAL-PREFLIGHT-2026-08-09.md) | 发布前证据 | 不代替当前版本的发布记录 |
| [Phase 9 计划](PHASE9-PLAN.md) / [PR 审计](PHASE9-PR-AUDIT-20260823.md) | 当前阶段支持材料 | 计划和审计证据不等于上游合并或生产验收 |
| [P4 循环工程指南](P4-LOOP-ENGINEERING.md) | 恢复/协作材料 | 保留轮次证据等级、停止条件和恢复点 |

`.planning/`、带日期的 `PHASE*`、临时 handoff/review 和生成实验材料都是历史输入。
当它们与产品、架构、路线图或当前状态冲突时，以上方的主要文档为准。

## 信息应该放在哪里？ / Where Should Information Go?

- 面向第一次使用者的稳定信息放在 README 和 Quick Start。
- 某个版本的下载、升级、变化、验证范围和已知问题放在对应 Release Notes。
- 持续变化的真实进度、验证证据和阻塞项放在 `STATUS.md`。
- 长期产品、架构和安全选择放在 `PRODUCT.md`、`ARCHITECTURE.md` 与 `DECISIONS.md`。
- 阶段目标和验收条件放在 `ROADMAP.md` 与专题合同中。
- 临时会话记录、真实地址、凭证、日志和未脱敏截图不进入公开文档。
