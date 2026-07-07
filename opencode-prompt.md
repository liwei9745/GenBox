## 硬重置 + 重新打磨 Apple 风格

先执行清理，再精修视觉效果。

### 立即执行：清理旧代码

STOP 所有进行中的工作。

执行以下操作后给我确认：

1. 从 `static/index.html` 的 `<style>` 标签中删除所有旧的 CSS 变量声明 (`:root { --bg-base: ... }` 那段) — 这些已由 `design-system.css` 接管
2. 删除旧的布局 CSS（`.app-shell`, `.sidebar`, `.main-content`, `.content-header`, `.content-scroll`, `.generate-layout`, `.provider-card` 等所有在 `<style>` 里的旧样式）— 这些已由 `pages.css` 接管
3. 从 `<head>` 中删除 `tailwindcss` CDN 脚本 — 不再需要，有冲突
4. 从 index.html 中删除 `<nav class="sidebar">...</nav>` 整个侧边栏 HTML 块（约第1430行附近）
5. 删除所有灯箱 (lightbox)、对比模式、Provider 设置弹窗、登录页、设置向导、LLM 弹窗等弹窗的旧内联样式（`style=""` 属性），改为使用新 CSS 类
6. 删除 `<style>` 中所有 `.sw-card`, `.sw-input`, `.sw-type-btn` 等设置向导样式 — 这些已由 `setup.css` 接管
7. 删除所有未拆分的旧内联 `<script>` 内容（约1200-7130行）— 只用外链 JS 文件

### 然后：精修毛玻璃效果

用 glass.css 全面替换视觉效果：

- 所有卡片（provider-card, glass-card, 弹窗等）加上 `class="glass-card"` 或使用 glass.css 的变量
- 弹窗背景（lightbox, 所有 modal）使用 `glass-overlay` 类 + backdrop-filter: blur(20px)
- 页面背景加上 `page-bg` 类，激活柔光渐变背景
- 所有 input/textarea 背景改为半透明毛玻璃 `background: rgba(255,255,255,0.6); backdrop-filter: blur(10px)`
- 导航栏底部 Dock 背景改为强毛玻璃 `backdrop-filter: blur(40px) saturate(200%)`

### 然后：添加苹果风格动画

在 pages.css 底部或新建 `static/css/animations.css`：

```css
/* Spring 弹性过渡 */
@keyframes spring-in {
  0% { transform: scale(0.95); opacity: 0; }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes dock-magnify {
  0% { transform: scale(1); }
  100% { transform: scale(1.25); }
}

/* Dock 悬停放大 + 弹性 */
.dock-item {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.dock-item:hover {
  transform: scale(1.25) translateY(-4px);
}
.dock-item:hover ~ .dock-item {
  transform: translateX(6px);
}

/* 卡片入场动画 */
.glass-card {
  animation: fade-up 0.4s cubic-bezier(0.25, 0.1, 0.25, 1) both;
}
.glass-card:nth-child(2) { animation-delay: 0.05s; }
.glass-card:nth-child(3) { animation-delay: 0.1s; }
.glass-card:nth-child(4) { animation-delay: 0.15s; }
.glass-card:nth-child(5) { animation-delay: 0.2s; }
```

### 然后：修复所有弹窗样式

所有弹窗（lightbox, compareModal, providerModal, loginPage, 等）统一使用以下结构：

```html
<div class="glass-overlay" style="display:flex;align-items:center;justify-content:center;">
  <div class="glass-panel" style="...">
    <!-- 内容 -->
  </div>
</div>
```

- 移除所有 `style="background:rgba(...);backdrop-filter:..."` 旧内联
- 所有按钮用统一的 `.btn` 类体系（`.btn-primary`, `.btn-secondary`, `.btn-ghost`）

### 最终确认

完成所有步骤后给出清单：
- [ ] index.html 行数（目标 < 500 行骨架）
- [ ] 所有旧 CSS 内联已删除
- [ ] 所有旧 JS 内联已删除
- [ ] Tailwind CDN 已移除
- [ ] Sidebar 已从 DOM 移除
- [ ] 所有卡片使用 glass-card 类
- [ ] 所有弹窗使用 glass-overlay + glass-panel
- [ ] Dock 动画生效（悬停放大 + 弹性）
- [ ] 卡片入场动画（淡入上移 + 级联延迟）
- [ ] 毛玻璃效果在所有组件上一致
- [ ] 深色模式正常切换
- [ ] 所有功能（生图/视频/媒体库/设置等）正常工作
