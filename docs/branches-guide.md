# GenBox 分支指南 | Branch Guide

GenBox 有两个主要分支，面向不同使用场景：

| 分支 | 定位 | 端口 | 适合谁 |
|------|------|------|--------|
| `master` | 稳定版 | 8890 | 日常使用、生产环境 |
| `feat/glass-ui-redesign` | 前瞻版 | 8891 | 喜欢新设计、愿意尝鲜 |

---

## 🎯 如何选择？

```
你需要什么？
│
├─ 稳定可靠、功能完整 ──────────→ master
│
├─ 毛玻璃科幻风、Mac Dock 导航 ─→ feat/glass-ui-redesign
│
├─ 并发生图（最多16个）─────────→ feat/glass-ui-redesign
│
├─ IP 体检 + 宿主机监控 ────────→ feat/glass-ui-redesign
│
└─ 不确定 ─────────────────────→ 先用 master，体验后再切换
```

---

## 📦 master 分支 — 稳定版

**特点：**
- 传统白色卡片 UI，简洁清晰
- 经过充分测试，稳定性高
- 所有核心功能完整
- 社区反馈的主要分支

**适合：**
- 日常 AI 创作工作
- 生产环境部署
- 不喜欢折腾的用户

**启动：**
```bash
git clone https://github.com/liwei9745/GenBox.git
cd GenBox
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
python main.py
# 访问 http://localhost:8890
```

---

## ✨ feat/glass-ui-redesign 分支 — 前瞻版

**特点：**

| 特性 | 说明 |
|------|------|
| 🎨 毛玻璃 UI | backdrop-filter 模糊 + 饱和度，科幻感十足 |
| 🚀 Mac Dock 导航 | 底栏悬停放大 + 弹性动画 + 蓝色活跃点 |
| 🖱️ 可拖拽面板 | 预览区边缘可拖拽调整大小 |
| ☑️ 多 Provider 选择 | Checkbox 复选，支持多选对比生成 |
| 📊 分 Provider 进度 | 每个 Provider 独立进度条，可折叠 |
| 🌐 IP 体检 | Spamhaus 黑名单 + ISP 类型 + TCP 延迟 |
| 💻 宿主机监控 | CPU/内存/磁盘/Swap/网络 I/O/Top 进程 |
| ⚡ 16 路并发生图 | 移除信号量瓶颈，真正并行 |
| 🔧 协议检测修复 | URL 优先判断，避免 agnes 被误判 |

**适合：**
- 喜欢新设计风格的用户
- 需要高并发生图的场景
- 想要 IP 信誉检测的用户
- 愿意尝试新功能的尝鲜者

**启动：**
```bash
git clone -b feat/glass-ui-redesign https://github.com/liwei9745/GenBox.git GenBox-glass
cd GenBox-glass
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
python main.py
# 访问 http://localhost:8891
```

> ⚠️ 注意：glass-ui 分支使用 **8891** 端口，与 master 的 8890 不冲突，可以同时运行。

---

## 🔄 如何切换分支？

### 从 master 切换到 glass-ui
```bash
cd GenBox
git checkout feat/glass-ui-redesign
pip install -r requirements.txt  # 可能有新依赖
python main.py  # 端口变为 8891
```

### 从 glass-ui 切换回 master
```bash
git checkout master
python main.py  # 端口恢复 8890
```

### 同时运行两个版本
```bash
# 终端 1: 运行 master
cd GenBox
python main.py  # 8890

# 终端 2: 运行 glass-ui
cd GenBox-glass
python main.py  # 8891
```

---

## 📊 功能对比

| 功能 | master | glass-ui |
|------|:------:|:--------:|
| 多模型生图 | ✅ | ✅ |
| 多模型生视频 | ✅ | ✅ |
| 图生图 / 变形 | ✅ | ✅ |
| LLM 提示词优化 | ✅ | ✅ |
| 提示词管理 | ✅ | ✅ |
| 统一媒体库 | ✅ | ✅ |
| 多账户密钥轮换 | ✅ | ✅ |
| 毛玻璃 UI | ❌ | ✅ |
| Mac Dock 导航 | ❌ | ✅ |
| 可拖拽面板 | ❌ | ✅ |
| 多 Provider 复选 | ❌ | ✅ |
| 分 Provider 进度 | ❌ | ✅ |
| IP 体检 | ❌ | ✅ |
| 宿主机监控 | ❌ | ✅ |
| 16 路并发 | ❌ | ✅ |

---

## ❓ 常见问题

**Q: 两个分支的数据通用吗？**
A: 是的。`.env` 配置、`storage/` 图库、`providers.json` 都是通用的，切换分支不会丢失数据。

**Q: glass-ui 分支稳定吗？**
A: 功能完整，但 UI 代码经过重构，可能有细微 bug。日常使用没问题，生产环境建议用 master。

**Q: 可以把 glass-ui 的功能合并到 master 吗？**
A: 可以。当你确认 glass-ui 稳定后，可以创建 PR 合并。

**Q: glass-ui 的新功能会同步到 master 吗？**
A: 目前两个分支独立开发。glass-ui 的后端优化（如协议检测修复）可以单独 cherry-pick 到 master。

---

<div align="center">

**选择适合你的分支，开始 AI 创作之旅！**

</div>
