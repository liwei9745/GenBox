# Open Design 整合路线图 — GenBox experiment/open-design

> 本文件记录 GenBox 与 Open Design 的整合计划，分阶段列出可在本分支中实验的功能。
> 创建日期：2026-07-07

---

## 项目背景

GenBox 是一个基于 FastAPI 的多模型生图/生视频工具箱，当前已支持 GPT Image 2、Gemini、Qwen、Agnes 等多个 Provider。
本分支 `experiment/open-design` 目标是探索将 Open Design 的 MCP（Model Context Protocol）能力整合进 GenBox，
使 GenBox 的生图工作流可以通过 MCP 被 Open Design 的设计工作区直接调用。

---

## Open Design 整合路线图

### Phase 1: 环境准备（当前阶段）

- [x] 安装 Open Design 桌面应用（Electron GUI）
- [ ] 从源码构建 `od` CLI（需要 Node 24 + pnpm 10.33）
  ```bash
  git clone https://github.com/nexu-io/open-design.git
  cd open-design
  corepack enable && pnpm install
  # od CLI 位于 apps/daemon/dist/cli.js
  ```
- [ ] 运行 `od mcp install opencode` 将 MCP server 注册到 OpenCode
- [ ] 验证 `od mcp` 可以暴露本地 Open Design 项目为 stdio MCP server

### Phase 2: MCP Server 集成

- [ ] 在 GenBox 中添加 MCP server 端点（`/api/mcp`）
  - 暴露 GenBox 的生图能力为 MCP tools
  - 关键 tools: `generate_image`, `list_providers`, `get_gallery`, `optimize_prompt`
- [ ] 实现 MCP tool 定义（JSON Schema）
  - `generate_image`: 接受 prompt、providers、size、quality 等参数
  - `list_providers`: 返回已配置的 Provider 列表
  - `get_gallery`: 返回图库中的图片列表
  - `optimize_prompt`: 调用 LLM 优化提示词
- [ ] 实现 MCP stdio transport（可通过 Open Design 的 `od mcp` 调用）

### Phase 3: Open Design Skills 集成

- [ ] 创建 GenBox skill（`od skill add` 格式）
  - 将 GenBox 的生图能力封装为 Open Design skill
  - 支持通过 skill 目录浏览和调用
- [ ] 实现 design-to-generation 工作流
  - Open Design 中的设计稿 → 自动提取配色/布局 → GenBox 生成素材
- [ ] 实现 generation-to-design 反馈循环
  - GenBox 生成的图片 → 自动导入 Open Design 项目

### Phase 4: 前端整合

- [ ] 在 GenBox 前端添加 Open Design 面板
  - 显示当前 Open Design 项目状态
  - 一键将 GenBox 生成的图片推送到 Open Design 项目
- [ ] 实现 Open Design 设计系统预览
  - 在 GenBox 中预览 Open Design 的设计系统（颜色、字体、组件）
- [ ] 添加 MCP 连接状态指示器

### Phase 5: 高级功能

- [ ] 实现双向同步
  - Open Design 中修改设计 → GenBox 自动重新生成素材
  - GenBox 中生成新变体 → Open Design 自动更新
- [ ] 实现批量生成模式
  - 从 Open Design 项目中提取所有需要素材的位置
  - 一键批量生成所有素材
- [ ] 实现版本控制集成
  - GenBox 生成的素材自动关联 Git commit
  - Open Design 项目变更自动触发 GenBox 重新生成

---

## 技术要点

### MCP Tool 定义示例

```json
{
  "name": "genbox_generate_image",
  "description": "Generate images using GenBox's multi-provider engine",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": { "type": "string", "description": "Image generation prompt" },
      "providers": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Provider IDs to use (empty = all enabled)"
      },
      "size": { "type": "string", "description": "Image size (e.g. 1024x1024)" },
      "quality": { "type": "string", "description": "Image quality (low/standard/high)" }
    },
    "required": ["prompt"]
  }
}
```

### GenBox API 端点映射

| MCP Tool | GenBox API | 说明 |
|----------|-----------|------|
| `genbox_generate_image` | `POST /api/generate` | 文生图/图生图 |
| `genbox_list_providers` | `GET /api/providers` | 获取 Provider 列表 |
| `genbox_get_gallery` | `GET /api/gallery` | 获取图库 |
| `genbox_optimize_prompt` | `POST /api/llm/optimize` | LLM 提示词优化 |

### 端口规划

| 服务 | 端口 | 说明 |
|------|------|------|
| GenBox | 8890 | 现有服务 |
| Open Design daemon | 7456 | MCP server 端口 |
| Open Design web | 8080 | 设计工作区 UI |

---

## 注意事项

1. **API Key 安全**: `.env` 和 `config/` 中的 API Key 已在 `.gitignore` 中排除，不要提交
2. **Node 版本**: Open Design 需要 Node 24，当前系统需确认版本
3. **端口冲突**: 确保 7456 和 8080 端口未被占用
4. **Windows 兼容性**: 部分 MCP 功能可能需要 WSL 支持

---

## 参考资源

- [Open Design GitHub](https://github.com/nexu-io/open-design)
- [Open Design Quickstart](https://open-design.ai/quickstart/)
- [Open Design MCP Docs](https://opendesigner.io/mcp)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
