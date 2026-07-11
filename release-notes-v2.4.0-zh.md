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

### 更新日志 v2.4.0

**新增：云端同步（chatgpt2api）**
- 新增「系统设置 → 云端同步」面板，可添加 / 编辑 / 删除远程 chatgpt2api 部署（地址 + API Key），并支持一键连接测试
- 按日期范围拉取远端图片，自动按内容哈希去重，避免重复导入到本地媒体库
- 支持按日期 / 体积 / 比例维度批量筛选与选择要同步的图片
- 同步后的图片自动写入 PNG 元数据：来源标签 `cloud`、提示词、模型；媒体库中以「☁ 云端」角标展示
- 通过读取远端 `/api/logs` 调用日志，按图片 URL 关联原始提示词与模型，回填到同步图片，可直接在灯箱「复制提示词」中复用
- 缩略图经服务端同源代理加载（`/api/sync/thumbnail`）并带磁盘缓存，规避浏览器跨域限制；点击缩略图复用灯箱放大查看

**修复与打磨**
- 修复「从远程同步」按钮点击无响应的弹窗显示问题
- 修复部署保存无反馈、列表不刷新；部署列表接口不再返回 API Key 明文
- 修复同源 POST/DELETE 被 CSRF 误拦：允许同源（请求 host 与源一致），跨域仍拦截
- 修复同步弹窗按钮在浅色主题下不可见、删除按钮红色高亮、Esc / 焦点陷阱与移动端响应式
- 修复预览卡死：解析远端文件名中的内容 MD5 与本地索引比对，免下载即可去重（55 张预览约 2.4s）
- 修复历史同步图片因 `PIL` 导入缺失导致 PNG 元数据未写入的问题，并在预览时对已同步图片自动补写云端标签
- 修复同步弹窗右上角关闭按钮对比度过低、不够明显的问题，改为带背景的圆形按钮并增加悬停高亮

**依赖同步**
- `requirements.txt` 对齐本地实测版本，补齐运行时依赖 `requests`（此前仅在 CI 临时安装，易导致用户环境缺包）

### 系统要求

- Python 3.10 或更高
- 无需安装依赖（exe 为自包含）

### 已知问题

- Windows 杀毒软件可能误报（PyInstaller 常见问题）
- macOS 首次运行需 `xattr -c` 去除隔离
- Linux GUI 模式需要 `libgl1` 依赖
- `updater.CURRENT_VERSION` 当前为 `2.4.0`，打正式发布时建议同步更新

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
