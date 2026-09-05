# 抠图结构质量与离线运行门禁（2026-09-05）

## 门禁目标

该门禁为 U²-Net 与 MODNet 提供可重复的本地运行证据，但不把合成图 smoke
误写成真实人物质量验收。执行命令：

```powershell
$env:PYTHONPATH='.'
python -m image_tools.cutout_quality_gate
```

也可以只检查一个算法：

```powershell
python -m image_tools.cutout_quality_gate --adapter u2net-human-seg-onnx
python -m image_tools.cutout_quality_gate --adapter modnet-portrait-onnx
```

输出为 `genbox-cutout-quality-gate-v1` JSON，不保存输入或输出图片，也不暴露
本地绝对路径。

## 可重复检查项

- 模型文件必须通过固定大小、SHA-256 和 MD5 清单校验。
- ONNX Runtime 会话必须只报告 `CPUExecutionProvider`。
- 创建会话和推理期间设置常见离线环境变量，并在 Python 层阻断 DNS、
  `socket.connect`、`socket.connect_ex` 和 `socket.create_connection`。
- 固定合成全身轮廓输入为 `96 × 128` RGB PNG；输出必须仍为
  `96 × 128` RGBA PNG。
- Alpha 必须同时包含 `0` 与 `255`；报告还记录全透明、全不透明和软 Alpha
  像素数。

`python_network_blocked=true` 证明本进程在门禁覆盖的 Python 网络入口没有联网，
不等于操作系统防火墙或物理断网证明。Release 前的强断网验收仍应在禁用网卡或
隔离容器中重复运行同一命令，并保存命令、退出码和 JSON 摘要。

## 2026-09-05 本机证据

在当前开发机运行统一命令，退出码为 `0`，总结果为 `passed=true`：

- **VERIFIED / LOCAL / U²-Net:** 固定模型大小 `175997641`，SHA-256
  `01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c`；
  CPU-only 会话、Python 网络尝试 `0`、输出 `96 × 128` RGBA PNG、Alpha
  `0..255`，软 Alpha 像素 `677`。
- **VERIFIED / LOCAL / MODNet:** 固定模型大小 `6632188`，SHA-256
  `92e49898c3e05a6d7a944fc67a8cb87c4aad754ffb6ebd949528c7d1105fee3a`；
  CPU-only 会话、Python 网络尝试 `0`、输出 `96 × 128` RGBA PNG、Alpha
  `0..255`，软 Alpha 像素 `214`。
- **VERIFIED / TEST:** `tests/test_cutout_quality_gate.py` 覆盖通过证据、非 CPU
  能力拒绝、联网尝试阻断和缺少可选模型时的不泄露/fail-closed 行为。

这些项目无论是否通过，都不能自动把真实人物边缘质量标为通过。

## 真实质量验收仍需授权样本

以下项目保持 `UNVERIFIED`，需要用户拥有使用与测试权利的非敏感样本；不得把
用户原图、提示词或输出提交到 Git、普通日志或公开截图：

| 场景 | 最低检查 | 当前状态 |
|---|---|---|
| 完整全身与腿部 | 两条腿、鞋和腿间负空间均保留，无大块缺失 | `UNVERIFIED` |
| 发丝与头部轮廓 | 散发不过度截断，背景残留可接受 | `UNVERIFIED` |
| 半透明边缘 | 纱、薄发、玻璃等 Alpha 有连续过渡，不被二值化 | `UNVERIFIED` |
| 低对比与复杂背景 | 主体与近色背景分离，肢体和衣物不误删 | `UNVERIFIED` |
| 多人、遮挡与裁切 | 明确记录算法是否保留全部人物及其失败模式 | `UNVERIFIED` |

建议每个场景至少使用 3 张授权样本，U²-Net 与 MODNet 使用同一输入、同一边缘
精修参数，人工盲看并记录“通过/可修复/失败”。在腿部、发丝和半透明边缘样本
完成前，MODNet 只能标记为本地实验性算法，不能标记为默认质量通过。

## 许可与发布边界

- U²-Net 官方仓库在 GitHub 标记为 Apache-2.0，但 GenBox 当前固定 ONNX 文件
  来自 `danielgatis/rembg` 的 `v0.0.0` Release 资产。该 Release 资产没有独立
  digest，代码仓库许可证也不能自动证明转换权重、训练数据和商业再分发链。
- MODNet 官方仓库明确声明仓库内代码、模型和 demo（排除指定 GIF）使用
  Apache-2.0。当前本地 ONNX 来自
  `onnx-community/modnet-webnn` 固定修订
  `6af52070d14deafc5e55ce6cc4d752a322cdff76`，其模型卡声明 Apache-2.0；但该
  社区转换资产仍需在 Release 前完成来源对应、Apache NOTICE/归属和再发布清单
  审查。
- 因此当前两个模型权重都不放入 Git 或 GenBox Release，也不由运行时自动下载。
  MODNet 继续采用用户主动导入、清单校验、许可确认和 fail-closed 能力探测。

主要来源：

- `https://github.com/xuebinqin/U-2-Net`
- `https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE`
- `https://github.com/danielgatis/rembg/releases/tag/v0.0.0`
- `https://github.com/ZHKKKe/MODNet`
- `https://github.com/ZHKKKe/MODNet/blob/master/LICENSE`
- `https://huggingface.co/onnx-community/modnet-webnn/tree/6af52070d14deafc5e55ce6cc4d752a322cdff76`

许可证核对证明的是来源页面和明确文本，不替代法律意见。权重再分发链未闭合时，
保持“不打包、不托管、用户主动导入”是当前发布门禁。
