# GenBox v2.6.6 - 精细编辑 V4 与 CI 修复

发布日期：2026-09-03

## 包含内容

- 可编辑的精细编辑标注：箭头、矩形、椭圆、画笔、橡皮和文字工具，并支持
  可安全撤销/重做的编辑流程。
- 支持尺寸的仅调整大小扩展。仅调整大小请求不会携带标注字段；默认仍严格要求
  精确输出尺寸，并为符合条件的近似比例结果提供显式 `fit_crop` 处理。
- 结果版本对比、透明结果棋盘格显示、本地抠图与细化、与选区关联的羽化和
  前景恢复，以及适配窄屏和桌面的响应式工作台。
- 用户可选择模型可见性；Provider 能力和别名必须明确声明，缺失或歧义时
  fail closed。
- Provider 输出执行 MIME、压缩字节、解码像素、解压炸弹及敏感错误详情保护。

## 桌面打包修复

- onefile 构建现在显式打包完整的直接运行时合同，不再依赖 PyInstaller 自动
  发现动态导入。合同包含 Pydantic Settings 及其必要运行时模块、所需 Uvicorn
  子模块、原生库/数据收集，以及全部 18 个固定直接依赖的分发元数据。
- 生成的 spec 与 PyInstaller CLI 使用同一组收集清单。打包运行时 smoke 会导入
  全部合同模块、校验精确依赖版本，并检查关键 API 符号。
- Windows、macOS 和 Linux 的空目录检查会移除 `PYTHONPATH` 和 `PYTHONHOME`，
  并设置 `PYTHONNOUSERSITE=1` 后再运行打包程序。
- 带口令的 OpenSSH 私钥现在显式依赖 `bcrypt==5.0.0`。桌面与 Docker smoke
  会生成合成的加密 Ed25519 OpenSSH 私钥，并要求
  `asyncssh.import_private_key(..., passphrase)` 成功。
- bcrypt 的完整 Apache License 2.0 文本会随桌面包、Docker 镜像、Docker
  Compose 包和源码包一起提供。收集器兼容已验证的 Windows 与 Linux wheel
  元数据布局，同时仍要求精确匹配唯一一份许可证文件。

## Docker 就绪修复

- 精确镜像 HTTP smoke 改用有界就绪循环，不再把启动阶段的第一次连接重置直接
  判定为应用终止失败。
- 每次尝试都会检查容器运行状态和健康状态，再验证生产 setup-status 响应；
  最终失败时输出有界且凭据脱敏的日志。工作流仍只 smoke 并发布单次构建步骤
  产生的精确镜像 ID。
- Docker 构建与发布权限已分离。发布 job 会重新加载已经通过 smoke 的精确镜像
  产物，并在不重新构建的前提下校验原始镜像 ID、打标签和推送。
- 发布工作流使用经审查的完整 commit SHA 固定外部 action。默认权限只读；仅
  Release 与包发布 job 获得各自必需的最小写权限。

## 验证与边界

- 全新本地 Python 3.12.8/PyInstaller 6.21.0 Windows onefile 构建生成了
  67,631,005 字节的可执行文件，并通过 v2.6.6 空目录版本、全部 18 个固定运行时
  版本、API 符号、加密 OpenSSH 私钥和打包客户端 HTTP smoke。
- 当前源码构建的本地 Docker 镜像已通过精确镜像运行时、bcrypt 许可证、加密
  OpenSSH 私钥和有界 HTTP 就绪 smoke。
- 最终本地验证通过 42 个发布打包测试与 1,302 个仓库全量测试，并通过 v2.6.6
  标签合同、工作流 YAML 解析、Python 编译和 diff 空白检查。
- 自动更新应用和重启继续禁用。应用内版本检查仅提供信息；在签名清单和回滚
  合同实现前，安装仍通过手动获取发布资产完成。
- ONNX 抠图模型仍为外部文件。由于来源和商业使用权利仍为 **UNVERIFIED**，
  生产联网下载与安装继续禁用。
- 本次发布验证未执行真实 Provider 请求、VPS 部署、源图清理或跨项目端到端
  操作。

## v2.6.5 历史结果

- 已推送 `v2.6.5` 标签，但 Desktop Clients 运行 `33715658824` 和 Docker Image
  运行 `33715658700` 均失败。
- 未创建 v2.6.5 GitHub Release、发布资产或 GHCR 镜像。
- v2.6.6 使用上述桌面依赖与 Docker 就绪修复取代该失败标签。

## 发布包

- Docker Compose 默认镜像固定为 `ghcr.io/liwei9745/genbox:2.6.6`。
- 桌面、Docker Compose、Docker 镜像和源码发布包均包含适用的第三方声明与
  已收集的运行时许可证文件。
