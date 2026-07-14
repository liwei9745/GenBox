# GenBox Client Quick Start / 客户端快速开始

The desktop client is self-contained. Python is not required.

桌面客户端已经包含运行环境，不需要安装 Python。

## Start / 启动

- Windows: double-click `GenBox.exe`.
- macOS: run `chmod +x GenBox-macOS && xattr -c GenBox-macOS && ./GenBox-macOS`.
- Linux: run `chmod +x GenBox-Linux-x64 && ./GenBox-Linux-x64`.

Open `http://localhost:8891` if the browser does not open automatically.

如果浏览器没有自动打开，请访问 `http://localhost:8891`。

On first startup, choose the mode that matches your environment and keep the
generated administrator key in a password manager. Provider API keys can be
added later from Model settings.

首次启动时按使用环境选择模式，并把生成的管理员密钥保存在密码管理器中。
模型 API Key 可以稍后在“模型设置”中添加。

Runtime configuration and media stay beside the executable under `storage/`.
Do not share that directory in bug reports or release packages.

运行配置和媒体保存在客户端旁边的 `storage/` 目录。提交问题或分享安装包时，
不要上传该目录。
