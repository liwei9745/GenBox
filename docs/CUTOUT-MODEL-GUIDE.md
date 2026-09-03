# GenBox 人物抠图模型手动安装指南

## 用途与当前边界

`u2net_human_seg.onnx` 是 GenBox 精准改图工作台的本地人物分割模型，
用于“一键抠出人物”和带透明 Alpha 的边缘精修。它在本地 CPU 上通过
ONNX Runtime 执行，不是 Provider 生图请求。

GenBox 当前不捆绑、不重托管该模型权重，生产环境的公开自动下载/安装
也仍禁用。用户需要自行从上游来源获取文件、阅读来源与权利信息，
然后手动放入固定路径。

## 固定文件合同

GenBox 只接受以下完整匹配的文件：

| 字段 | 固定值 |
|---|---|
| 文件名 | `u2net_human_seg.onnx` |
| 字节数 | `175997641` |
| SHA-256 | `01eb6a29a5c4d8edb30b56adad9bb3a2a0535338e480724a213e0acfd2d1c73c` |
| MD5 | `c09ddc2e0104f800e3e1bb4652583d1f` |

文件大小或任一摘要不匹配时，GenBox 会 fail closed，不会加载或执行该文件。
MD5 在这里仅是上游文件身份的第二个固定校验值；安全完整性以
SHA-256 同时匹配为必要条件。

## 上游来源与研究背景

- [rembg v0.0.0 Release 模型页](https://github.com/danielgatis/rembg/releases/tag/v0.0.0)
- [rembg 中的 `u2net_human_seg.onnx` 资产](https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx)
- [U²-Net 官方仓库](https://github.com/xuebinqin/U-2-Net)
- [U²-Net 论文](https://arxiv.org/abs/2005.09007)
- [Supervisely Persons Dataset](https://ecosystem.supervisely.com/projects/persons)

**使用限制：** 在权重转换历史、训练数据授权和商业使用权利得到单独
确认之前，GenBox 只建议将该权重用于 **非商业研究、教学和个人实验**。
rembg 或 U²-Net 代码的开源许可证不等于模型权重的再分发或商业使用授权，
数据集页面也不自动为下游权重提供再分发授权。这是 GenBox 的保守使用边界，
不是对任何上游项目或数据集进行新的法律定性。

## Windows 客户端

1. 退出 GenBox。
2. 在 `GenBox.exe` 所在目录中创建 `storage/models/cutout/`。
3. 将下载的文件重命名并放到：
   `storage/models/cutout/u2net_human_seg.onnx`。
4. 在 `GenBox.exe` 目录打开 PowerShell 并校验：

```powershell
$Model = Join-Path (Get-Location) "storage/models/cutout/u2net_human_seg.onnx"
(Get-Item -LiteralPath $Model).Length
(Get-FileHash -LiteralPath $Model -Algorithm SHA256).Hash.ToLower()
certutil -hashfile $Model MD5
```

5. 确认字节数、SHA-256 和 MD5 与上方固定合同完全一致，再启动 GenBox。

## macOS 客户端

1. 退出 GenBox，并进入 `GenBox-macOS` 可执行文件所在目录。
2. 创建目录并放入模型：

```bash
mkdir -p storage/models/cutout
# 将已下载文件移动为：
# storage/models/cutout/u2net_human_seg.onnx
```

3. 校验字节数和摘要：

```bash
wc -c < storage/models/cutout/u2net_human_seg.onnx
shasum -a 256 storage/models/cutout/u2net_human_seg.onnx
md5 -q storage/models/cutout/u2net_human_seg.onnx
```

4. 三项都匹配后重新启动 GenBox。

## Linux 客户端

1. 退出 GenBox，并进入 `GenBox-Linux-x64` 可执行文件所在目录。
2. 创建目录并放入模型：

```bash
mkdir -p storage/models/cutout
# 将已下载文件移动为：
# storage/models/cutout/u2net_human_seg.onnx
```

3. 校验字节数和摘要：

```bash
wc -c < storage/models/cutout/u2net_human_seg.onnx
sha256sum storage/models/cutout/u2net_human_seg.onnx
md5sum storage/models/cutout/u2net_human_seg.onnx
```

4. 三项都匹配后重新启动 GenBox。

## Docker Compose

Compose 宿主机路径是：

```text
./storage/models/cutout/u2net_human_seg.onnx
```

1. 在 `docker-compose.yml` 所在目录创建目录：

```bash
mkdir -p ./storage/models/cutout
```

2. 将文件放到上述宿主机路径，使用对应系统的命令校验固定字节数、
   SHA-256 和 MD5。
3. 重启自己的 GenBox 服务：

```bash
docker compose restart genbox
```

4. 返回精准改图工作台刷新模型状态。只有同时显示 `ready` 和
   `executable=true` 时，人物抠图操作才会启用。

## 已验证状态（2026-09-03）

- **VERIFIED / LOCAL:** 本机文件的字节数、SHA-256 和 MD5 与固定合同一致。
- **VERIFIED / LOCAL:** 本机能力检查返回 `state=ready`、`available=true`、
  `executable=true` 和 `adapter=u2net-human-seg-onnx`。
- **VERIFIED / LOCAL:** 96×128 合成人形图片完成一次真实 ONNX 推理，生成
  96×128 PNG，Alpha 范围为 `0..255`。
- **UNVERIFIED / BLOCKED:** 公开自动下载、生产联网安装、GenBox Release 权重资产、
  权重商业使用/再分发授权和真实 Provider 端到端调用。

本机通过不代表其他设备已安装模型，也不把合成图本地推理升级为真实照片、
真实 Provider 或跨环境端到端验收。
