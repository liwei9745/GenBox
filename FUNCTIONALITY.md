# GenBox Frontend Functionality Document

Complete reference for `static/index.html` — all features, API endpoints, HTML elements, state variables, and function dependencies.

---

## Table of Contents

1. [Global Architecture](#1-global-architecture)
2. [Authentication & Security](#2-authentication--security)
3. [Navigation System](#3-navigation-system)
4. [Dashboard (系统看板)](#4-dashboard-系统看板)
5. [Image Generation (生图)](#5-image-generation-生图)
6. [Video Generation (生视频)](#6-video-generation-生视频)
7. [Gallery (媒体库)](#7-gallery-媒体库)
8. [History (历史记录)](#8-history-历史记录)
9. [Provider Management Modal](#9-provider-management-modal)
10. [Image Settings Panel](#10-image-settings-panel)
11. [Quick Prompts System](#11-quick-prompts-system)
12. [LLM Prompt Optimization](#12-llm-prompt-optimization)
13. [Lightbox](#13-lightbox)
14. [Compare Mode](#14-compare-mode)
15. [Theme System](#15-theme-system)
16. [Log Viewer](#16-log-viewer)
17. [Setup Wizard & Welcome Page](#17-setup-wizard--welcome-page)
18. [Drag-to-Resize Panels](#18-drag-to-resize-panels)
19. [Utility Functions](#19-utility-functions)
20. [Complete API Endpoint Reference](#20-complete-api-endpoint-reference)

---

## 1. Global Architecture

### Tech Stack
- **Frontend**: Single-page HTML + inline CSS + inline JS (no build system)
- **CSS**: Tailwind CSS via CDN + extensive custom CSS variables
- **Layout**: Flexbox-based app shell with sidebar + main content area

### State Variables

| Variable | Type | Purpose |
|---|---|---|
| `allProviders` | `Array<Object>` | All providers loaded from API |
| `selectedProviders` | `Array<string>` | IDs of selected image providers for generation |
| `currentMode` | `string` | `'t2i'` \| `'i2i'` \| `'variation'` |
| `uploadedImageData` | `string\|null` | Base64 data URL for i2i mode reference image |
| `variationImageData` | `string\|null` | Base64 data URL for variation mode source image |
| `continuousSessionId` | `string\|null` | Session ID for continuous generation mode |
| `currentResults` | `Object` | Latest generation results for lightbox/compare |
| `currentGroupTimings` | `Object` | Per-provider timing data `{pid: {total, images: []}}` |
| `quickPrompts` | `Object` | Rendered quick prompt categories |
| `providerQuantities` | `Object` | Per-provider image quantity `{provider_id: int}` |
| `previewImages` | `Array<Object>` | Current preview results `[{pid, src, name, color, seq, fname, realPid}]` |
| `previewIndex` | `number` | Current index in preview viewer |
| `previewGroups` | `Object` | Grouped preview `{realPid: [previewImage, ...]}` |
| `failedGroups` | `Object` | Failed results `{realPid: [{pid, error, seq}]}` |
| `lightboxZoom` | `number` | Current lightbox zoom level |
| `lightboxCurrentPrompt` | `string` | Prompt text shown in lightbox |
| `galleryItems` | `Array<Object>` | Full gallery data |
| `selectedGalleryItems` | `Array<string>` | IDs of selected gallery items |
| `allGalleryIds` | `Array<string>` | All gallery item IDs |
| `gallerySelectMode` | `boolean` | Whether gallery is in selection mode |
| `activeMediaTab` | `string` | `'image'` \| `'video'` |
| `allHistoryItems` | `Array<Object>` | Full history data |
| `promptMode` | `string` | `'newbie'` \| `'pro'` |
| `genPollTimer` | `Interval\|null` | Image generation polling timer |
| `genCurrentGenId` | `string\|null` | Current generation task ID |
| `genDisplayedResults` | `Object` | Already-displayed results to avoid duplication |
| `genStartTs` | `number` | Generation start timestamp |
| `genTimerInterval` | `Interval\|null` | Elapsed time display timer |
| `genProviderCollapsed` | `Object` | Collapsed state of per-provider progress groups |
| `llmPreviewData` | `Object\|null` | LLM optimization result data |
| `llmOriginalPrompt` | `string` | Original prompt before LLM optimization |
| `selectedLLMProvider` | `string` | Selected LLM provider ID |
| `currentLogCategory` | `string` | Current log filter category |
| `THEME_PRESETS` | `Array<Object>` | 8 theme preset definitions |
| `providerEditOpenIdx` | `number` | Index of expanded provider in edit modal |
| `videoProviders` | `Array<Object>` | Video-type providers |
| `currentVideoMode` | `string` | `'ti2vid'` \| `'i2vid'` \| `'keyframes'` |
| `videoImageRole` | `string` | `'first_frame'` \| `'reference'` \| `'first_last'` \| `'last_frame'` |
| `videoImages` | `Array<string>` | Base64 images for video i2v mode |
| `kfImages` | `Array<string>` | Base64 keyframe images |
| `videoPollTimer` | `Interval\|null` | Video polling timer |
| `videoElapsedTimer` | `Interval\|null` | Video elapsed time timer |
| `videoStartTime` | `number` | Video generation start timestamp |
| `currentVideoTaskId` | `string\|null` | Current video task ID |
| `videoHistoryItems` | `Array<Object>` | Session video list |
| `selectedVideoProviderIds` | `Array<string>` | Multi-provider selection for video |
| `videoPreviewGroups` | `Object` | Video grouped preview `{provider_id: [task, ...]}` |
| `videoGroupNavIdx` | `Object` | Video group navigation index `{provider_id: int}` |
| `videoActivePollTasks` | `Object` | Active polling tasks `{task_id: {provider_id, ...}}` |
| `videoGlobalSettings` | `Object` | `{size, fps, frames, customW, customH, steps, seed}` |
| `dragProviderId` | `string\|null` | Image provider being dragged |
| `videoDragProviderId` | `string\|null` | Video provider being dragged |
| `_adminKey` | `string` | Admin authentication key (from localStorage) |

---

## 2. Authentication & Security

### Functions

| Function | Purpose |
|---|---|
| `_authFetch(url, opts)` | Wraps `fetch()` with `X-Admin-Key` header; redirects to login on 401 |
| `_showLogin()` | Shows login page overlay |
| `_hideLogin()` | Hides login page overlay |
| `doLogin()` | Validates admin key against `/api/providers`; stores in localStorage on success |
| `_showWelcome(key)` | Shows welcome page with generated key |
| `copyWelcomeKey()` | Copies admin key to clipboard |
| `confirmWelcome()` | Closes welcome page, opens setup wizard |
| `checkSetupWizard()` | Calls `/api/setup/status`; routes to first-run, login, or normal load |
| `closeSetupWizard()` | Closes setup wizard |
| `submitSetupWizard()` | Saves wizard-configured providers via `/api/providers` POST |
| `saveWizardProvider(pid, pname, ptype, url, key, color)` | Creates/updates a provider during wizard setup |

### HTML Elements

| ID | Purpose |
|---|---|
| `loginPage` | Full-screen login overlay |
| `loginKeyInput` | Password input for admin key |
| `loginError` | Error message display |
| `welcomePage` | First-run welcome overlay |
| `welcomeKeyBox` | Clickable box to copy key |
| `welcomeKeyText` | Display of generated admin key |
| `setupWizard` | Setup wizard overlay |
| `sw_gpt_url`, `sw_gpt_key` | GPT Image provider inputs |
| `sw_gem_url`, `sw_gem_key` | Gemini provider inputs |
| `sw_qwen_url`, `sw_qwen_key` | Qwen provider inputs |
| `sw_agnes_v_url`, `sw_agnes_v_key` | Agnes Video provider inputs |
| `sw_gem_v_url`, `sw_gem_v_key` | Gemini Video provider inputs |
| `sw_qwen_v_url`, `sw_qwen_v_key` | Qwen Video provider inputs |
| `sw_llm_url`, `sw_llm_key` | LLM provider inputs |

### API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/setup/status` | Check if first-run setup needed |
| POST | `/api/setup/first-run` | Generate initial admin key |
| GET | `/api/providers` | Validate admin key (401 = invalid) |

---

## 3. Navigation System

### Function

```js
switchNav(name, el)
```

Toggles visibility of page containers (`pageGenerate`, `pageVideo`, `pageGallery`, `pageHistory`, `pageDashboard`). Updates sidebar active state. Triggers page-specific data loading.

### Sidebar Elements

| ID | Target Page | Click Handler |
|---|---|---|
| `navDashboard` | `pageDashboard` | `switchNav('dashboard', this)` |
| `navGen` | `pageGenerate` | `switchNav('generate', this)` |
| `navVideo` | `pageVideo` | `switchNav('video', this)` |
| `navGallery` | `pageGallery` | `switchNav('gallery', this)` |
| `navHistory` | `pageHistory` | `switchNav('history', this)` |

### Footer Navigation

| Action | Handler |
|---|---|
| 模型设置 | `openProviderModal()` |
| 提示词优化设置 | `openProviderModal('llm')` |
| 主题设置 | `openThemeModal()` |
| 查看日志 | `openLogModal()` |
| 刷新页面 | `location.reload()` |

---

## 4. Dashboard (系统看板)

### Function

```js
loadDashboard()
```

Fetches `/api/dashboard` and renders the entire dashboard HTML dynamically into `#dashboardContent`.

### Sub-features

#### 4.1 Score Display
- **Data source**: `d.score` → `{total, connectivity, config, disk, dependency}`
- **Max values**: connectivity=40, config=30, disk=15, dependency=15
- **Color coding**: ≥80 green, ≥50 amber, <50 red
- Rendered via `_scoreBar(label, value, max, color)`

#### 4.2 System Info
- **Data source**: `d.system` → `{os, arch, machine, hostname, python, uptime_seconds, disk_free_gb, disk_total_gb, disk_pct, gallery_count, gallery_size, video_count, video_size}`
- Rendered via `_infoRow(label, value)`
- Disk usage shown as colored progress bar (green/amber/red based on percentage)

#### 4.3 Stats Cards
- **Data source**: `d.stats` → `{image: {total, success, failed, avg_time}, video: {total, success, failed}}`
- Rendered as 4-card grid via `_dashCard(title, body, accentColor)`

#### 4.4 Provider Groups
- **Function**: `_renderProviderGroups(providers)`
- **Data source**: `d.providers`
- Two-level classification:
  - **Image Models**: 文生图 / 图生图 (all `type=image` providers, i2i if model contains "i2i" or "edit")
  - **Video Models**: 文生视频 / 图生视频 (all `type=video` providers, i2v if model contains "i2v")
  - **LLM Models**: flat list (all `type=llm` providers)
- Provider cards show: status dot (green=enabled, amber=disabled, gray=unconfigured), name, model, status text

#### 4.5 Network Status Bar
- **Function**: `_loadNetStatus()`
- **API**: GET `/api/dashboard/network`
- Tests TCP connectivity to 12 major providers: OpenAI, Gemini, Anthropic, Agnes, Qwen, Zhipu, Volcengine, Baidu, Tencent, Moonshot, DeepSeek, MiniMax
- Renders colored dots with ms latency
- Element: `#netStatusBar`

#### 4.6 Recent Activity Logs
- **Data source**: `d.recent_logs` → `[{category, message, timestamp}]`
- Category icons: generate=🎨, delete=🗑, error=⚠️, system=💻

#### 4.7 Quick Navigation Cards
- 4 cards linking to: 生图, 生视频, 媒体库, 历史

#### 4.8 Server Control
- **Function**: `serverControl(action)`
- **API**: GET `/api/server/control?action=restart|stop`
- Restart: Shows loading page, reloads after 5s
- Stop: Shows "server stopped" page

#### 4.9 Connectivity Test
- **Function**: `runConnectivityTest()`
- **API**: GET `/api/dashboard/connectivity`
- Tests each provider's endpoint, displays response time per provider card
- Element: `#connTestBtn`
- Per-provider elements: `#conn_ms_{pid}`, `#conn_card_{pid}`

### Dashboard HTML Elements

| ID | Purpose |
|---|---|
| `dashboardContent` | Main container for rendered dashboard |
| `netStatusBar` | Network connectivity status bar |
| `connTestBtn` | "一键连通性检测" button |

---

## 5. Image Generation (生图)

### Layout
Three-column layout: `generate-left` (models + settings) | `generate-center` (input + quick prompts) | `generate-preview` (results)

### 5.1 Provider Selection (Left Panel)

#### Function

```js
renderProviderList()
```

Renders `image`-type providers as selectable cards with:
- Color dot, name
- Checkbox (`.provider-check`)
- Model dropdown (filtered by `filterModelsByType(models, 'image')`)
- Drag-and-drop reordering

#### State

| Variable | Purpose |
|---|---|
| `selectedProviders` | Array of selected provider IDs |
| `providerQuantities` | Per-provider quantity `{pid: count}` |

#### Functions

| Function | Purpose |
|---|---|
| `toggleProvider(id)` | Toggle provider selection |
| `updateSelCount()` | Updates `#selCountBadge` count |
| `onImageModelChange(pid, newModel)` | Updates model for a provider |
| `saveAllProviderSettings()` | Saves per-provider settings to localStorage |
| `onProviderDragStart(e, pid, idx)` | Drag start handler |
| `onProviderDragOver(e, pid)` | Drag over handler |
| `onProviderDrop(e, pid)` | Drop handler — reorders providers |
| `resetDragStyle()` | Resets drag visual state |
| `saveProviderOrder()` | Persists order to `localStorage.providerOrder` |
| `loadProviderOrder()` | Restores order from localStorage |

#### HTML Elements

| ID | Purpose |
|---|---|
| `providerList` | Container for provider cards |
| `selCountBadge` | Badge showing selected provider count |

### 5.2 Image Settings Panel

#### Functions

| Function | Purpose |
|---|---|
| `loadModelDropdown()` | Populates `#selModel` with all image provider models + "全局" option |
| `onImageSettingsModelChange()` | Loads settings for selected model |
| `loadImageSettings(modelKey)` | Loads quality/ratio/size/qty from localStorage for a model |
| `saveImageSettings()` | Saves current settings to `localStorage.genbox_image_settings` |
| `setQuality(el, val)` | Sets quality button active state |
| `setQty(el, val)` | Sets quantity button active state |
| `setRatio(el, ratio)` | Sets ratio button + updates size inputs |
| `onSizeInput()` | Updates ratio selection when size inputs change manually |

#### Constants

```js
RATIO_SIZES = {
  '1:1': [1024, 1024], '2:3': [832, 1248], '3:2': [1248, 832],
  '3:4': [896, 1152], '4:3': [1152, 896], '9:16': [768, 1360],
  '16:9': [1360, 768], '21:9': [1536, 656],
  '1:1-2k': [1536, 1536], '16:9-2k': [2048, 1152],
  '9:16-2k': [1152, 2048], '21:9-2k': [2560, 1092],
  '16:9-4k': [4096, 2304], '9:16-4k': [2304, 4096]
}
```

#### HTML Elements

| ID | Purpose |
|---|---|
| `selModel` | Model dropdown (global + per-model) |
| `selQuality` | Hidden input for quality value |
| `selRatio` | Hidden input for ratio value |
| `selQty` | Hidden input for quantity value |
| `qualityBtns` | Quality button group container |
| `qtyBtns` | Quantity button group container |
| `ratioGrid` | Ratio button grid |
| `inputW` | Width input |
| `inputH` | Height input |
| `chkContinuous` | Continuous generation checkbox |
| `chkUpscale` | Post-generation upscale checkbox |
| `upscaleSize` | Upscale target size select |
| `upscaleMethod` | Upscale algorithm select |
| `upscaleOpts` | Upscale options container (shown/hidden) |
| `selStrength` | i2i transformation strength slider |
| `strengthVal` | Displayed strength value |
| `strengthGroup` | Strength slider container (shown only in i2i mode) |

### 5.3 Mode Switching (Text-to-Image / Image-to-Image / Variation)

#### Function

```js
switchSubTab(mode)
```

Switches between `'t2i'`, `'i2i'`, `'variation'`. Toggles panel visibility, shows/hides strength slider and quick prompts card.

#### HTML Elements

| ID | Purpose |
|---|---|
| `subTabT2I` | Text-to-image tab button |
| `subTabI2I` | Image-to-image tab button |
| `subTabVAR` | Variation tab button |
| `panelT2I` | Text-to-image panel |
| `panelI2I` | Image-to-image panel |
| `panelVAR` | Variation panel |

### 5.4 Text-to-Image Input

#### Prompt Modes

```js
setPromptMode(mode) // 'newbie' | 'pro'
getFinalPrompt()    // Returns combined prompt based on mode
```

- **Newbie mode**: Single textarea `#txtPrompt`
- **Pro mode**: System prompt `#txtSysPrompt` + User prompt `#txtUserPrompt`

#### HTML Elements

| ID | Purpose |
|---|---|
| `btnModeNewbie` | Newbie mode button |
| `btnModePro` | Pro mode button |
| `promptNewbie` | Newbie prompt container |
| `promptPro` | Pro prompt container |
| `txtPrompt` | Main prompt textarea |
| `txtSysPrompt` | System prompt textarea (pro mode) |
| `txtUserPrompt` | User prompt textarea (pro mode) |

### 5.5 Image-to-Image Input

#### Functions

| Function | Purpose |
|---|---|
| `handleFileSelect(e)` | File input change handler |
| `handleFile(f)` | Validates + reads image file as base64 |
| `handleFileSelectVar(e)` | Variation mode file handler |
| `handleFileVar(f)` | Reads variation source image |

#### HTML Elements

| ID | Purpose |
|---|---|
| `uploadZone` | Drag-and-drop zone for i2i |
| `fileInput` | Hidden file input for i2i |
| `uploadPreview` | Preview image for uploaded reference |
| `txtPromptI2I` | Modification prompt textarea |

### 5.6 Variation Mode

#### HTML Elements

| ID | Purpose |
|---|---|
| `uploadZoneVar` | Drag-and-drop zone for variation |
| `fileInputVar` | Hidden file input for variation |
| `uploadPreviewVar` | Preview image for variation source |
| `varSize` | Output size select |
| `varCount` | Generation count select |

### 5.7 Progress Tracking

#### Functions

| Function | Purpose |
|---|---|
| `startGenPolling(genId)` | Starts polling `/api/generate/status/{genId}` every 1.5s |
| `stopGenPolling()` | Clears polling and elapsed timers |
| `renderGenPerProviderBars(providerStates)` | Renders per-provider progress bars with status |
| `toggleGenProviderGroup(name)` | Collapses/expands provider group |
| `genLogProvider(key, msg, type)` | Logs to per-provider mini log |
| `_smartScroll(el)` | Smart auto-scroll (only if near bottom) |

#### State

| Variable | Purpose |
|---|---|
| `genProviderCollapsed` | `{groupName: boolean}` collapse state |
| `window._lastProviderStates` | Cached last provider states for re-render |

#### HTML Elements

| ID | Purpose |
|---|---|
| `progressBox` | Progress section container |
| `progressText` | Progress status text |
| `progressFill` | Main progress bar fill |
| `elapsedSeconds` | Elapsed time display |
| `progressCloseBtn` | Close button (shown after completion) |
| `perProviderSection` | Per-provider progress bars container |
| `genLogWrap` | Real-time log wrapper |
| `genLogArea` | Real-time log output |
| `genLogCount` | Log completion count |

### 5.8 Generation Submission

#### Function

```js
doGenerate()
```

Collects all settings, builds payload, POSTs to `/api/generate`, then calls `startGenPolling()`.

#### Payload Structure

```js
{
  prompt: string,
  providers: string[],
  enhance_prompt: boolean,
  llm_provider_id: string | undefined,
  mode: 't2i' | 'i2i',
  size: string, // e.g. "1024x1024"
  quality: string,
  continuous: boolean,
  system_prompt: string | null,
  continuous_id: string | null,
  quantities: { provider_id: number },
  image_data: string, // base64, only for i2i
  strength: number, // 0.1-0.95, only for i2i
  upscale_to: string, // e.g. "2048x2048", if upscale enabled
  upscale_method: string // "lanczos3" | "bicubic" | "nearest"
}
```

#### API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/generate` | Submit generation task |
| GET | `/api/generate/status/{genId}` | Poll generation status |

### 5.9 Variation Submission

#### Function

```js
doVariation()
```

Submits variation via `/api/images/variations`.

#### Payload

```js
{
  image_data: string, // base64
  provider_id: string,
  size: string, // "1024x1024" | "512x512" | "256x256"
  n: number // 1-4
}
```

#### API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/images/variations` | Submit variation task |

### 5.10 Results Preview

#### Functions

| Function | Purpose |
|---|---|
| `showResults(results, prompt, timings)` | Renders complete results with grouped cards |
| `addResultToPreview(key, result)` | Adds single result incrementally during polling |
| `renderGroupedPreview(container)` | Renders grouped preview with per-group navigation |
| `renderPreviewViewer(container)` | Renders single-image preview with thumbnails |
| `groupNav(rp, dir)` | Navigate within a provider group |
| `renderGroupThumbs(rp, groupImgs, activeIdx, color)` | Updates thumbnail active state |
| `previewPrev()` / `previewNext()` | Global preview navigation |
| `findProvider(pid)` | Finds provider by ID (with `_N` suffix fallback) |
| `getProviderDisplayName(pid)` | Returns display_name or name |

### 5.11 Model Filtering

#### Functions

| Function | Purpose |
|---|---|
| `filterModelsByType(models, providerType)` | Filters models by type (`image`/`video`/`llm`) |
| `groupImageModels(models)` | Groups image models by category (Imagen, Gemini variants, etc.) |
| `groupVideoModels(models)` | Groups video models by category (T2V, I2V, R2V, etc.) |
| `buildModelOptsGrouped(models, selectedModel, groupFn)` | Builds `<optgroup>` HTML |

---

## 6. Video Generation (生视频)

### Layout
Same three-column layout as image generation.

### 6.1 Video Provider Cards

#### Functions

| Function | Purpose |
|---|---|
| `loadVideoProviders()` | Fetches `/api/providers`, filters `type=video` |
| `renderVideoProviderCards()` | Renders selectable provider cards with model dropdowns |
| `toggleVideoProvider(vpid)` | Toggles video provider selection |
| `updateVideoGenerateButton()` | Updates button text/disabled state |
| `onVideoModelChange(event)` | Auto-adjusts recommended settings based on model |
| `refreshProviderModels(vpid)` | Fetches models from provider's `models_url` |

#### Drag Reorder

| Function | Purpose |
|---|---|
| `onVideoProviderDragStart(e, pid)` | Drag start |
| `onVideoProviderDragOver(e, pid)` | Drag over |
| `onVideoProviderDrop(e, pid)` | Drop — reorders |
| `resetVideoDragStyle()` | Reset drag styles |

#### State

| Variable | Purpose |
|---|---|
| `selectedVideoProviderIds` | Array of selected video provider IDs |
| `videoProviders` | All video-type providers |

#### HTML Elements

| ID | Purpose |
|---|---|
| `videoProviderCards` | Container for video provider cards |
| `videoGenBtn` | Generate button |

### 6.2 Video Settings (Left Panel)

#### HTML Elements

| ID | Purpose |
|---|---|
| `videoSize` | Size preset dropdown |
| `videoCustomSize` | Custom size input container |
| `videoCustomW` | Custom width input |
| `videoCustomH` | Custom height input |
| `videoFrames` | Frame count input |
| `videoFPS` | FPS dropdown |
| `videoSteps` | Inference steps input (advanced) |
| `videoSeed` | Seed input (advanced) |
| `videoNegPrompt` | Negative prompt input (advanced) |
| `videoAdvanced` | Advanced options container |
| `videoAdvChevron` | Chevron for advanced toggle |

#### Functions

| Function | Purpose |
|---|---|
| `onVideoSizeChange()` | Shows/hides custom size inputs |
| `getVideoDimensions()` | Returns `{width, height}` from current selection |
| `setVideoDuration(frames, fps, el)` | Sets duration preset buttons |
| `toggleVideoAdvanced()` | Toggles advanced options visibility |

### 6.3 Video Sub-tabs

```js
switchVideoSubTab(mode) // 'ti2vid' | 'i2vid' | 'keyframes'
```

| Tab | Panel | Purpose |
|---|---|---|
| 文生视频 | (none) | Text-to-video |
| 图生视频 | `videoI2VPanel` | Image-to-video |
| 关键帧 | `videoKeyframesPanel` | Keyframe interpolation |

#### Image Role Selection

```js
setVideoImageRole(role, el) // 'first_frame' | 'reference' | 'first_last' | 'last_frame'
```

#### Image Upload (i2v)

| Function | Purpose |
|---|---|
| `handleVideoFileSelect(evt)` | File input handler |
| `handleVideoDrop(evt)` | Drag-and-drop handler |
| `readVideoImageFile(file)` | Reads file as base64, adds to `videoImages` |
| `renderVideoImagePreview()` | Renders image thumbnails with remove buttons |
| `removeVideoImage(idx)` | Removes image from array |

#### Keyframe Upload

| Function | Purpose |
|---|---|
| `handleKfFileSelect(evt)` | File input handler |
| `handleKfDrop(evt)` | Drag-and-drop handler |
| `readKfImageFile(file)` | Reads file, adds to `kfImages` |
| `renderKfImagePreview()` | Renders keyframe thumbnails |
| `removeKfImage(idx)` | Removes keyframe |

#### Pick from Gallery

| Function | Purpose |
|---|---|
| `openVideoPreviewPicker()` | Fetches `/api/preview/images` |
| `showVideoImagePickerModal(items)` | Creates temporary modal for image selection |

#### HTML Elements

| ID | Purpose |
|---|---|
| `videoI2VPanel` | i2v upload panel |
| `videoKeyframesPanel` | keyframe upload panel |
| `videoUploadZone` | i2v drag zone |
| `videoFileInput` | i2v file input |
| `videoImagePreview` | i2v image preview container |
| `kfFileInput` | keyframe file input |
| `kfImagePreview` | keyframe preview container |

### 6.4 Video Generation Submission

```js
startVideoGenerate()
```

Submits tasks sequentially to each selected provider via `/api/video/generate`.

#### Payload

```js
{
  prompt: string,
  provider_id: string,
  model: string,
  mode: 'ti2vid' | 'i2vid' | 'keyframes',
  width: number,
  height: number,
  num_frames: number, // must be 8n+1
  frame_rate: number,
  image: string[], // base64 array, only for i2vid/keyframes
  image_role: string, // only for i2vid
  num_inference_steps: number | null,
  seed: number | null,
  negative_prompt: string | null
}
```

#### API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/video/generate` | Submit video generation task |
| GET | `/api/video/status/{taskId}` | Poll video task status |

### 6.5 Video Progress & Polling

#### Functions

| Function | Purpose |
|---|---|
| `startVideoPolling(tasks, startTime)` | Polls all submitted tasks |
| `startVideoElapsedTimer()` | Updates elapsed display every 1s |
| `stopVideoElapsedTimer()` | Clears elapsed timer |
| `videoLog(msg, type)` | Logs to video log area |
| `videoLogProvider(providerId, msg, type)` | Logs to per-provider mini log |
| `clearVideoLog()` | Clears log areas |
| `renderVideoPerProviderBars()` | Renders per-provider progress bars |

#### HTML Elements

| ID | Purpose |
|---|---|
| `videoProgressBar` | Progress bar wrapper |
| `videoProgressFill` | Progress bar fill |
| `videoProgressText` | Progress percentage text |
| `videoElapsed` | Elapsed time display |
| `videoTaskStatus` | Task status text |
| `videoResultCount` | Result count text |
| `videoLogWrap` | Video log wrapper |
| `videoLogArea` | Video log output |
| `videoPerProviderSection` | Per-provider progress container |

### 6.6 Video Results Preview

#### Functions

| Function | Purpose |
|---|---|
| `renderVideoGroupedPreview()` | Renders grouped video results with thumbnails |
| `renderVideoHistory()` | Renders session video history list |

#### HTML Elements

| ID | Purpose |
|---|---|
| `videoPreviewEmpty` | Empty state placeholder |
| `videoPreviewResults` | Grouped preview results container |
| `videoHistoryList` | Session video history list |

### 6.7 Video Provider Capability Detection

```js
getVideoProviderCapabilities(p) // Returns {t2v, i2v, keyframes, ...}
isModelMatchMode(modelName, mode) // Checks if model supports given mode
```

Capabilities derived from:
1. `p.model_capabilities` (from API)
2. Model name pattern matching (`t2v`, `i2v`, `r2v`, `interpolation`, `veo_`)

---

## 7. Gallery (媒体库)

### Functions

| Function | Purpose |
|---|---|
| `loadGallery()` | Fetches `/api/gallery?limit=80`, saves to `galleryItems`, renders |
| `switchMediaTab(type)` | Switches between `'image'` and `'video'` tabs |
| `renderGalleryItems(items)` | Applies filters/sort, renders grid |
| `applyGallerySort()` | Triggers re-render with current sort |
| `applyMediaFilters()` | Triggers re-render with current filters |
| `updateGalleryProviderFilter()` | Populates provider filter dropdown |

### Filtering & Sorting

| Control | ID | Purpose |
|---|---|---|
| Sort | `gallerySortBy` | Sort by time/provider/prompt |
| Provider filter | `galleryProviderFilter` | Filter by provider |
| Search | `gallerySearchInput` | Search by prompt text |

### Selection Mode

| Function | Purpose |
|---|---|
| `toggleGallerySelectMode()` | Toggles select mode on/off |
| `selectAllGallery()` | Selects all visible items |
| `deselectAllGallery()` | Deselects all |
| `toggleGalleryItem(id, el)` | Toggles individual item selection |
| `updateGallerySelectionUI()` | Updates count badges and visual selection |
| `showGalleryToolbar(show)` | Shows/hides batch action buttons |

### Batch Operations

| Function | API | Purpose |
|---|---|---|
| `batchDownloadGallery()` | POST `/api/gallery/batch-download` | Downloads selected as ZIP |
| `deleteSelectedGallery()` | POST `/api/gallery/batch-delete` | Deletes selected items |

### Rename & Push

| Function | API | Purpose |
|---|---|---|
| `galleryStartRename()` | POST `/api/gallery/rename` | Renames single selected item |
| `pushGalleryToReference()` | GET `/api/gallery/image/{fname}/base64` | Pushes image to i2i reference |

### Video Hover Preview

```js
initVideoHoverPreview() // Binds mouseenter/mouseleave on gallery grid
```

On hover over video card: loads `<video>` from `data-src`, plays muted preview after 350ms delay.

### Click Handlers

| Mode | Handler | Purpose |
|---|---|---|
| Image (normal) | `openLightboxFromGallery(id)` | Opens lightbox |
| Image (select) | `toggleGalleryItem(id, el)` | Toggles selection |
| Video (normal) | `playVideoFromGallery(id)` | Opens video in lightbox |
| Video (select) | `toggleGalleryItem(id, el)` | Toggles selection |

### HTML Elements

| ID | Purpose |
|---|---|
| `pageGallery` | Gallery page container |
| `mediaTabImage` | Image tab button |
| `mediaTabVideo` | Video tab button |
| `gallerySortBy` | Sort dropdown |
| `galleryProviderFilter` | Provider filter dropdown |
| `gallerySearchInput` | Search input |
| `galleryGrid` | Main gallery grid |
| `btnGallerySelect` | Select mode toggle button |
| `btnSelAll` | Select all button |
| `btnSelNone` | Deselect all button |
| `btnGalleryRename` | Rename button |
| `btnPushToRef` | Push to i2i reference button |
| `btnDlSelected` | Batch download button |
| `btnDelSelected` | Batch delete button |
| `dlGalleryCount` | Download count badge |
| `selGalleryCount` | Selection count badge |

---

## 8. History (历史记录)

### Functions

| Function | Purpose |
|---|---|
| `loadHistory()` | Fetches `/api/history` with filters, renders list |
| `updateHistoryFilterProviders()` | Populates provider filter from history data |

### Filtering

| Control | ID | Purpose |
|---|---|---|
| Search | `historySearch` | Search by prompt text |
| Provider | `historyFilterProvider` | Filter by provider |
| Mode | `historyFilterMode` | Filter by mode (t2i/i2i) |
| Sort | `historySortBy` | Sort by time ascending/descending |

### API

| Method | Endpoint | Query Params |
|---|---|---|
| GET | `/api/history` | `limit`, `search`, `provider`, `mode` |

### HTML Elements

| ID | Purpose |
|---|---|
| `pageHistory` | History page container |
| `historySearch` | Search input |
| `historyFilterProvider` | Provider filter dropdown |
| `historyFilterMode` | Mode filter dropdown |
| `historySortBy` | Sort dropdown |
| `historyList` | History items container |

---

## 9. Provider Management Modal

### Functions

| Function | Purpose |
|---|---|
| `openProviderModal(type?)` | Opens modal, optionally scrolls to a type group |
| `closeProviderModal()` | Closes modal |
| `renderProviderEdit()` | Full render of provider edit UI (3-column grid + proxy section) |
| `toggleProviderEdit(idx)` | Expands/collapses provider editor |
| `saveProvider(idx)` | Saves provider via POST `/api/providers` |
| `deleteProvider(id)` | Deletes provider via DELETE `/api/providers/{id}` |
| `testProvider(id)` | Tests provider via GET `/api/providers/test/{id}` |
| `fetchModels(idx)` | Fetches models via GET `/api/providers/fetch-models/{id}` |
| `reloadProviders()` | Reloads config via POST `/api/providers/reload` |
| `addEndpoint(idx)` | Adds new endpoint row |
| `removeEndpoint(idx, ei)` | Removes endpoint row |
| `collectEndpoints(idx)` | Collects endpoint data from DOM |

### Provider Card UI

Each provider card shows:
- Color picker (inline)
- Name input
- Type selector (image/video/llm)
- Display name input
- Provider ID (readonly if existing)
- Base URL input
- API Key input
- Multi-key textarea (api_keys, one per line)
- Key pool status display (available/total, cooldown timers)
- Multi-endpoint section (name, URL, key, enabled toggle per endpoint)
- Model dropdown + "拉取" button
- Enable checkbox
- Save / Test / Delete buttons

### Endpoint Management

Each endpoint has:
- Name input
- Enabled checkbox
- URL input
- API Key input
- Remove button

Data collected via `collectEndpoints(idx)` which reads `data-ep-idx` and `data-field` attributes.

### HTML Elements

| ID | Purpose |
|---|---|
| `providerModal` | Modal overlay |
| `providerEditBody` | Modal body content |
| `addProviderTypeModal` | Type selection modal (image/video/llm) |

### Add Provider Type Modal

| Function | Purpose |
|---|---|
| `openAddProviderTypeModal()` | Opens type selection |
| `closeAddProviderTypeModal()` | Closes type selection |
| `addProviderWithType(type)` | Creates empty provider of type, opens editor |

### API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/providers` | List all providers |
| POST | `/api/providers` | Create/update provider |
| DELETE | `/api/providers/{id}` | Delete provider |
| POST | `/api/providers/reload` | Reload config from disk |
| GET | `/api/providers/test/{id}` | Test provider connectivity |
| GET | `/api/providers/fetch-models/{id}` | Fetch available models |

---

## 10. Image Settings Panel

### Per-Provider Settings

Each provider card in the generation panel can have independent settings:

#### Functions

| Function | Purpose |
|---|---|
| `setProviderRatio(pid, ratio, el)` | Sets per-provider ratio |
| `setProviderQuality(pid, val, el)` | Sets per-provider quality |
| `adjustProviderQty(pid, delta)` | Adjusts per-provider quantity (+/-) |
| `onProviderSizeChange(pid)` | Handles manual size input |
| `saveProviderSetting(pid, key, val)` | Saves to `localStorage.genbox_provider_settings` |
| `loadProviderSettings()` | Loads from localStorage |
| `buildRatioBtns(pid, activeRatio)` | Builds per-provider ratio buttons |

### Size Inference

```js
inferSize(prompt)
```

Infers image size from prompt keywords:
- Wide keywords → `1792x1024`
- Tall keywords → `1024x1792`
- Portrait keywords → `1536x1024`
- Default → `1024x1024`

---

## 11. Quick Prompts System

### Constants

```js
QUICK_PROMPTS = {
  "🎬 风格": [...], // 8 prompts
  "👘 古风": [...], // 5 prompts
  "🌿 自然": [...], // 5 prompts
  "🏙 建筑": [...], // 5 prompts
  "🎭 人像": [...], // 5 prompts
  "🚀 科幻": [...]  // 5 prompts
}
```

Each entry: `{label: "Chinese name", en: "English prompt text"}`

### Functions

| Function | Purpose |
|---|---|
| `renderQuickPrompts()` | Renders all categories with collapsible sections |
| `toggleQuickSection(header)` | Toggles section open/closed |
| `filterQuickPrompts(query)` | Filters tags by search text (label + English) |
| `insertQuickPrompt(btn)` | Appends prompt to current textarea |

### HTML Elements

| ID | Purpose |
|---|---|
| `quickArea` | Quick prompts container |
| `quickCard` | Quick prompts card (hidden in i2i/variation mode) |
| `quickSearch` | Search input for quick prompts |

---

## 12. LLM Prompt Optimization

### LLM Settings Modal

| Function | Purpose |
|---|---|
| `openLLMSettings()` | Opens LLM modal |
| `closeLLMModal()` | Closes LLM modal |
| `loadLLMProviders()` | Fetches LLM-type providers |
| `selectLLMProvider(id)` | Sets selected LLM provider in localStorage |

#### HTML Elements

| ID | Purpose |
|---|---|
| `llmModal` | LLM settings modal |
| `llmProviderList` | LLM provider card list |

### LLM Preview Optimization

| Function | Purpose |
|---|---|
| `previewLLMOptimize()` | Calls `/api/llm/optimize` for preview |
| `insertLLMPreview()` | Inserts optimized prompt into textarea |
| `closeLLMPreview()` | Closes preview box |
| `undoLLMOptimize()` | Reverts to original prompt |

### Enhancement Result Display

| Function | Purpose |
|---|---|
| `showEnhanceResult(text)` | Shows enhancement result box |
| `hideEnhance()` | Hides enhancement result |
| `insertEnhance()` | Inserts enhanced text into prompt |
| `copyEnhance()` | Copies enhanced text to clipboard |

#### API

| Method | Endpoint | Payload |
|---|---|---|
| POST | `/api/llm/optimize` | `{prompt, llm_provider_id}` |

#### HTML Elements

| ID | Purpose |
|---|---|
| `chkEnhance` | Enable LLM optimization checkbox |
| `btnPreviewLLM` | "点击优化" button |
| `btnUndoLLM` | "撤销回退" button |
| `llmPreviewBox` | LLM preview comparison box |
| `llmPreviewOriginal` | Original prompt display |
| `llmPreviewOptimized` | Optimized prompt display |
| `llmPreviewError` | Error message display |
| `enhanceResult` | Enhancement result box |
| `enhanceText` | Enhanced text content |

---

## 13. Lightbox

### Functions

| Function | Purpose |
|---|---|
| `openLightbox(src, label, prompt?)` | Opens lightbox with image/video |
| `closeLightbox(e?)` | Closes lightbox |
| `toggleZoom(e)` | Toggles 1.5x zoom |
| `zoomIn(e)` | Increases zoom by 0.5 |
| `zoomOut(e)` | Decreases zoom by 0.5 |
| `zoomReset(e)` | Resets to 1x |
| `copyLightboxPrompt()` | Copies prompt to clipboard |

### HTML Elements

| ID | Purpose |
|---|---|
| `lightbox` | Lightbox overlay |
| `lightbox-img` | Main image element |
| `lightbox-video` | Video element (hidden by default) |
| `lightbox-controls` | Control buttons row |
| `lightbox-dl` | Download link |
| `lightbox-info` | Label/info text |
| `lightbox-prompt-box` | Prompt display box |
| `lightbox-prompt` | Prompt text content |

### Keyboard Shortcuts

- `Escape`: Close lightbox
- `ArrowLeft` / `ArrowRight`: Navigate preview images

---

## 14. Compare Mode

### Functions

| Function | Purpose |
|---|---|
| `openCompare()` | Opens compare modal with all successful results |
| `openCompareFromLightbox(e)` | Closes lightbox, opens compare |
| `closeCompare()` | Closes compare modal |

### Requirements
- At least 2 successful results in `currentResults`

### HTML Elements

| ID | Purpose |
|---|---|
| `compareModal` | Compare modal overlay |
| `compareItems` | Scrollable container for comparison items |

---

## 15. Theme System

### Theme Presets

8 built-in themes:

| Name | ID | Primary Colors |
|---|---|---|
| 深空蓝 (default) | `default` | `#0c0e14` / `#5b8def` |
| 墨夜 | `midnight` | `#08090c` / `#e2e8f0` |
| 极光 | `aurora` | `#070a08` / `#34d399` |
| 琥珀 | `amber` | `#0c0a07` / `#f59e0b` |
| 赛博 | `cyber` | `#0a0612` / `#a78bfa` |
| 冰川 | `glacier` | `#e8edf2` / `#2563eb` |
| 樱花 | `sakura` | `#120a0e` / `#f472b6` |
| 海洋 | `ocean` | `#041215` / `#38bdf8` |

Each theme defines 14 CSS custom properties.

### Functions

| Function | Purpose |
|---|---|
| `openThemeModal()` | Opens theme modal |
| `closeThemeModal()` | Closes theme modal |
| `renderThemePresets()` | Renders theme cards with preview dots |
| `applyTheme(id)` | Applies theme CSS vars to `:root`, saves to localStorage |

### Storage
- `localStorage.igs_theme` — saved theme ID

### HTML Elements

| ID | Purpose |
|---|---|
| `themeModal` | Theme modal overlay |
| `themePresets` | Theme preset cards container |

---

## 16. Log Viewer

### Functions

| Function | Purpose |
|---|---|
| `openLogModal()` | Opens log modal, loads logs |
| `closeLogModal()` | Closes log modal |
| `filterLog(cat)` | Filters by category |
| `loadLogs()` | Fetches `/api/logs` with category filter |
| `clearLogs()` | Clears all logs via DELETE `/api/logs` |

### Log Categories

| Category | Icon | CSS Class |
|---|---|---|
| generate | 🎨 | `log-cat-generate` |
| delete | 🗑 | `log-cat-delete` |
| provider | 📌 | `log-cat-provider` |
| system | 💻 | `log-cat-system` |
| error | ⚠️ | `log-cat-error` |

### API

| Method | Endpoint | Query Params |
|---|---|---|
| GET | `/api/logs` | `limit`, `category` |
| DELETE | `/api/logs` | (none) |

### HTML Elements

| ID | Purpose |
|---|---|
| `logModal` | Log modal overlay |
| `logBody` | Log entries container |

---

## 17. Setup Wizard & Welcome Page

### Welcome Page Flow

1. `checkSetupWizard()` calls `/api/setup/status`
2. If `needs_first_run`: POST `/api/setup/first-run` → receives `admin_key`
3. Shows welcome page with key display + copy button
4. User clicks "我已保存" → opens setup wizard

### Setup Wizard

3-column layout:
- **生图模型**: GPT Image, Gemini, Qwen (URL + Key inputs)
- **生视频模型**: Agnes Video, Gemini Video, Qwen Video (URL + Key inputs)
- **提示词优化**: LLM (URL + Key inputs, optional)

`submitSetupWizard()` creates providers via POST `/api/providers` for each filled key.

---

## 18. Drag-to-Resize Panels

### Implementation

IIFE-bound mouse event handlers on `.divider-drag` elements.

- `onMouseDown`: Records initial widths of `.generate-left` and `.generate-center`
- `onMouseMove`: Adjusts `leftEl.style.width` based on mouse delta
- `onMouseUp`: Cleans up

Two dividers:
1. Between left panel and center (`data-prev="left" data-next="center"`)
2. Between center and preview (`data-prev="center" data-next="preview"`)

---

## 19. Utility Functions

| Function | Purpose |
|---|---|
| `escHtml(s)` | HTML entity escaping |
| `escAttr(s)` | Attribute value escaping (single/double quotes) |
| `setStatus(msg)` | Updates `#statusLeft` text |
| `_smartScroll(el)` | Auto-scrolls only if user is near bottom (threshold: 80px) |

---

## 20. Complete API Endpoint Reference

### Authentication
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/setup/status` | No | Check first-run status |
| POST | `/api/setup/first-run` | No | Generate admin key |

### Providers
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/providers` | Yes | List all providers |
| POST | `/api/providers` | Yes | Create/update provider |
| DELETE | `/api/providers/{id}` | Yes | Delete provider |
| POST | `/api/providers/reload` | Yes | Reload config from disk |
| GET | `/api/providers/test/{id}` | Yes | Test provider connectivity |
| GET | `/api/providers/fetch-models/{id}` | Yes | Fetch available models |

### Generation
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/generate` | Yes | Submit image generation task |
| GET | `/api/generate/status/{genId}` | Yes | Poll generation status |
| POST | `/api/images/variations` | Yes | Submit variation task |

### Video
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/video/generate` | Yes | Submit video generation task |
| GET | `/api/video/status/{taskId}` | Yes | Poll video task status |

### Gallery
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/gallery` | Yes | List gallery items (params: `limit`) |
| GET | `/api/gallery/image/{filename}` | No | Serve image file |
| GET | `/api/gallery/thumb/{filename}` | No | Serve thumbnail |
| GET | `/api/gallery/image/{filename}/base64` | Yes | Get image as base64 JSON |
| POST | `/api/gallery/batch-delete` | Yes | Batch delete items |
| POST | `/api/gallery/batch-download` | Yes | Batch download as ZIP |
| POST | `/api/gallery/rename` | Yes | Rename gallery item |

### Dashboard
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/dashboard` | Yes | Full dashboard data |
| GET | `/api/dashboard/network` | Yes | Network connectivity test |
| GET | `/api/dashboard/connectivity` | Yes | Provider connectivity test |

### History
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/history` | Yes | List history (params: `limit`, `search`, `provider`, `mode`) |

### Logs
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/logs` | No | List logs (params: `limit`, `category`) |
| DELETE | `/api/logs` | No | Clear all logs |

### LLM
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/llm/optimize` | Yes | Optimize prompt via LLM |

### Proxy
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/proxy` | Yes | Get proxy configuration |
| POST | `/api/proxy` | Yes | Save proxy configuration |
| POST | `/api/proxy/test` | Yes | Test proxy connectivity |

### Server
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/server/control` | Yes | Restart/stop server (param: `action`) |

### Preview
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/preview/images` | Yes | Get images for picker (returns base64) |

---

## localStorage Keys

| Key | Purpose |
|---|---|
| `igs_admin_key` | Admin authentication key |
| `igs_theme` | Selected theme ID |
| `igs_llm_provider` | Selected LLM provider ID |
| `igs_models_{pid}` | Cached model list per provider |
| `genbox_image_settings` | Per-model image settings (quality, ratio, size, qty) |
| `genbox_provider_settings` | Per-provider settings (w, h, quality, ratio, qty) |
| `providerOrder` | Image provider display order |
