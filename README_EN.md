# GenBox - All-in-One AI Creation Platform

> A desktop-grade AI creation tool integrating text-to-image, text-to-video, image upscaling, and media library management.
> Supports GPT Image / Gemini / Qwen / Agnes and more — ready to use out of the box.

> 💡 Like it? Give us a [Star](https://github.com/liwei9745/GenBox/stargazer) to show your support!

![Dashboard](screenshots/sanitized/01-dashboard.png)

---

## Features

### Multi-Model Aggregation
Connect OpenAI, Gemini, Qwen, Agnes and more — manage all providers from a single interface.

### Parallel Generation + Real-time Preview
Generate images from multiple models simultaneously, with real-time grouped results and automatic retry on failure.

### Image Upscaling
Built-in Lanczos3 super-resolution algorithm — upscale to 4K with one click after generation.

### Video Generation
Supports text-to-video, image-to-video, keyframe interpolation, and multiple duration options.

### Frosted Glass UI
Sci-fi frosted glass design with 8 themes — switch instantly.

### Media Library
Unified management for local images and videos with batch download, delete, and rename.

---

## Screenshots

### Generation Workspace

Three-column layout: Model Selection | Real-time Preview | Prompt Input

![Generate Page](screenshots/sanitized/02-generate-t2i.png)

<details>
<summary>More generation modes</summary>

| Image-to-Image | Variation |
|----------------|-----------|
| ![Image-to-Image](screenshots/sanitized/03-generate-i2i.png) | ![Variation](screenshots/sanitized/04-generate-variation.png) |

</details>

---

### Video Generation

Supports text-to-video, image-to-video, and keyframe modes

![Video Page](screenshots/sanitized/05-video-t2v.png)

<details>
<summary>More video modes</summary>

| Image-to-Video | Keyframes | Advanced Options |
|----------------|-----------|------------------|
| ![Image-to-Video](screenshots/sanitized/06-video-i2v.png) | ![Keyframes](screenshots/sanitized/07-video-keyframes.png) | ![Advanced](screenshots/sanitized/08-video-advanced.png) |

</details>

---

### Media Library

Unified management for locally generated images and videos

![Media Library](screenshots/sanitized/09-gallery-images.png)

---

### Settings

| Provider Management | Theme Switching | Log Viewer |
|---------------------|-----------------|------------|
| ![Provider](screenshots/sanitized/12-modal-provider.png) | ![Theme](screenshots/sanitized/13-modal-theme.png) | ![Log](screenshots/sanitized/14-modal-log.png) |

---

## Quick Start

### Requirements

- Python 3.10+ (local deployment)
- Or Docker (container deployment)
- Windows / macOS / Linux

### Installation

**Step 1: Clone the repo**

```bash
git clone -b feat/glass-ui-redesign https://github.com/liwei9745/GenBox.git
cd GenBox
```

**Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 3: Configure API**

Option A: Web interface (recommended)

Start the server, then open Provider Management in the browser to fill in API URLs and keys.

Option B: Environment variables

```bash
cp .env.example .env
# Edit .env to add your API keys
```

Both methods sync automatically — use either one.

**Step 4: Start**

```bash
python main.py
```

Browser opens automatically at `http://localhost:8891`

---

### Docker Deployment

No Python or dependencies needed — one command to start:

**Option A: docker-compose (recommended)**

```bash
git clone -b feat/glass-ui-redesign https://github.com/liwei9745/GenBox.git
cd GenBox
cp .env.example .env
# Edit .env to add API keys
docker-compose up -d
```

**Option B: Direct run**

```bash
docker build -t genbox .
docker run -d -p 8891:8891 \
  -v ./storage:/app/storage \
  -v ./.env:/app/.env \
  genbox
```

Visit `http://localhost:8891`

---

## Usage

1. On first run, an admin key is generated automatically
2. Click "Provider Management" in the bottom Dock to add your AI models
3. Select model → Enter prompt → Click "Generate"
4. Generated images are managed in the Media Library

---

## Supported Model Protocols

| Protocol | Supported Models |
|----------|------------------|
| OpenAI Compatible | GPT Image 2, DALL-E 3, Flux, SD-XL, SD-3, etc. |
| Gemini | gemini-2.0-flash, gemini-3.1-flash, etc. |
| Qwen | qwen3.6-Plus, qwen3.5-Plus, Wanx series |
| Agnes | agnes-image-2.0-flash (image), agnes-video (video) |

---

## Configuration

### API URL Configuration

In the Web interface's Provider Management, you can:

- Configure multiple endpoints per model (automatic round-robin failover)
- Configure multiple API Keys per endpoint (automatic round-robin rate-limit handling)
- Configure HTTP/SOCKS5 proxy

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GPT_IMAGE_API_KEY` | OpenAI / GPT Image API Key |
| `GPT_IMAGE_BASE_URL` | API URL, default `https://api.openai.com/v1` |
| `GEMINI_API_KEY` | Google Gemini API Key |
| `QWEN_API_KEY` | Qwen (通义千问) API Key |
| `AGNES_API_KEY` | Agnes AI API Key |
| `LLM_API_KEY` | LLM for prompt optimization (optional) |
| `APP_MODE` | `dev` (no auth) or `prod` (admin key required) |

---

## Tech Stack

- Backend: Python + FastAPI
- Frontend: Vanilla HTML/CSS/JS (Frosted Glass UI)
- AI Interface: OpenAI-compatible protocol
- Image Processing: Pillow (Lanczos3 upscaling)

---

## Community

QQ Group: 1005859624

Welcome to share usage tips and feedback issues!

---

## License

MIT
