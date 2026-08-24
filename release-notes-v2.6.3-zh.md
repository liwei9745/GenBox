# GenBox v2.6.3 —— Provider 与 Store 稳定性修复

## 包含内容

- Provider 页面不再把脱敏 API Key 当作真实凭证发送。
- OpenAI 兼容模型拉取支持有效多 Key 轮换。
- 拉取模型不再覆盖多端点和 Provider 其他配置。
- 多 target 场景下 Store Installed 投影保持目标归属一致。
- Windows 启动脚本统一设置 UTF-8 控制台与 Python 输出，并提供中英双语
  启动及错误提示。

## 安全与边界

- 脱敏或不可用凭证 fail closed，需要用户明确重新输入。
- 本版本未修改生产 VPS、上游仓库或远程部署。

## 验证

- 全量本地回归：`698 passed`。
- Provider/启动脚本/发布 focused 契约测试：`16 passed`。
- JavaScript 语法、Python 编译与 `git diff --check` 均通过。
