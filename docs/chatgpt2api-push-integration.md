# chatgpt2api -> GenBox 图片推送集成

## 可行性结论

该集成可行，但 VPS 必须能够访问 GenBox。普通家庭网络中的 `localhost:8891`
不能被 VPS 直接连接，推荐使用 Tailscale/Headscale、Cloudflare Tunnel 或带 TLS
的反向代理。不要将未加密的 GenBox 端口直接暴露到公网。

GenBox 保留现有“本地主动拉取”模式作为无入站网络条件下的兼容方案。

## 接收协议 v1

`POST /api/sync/push`，请求为 `multipart/form-data`：

- Header `X-GenBox-Source`: 稳定的数据来源身份，例如 `chatgpt2api-vps`
- Header `X-GenBox-Key`: 与来源身份绑定的独立 API Key
- File `image`: 图片二进制，默认最大 25 MiB
- Form `remote_path`: chatgpt2api 中的稳定相对路径，必填
- Form `created_at`, `prompt`, `model`: 可选元数据

GenBox 通过 `GENBOX_PUSH_KEYS` 配置来源身份：

```env
GENBOX_PUSH_KEYS={"chatgpt2api-vps":"replace-with-a-long-random-key"}
```

该路径不接受或要求 `X-Admin-Key`。专用来源密钥泄漏时可以只吊销一个 VPS，
而不影响 GenBox 管理员会话。

当前成功响应包含 `sha256`、`local_file` 和
`safe_to_delete_source=true`。该字段只表示 GenBox 已安全提交本次内容，不表示发送端
应默认删除源文件；发送端仍必须检查用户独立 opt-in、回执哈希和源文件当前哈希。相同
`source_id + remote_path + sha256` 重试会返回 `already-imported`，不会重复落库。

## chatgpt2api 侧设计

单次推送、图片管理批量推送、定时增量推送必须调用同一个服务层：

1. 读取本地/WebDAV 图片字节和元数据。
2. 上传到 GenBox，失败时指数退避并保留源文件。
3. 校验 HTTP 200、`ok=true`、回执 SHA-256 与本地内容一致。
4. 持久化 `source path -> receipt`，支持幂等重试和断点续传。
5. 仅当用户独立启用“确认后删除源文件”时，才在成功回执后删除 VPS 本地副本。

默认计划为每周增量推送一次；自定义模式支持 cron/星期时间和起止日期。调度器
应保存游标和每张图片状态，不应只依赖“上次执行时间”，否则时钟偏差和补录文件
会造成漏传。

## PR 拆分建议

1. GenBox PR：接收 API、来源密钥配置、幂等清单、测试和文档。
2. chatgpt2api PR A：推送配置、服务层、持久化状态、手动批量接口。
3. chatgpt2api PR B：Studio 单次勾选、Gallery 批量操作和进度 UI。
4. chatgpt2api PR C：周计划/自定义计划、失败重试、确认后清理策略。

拆分可降低上游审查风险，也避免调度和删除逻辑阻塞基础互通能力。
