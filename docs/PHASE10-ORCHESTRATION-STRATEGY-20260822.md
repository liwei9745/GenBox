# Phase 10 编排与安全策略

**研究日期：** 2026-08-22  
**仓库 HEAD：** `c1cedd111829e349157f6bfddadca4bfa43ffb33`  
**分支：** `codex/phase7-campaign-20260820`  
**范围：** 只读架构/安全研究与 Agent 编排策略。本文不证明任何尚未执行的运行时、VPS、浏览器或跨项目验收。

## 1. 已验证事实与未验证边界

### 已验证事实

- `docs/STATUS.md` 和 `docs/ROADMAP.md` 均将 Phase 10 标为 In Progress。已记录的切片包括 Store 的 Installed/Recommended/All 投影、后端能力派生 action，以及绑定 target identity、过期和未来时间 fail-closed 的环境投影检查。
- `extensions/models.py:94-104` 当前的 `EnvironmentProjection` 只包含 `target_id`、`target_identity_digest`、`observed_at`、Docker/Compose 布尔值、`evidence_complete` 和 `confidence`；它不是完整的环境事实模型。
- `extensions/store.py:75-88` 的 `target_identity_digest()` 将目标 endpoint、用户名、identity generation、主机信任和网络 URL 纳入 SHA-256 摘要。`get_environment_projection()` 在摘要不匹配、时间无效、未来时间或超过 3600 秒时返回无投影。
- `extensions/orchestrator.py:1726-1768` 的 `public_discovery()` 从服务端 discovery 生成脱敏 DTO；`evidence_manifest.complete` 依赖端口绑定和 listener probe 完整，Docker/Compose 可用性来自环境版本字段。
- `main.py:4106-4117` 的只读 discovery 成功路径调用 `public_discovery()`，随后 `main.py:4139-4143` 只通过 `verified_environment_projection()` 取得写入令牌，再持久化 Store 投影。浏览器不能直接注入投影；该边界由 `tests/test_extension_store_contract.py:166-178` 覆盖。
- `store_projection()` 使用显式 public-field 白名单，并由 `project_store_actions()` 产生 action；已安装外部实例 action 为空，计划条目 action 为空。相关行为由 `tests/test_extension_store_contract.py:32-43、251-289、348-357` 覆盖。
- 现有 `extensions.json` 读取逻辑对缺失文件、非对象、坏 target/instance/projection 记录采取空值或逐条隔离策略；旧文件没有 `environment_projections` 时按空列表处理，属于兼容读取而非环境事实迁移。
- Ops 账本已记录：无 agent roster/lease/task registry；无当前 Phase 10 运行验证进程；`.pytest_cache/` 新鲜度未知；不得把文档、mock 或旧缓存当作 live acceptance。

### 未验证边界

- 尚未验证真实目标的 EnvironmentFacts 采集、TTL 行为在真实时钟/重启/身份变更下的完整闭环，也未验证多个目标并存时的选择、竞争和失效策略。
- 尚未验证 Phase 10 全部 Store acceptance；已有测试属于本地自动化证据，不等于隔离 VPS、干净部署、真实 adapter 或跨项目 E2E。
- 尚未验证 adapter lifecycle 的独立契约。当前存在 deployment/orchestrator 能力，但不能据此声称已经拥有 Store 所需的完整 versioned adapter（尤其 upgrade、backup、rollback、uninstall、repair 生命周期）。
- 尚未验证所有 catalog manifest 的 source、license、permissions、network exposure、data sensitivity、operational risk 元数据质量、来源可追溯性和许可证兼容性。
- 不推测未知事实：没有 Docker/Compose 证据不能推断不可用；只有局部证据不能推断 complete；外部 instance 的运行状态不能推断所有权。

## 2. Phase 10 剩余四项 acceptance criteria 证据矩阵

ROADMAP 的第一项“visible action 必须来自 backend adapter capability”已有代码和本地测试证据，因此列为已满足的基线，不把它计入剩余四项。以下四项仍需独立闭环证据。

| 剩余标准 | 当前证据 | 缺口/不可声称内容 | 完成证据 |
|---|---|---|---|
| Unknown environment facts 和 unavailable apps 显式呈现并 fail closed | `EnvironmentProjection` 的 `confidence` 有 `unknown`；过期、未来、身份漂移会丢弃投影；无完整证据不会生成写入令牌；推荐测试覆盖 medium/unknown、缺 Docker/Compose、`evidence_complete=false` | 当前模型不是所需完整 `EnvironmentFacts`；未证明每种未知都能在 UI/API 显式解释；未证明所有 unavailable catalog 项在所有输入下保持不可执行 | 为每类未知事实建立字段级 fixture 和 public response contract；验证 Recommended 为空、All 保留 unavailable reason、actions 为空；运行 focused/full 本地命令并记录结果；如需真实目标，另记隔离环境证据 |
| External instances 在 verified adoption flow 前保持 advisory/read-only | `store_projection()` 将非 managed instance 标为 `external` 且 actions=[]；测试覆盖 external read-only；合同明确 external 只读 | 未证明所有后续 route、resume、repair、lifecycle API 都不能借 Store projection 绕过 ownership；未实现也未验证 adoption flow | 对每个能接收 instance handle 的 route 做 capability/ownership 矩阵测试；外部实例的 deploy/upgrade/backup/rollback/uninstall/repair 均应无 action 或明确拒绝；不把“没有测试”写成完成 |
| Store metadata 标识 source、license、permissions、exposure、risk | `_PUBLIC_STORE_FIELDS` 白名单包含 repository、provenance、license、permissions、network_exposure、data_sensitivity、operational_risk；Store route contract 测试检查 required keys | 现有测试主要检查字段存在和敏感字段不泄露，未证明每个 manifest 的值有可信来源、license compatibility、风险语义和缺失值说明；未证明 UI 能诚实展示 reason/provenance | 为每个 catalog item 建 manifest provenance/metadata fixture 和缺失字段策略；验证 public response 不泄露私密字段且所有值可追溯；独立 reviewer 审核 license/risk 解释 |
| 四项合并后的完整 Store acceptance | STATUS 只记录 projection slice、target-bound fail-closed 和历史 258/632 结果；Ops ledger 明确 full acceptance 未证实 | 没有新鲜的本轮验证、clean deployment、跨目标/重启/身份漂移及完整 Store acceptance 记录；`632` 是文档引用，不是本次运行结果 | 按串行波次完成实现、focused tests、full tests、clean worktree review；每项 acceptance 写入 dated command/result/evidence location；roadmap/status 只在证据齐全后更新 |

## 3. EnvironmentFacts 最小设计

`EnvironmentFacts` 是服务端采集的事实记录，不是浏览器提交的推荐结果，也不是 adapter manifest。最小正确模型如下：

```text
EnvironmentFacts {
  target_id: non-empty stable target identifier
  identity_digest: sha256(target identity generation and verified endpoint identity)
  observed_at: UTC RFC3339 timestamp
  ttl_seconds: positive bounded TTL, server policy value
  facts: typed known/unknown fields only
  extra: forbidden
}
```

- `target_id` 必须绑定已保存 target，不能由 public Store item 或浏览器自由指定一个未注册目标。
- `identity_digest` 必须由服务端按当前 target 重新计算并比较；目标 host/port/username、host-key trust、identity generation 或其他纳入 identity 的字段发生变化时，旧事实立即不可用。
- `observed_at` 必须由服务端在成功的只读采集后生成，禁止接受客户端时间。未来时间、无法解析的时间和超出 TTL 的事实均视为 unknown。
- `TTL` 应是明确的服务端策略字段或等价常量，比较应同时拒绝负年龄和超龄；默认可沿用现有 3600 秒，但必须在模型/策略中命名，不能散落为隐含 magic number。TTL 不是成功证明，只是新鲜度门槛。
- `facts` 只允许已定义、可验证、非秘密的类型，例如 `os_family`、`architecture`、`memory_mb`、`storage_free_mb`、`container_runtime`、`compose_available`、`network_constraints` 和冲突摘要。每个事实应能表达 unknown，不用默认值伪装“不可观测”为 false。
- `extra=forbid` 是安全边界：Pydantic 模型配置和持久化入口都拒绝未知字段。未知字段不能通过旧 JSON、浏览器 payload 或 catalog metadata 进入推荐逻辑。
- 旧 `extensions.json` 兼容：缺少 `environment_facts` 按无事实处理；已有 `environment_projections` 可在读取时保留为历史/兼容记录，但不能自动升级为新 EnvironmentFacts，也不能从旧 projection 推测缺失事实。坏记录逐条隔离，不能阻止其他合法 target 加载。
- 未知不推测：没有采集到 memory、storage、OS、runtime、network constraint 或 conflict 时，值为 unknown；推荐 confidence 降级或不推荐，永远不把 unknown 当作满足要求。
- `EnvironmentFacts` 不应保存密码、token、原始命令、完整路径、host identity 原文、raw logs 或用户数据。必要的冲突信息只保存脱敏的类型/存在性摘要。
- 投影层仍必须重新检查 adapter capability。EnvironmentFacts 只能影响兼容性解释和推荐，不能新增 action。

## 4. 最小正确实现顺序和依赖图

### 顺序

1. **事实契约**：定义 `EnvironmentFacts`、字段状态、TTL、identity digest 输入、`extra=forbid`、旧文件读取规则和 unknown 语义；先补模型单测。
2. **采集转换**：在只读 discovery 的服务端路径中，将已验证 discovery 转换为 facts；只收集最小非秘密字段，采集失败返回 unknown，不写半成品成功事实。
3. **原子持久化/失效**：按 target identity 加锁写入；target 修改、host trust reset、采集不完整、TTL 过期时使事实不可用；保留旧 projection 仅作兼容读取，不混用语义。
4. **推荐解释**：Store 只读取新鲜、identity-bound、字段类型正确的 facts；按 catalog requirements 计算 reasons/confidence；未知减少置信度，不能补默认事实。
5. **能力 action 门禁**：继续以 backend adapter capability registry 为唯一 action 来源；manifest、facts、recommendation、AI 输出均无权添加 action。
6. **ownership 门禁**：managed/external 分流覆盖 Store、deploy、resume、lifecycle 入口；external 仍只读，adoption 不在本阶段伪造。
7. **metadata 完整性**：为 manifest 建 provenance/license/permissions/exposure/sensitivity/risk 的可追溯校验和显式缺失状态。
8. **验证与证据锁**：先 focused，再 full，再 clean worktree/reviewer gate；只有四项矩阵都有 dated evidence 才更新 Phase 10 状态。

### 依赖图

```text
EnvironmentFacts schema + unknown rules
        |
        v
server-side discovery -> typed facts -> identity/TTL validation -> atomic store
                                                        |
                                                        v
                                      recommendation reasons/confidence
                                                        |
                         +------------------------------+------------------------------+
                         v                                                             v
                 capability-derived actions                                  ownership/read-only gates
                         |                                                             |
                         +------------------------------+------------------------------+
                                                        v
                                      manifest metadata validation
                                                        |
                                                        v
                                           Store acceptance evidence
```

不可跨越的依赖：没有 typed facts 和 freshness/identity validation，不得做 high recommendation；没有 capability registry，不得渲染可执行 action；没有 ownership proof，不得对 external instance 做 lifecycle mutation；没有 evidence matrix，不得把 Phase 10 标记 Complete。

## 5. 串行心跳波次与思考强度匹配

规则：每一波只有一个真实 Agent 动作。动作完成并交接后，下一波才开始；reviewer 和 Ops heartbeat 不与业务实现并行写同一文件。思考强度使用“高 / 中高 / 中等”，按风险匹配角色，不以 Agent 数量替代证据。

| 波次 | 唯一真实动作 | 角色与强度 | 进入条件 | 退出条件 |
|---|---|---|---|---|
| W0 | 建立只读基线、确认 roster/lease、列出未知项 | 专职 Ops，**中等** | 当前仓库和 Phase 10 文档可读 | 有 branch/HEAD/status、当前 wave、进程观察和未知清单；不改业务文件 |
| W1 | 起草并实现 EnvironmentFacts 契约 | 架构/安全 Agent，**高** | W0 交接无冲突 | 模型、兼容规则、unknown/TTL/forbid 测试完成；只触及允许文件 |
| W2 | 实现服务端采集与原子投影接线 | Orchestration Agent，**高** | W1 reviewer PASS | discovery-to-facts、身份绑定、TTL、失败不写入通过 focused tests |
| W3 | 实现 Store 推荐解释与 metadata 校验 | Store contract Agent，**中高** | W2 交接完整 | reasons/confidence、manifest 字段和 unavailable 状态有契约测试 |
| W4 | 补 ownership/capability 全入口测试 | Security boundary Agent，**高** | W3 无未决高风险 | external 只读、planned 不可执行、action 唯一来源均有 route-level 证据 |
| W5 | 执行 focused/full/静态检查并整理证据 | Verification Agent，**中高** | W4 reviewer PASS | 命令、结果、环境、时间和失败说明写入交接；不运行浏览器/npm/远程 |
| W6 | 独立审查实现、证据和 Phase 12 边界 | Reviewer，**高** | W5 结果可复现 | PASS 或列出阻断项；不得顺手修代码 |
| W7 | 维护状态/账本并决定是否请求 Phase 10 close | Ops/Release gate Agent，**中等** | W6 PASS、无脏文件归属争议 | 只更新策略/状态类文档；未满足项保持 In Progress |

任一波失败都停止后继波次，回到失败波次的 owner；禁止用下一波“补解释”掩盖前一波没有实现或验证。

## 6. Agent 输入、输出、禁止范围、验证命令、交接格式

### 通用交接格式

每个 Agent 必须输出一份短交接，格式固定为：

```text
AGENT: <role>
WAVE: W<n>
STATUS: PASS | BLOCKED | FAIL
INPUT_HEAD: <commit or observed HEAD>
CHANGED_FILES: <exact paths, or NONE>
RESULT: <事实性摘要>
EVIDENCE: <commands, results, artifact paths, timestamps>
UNKNOWN: <未验证事项>
RISKS: <安全/回滚/脏树风险>
NEXT: <唯一允许的下一动作>
```

| Agent | 输入 | 输出文件 | 禁止范围 | 验证命令 |
|---|---|---|---|---|
| Ops | 必读 docs、git 状态、当前进程观察 | 仅 Ops ledger 或本策略/状态文档；本次任务另有本策略文档 | 不改业务代码；不启动/停止进程；不浏览器/npm install；不远程 | `git status --short --branch`; `git rev-parse HEAD`; `git log -10 --oneline --decorate`; 只读进程观察 |
| 架构/安全 Agent | PRODUCT、ARCHITECTURE、STATUS、ROADMAP、Store contract、models/store 现状 | `extensions/models.py` 及其 focused tests，或明确 BLOCKED | 不改 orchestrator/main/frontend；不引入秘密；不把 projection 自动升级成事实 | `python -m pytest -q tests/test_extension_store_contract.py`; `python -m py_compile extensions/models.py` |
| Orchestration Agent | W1 模型契约、`public_discovery`、`_save_store_environment_projection` | `extensions/store.py`、必要的 `main.py` 接线和 focused tests | 不改变任意 shell allowlist、SSH trust、生产配置；不连接远程 | `python -m pytest -q tests/test_extension_store_contract.py tests/test_extensions.py`; `python -m py_compile main.py extensions/store.py` |
| Store contract Agent | catalog、Store contract、EnvironmentFacts 接口 | Store projection/manifest tests，必要时最小 Store 代码 | 不创建新 action；不让 manifest/facts 授权 deploy；不改 adapter lifecycle | `python -m pytest -q tests/test_extension_store_contract.py`; `git diff --check` |
| Security boundary Agent | capability registry、ownership routes、external contract | route/contract tests | 不实现 adoption、repair、upgrade、rollback、uninstall；不放宽 external 权限 | `python -m pytest -q tests/test_extension_store_contract.py tests/test_extensions.py` |
| Verification Agent | 前序交接、变更 diff、测试基线 | 验证日志/证据文档，不修业务代码 | 不修改测试使其变绿；不运行浏览器/npm install/远程 | focused 命令、`python -m pytest -q`、`python -m py_compile main.py extensions/*.py`、`git diff --check` |
| Reviewer | 全部 diff、交接、测试结果、contract 和 roadmap | review report 或本策略文档的审查记录 | 不实现修复；不把历史结果冒充本轮结果；不批准未证据化功能 | 静态 diff 审查；按失败项指定重跑命令，不代跑未授权外部验证 |

## 7. Reviewer 门禁、失败重试、回滚和脏工作树处理

- **Reviewer 门禁：** 必须检查四项 acceptance 是否逐项有证据、action 是否只来自 capability、unknown 是否 fail closed、external 是否无 mutation、metadata 是否可追溯、是否有敏感字段泄露。任何一项缺证据即 BLOCKED，不得以“代码存在”替代验收。
- **失败重试：** 只允许在同一波、同一 owner、同一输入 HEAD 上重试一次；重试前记录失败命令和未变更事实。若是环境抖动，必须说明重试理由和两次结果；若是逻辑失败，回到上一依赖波次，不扩大 scope。
- **回滚：** 业务代码回滚只能由产生该变更的 owner 按精确文件/补丁边界执行，且先获得 reviewer 指定的回滚范围；不得 `git reset --hard`、`git checkout --` 或删除他人未识别变更。环境投影回滚采用失效/删除该 target 的投影记录，不恢复旧的过期或身份不匹配事实。
- **脏工作树：** 开始每波记录 `git status --short --branch`。发现非本 Agent 变更时不覆盖、不清理、不纳入自己的交接；若与目标文件冲突则 BLOCKED 并报告路径、所有权未知、建议隔离。只允许在交接中列明自己精确修改的文件。
- **文档与业务分离：** Ops ledger 和本策略文档的未跟踪状态不构成业务实现证据。状态文档只能记录已观察结果；不得为了通过门禁删除缓存、历史 artifact 或他人未识别文件。
- **安全失败默认：** 任何未知 target、digest 不匹配、时间异常、extra 字段、能力类型错误、ownership 不明、manifest 来源不明或 reviewer 无法复现，均保持不可执行并进入 BLOCKED。

## 8. 专职 Ops Agent 周期检查与升级条件

### 周期检查

- 记录时间、branch、HEAD、`git status --short --branch`，与上次 heartbeat 比较。
- 检查 Phase 10 当前 wave、Agent roster、lease、task registry 和 named evidence；不存在的数据明确标记 UNKNOWN。
- 只读观察 pytest/Playwright/Node/Python/Docker 相关进程命令行；不启动、不停止、不猜测其归属。
- 检查是否出现新的 `.pytest_cache`、临时文件、日志或未跟踪文档；不把缓存当验证结果，不删除不明文件。
- 对照 STATUS/ROADMAP/本策略矩阵，确认状态声明没有超过证据；检查文档中无秘密、真实凭据、未验证 IP/port 或生产事实。
- 确认每波只有一个真实 Agent 动作、交接格式完整、下一动作唯一；发现并行写同一业务文件即记录冲突。
- 只在收到新的 dated command/result 后更新 ledger；历史结果必须标为历史来源。

### 升级条件

- 发现 branch/HEAD 与交接不一致、非预期文件变化、未授权 commit/push、或业务文件被未知 Agent 修改。
- 发现 Agent 无 lease/roster、同一波出现多个真实动作、交接缺少输入 HEAD 或验证结果。
- 发现任何 credential、secret、raw log、host identity、真实用户数据进入代码、测试、文档、URL、日志或截图。
- 发现把 documentary/mock/stale cache 当作 live、VPS、clean deployment 或 cross-project evidence。
- 发现 discovery 不完整却生成 high recommendation、unknown 被默认成满足、external 获得 mutation action、或 action 来自 manifest/recommendation/AI 输出。
- 发现远程环境、生产容器、Docker/Compose、浏览器、npm install 被未经授权触碰。此时暂停后续波次，保留证据，等待人工决策。

## 9. Phase 12 才做的 adapter lifecycle 边界

Phase 10 只建立可信 Store projection、环境兼容事实、metadata 和 capability/ownership 门禁。以下内容明确留到 Phase 12 的“Additional Service Adapters”，不能在 Phase 10 以 catalog entry、placeholder 或 action 名称提前声称完成：

- 为每个新服务确认唯一 source repository identity、license、配置契约和维护状态。
- 为每个 adapter 定义 secrets、ports、persistence、network exposure、health check、delivery information 和数据敏感性。
- 实现并独立验证 versioned adapter 的 discover、plan、deploy、health check、upgrade、backup、rollback、uninstall；每个动作都必须有 ownership、隔离、审计和失败恢复边界。
- 定义 adapter-owned repair allowlist。Phase 10 不实现 AI repair，不将 Store action 解释为 repair capability，也不建立 external adoption。
- 为每个 adapter 建立真实的本地/隔离环境测试、回滚测试、清理验证和 sanitized evidence；manifest 不能授予执行权。
- 未满足上述契约的服务继续显示为 planned/unavailable，actions 为空；Recommended 只能基于已验证环境事实和现有 backend capability，不因“未来 adapter”而推荐或部署。

因此，Phase 10 的完成条件不是“catalog 看起来完整”，而是四项剩余 acceptance 都有可复现、日期明确、边界诚实的证据；adapter lifecycle 的完整性属于 Phase 12 的独立验收。
