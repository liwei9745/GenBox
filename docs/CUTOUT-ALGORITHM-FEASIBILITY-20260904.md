# 抠图算法可行性与发布边界（更新至 2026-09-05）

## 当前结论

GenBox 的默认抠图算法仍是已验证的 U²-Net ONNX 路径。MODNet 已证明“技术上
可运行”：在用户主动导入固定 ONNX 文件、提交完整清单、确认自己拥有适用许可、
并通过 CPU-only 运行时探测后，独立适配器可以执行本地实验。MODNet 的真实照片
质量仍未验收，因此不是 GenBox 的产品质量保证，也不是 Release 资产。

InSPyReNet、BiRefNet 和 BRIA RMBG-2.0 仍保持
`UNVERIFIED / state=unavailable / executable=false`，继续 fail-closed；仅有
目录条目、代码仓库或可下载链接不能使它们变成可执行算法。

## 状态矩阵

| 算法 | 当前状态 | 用户可见行为 | Release 边界 |
|---|---|---|---|
| U²-Net | `VERIFIED / available=true / executable=true`（固定本地权重和运行合同） | 默认使用 | 按现有模型指南执行；权重不由 GenBox 自动联网安装 |
| MODNet ONNX | `TECHNICALLY RUNNABLE / LOCAL EXPERIMENTAL`；实例级探测通过后可 `executable=true` | 仅用户导入并明确选择；质量未验收 | 不打包、不托管、不自动下载权重 |
| InSPyReNet | `UNVERIFIED / unavailable / executable=false` | 描述性候选；请求 fail-closed | 不随 Release 提供 checkpoint |
| BiRefNet | `UNVERIFIED / unavailable / executable=false` | 描述性候选；请求 fail-closed | 不随 Release 提供权重 |
| BRIA RMBG-2.0 | `UNVERIFIED / unavailable / executable=false` | 描述性候选；请求 fail-closed | 不随 Release 提供权重 |

## MODNet：可运行但仅限用户导入

代码层面的 MODNet 适配器（`image_tools/cutout_modnet.py`）是隔离的、无隐式
联网的 CPU-only ONNX 路径。它要求：

- 文件是本地 regular file，不能是符号链接；
- manifest 同时包含安全 `filename`、`size_bytes`、`sha256`、`md5`，且与文件
  完全匹配；
- 用户明确提交 `license_confirmed=true`，并可填写 `license_source`；
- `onnxruntime` 和 `numpy` 可用，且会话只使用 `CPUExecutionProvider`；
- 输入/输出结构有效，并能生成与原图同尺寸的 RGBA PNG。

导入端点只接受 multipart 文件内容和 JSON manifest：
`POST /api/image-tools/cutout/modnet/import`。导入管理器固定写入
`storage/models/cutout/modnet/modnet.onnx` 及其 manifest，不接受服务器路径或
远程 URL。导入响应中的 `runtime.executable` 仅表示本次运行时探测结果；
`true` 不代表真实照片质量验收，也不代表可随 Release 再分发。

权重的具体授权由用户自行核对。GenBox 不对上游权重作新的法律定性；若权利
条款未明确允许商业使用，应将该权重限制为非商业研究、教学或个人实验。任何
公共下载、商业部署或 Release 打包都必须另行取得并保存明确的权重授权、来源链
和固定摘要证据。

## 其他候选：继续 fail-closed

### InSPyReNet

当前仅有独立描述性适配器 `image_tools/cutout_inspyrenet.py`，不会导入可选推理
依赖、下载 checkpoint 或修改默认注册表。缺少固定本地权重、SHA-256、离线推理
和真实照片质量验收中的任一项时，保持不可用。详见
[`CUTOUT-INSPYRENET-FEASIBILITY-20260904.md`](CUTOUT-INSPYRENET-FEASIBILITY-20260904.md)。

### BiRefNet 与 BRIA RMBG-2.0

注册表中的条目是 `UnavailableCutoutAdapter` 描述，不是安装或执行入口。没有
GenBox 已核验的固定权重、摘要、离线运行证据和适用授权时，不能公开
`available=true` 或 `executable=true`，也不能触发下载。对任何仅允许非商业使用
的用户取得权重，商业用途仍被禁止，除非用户另行取得明确商业授权。

## 解锁任一候选的共同门槛

1. 固定版本、文件名、大小和 SHA-256；保存来源、许可证全文及授权边界。
2. 依赖版本和 CPU 执行路径锁定；禁止运行时隐式联网下载。
3. 在断网环境完成 RGBA、尺寸、alpha、损坏文件、超时、并发和取消测试。
4. 用经授权的非敏感真实样本完成腿部、发丝、半透明边缘和复杂背景质量验收。
5. 通过独立集成审查后，才可把适配器注册为 `verified=true` 并公开可执行能力。

在门槛完成前，失败必须保持 fail-closed，并继续使用 U²-Net 默认路径。

## 证据标签与相关文档

- **VERIFIED / LOCAL:** 运行时代码、导入边界和本地测试所证明的行为。
- **UNVERIFIED:** 尚缺权重、授权、质量或跨环境证据；不表示权利存在或不存在。
- **USER-CONFIRMED:** 用户在导入时对其自行取得的权重许可作出的确认；不等同于
  GenBox 或上游作者的授权声明。

实现证据：`../image_tools/cutout_registry.py`、`../image_tools/cutout_modnet.py`、
`../image_tools/cutout_modnet_import.py`、`../image_tools/cutout_inspyrenet.py`。
用户操作见 [`MODNET-USER-IMPORT-GUIDE.md`](MODNET-USER-IMPORT-GUIDE.md)；U²-Net
固定安装合同见 [`CUTOUT-MODEL-GUIDE.md`](CUTOUT-MODEL-GUIDE.md)。
