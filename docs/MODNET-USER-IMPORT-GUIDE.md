# MODNet 用户自带模型导入指南

## 状态标签（截至 2026-09-05）

- **VERIFIED / DEFAULT:** U²-Net 是 GenBox 当前默认且已验证的本地抠图路径。
- **TECHNICALLY RUNNABLE / LOCAL EXPERIMENTAL:** MODNet ONNX 适配器可以在满足
  文件、清单、许可确认、依赖和 CPU 会话条件时运行，但仅支持用户主动导入的
  本地实验。真实照片质量尚未验收。
- **NOT A RELEASE ASSET:** GenBox 不随 Release 打包、托管或自动下载 MODNet
  权重。导入 MODNet 不改变 U²-Net 默认选择。

该状态不是产品质量或法律授权背书。只有你自行取得并确认具体权重的使用权，
并能在所选用途下合法使用时，才应导入。若权利条款没有明确允许商业使用，
请将该权重限制在非商业研究、教学或个人实验；GenBox 不替你作出许可结论。

## 获取与安装

1. 从你有权使用的来源下载一个 MODNet ONNX 文件。下载是用户主动行为；GenBox
   不提供运行时联网下载，也不接受浏览器提交的远程 URL 或服务器路径。
2. 在 GenBox 安装根目录下，将文件内容上传到
   `POST /api/image-tools/cutout/modnet/import`。接口只接受 multipart 文件，
   不接受路径字符串。
3. 同时提交 JSON `manifest`，至少包含：`filename`、`size_bytes`、`sha256`
   和 `md5`；`filename` 必须是安全的 `.onnx` 文件名。
4. 将表单字段 `license_confirmed=true`，并在 `license_source` 写下你核对过的
   来源或授权说明。该确认表示你承担该权重的使用责任，不表示 GenBox 已验证
   上游许可。

导入管理器会把内容原子写入以下固定位置（上传文件名不会成为服务器路径）：

```text
<GenBox 安装根目录>/storage/models/cutout/modnet/modnet.onnx
<GenBox 安装根目录>/storage/models/cutout/modnet/modnet.onnx.manifest.json
```

Docker Compose 使用仓库目录的 `./storage` 挂载到容器的 `/app/storage`；因此在
宿主机上对应的持久化文件是：

```text
./storage/models/cutout/modnet/modnet.onnx
./storage/models/cutout/modnet/modnet.onnx.manifest.json
```

即使文件已放在宿主机目录，也应通过导入端点写入并生成 manifest，不要手工改名
或替换运行中的目标文件。

文件大小、SHA-256 或 MD5 不匹配，文件为空、过大、为路径/URL 或目标是符号
链接时，导入会拒绝并清理临时文件。接口响应不会泄露本地文件路径。

## 导入后运行提示

导入成功响应中的 `runtime` 反映一次新的本地能力探测：

- `runtime.executable=true`、`state=ready`：当前进程已用 CPU-only ONNX Runtime
  成功加载该用户权重；可在精准改图中明确选择 MODNet 做本地实验。
- `runtime.executable=false`：文件已保存但尚未可执行。常见原因是依赖缺失、
  清单/摘要不匹配、模型会话结构不符合要求或 CPU provider 不可用；继续使用
  U²-Net，不要把“已导入”当成“已验收”。

再次访问 `/api/image-tools/cutout/capabilities` 会重新探测已导入文件。删除或
修改模型后，能力会回到 fail-closed；没有已验证可执行适配器时，系统拒绝生成
结果，不会静默使用未验证算法。

## 运行边界

- MODNet 仅使用 `CPUExecutionProvider`，需要 `onnxruntime` 与 `numpy`；输出须
  是与原图同尺寸的 RGBA PNG。
- 当前只有合成图和适配器契约测试证明技术路径；腿部、发丝、半透明边缘、复杂
  背景等真实照片质量仍 **UNVERIFIED**。
- MODNet 不能替换 U²-Net 默认模型，也不能通过把文件放入目录来绕过清单、摘要
  或许可确认。
- 不要把用户权重、许可文本、账号、密钥或原始图像写入日志、URL、Git 或截图。

## 证据与相关文档

- 适配器：`../image_tools/cutout_modnet.py`
- 导入管理器：`../image_tools/cutout_modnet_import.py`
- HTTP 路由：`../main.py` 的 `/api/image-tools/cutout/modnet/import`
- 默认能力路由：`../main.py` 的 `/api/image-tools/cutout/capabilities`
- 导入与运行测试：`../tests/test_cutout_modnet.py`、
  `../tests/test_cutout_modnet_import.py`、
  `../tests/test_cutout_modnet_import_route.py`
- 多算法边界：[`CUTOUT-ALGORITHM-FEASIBILITY-20260904.md`](CUTOUT-ALGORITHM-FEASIBILITY-20260904.md)

测试和本地运行记录证明的是代码行为，不是第三方权重的质量、许可或可再分发
权利。任何 Release、公共下载或商业部署前，仍需单独完成权重来源、固定摘要、
许可证和质量验收。
