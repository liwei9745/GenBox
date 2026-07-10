- **Windows**: 双击 `GenBox.exe` 启动（建议先运行 `check_env.py` 检查环境）
- **macOS**: 解压后运行 `./GenBox-macOS`（需先执行 `xattr -c GenBox-macOS` 去除隔离属性）
- **Linux**: 解压后运行 `./GenBox-Linux-x64`

### 快速开始

1. 确保已安装 Python 3.10+
2. 下载对应平台压缩包
3. 解压并运行：
   ```bash
   # Windows
   GenBox.exe

   # macOS/Linux
   ./GenBox-macOS  # 或 ./GenBox-Linux-x64
   ```

### 环境配置

首次运行进入**交互式配置向导**：
- 选择运行模式：本地开发 / VPS 生产 / Docker
- 配置 API Key（支持 OpenAI、Claude、Gemini 等 13 家厂商）
- 可选代理配置

### 更新日志 v2.3.1

**供应商配置稳健性 & 端点协议类型**
- 新增显式 `endpoint_type` 选择（auto / openai / gemini / qwen / agnes / volc_ark_plan / volc_ark），可手动指定协议，避免自动识别误判
- 移除火山方舟硬编码假模型列表：`volc_ark_plan` 现在只返回官方候选模型（doubao-seedance 系列），不再伪造可用模型
- 模型拉取失败时如实报错，不再静默返回「推荐列表」（假成功）
- 视频生成路由现在尊重显式 `endpoint_type`

**上游错误中文化**
- 新增 `translate_upstream_error`：将上游常见英文错误翻译为中文显示，如 `does not support image input`（不支持图片输入）、`ModelNotOpen`（模型未开通）、`UnsupportedModel`（模型不支持）、鉴权失败、余额/配额不足、限流、超时等，同时保留原始信息便于排查

### 系统要求

- Python 3.10 或更高
- 无需安装依赖（exe 为自包含）

### 已知问题

- Windows 杀毒软件可能误报（PyInstaller 常见问题）
- macOS 首次运行需 `xattr -c` 去除隔离
- Linux GUI 模式需要 `libgl1` 依赖
- `updater.CURRENT_VERSION` 当前为 `2.2.0`，打正式发布时建议同步改为 `2.3.1`

### 相关链接

- [GitHub 仓库](https://github.com/liwei9745/GenBox)
- [Issue 跟踪](https://github.com/liwei9745/GenBox/issues)
- [配置文档](https://github.com/liwei9745/GenBox/blob/main/README.md)

### 重置管理员密钥

删除 `config/settings.yaml` 并重启服务，首次运行向导会提示重新设置：

```bash
# Windows
del config\settings.yaml

# macOS/Linux
rm config/settings.yaml
```
