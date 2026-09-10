# Message Channel Contract

This contract defines the future GenBox message-channel layer. It is a planning
contract, not evidence that any channel is currently implemented.

## Purpose

Message channels let a user observe selected GenBox events and trigger selected
GenBox workflows from an external conversation surface. They are convenience
entry points, not alternate trust domains.

## Scope

Future message-channel support may include:

- outbound notifications for generation, import, deployment, and retry states
- inbound bot or webhook actions for bounded existing workflows
- explicit channel binding between a GenBox user or workspace and an external
  message identity
- per-channel capability metadata and risk labels

## Non-Goals

- arbitrary shell or unrestricted VPS command execution from a message
- treating a message account as equivalent to GenBox administrator auth
- bypassing existing deployment, Push, cleanup, or repair approval boundaries
- hiding platform-specific auth or review differences behind a fake universal
  OAuth model

## Architecture

The message-channel layer is split into four pieces:

- `channel registry`: capability matrix, auth model, media limits, review needs
- `auth broker`: channel-specific user or workspace binding flows
- `outbound event outbox`: durable non-secret events fanned out to channels
- `inbound gateway`: authenticated callbacks mapped to fixed backend intents

The inbound gateway may call only backend-owned intents that already have
validation, authorization, and recovery semantics in GenBox.

## Capability Levels

### Level 1: Notifications

Outbound-only delivery such as:

- generation completed
- video completed
- import succeeded or failed
- deployment completed
- retry required

### Level 2: Fixed Commands

Inbound actions that map to fixed intents such as:

- start a saved image generation preset
- start a saved video generation preset
- query task or deployment status
- request a bounded remote import workflow
- retry a failed but already authorized workflow

### Level 3: Guided Conversation

Multi-turn collection of parameters and confirmations before invoking a fixed
GenBox intent. This remains a later layer and must not bypass Level 2 safety
rules.

## Identity And Authentication

- A channel binding is explicit and scoped. It grants only named capabilities.
- Channel identity is separate from GenBox administrator identity.
- Channel identity is separate from Push source identity.
- Channel identity is separate from VPS ownership.
- Bot tokens, app secrets, signing secrets, and refresh tokens are secrets and
  follow the same handling rules as other GenBox credentials.

High-risk actions may require an additional in-GenBox confirmation or approval
step even after the message channel itself is authenticated.

## Initial Planning Assumptions

As of 2026-07-23, the planning assumption is:

- Telegram is the best first candidate for a consumer-friendly channel.
- Feishu is a later candidate for tenant or team-oriented workflows.
- QQ is a later candidate whose bot and login ecosystems must be treated as
  separate integration surfaces.

These are planning assumptions only. Official platform docs, auth rules, review
requirements, media constraints, and callback guarantees must be re-verified at
implementation time.

## Safety Rules

- No message channel may submit arbitrary shell.
- No message channel may bypass host-key verification, deployment ownership, or
  receipt-gated cleanup rules.
- No message channel may invent a new remote mutation path outside an existing
  reviewed GenBox workflow.
- Callback payloads, raw prompts, raw media, and user identities must not leak
  into public logs, browser storage, screenshots, URLs, or Git.
- Unsupported or partially implemented channels must remain explicit planned
  states in product surfaces.

## Suggested Delivery Order

1. notifications
2. fixed commands
3. guided conversation

This keeps the first release useful without turning the message channel into a
second full UI before the core image-transfer and deployment phases are fully
verified.
