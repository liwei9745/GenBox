# GenBox v2.5.1 - 启动和登录更安全

> v2.5.1 是一版聚焦安全与稳定性的更新：收紧首次启动认证路径，
> 浏览器在状态不明确时默认要求登录，并让 Docker Compose 固定使用本版本镜像。

## 先下载哪个？

| 设备 | 推荐下载 | 下载后怎么做 |
|---|---|---|
| Windows 10/11 | [GenBox-Windows.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-Windows.zip) | 解压后双击 `GenBox.exe` |
| macOS | [GenBox-macOS.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-macOS.zip) | 解压后运行 `GenBox-macOS` |
| Linux | [GenBox-Linux-x64.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-Linux-x64.zip) | 解压、添加执行权限后运行 |
| NAS / VPS / Docker | [GenBox-Docker-Compose-v2.5.1.zip](https://github.com/liwei9745/GenBox/releases/download/v2.5.1/GenBox-Docker-Compose-v2.5.1.zip) | 解压、配置 `.env` 后启动 Compose |

桌面压缩包已包含运行环境，不需要安装 Python。启动后访问
`http://localhost:8891`。

`GenBox.exe`、`GenBox-macOS` 和 `GenBox-Linux-x64` 是在线更新器使用的
独立文件；第一次下载通常应选择 ZIP 压缩包。

## 这次修复了什么？

- 生产模式缺少 `ADMIN_KEY` 时现在会安全地拒绝启动；服务不会再通过浏览器接口
  生成或展示管理员密钥。
- 唯一不需要管理员认证的设置接口只返回固定、无密钥的就绪状态。此前可通过 HTTP
  完成首次设置的接口不再可被未认证请求使用。
- 浏览器拿到缺失、格式错误、失败或被拒绝的设置状态时，会默认显示登录页，
  不会把它当成“允许访问”。
- 登录和 Provider 加载会忽略较早请求迟到的结果，避免旧登录失败覆盖较新的成功登录。
- 本地桌面首次选择开发模式后会在同一进程立即生效，只监听 `127.0.0.1:8892`，
  且不会创建管理员密钥。
- Docker Compose 示例改为固定使用
  `ghcr.io/liwei9745/genbox:2.5.1`，不再使用会变化的 `latest` 标签。

## 安全升级

1. 备份 `.env`、`storage/providers.json`、媒体文件和其余 `storage/` 数据。
2. 不要用发布包覆盖已有的 `storage/` 目录。
3. 从 v2.4.1 或更早 Windows 版本升级时，先退出 GenBox，下载
   `GenBox-Windows.zip` 后手动替换一次。那一次不要使用旧版内置更新器。
4. Docker 用户保留已有 `.env` 和 `storage/`，只替换 Compose 包，然后运行
   `docker compose pull` 和 `docker compose up -d`。
5. 启动后检查模型设置、媒体库、生产模式管理员登录，以及已有的远程同步配置。

## Docker 快速启动

```bash
cp .env.example .env
# 生产模式启动前必须填写一个足够强、由你自己保管的 ADMIN_KEY。
docker compose pull
docker compose up -d
```

生产模式下 `ADMIN_KEY` 留空会拒绝启动。不要把密钥放进截图、日志、URL 或求助信息中。

## 校验与当前限制

- v2.5.1 候选在 2026-07-16 已通过 111 项自动化测试、JavaScript 语法检查、
  README Lab 生成、发布包检查、Windows 启动/升级验收及隔离本地 Docker 验收。
- Windows 验收目前来自一台 Windows 10 设备；v2.5.1 没有单独验收 ANSI 显示效果。
- 最终 `v2.5.1` 标签获得授权并推送后，GitHub Actions 会重新构建三平台客户端并发布
  SHA-256 校验值。
- chatgpt2api 发送端的生成后自动 Push、批量/定时传输和回执确认后的源文件清理尚未
  端到端完成。
- NetBird 和 Cloudflare Tunnel 尚未获得与 Tailscale 相同的验收覆盖。

## 参考资料

- [更新记录](CHANGELOG.md)
- [当前验证状态](docs/STATUS.md)
- [全部 v2.5.1 发布文件](https://github.com/liwei9745/GenBox/releases/tag/v2.5.1)
