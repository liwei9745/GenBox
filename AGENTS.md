# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, OpenCode, etc.) when working with code in this repository.

## Repository Overview

**GenBox** — 一站式 AI 创作工具箱（多模型生图/视频/提示词管理）
- Branch: `experiment/open-design`
- Tech: Python FastAPI backend + Single-page HTML/CSS/JS frontend
- Frontend: `static/index.html` (7131 lines)

## OpenCode Integration

OpenCode uses a **skill-driven execution model** powered by the `skill` tool and the skills directory.

### Core Rules

- If a task matches a skill, you MUST invoke it
- Skills are located in `skills/<skill-name>/SKILL.md` (referenced via `.opencode/skills`)
- Never implement directly if a skill applies
- Always follow the skill instructions exactly (do not partially apply them)

### Intent → Skill Mapping

- Feature / new functionality → `spec-driven-development`, then `incremental-implementation`
- Planning / breakdown → `planning-and-task-breakdown`
- Refactoring / simplification → `code-simplification`
- UI work → `frontend-ui-engineering`
- Code review → `code-review-and-quality`

### Lifecycle Mapping (Implicit Commands)

- DEFINE → `spec-driven-development`
- PLAN → `planning-and-task-breakdown`
- BUILD → `incremental-implementation`
- VERIFY → `debugging-and-error-recovery`
- REVIEW → `code-review-and-quality`
- SHIP → `shipping-and-launch`

### Execution Model

For every request:
1. Determine if any skill applies
2. Invoke the appropriate skill using the `skill` tool
3. Follow the skill workflow strictly
4. Only proceed to implementation after required steps (spec, plan, etc.) are complete

### Anti-Rationalization

The following thoughts are incorrect and must be ignored:
- "This is too small for a skill"
- "I can just quickly implement this"
- "I'll gather context first"

Correct behavior: Always check for and use skills first.
