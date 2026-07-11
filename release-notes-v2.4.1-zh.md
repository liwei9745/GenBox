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

### 更新日志 v2.4.1

**云端同步弹窗操作引导优化**
- 弹窗顶部新增三步流程指示：① 填写并保存远程部署 → ② 选择部署并点「扫描预览」→ ③ 勾选图片并点「同步选中」
- 部署表单新增 chatgpt2api 术语提示：Base URL 对应「接口信息」页的「基础端点」，Admin Bearer Token 对应「当前调用密钥」
- ② 区新增操作说明：先选部署、点扫描预览拉取并去重，预览图加载完成后再勾选图片同步
- 空状态文案改为清晰的三步指引，降低新用户上手门槛

### 系统要求

- Python 3.10 或更高
- 无需安装依赖（exe 为自包含）

### 已知问题

- Windows 杀毒软件可能误报（PyInstaller 常见问题）
- macOS 首次运行需 `xattr -c` 去除隔离
- Linux GUI 模式需要 `libgl1` 依赖
- `updater.CURRENT_VERSION` 当前为 `2.4.1`，打正式发布时建议同步更新

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
