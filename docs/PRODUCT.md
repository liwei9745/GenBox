# GenBox Extension Center Product Definition

## Background

`yukkcat/chatgpt2api` can generate and retain images on a remote VPS. Generated
media can consume significant VPS disk space over time. GenBox is commonly run
on a user's local computer, but it may also run on a NAS or another VPS with
more suitable storage.

The first product goal is to connect the two applications so remote images can
be transferred into the GenBox media library with their useful metadata. The
second goal is to make selected AI gateways and network tools deployable through
a guided web experience for users who cannot or do not want to operate from
source code and command-line instructions.

## Target Users

- Users who generate images through a remote chatgpt2api deployment.
- Users who want to retain media locally or on a NAS instead of on a small VPS.
- Non-developers who need strong guidance for installing and accessing related
  services.
- Advanced users who need observable, repeatable deployments without giving up
  control of credentials, networking, backup, and recovery.

## Product Goals

1. Add an extension center to GenBox for guided service discovery, deployment,
   connection, access, and maintenance.
2. Integrate GenBox and chatgpt2api through an authenticated, idempotent image
   transfer protocol.
3. Support one-time generation push, manual batch push, and scheduled
   incremental push.
4. Store imported images in the GenBox image library with source, prompt, model,
   creation time, and transfer metadata where available.
5. Reduce remote storage use without risking loss of unconfirmed source media.
6. Present deployed service URLs, API endpoints, login information, and
   one-time credentials with clear open and copy actions.
7. Establish a reusable deployment-adapter model for additional services.
8. After the core integration is verified, evolve the catalog into a GenBox
   Store with Installed, Recommended, and All views backed by honest capability,
   environment, license, and risk metadata.
9. Provide an advisory-first Repair Copilot that explains sanitized diagnoses
   and offers only user-authorized, adapter-allowlisted repair actions.
10. Add optional message-channel notifications and capability-scoped bot
    interaction so users can observe and trigger selected GenBox workflows
    without turning a chat channel into a general remote shell.

## Primary User Journeys

### Push A Newly Generated Image

The user enables "Push to GenBox" for one generation. chatgpt2api stores the
source image, sends it to GenBox, verifies the receipt, and records transfer
state. GenBox imports it into the image library and applies metadata and tags.

### Push Existing Images In A Batch

The user opens chatgpt2api image management, selects images or a date range,
starts a batch, and sees per-image progress and failures. Retrying the same
batch does not create duplicates.

### Schedule Incremental Push

The user accepts the default weekly schedule or selects a custom schedule and
optional date bounds. The scheduler persists a cursor and per-image state so a
restart, late file, or clock adjustment does not cause silent omission.

### Reclaim VPS Storage

The default behavior retains source images. When the user separately enables
confirmed cleanup, chatgpt2api removes only files whose authenticated GenBox
receipt contains a matching SHA-256 and explicitly permits source deletion.

### Deploy A Service Without Writing Code

The user selects an available catalog item, follows environment discovery and
network steps, reviews a deployment plan, deploys an isolated service, and
receives its status, console URL, API URL, login guidance, and one-time secrets.

### First-Time VPS Trust For Personal Users

For a personal user who already has a trusted SSH terminal session, GenBox now
provides a local trusted SSH-session pairing flow. After saving the target host,
port, and username, GenBox presents one fixed, one-line helper and accepts a
one-line response pasted back by the user. The page reports the result in plain
language and keeps the technical host identity in advanced details. This local
capability is covered by local tests; isolated-VPS and cross-project E2E
verification remain pending.

The already trusted terminal session or its known-host record is a user-supplied
trust anchor for the initial pairing; it does not prove VPS ownership and does
not replace SSH credentials. Users without an accessible trusted session use a
safe advanced fallback such as their provider console or an existing known-host
record. A provider-account verification flow is outside the current scope.

### Find And Repair A Compatible Service

After the core delivery phases, the user can see installed apps, environment-
appropriate recommendations, and the full catalog. When a managed app fails,
deterministic checks run first; Repair Copilot may then explain sanitized
evidence and propose a bounded action for explicit approval and health recheck.

### Operate Through A Message Channel

After the core transfer and deployment workflows are verified, the user may bind
an optional message channel such as Telegram, Feishu, or a later approved
platform. GenBox can send status updates, completed image or video results,
deployment notices, and retry prompts to that channel. The user can then invoke
selected fixed actions such as starting a saved generation preset, checking task
status, or requesting a bounded image-import workflow from a trusted remote
source.

Message-channel interaction is a convenience layer over existing GenBox
capabilities, not a replacement for backend authorization or workflow safety.
It does not grant arbitrary shell access, does not make a third-party chat
identity equal to a GenBox administrator, and does not bypass existing review,
network, or deletion constraints.

## Service Catalog Scope

### API Proxies And Model Gateways

- `chatgpt2api`: catalogued and supported by deployment code and local tests;
  isolated live deployment verification remains pending.
- `grok2api`: planned.
- `AIClient2API`: planned.
- `gemini2api` repositories: planned; unique catalog identities are required.
- `mimocode2api`: planned.
- `flow2api`: planned.
- `kiro2api`: repository must be confirmed before planning deployment.

### Account And Token Management

- Account registration and Token management: planned.

### Proxy Networks And Node Tools

- `Free-Residential-IP-Proxy-Controller`: planned.
- `aimili-vpngate`: planned.
- `socks5-proxy`: planned.

A catalog entry is not deployable until its adapter, security boundaries,
health checks, delivery information, rollback, and tests are implemented.

## Success Measures

- A generated image can reach the GenBox media library without manual download.
- Repeated Push requests do not duplicate media.
- Interrupted batches resume without silently skipping images.
- Optional cleanup never deletes a source without a verified receipt.
- A non-developer can deploy the supported chatgpt2api preset and open the
  resulting service using information presented by GenBox.
- A clean deployment from the owner's sanitized GitHub repository reproduces
  the tested development result.

## Non-Goals For The Initial Delivery

- Arbitrary browser-supplied shell execution.
- Automatic deployment of every catalog entry.
- Direct feature development inside an existing production container.
- Default or unconditional deletion of source media.
- Public exposure of GenBox without an authenticated private network or a
  properly secured HTTPS endpoint.
- Treating a UI placeholder or command plan as a completed provider adapter.
- Letting a catalog manifest, recommendation, or AI response grant deployment or
  repair capability without a verified backend adapter.
- Treating a third-party message account, bot session, or platform OAuth result
  as equivalent to GenBox administrator authentication.
- Letting a message channel submit arbitrary shell, unrestricted VPS commands,
  or other unbounded remote mutations.
- Training on raw operational logs or sending secrets, personal data, user media,
  prompts, host identities, or credentials to a diagnostic model.
- Giving AI arbitrary shell access, direct root control, or permission to mutate
  an external instance without verified ownership and explicit authorization.

## Terms

- **Production source instance**: an existing chatgpt2api deployment that must
  remain operational and read-only during development.
- **Development clone**: an isolated copy used for implementation and testing.
- **Push**: chatgpt2api sends an image to GenBox.
- **Pull**: GenBox requests and imports images from chatgpt2api.
- **Receipt**: GenBox's authenticated response describing accepted content and
  whether the source is safe to delete.
- **Delivery information**: service URLs, login guidance, and one-time secrets
  presented after deployment.
- **Trusted SSH-session pairing**: local first-time host-identity confirmation
  using a user-operated helper in an already trusted SSH terminal session;
  isolated-VPS verification remains a separate gate.
- **Message channel**: an external conversation surface such as Telegram,
  Feishu, or a later approved platform that may receive notifications or submit
  fixed GenBox intents after explicit binding.
- **Channel binding**: an explicit link between a GenBox user or workspace and a
  specific external message identity plus its permitted capabilities.
