- **Windows**: Double-click `GenBox.exe` to start (recommended to run `check_env.py` first to check environment)
- **macOS**: After extracting, run `./GenBox-macOS` (need to run `xattr -c GenBox-macOS` to remove quarantine)
- **Linux**: After extracting, run `./GenBox-Linux-x64`

### Quick Start

1. Ensure Python 3.10+ is installed
2. Download the zip package for your platform
3. Extract and run:
   ```bash
   # Windows
   GenBox.exe

   # macOS/Linux
   ./GenBox-macOS  # or ./GenBox-Linux-x64
   ```

### Environment Configuration

First run will enter **interactive configuration wizard**:
- Select runtime mode: Local dev / VPS production / Docker
- Configure API Keys (supports 13 providers including OpenAI, Claude, Gemini, etc.)
- Optional proxy configuration

### Changelog v2.3.0

**Security Hardening**
- API key masking: Provider API Keys are automatically masked when returned (e.g., `sk-a****12c`)
- SSRF protection: Blocks private IP requests, prevents port scanning
- CSRF protection: Origin/Referer validation middleware
- CSP enhancement: Stricter Content-Security-Policy

**Auto-Update System**
- One-click update check: `/api/update/check`
- GitHub mirror acceleration: Supports 6 Chinese mirror sources
- Auto-fix: Detects and repairs corrupted installations
- Docker adaptation: Container environment detection and prompts

**Production Mode Upgrade**
- First-run wizard: 3 runtime modes (Local/VPS/Docker)
- Admin authentication: VPS deployment enforces key setup
- Security headers: CSP + CSRF + Auth middleware

**Configuration Enhancement**
- Per-provider proxy: `skip_proxy: true` skips proxy for specific providers
- Config file: `config/settings.yaml` with detailed comments
- Environment variables: `.env.example` documentation improved

### System Requirements

- Python 3.10 or higher
- No dependency installation required (exe is self-contained)

### Known Issues

- Windows antivirus may give false positives (common PyInstaller issue)
- macOS first run requires `xattr -c` to remove quarantine
- Linux requires `libgl1` dependency (GUI mode)

### Related Links

- [GitHub Repository](https://github.com/liwei9745/GenBox)
- [Issue Tracker](https://github.com/liwei9745/GenBox/issues)
- [Configuration Documentation](https://github.com/liwei9745/GenBox/blob/main/README.md)

### Key Reset

To reset admin key, delete `config/settings.yaml` and restart the service. First-run wizard will prompt for new setup:

```bash
# Windows
del config\settings.yaml

# macOS/Linux
rm config/settings.yaml
```
