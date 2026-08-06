# GenBox v2.6.0-rc.1

> 实验候选客户端版本，仅用于本地评估已经完成的 GenBox 与 chatgpt2api
> 联动能力，不是稳定正式版。

## 包含内容

- 单张图片 Push 到 GenBox 媒体库。
- 支持重试和幂等导入的批量 Push。
- 保存进度并处理迟到图片的计划增量 Push。
- 已部署 chatgpt2api 可重新打开 GenBox Push 配置、复制配置，并将 Push Key、Source ID 和 URL 显式保存到加密的本机凭证库。
- 打包客户端对 `-rc.N` 预发布版本的更新比较支持。

## 重要限制

- 源文件 cleanup 仍默认关闭，本候选版不提供可用的 cleanup 功能。
- Phase 6 安全工作不属于本候选版；A1、A2、A3、A10、A11 尚未完成，稳定版和 cleanup
  仍不得宣称完成。
- 本候选版不创建稳定 tag，也不创建 GitHub Release。

## 评估说明

请使用现有的本地测试、Windows 客户端构建和本地启动检查流程。远程部署或生产实例证据
不属于本候选版范围。
