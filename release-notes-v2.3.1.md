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

### Changelog v2.3.1

**Provider Config Robustness & Endpoint Type**
- Added explicit `endpoint_type` selector (auto / openai / gemini / qwen / agnes / volc_ark_plan / volc_ark) so users can pin the protocol instead of relying on URL heuristics
- Removed the hardcoded Volcano model fallback: `volc_ark_plan` now only returns official candidate models (doubao-seedance series), no longer faking available models
- Model fetching now reports real errors on failure instead of silently returning a "recommended" fake list
- Video generation routing now honors the explicit `endpoint_type`

**Localized Upstream Errors**
- Added `translate_upstream_error`: common upstream English errors are now shown in Chinese — e.g. `does not support image input`, `ModelNotOpen`, `UnsupportedModel`, auth failures, insufficient balance/quota, rate limit, timeout — while preserving the original message for debugging

### System Requirements

- Python 3.10 or higher
- No dependency installation required (exe is self-contained)

### Known Issues

- Windows antivirus may give false positives (common PyInstaller issue)
- macOS first run requires `xattr -c` to remove quarantine
- Linux requires `libgl1` dependency (GUI mode)
- `updater.CURRENT_VERSION` is currently `2.2.0` and should be bumped to `2.3.1` when cutting the release

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
