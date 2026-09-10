# InSPyReNet 抠图算法可行性核验（2026-09-04，当前边界更新至 2026-09-05）

## 结论

InSPyReNet 仍是质量验证候选，不是 GenBox 可执行算法。当前状态为
`UNVERIFIED / state=unavailable / executable=false`，请求必须 fail-closed。
U²-Net 继续作为默认路径；MODNet 虽已具备用户导入后的技术运行能力，但与本
候选一样不改变默认模型，也不代表 Release 可再分发。

## 已记录证据

以下是 2026-09-04 的只读核验记录，属于历史证据，不是实时服务保证：

- 官方实现和封装代码的来源页面可定位，但代码许可证不自动覆盖 checkpoint、
  转换文件或托管资产。
- model zoo 与封装使用外部 checkpoint；GenBox 当前没有固定、经本地 SHA-256
  核验且可离线加载的 InSPyReNet 权重。
- 封装在缺少 checkpoint 时可能尝试下载；GenBox 禁止推理期间隐式联网，因此
  候选适配器不得调用此类下载路径。

这些记录只说明来源和当前缺口，不对任何权重的再分发权、商业权利或质量作出
推断。具体授权必须由取得权重的用户或授权构建流程单独提供。

## 运行与接入门槛

若未来接入，必须由独立适配器在隔离目录使用用户主动提供的固定文件，并完成：

1. 文件名、大小、SHA-256、变体、来源和许可证全文记录；
2. PyTorch/torchvision 等依赖的版本锁定，以及 CPU-only 执行路径；
3. 断网启动和推理，禁止 `gdown`、`wget` 或其他运行时下载；
4. RGBA、尺寸、alpha 范围、损坏权重、超时、并发和取消行为测试；
5. 经授权的非敏感真实样本质量验收，重点检查腿部、发丝、半透明边缘、复杂
   背景和低对比度场景。

在上述证据全部通过并经集成审查前，注册表不得公开
`available=true`、`executable=true` 或任何安装/运行按钮。

## 授权与使用边界

GenBox 不把“代码仓库可见”“Release 可下载”或“用户已取得文件”当成模型授权
证据。用户须自行确认具体 checkpoint 的使用范围；若条款未明确允许商业使用，
请仅用于非商业研究、教学或个人实验。GenBox 不替用户或上游作者作出法律结论，
也不随 GenBox Release 打包、托管或自动下载 InSPyReNet 权重。

## 当前代码状态

`image_tools/cutout_inspyrenet.py` 提供无网络、fail-closed 的描述性适配器；它
不会导入可选推理依赖、下载 checkpoint 或修改默认注册表。测试覆盖能力探测、
结构化不可用错误和来源元数据，但不构成真实照片质量、Provider、VPS 或发布
验收。相关实现和测试应保持与 [`CUTOUT-ALGORITHM-FEASIBILITY-20260904.md`](CUTOUT-ALGORITHM-FEASIBILITY-20260904.md)
及 [`MODNET-USER-IMPORT-GUIDE.md`](MODNET-USER-IMPORT-GUIDE.md) 的状态词一致。

## 来源（历史核验入口）

- `https://github.com/plemeri/InSPyReNet`
- `https://github.com/plemeri/InSPyReNet/blob/main/docs/model_zoo.md`
- `https://github.com/plemeri/transparent-background`
- `https://github.com/plemeri/transparent-background/releases/tag/1.2.12`
- `https://raw.githubusercontent.com/plemeri/transparent-background/main/transparent_background/config.yaml`
- `https://raw.githubusercontent.com/plemeri/transparent-background/main/transparent_background/Remover.py`
