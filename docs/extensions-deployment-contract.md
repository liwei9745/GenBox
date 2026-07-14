# GenBox 扩展功能与 VPS 连接契约

## 目标

“扩展功能”是一个向导式部署中心，用于：

1. 配置并验证 VPS SSH 连接。
2. 在 VPS 上部署或恢复 chatgpt2api。
3. 选择一个主连接方案，让 VPS 能访问本机 GenBox。
4. 验证 chatgpt2api、连接层和 GenBox 推送 API 的完整链路。
5. 保存非敏感连接信息，并将敏感凭证作为不可回显的秘密处理。

## 连接方案决策

连接方式采用“一个主方案 + 可选备用方案”，而不是同时启用多个主方案。
多个 VPN/隧道同时接管路由会增加 DNS、端口和故障排查复杂度；备用方案只在用户
明确切换时启用。

| 方案 | 推荐级别 | 适用人群 | 关键条件 |
|---|---|---|---|
| Tailscale Personal | 默认推荐 | 个人用户、低维护需求 | 两端登录同一 Tailnet；免费个人计划，客户端成熟 |
| NetBird | 自托管推荐 | 重视开源和控制面自主权 | 云端账号或自建控制面；使用一次性 setup key |
| Cloudflare Tunnel | 域名用户推荐 | 已有 Cloudflare 域名 | 本机运行 cloudflared，VPS 通过 HTTPS 域名访问 |

Tailscale 和 NetBird 属于私网覆盖网络；Cloudflare Tunnel 属于出站隧道。三者
都由用户在向导中选择，GenBox 只保存最终可访问的 URL/主机名，不把业务协议
绑定到某个供应商。

## 向导步骤

1. **VPS 信息**：IP/域名、SSH 端口、用户、密码或私钥、主机指纹确认。
2. **部署 chatgpt2api**：检查 Docker、选择镜像版本、生成管理密钥、启动并等待健康检查。
3. **选择连接方式**：Tailscale、NetBird、Cloudflare Tunnel 单选；Tailscale 会先检测并引导安装本机客户端。
4. **配置连接**：输入一次性 auth key/setup key/tunnel token，不写入前端存储。
5. **验证并完成**：验证本机、VPS、容器、双向连接和 GenBox 私网入口。

### Tailscale 本机准备

Windows 本地模式可通过固定 `winget` 包 ID 安装 Tailscale。安装可能触发 UAC，登录由
Tailscale 官方客户端或浏览器完成，GenBox 不接触 Tailnet 账号密码。登录后，目标设计
使用 Tailnet 入口端口代理 GenBox 的实际本地监听端口。开发环境默认使用
`tailscale serve --bg --http=8893 http://127.0.0.1:8892`；正式交付使用
`tailscale serve --bg --http=8892 http://127.0.0.1:8891`。入口端口与上游应用端口必须
分别配置和验证。当前 GenBox 进程实际绑定 `0.0.0.0:8891`；后续可以在不影响本地使用
和容器部署的前提下评估是否收紧监听范围。当前 Tailscale Serve 配置与状态检测仍把入口
和上游视为同一端口，必须按当前环境验证对应映射后才能完成真实链路
验收。

VPS 注册后，任务必须同时通过以下检查才标记成功：

- 本机 `tailscale ping` 可到达 VPS 的 `100.x.x.x` 地址。
- VPS 可通过本机 Tailscale 地址访问 GenBox。
- 最终生成的 chatgpt2api GenBox URL 使用 Tailscale 地址而非公网地址或 `127.0.0.1`。

每一步都由服务端返回阶段、百分比、日志（已脱敏）和恢复动作。刷新页面后通过
任务 ID 查询状态；中断任务必须标记为“需要处理”，不能假装仍在运行。

## 凭证规则

- SSH 密码、私钥、私钥口令、隧道 token、GenBox API Key 永不进入 localStorage、URL、普通日志。
- 新服务管理密钥默认“一次性显示”，GenBox 不持久化；丢失后通过重新验证 SSH 所有权并轮换来恢复，而不是从存储中找回。
- 用户可选择“保存在本地方便以后查看”。本地保存默认关闭，必须用户逐条显式开启，并在开启前给出明确风险提示。适用范围包括用户主动选择保存的托管实例管理密钥和 VPS SSH 凭据；入网 token、推送 Key、GenBox 管理员 Key 仍禁止写入浏览器存储。
- 一次性显示与本地保存都是用户可选项，不写死在产品中。
- 首选 SSH 私钥；密码只用于一次部署会话，成功后提示用户轮换。
- 已保存凭证只返回 `has_credential: true`，不返回内容。
- 当前凭证存储使用 `storage/` 下的应用级加密文件：PBKDF2-SHA256 从用户解锁口令派生密钥，Fernet 加密每个托管实例的凭证。文件只含随机盐、KDF/版本/字段元数据和密文；解锁口令与派生密钥不持久化，派生密钥只在 GenBox 进程内存中保留并支持显式锁定。
- GenBox 的管理密钥与推送 API Key 分离；推送 Key 按 `source_id` 单独吊销。
- 所有 SSH 连接要求主机指纹确认或预置 known_hosts，禁止默认关闭主机校验。
- 远程执行命令由服务端固定清单生成，浏览器不能提交任意 shell 字符串。

## 远程部署边界

第一版只支持固定的 chatgpt2api Compose 预设：检查 Docker、创建应用目录、写入
配置、拉取固定 digest 镜像、启动容器、健康检查。不会提供任意脚本执行器。

任何短暂停机快照或切换只能作用于 GenBox 新建并管理的隔离实例，不能作用于现有
生产源实例。失败时保留 VPS 原栈，不自动删除 VPS 数据。图片
源文件只有在 GenBox 返回 SHA-256 匹配且 `safe_to_delete_source=true` 后，且用户
独立开启“确认回执后删除”时才允许清理。

## 实例发现与部署决策

部署前必须执行只读发现，检查 VPS 资源、Docker/Compose/Python 能力、监听端口和
已有 chatgpt2api 实例。发现结果提供三种策略：

- 接入已有实例：只登记入口，不写文件、不重启容器、不读取管理密钥。
- 创建隔离测试实例：使用独立实例 ID、端口、目录和 Compose project。
- 新建生产实例：仅指从隔离开发成果全新部署的 GenBox 管理实例，不得原地转换或
  替换现有生产源；其隔离模型相同，但要求更严格的镜像和备份策略。

当前达到自动安全执行条件的是标准 Docker Compose。WARP 和 Python 模式会显示环境
适用性和说明，但在各自的资源冲突、systemd 托管和回滚契约完成前不允许执行。

所有 GenBox 管理的实例必须带 `com.genbox.managed=true` 和实例 ID 标签，并在
`storage/extensions.json` 中只保存非敏感所有权信息。部署执行必须绑定十分钟有效的
计划 ID；计划生成后修改端口、镜像或目标会使执行失败。

### 隔离测试副本

开发验收场景推荐从发现到的主应用容器创建隔离副本，而不是修改生产实例。Compose
栈中的 WARP、Privoxy、FlareSolverr 和初始化容器必须聚合为一个应用实例，只允许
`app` 主服务的数据卷成为克隆源。

向导提供三种初始数据范围：

- 空白实例：不复制业务数据。
- 仅媒体：复制 `images/` 和 `image_index.json`。
- 安全工作副本：复制数据目录和项目设置，保留账号等业务配置以便开发验收。

安全工作副本必须生成新的主管理密钥，并移除克隆中的
`genbox_destination.json`、推送回执、调度状态和租约；项目配置中的主管理密钥必须
删除，继承的 Push `source_id` 和 Push key 必须删除并为开发副本重新生成，自动备份必须
关闭。源实例保持在线且全程只读。生成计划前应读取源数据大小，
目标磁盘可用空间不足 `源数据大小 + 512 MB` 时阻止执行。

## 部署交付与密钥恢复

新实例的主管理密钥由 GenBox 生成，只写入远端实例专属 `.env`（权限 `0600`），
不写 `config.json`、浏览器存储或任务日志。密钥通过一次性接口交付，读取后立即销毁。

用户丢失主管理密钥时，可以在重新验证 SSH 凭据和主机指纹后轮换密钥。轮换只允许
作用于 GenBox 管理且远端所有权标记匹配的实例；操作先备份 `.env`，只重建目标 app
服务，并通过 `/auth/login` 验证新密钥。验证失败必须恢复旧 `.env` 并重建原服务。
只读接入的已有实例不允许自动重置密钥。

## 阶段划分

### Phase A：扩展页与 SSH 编排基础

- GenBox `扩展功能` 页面和 5 步状态机
- 目标存储、任务进度、取消/重试
- SSH 主机指纹、固定部署清单、Docker 健康检查
- 不接入生产 VPS 自动切换

### Phase B：连接适配器

- Tailscale auth key 安装与验证
- NetBird setup key 安装与验证
- Cloudflare Tunnel token 安装与域名验证
- 一个主连接 + 备用连接配置

### Phase C：chatgpt2api 推送

- GenBox 目标设置与秘密掩码
- 单图推送、批量推送、日期范围推送
- SHA-256 回执、失败重试、确认后删除
- 周期调度和多 worker 租约

### Phase D：实战交付

- 本地容器联调
- 隧道链路联调
- GenBox 管理的新实例或隔离副本快照恢复测试；现有生产源不得作为恢复演练目标
- Windows/Linux 打包与文档

### Zero-Code Network Automation Boundary

The browser submits a structured choice such as provider, target, operation mode,
device name, and one-time enrollment token. GenBox backend adapters generate and
execute the fixed SSH command plan. Users do not need to type commands, while the
browser cannot submit arbitrary shell text or scripts.

Development defaults use GenBox on port `8892` and the Tailscale Serve entry on
port `8893`. Production delivery uses GenBox on `8891` and the Tailscale Serve
entry on `8892`. Both values are environment-configurable and must never be the
same on one host.

The wizard keeps one active primary network. Successfully verified providers are
remembered as available networks so a later phase can add one-click switching and
recovery. Switching must re-run endpoint and HTTP checks before replacing the
stored Push URL.
