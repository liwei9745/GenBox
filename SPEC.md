# Spec: GenBox Frontend Rewrite — Apple MAC Style

## Objective

Rewrite the GenBox frontend as a clean, modular Apple MAC-style SPA. All 213 functions and 30+ API endpoints from the original must be preserved. The new UI uses glassmorphism, SF Pro typography, Mac Dock navigation, and macOS-style modals.

## Design System

### Colors (Light/Dark)
- Light: `#f5f5f7 → #e8e8ed` gradient, `#ffffff` cards, `#007AFF` accent
- Dark: `#1c1c1e → #2c2c2e` gradient, `#3a3a3c` cards, `#0A84FF` accent
- Glass: `rgba(255,255,255,0.72)` bg, `blur(20px)`, `1px solid rgba(0,0,0,0.08)` border

### Typography
- Font: SF Pro Display / -apple-system / BlinkMacSystemFont / Inter
- Sizes: 10-48px scale
- Weights: 300-800

### Components
- `.glass-card` — Rounded corners (14px), glass background, subtle shadow
- `.glass-panel` — Modal content panel
- `.glass-overlay` — Modal backdrop with blur
- `.btn` / `.btn-primary` / `.btn-secondary` / `.btn-ghost` — Pill-shaped buttons
- `.dock` — Bottom Mac Dock with magnification
- `.sub-tab` — Pill-shaped tab switcher
- `.provider-card` — Provider selection card
- `.bubble` — Rounded bubble component

### Animations
- Spring elastic: scale 0.95 → 1.02 → 1
- Fade-in-up: translateY(12px) → 0
- Dock hover: scale 1.25, spring cubic-bezier(0.34, 1.56, 0.64, 1)

## Layout

### App Shell
```
┌─────────────────────────────────────┐
│           App Content               │
│  ┌───────┬───────────┬───────────┐  │
│  │ Left  │  Center   │  Right    │  │
│  │ Panel │  Panel    │  Panel    │  │
│  └───────┴───────────┴───────────┘  │
│           Status Bar                │
└─────────────────────────────────────┘
         ┌─────────────┐
         │  Mac Dock   │
         └─────────────┘
```

### Pages
1. **Dashboard** — Score cards, system info, provider groups, recent activity, quick nav
2. **Generate** — 3-column: left (settings), center (input), right (preview)
3. **Video** — 3-column: left (video settings), center (input), right (preview)
4. **Gallery** — Grid with tabs (image/video), sort/filter/search, batch ops
5. **History** — List with search/filter/sort

### Modals (glass-overlay + glass-panel)
- Theme settings
- Log viewer
- Provider management
- Add provider type
- LLM settings
- Setup wizard
- Login/Welcome pages
- Lightbox
- Compare mode

## File Structure

```
static/
  index.html          — Pure HTML skeleton (<500 lines)
  css/
    design-system.css — Tokens, reset, typography
    glass.css         — Glassmorphism components
    bubbles.css       — Bubble components
    dock.css          — Mac Dock
    pages.css         — Page-specific styles
    setup.css         — Setup wizard
    animations.css    — Spring elastic, fade-in-up
    utilities.css     — Utility classes
  js/
    app.js            — Core state, utilities, auth, init, dashboard
    providers.js      — Provider CRUD, drag, config modal
    generate.js       — Image gen, polling, results, quick prompts
    video.js          — Video gen, polling, history
    gallery.js        — Gallery, lightbox, batch ops, history
    modals.js         — Theme, log, compare modals
    navigation.js     — Dock nav, page switching
    theme.js          — Light/dark toggle
```

## Implementation Order

### Slice 1: Foundation
- CSS design system (tokens, reset, glass, dock, animations)
- HTML skeleton with all IDs
- Core JS (state, auth, navigation, theme)

### Slice 2: Dashboard
- Score cards, system info, provider groups
- Network status bar
- Recent activity, quick nav
- Server control, connectivity test

### Slice 3: Provider Management
- Provider list with edit/toggle/delete
- Add provider (type selection)
- Provider endpoints, test, fetch models
- Proxy config, drag reorder

### Slice 4: Image Generation
- Provider selection, image settings
- T2I, I2I, variation modes
- Quick prompts, LLM optimization
- Progress tracking, results preview

### Slice 5: Video Generation
- Video provider cards
- T2V, I2V, keyframes modes
- Video settings, progress, history

### Slice 6: Gallery & History
- Image/video tabs, sort/filter/search
- Select mode, batch ops
- Lightbox, compare
- History list

### Slice 7: Modals & Polish
- Theme settings, log viewer
- Setup wizard, login/welcome
- Final testing and polish

## Verification

After each slice:
1. Check browser console for errors
2. Test all interactive elements
3. Verify API calls work
4. Check light/dark mode
5. Test responsive layout

## Commands

- Start server: `python main.py` (from E:\AI\GenBox-od)
- Access: http://localhost:8891
- API test: `Invoke-RestMethod http://localhost:8891/api/dashboard`
