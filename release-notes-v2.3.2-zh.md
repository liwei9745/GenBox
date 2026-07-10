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

### 更新日志 v2.3.2

**更新状态常驻系统看板工具栏**
- 更新状态徽标从右上角悬浮改为常驻「系统看板」顶部工具栏，不再遮挡其他图标
- 支持多状态常驻显示：检查中 / 已是最新 / 可更新（高亮）/ 已忽略 / 检查失败 / 自动检查已关闭
- 点击徽标弹出更新说明弹窗，提供「稍后 / 忽略此版本 / 前往下载 / 立即更新」四种操作
- 新增「启动时自动检查更新」开关（设置页供应商管理区域），关闭后徽标保留手动检查入口

**统一设计语言**
- 系统看板顶部操作按钮（更新状态、GitHub、刷新、重启、停止）统一高度、圆角、边框与间距
- 网络连通状态条重构为独立第二行，采用统一胶囊样式，空间不足时独立横向滚动，不再挤压操作按钮
- 新增响应式断点：≤900px 统计卡 4→2 列、双栏→单列；≤560px 快捷导航 4→2 列、IP 信息 2→1 列

**更新流程修复**
- 修正更新接口返回字段不一致：前端由判断 `ok` 改为同时兼容 `success`，避免「实际成功却显示失败」
- 修正镜像线路参数传递（`mirror` 独立入参），源码模式按当前分支上游 reset 的逻辑保持不变

### 系统要求

- Python 3.10 或更高
- 无需安装依赖（exe 为自包含）

### 已知问题

- Windows 杀毒软件可能误报（PyInstaller 常见问题）
- macOS 首次运行需 `xattr -c` 去除隔离
- Linux GUI 模式需要 `libgl1` 依赖
- `updater.CURRENT_VERSION` 当前为 `2.3.2`，打正式发布时建议同步更新

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
