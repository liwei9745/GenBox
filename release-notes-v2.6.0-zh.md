# GenBox v2.6.0 —— 扩展中心与图片 Push

> v2.6.0 是扩展中心与认证图片 Push 接收端的稳定版本。它包含 chatgpt2api
> 引导式部署、带可选加密本地凭证库的受管 Push 来源配置，以及单张、批量与
> 定时增量图片 Push 接收进入 GenBox 媒体库。本版本不包含源文件清理。

## 先下载哪个？

| 设备 | 推荐下载 | 下载后怎么做 |
|---|---|---|
| Windows 10/11 | [GenBox-Windows.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-Windows.zip) | 解压后双击 `GenBox.exe` |
| macOS | [GenBox-macOS.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-macOS.zip) | 解压后运行 `GenBox-macOS` |
| Linux | [GenBox-Linux-x64.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-Linux-x64.zip) | 解压、添加执行权限后运行 |
| NAS / VPS / Docker | [GenBox-Docker-Compose-v2.6.0.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-Docker-Compose-v2.6.0.zip) | 解压、配置 `.env` 后启动 Compose |

桌面压缩包已包含运行环境，不需要安装 Python。启动后访问
`http://localhost:8891`。

## 包含内容

- 单张图片 Push 接收进入 GenBox 媒体库。
- 手动批量 Push 接收，导入幂等且去重。
- 定时增量 Push 接收，进度持久化并处理晚到图片。
- 面向隔离 `chatgpt2api` 实例的扩展中心引导式部署。
- 受管 Push 来源配置：已部署实例可打开 GenBox Push 配置并复制，新签发的
  Push Key 默认只显示一次；用户明确选择后方可加密保存在本机凭证库中，
  删除本地副本不会改变远端来源。
- 客户端打包改进，包括内置更新器对预发布版本排序的支持。

## 重要限制

- 源文件清理**不包含**在本版本中，且仍处于禁用状态。Push 回执不会授予
  源文件删除许可。
- chatgpt2api 集成的发送端与上游交付、以及干净重建部署的证据仍待完成。
  本版本不声称具备端到端的发送端清理能力。
- 接收端 Push 验证记录在 `docs/STATUS.md`；隔离发送端与干净部署证据是
  独立的发布门禁。

## 评估说明

- 请按照 `docs/STATUS.md` 记录的本地测试、JavaScript 语法检查、README Lab
  与客户端打包构建流程复现验证。
- rc.1 至 rc.8 的候选说明保持为历史记录，不表示稳定版本。
- 发布文件将在发布协调人授权 `v2.6.0` 标签后发布。

## 参考资料

- [更新记录](CHANGELOG.md)
- [当前验证状态](docs/STATUS.md)