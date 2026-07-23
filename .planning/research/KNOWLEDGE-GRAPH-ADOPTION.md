# Knowledge Graph Adoption Plan

**Date:** 2026-07-23
**Scope:** Post-P4 knowledge graph adoption for GenBox development efficiency

## Current Verified State

- No `.codegraph/` directory exists in this worktree, so CodeGraph is not
  currently available as a repository index.
- `.planning/config.json` does not explicitly enable `graphify.enabled`, so the
  GSD graph pipeline is currently disabled.
- No `.planning/graphs/` directory exists, so there is no built project graph.
- No `wiki-knowledge/` directory exists in this worktree.
- Lightweight knowledge assets already exist in `.planning/codebase/` and can be
  reused as graph-building inputs later.

## Recommendation

Do **not** interrupt the current Phase 4 mainline to build a knowledge graph
now. The immediate P4 bottleneck is remote evidence, not codebase discovery.

Adopt the graph in a staged way **after** the next P4 critical remote checkpoint
is complete:

1. Keep using `docs/*.md`, targeted file reads, and focused tests for current P4.
2. After the next isolated VPS/browser checkpoint, enable a lightweight graph.
3. Before Phase 13 message-channel development, upgrade that graph into a more
   durable code + capability map.

## Why Not Now

For the current P4 scope, most active work lives in a narrow slice:

- `main.py`
- `extensions/`
- `static/js/extensions.js`
- `tests/test_extensions.py`

That means the current productivity limit is not "finding the right file"; it is
safe implementation, independent review, and later real remote verification.
Building the graph now would help a little, but not enough to justify derailing
P4 execution.

## Expected Benefit

### Short-Term Benefit (Current P4)

- Faster call-path lookup during review
- Less repeated re-reading across resumed sessions
- Some token savings for new agents entering the task

Expected gain: **moderate**, not transformational

### Mid-Term Benefit (Post-P4 / Pre-Phase 13)

- Faster architecture reviews across backend, frontend, auth, and event flows
- Better change-impact analysis across deployment, Push/Pull, and future bot
  commands
- Lower repeated context cost when multiple agents or future sessions re-enter
  the same codebase

Expected gain: **high**

## Recommended Graph Layers

### Layer 1: Code Navigation Graph

Goal: speed up symbol lookup, call-path tracing, and review work.

Preferred tool:

- CodeGraph, if the user explicitly opts in to indexing this repository

Outputs:

- symbol graph
- caller/callee relationships
- file-level navigation shortcuts

When to build:

- after the next P4 remote checkpoint

### Layer 2: Project Knowledge Graph

Goal: connect code, docs, phases, contracts, and decisions.

Preferred tool:

- GSD graphify into `.planning/graphs/`

Inputs:

- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `.planning/codebase/*.md`

Outputs:

- project node and edge graph
- graph report
- status/diff support for later sessions

When to build:

- after the next P4 remote checkpoint

### Layer 3: Capability And Event Graph

Goal: support future message-channel and workflow orchestration work.

Nodes should eventually include:

- workflows: generate image, generate video, push image, pull/import image,
  deploy service, rotate key, retry failure
- trust boundaries: admin auth, Push auth, SSH trust, channel binding
- entry points: browser UI, Push API, Pull API, future bot/webhook gateway
- side effects: local storage write, remote SSH action, receipt generation,
  deletion authorization

This layer is most valuable before Phase 13 and later Repair/Store work.

## Minimal Post-P4 Rollout

### Step 1: Enable Graphify

Add explicit config only after the P4 checkpoint:

```json
{
  "graphify": {
    "enabled": true
  }
}
```

### Step 2: Build A Lightweight Project Graph

Target output:

- `.planning/graphs/graph.json`
- `.planning/graphs/GRAPH_REPORT.md`

Use this first for status/query work, not as a reason to stop reading code.

### Step 3: Decide On CodeGraph Opt-In

If symbol-level lookup is still costing time, then opt in to repository
indexing and build `.codegraph/`.

This should be a deliberate user choice because repository indexing changes the
working environment and adds another maintained artifact.

## Practical Token Guidance

The graph will save the most tokens when:

- a later session has to rebuild context quickly
- independent review needs repeated cross-file traversal
- multiple agents need to reason about the same architecture
- future message-channel work introduces many new boundaries

The graph will save the fewest tokens when:

- the work is confined to one or two hot files
- the current blocker is external verification, not code understanding

## Trigger To Start

Start the graph rollout when **all** of the following are true:

- current P4 local implementation and review are stable
- the next remote verification checkpoint is complete or deliberately paused
- there is no urgent P4 bug or review blocker
- development is about to widen into cross-cutting work such as Phase 13

## Immediate Next Step

Do not build the graph yet.

Continue the current P4 mainline with remote preflight and isolated evidence
preparation. Revisit this plan immediately after the next meaningful remote
checkpoint or before Phase 13 begins.
