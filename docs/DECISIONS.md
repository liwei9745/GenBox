# Architecture And Product Decisions

This file records durable choices. Update an existing decision when its status
changes; do not silently contradict it in implementation or another document.

## ADR-001: Push And Pull Coexist

**Status:** Accepted
**Date:** 2026-07-12

### Context

Some GenBox installations can accept traffic from chatgpt2api through a private
network or tunnel. Others are behind a network where only GenBox can initiate a
connection.

### Decision

Retain the existing GenBox-initiated Pull workflow and add chatgpt2api-initiated
Push. Both import into the same media library and use content hashes to prevent
duplicates. This is not general two-way synchronization.

### Consequences

Push and Pull use different initiators and credentials but need compatible
metadata and deduplication behavior.

## ADR-002: SHA-256 Confirms Content Identity

**Status:** Accepted
**Date:** 2026-07-12

### Context

Remote filenames, URLs, timestamps, ETags, and embedded MD5 values are not
reliable identifiers for every imported image.

### Decision

Use SHA-256 of image bytes for content confirmation. Push idempotency also uses
source identity and stable remote path to track transfer attempts.

### Consequences

Hashing adds I/O cost but gives a stable basis for deduplication, receipt
verification, and optional source cleanup.

## ADR-003: Source Cleanup Is Explicit And Receipt-Gated

**Status:** Accepted
**Date:** 2026-07-12

### Decision

Retain source media by default. Delete only when the user independently enables
cleanup and the sender validates an authenticated GenBox receipt containing the
same SHA-256 and `safe_to_delete_source=true`. Development clones never perform
automatic cleanup.

### Consequences

Storage is not reclaimed until transfer certainty is established. Failed,
pending, changed, or ambiguous files remain recoverable.

## ADR-004: Production chatgpt2api Is Read-Only During Development

**Status:** Accepted
**Date:** 2026-07-12

### Context

The existing VPS container provides a working service and may contain user
accounts, settings, and generated media.

### Decision

Do not develop in the existing instance. Use it only for approved read-only
discovery and as a source for an isolated development clone.

### Consequences

The clone requires separate storage, port, Compose identity, credentials, Push
identity, health checks, and evidence that production was not mutated.

## ADR-005: Network Providers Are Replaceable Adapters

**Status:** Accepted
**Date:** 2026-07-12

### Decision

Store and use a final GenBox destination URL without coupling the image-transfer
protocol to Tailscale, NetBird, or Cloudflare. Use one primary network adapter at
a time. Tailscale is the recommended first complete path.

### Consequences

Each adapter must implement enrollment, status, connectivity, secret handling,
and recovery consistently.

## ADR-006: Administrator And Push Credentials Are Separate

**Status:** Accepted
**Date:** 2026-07-12

### Decision

GenBox administrator authentication does not authenticate remote image senders.
Each sender receives a stable source ID and independently revocable Push key.

### Consequences

A compromised sender can be revoked without rotating the GenBox administrator
key. Push endpoints and ordinary management endpoints have different auth rules.

## ADR-007: Initial Automated Deployment Uses A Fixed Compose Preset

**Status:** Accepted
**Date:** 2026-07-12

### Decision

The first executable adapter deploys a fixed chatgpt2api Docker Compose preset.
WARP, Python, and additional catalog services remain non-executable until their
ownership, isolation, rollback, and health contracts are implemented.

### Consequences

The browser cannot submit arbitrary shell. Catalog availability must reflect
real backend capability rather than planned UI.

## ADR-008: Deployment Delivers Usable Access Information

**Status:** Accepted
**Date:** 2026-07-12

### Decision

A successful managed deployment presents service status, console URL, API URL,
login guidance, and required credentials. URLs and non-secret identifiers are
copyable. Newly generated secrets are delivered once by default and are not
stored in browser storage or ordinary instance records. The user may opt in to
saving a managed instance secret locally for later viewing; this is off by
default, requires an explicit per-secret choice, and warns before enabling. SSH
credentials, enrollment tokens, Push keys, and the GenBox administrator key are
never saved to browser storage. A lost show-once secret is recovered by rotation
after re-verifying ownership; an explicitly saved managed-instance secret may be
retrieved from the unlocked local vault.

### Consequences

Deployment is not complete merely because a container is running; the user must
be able to reach and authenticate to the service. The delivery page and a
separate "deployed services" list both expose only non-secret access information;
secret handling follows the user's chosen policy.

## ADR-010: Secret Delivery Is User-Choice, Not Hardcoded

**Status:** Accepted
**Date:** 2026-07-12

### Context

Earlier guidance hardcoded "deliver once, never store". A non-developer user
deploying several services wanted control: show-once plus a reset button, or
optional local save for later viewing. The product must not force one policy.

### Decision

Managed-instance secret delivery is a user choice: default show-once with
rotation-based recovery, plus an opt-in local save that warns before enabling and
applies only to secrets the user explicitly chooses to keep. User-selected VPS
SSH credentials may also be stored in the encrypted local vault after an explicit
warning and opt-in. Enrollment tokens, Push keys, and the GenBox administrator key
remain forbidden from browser storage in all cases. The fallback local vault is a versioned file
under `storage/` containing only PBKDF2-SHA256 parameters, a random salt, field
metadata, and Fernet ciphertext. The unlock password and derived key exist only
in process memory and explicit lock removes the derived key. Vault records are
limited to credentials for registered GenBox-managed instances.

### Consequences

The UI must present both the delivery panel and the deployed-services list with
a consistent secret policy. Local save is a per-secret, off-by-default action,
never an implicit default.

## ADR-009: Upstream Delivery Requires Clean GitHub Redeployment

**Status:** Accepted
**Date:** 2026-07-12

### Decision

After isolated-clone verification, sanitize the implementation and push it to
the project owner's GitHub repository. Create a fresh deployment only from that
repository and repeat acceptance testing before preparing an upstream PR or
proposal.

### Consequences

Container-only edits, ignored files, local secrets, and undocumented manual
steps cannot be mistaken for a reproducible contribution.

## ADR-011: Structured Intent With Backend-Generated Automation

**Status:** Accepted on 2026-07-12

GenBox provides zero-code remote deployment by accepting structured browser
requests and generating fixed commands in backend adapters. It does not expose a
general web shell. One network is active at a time; verified alternatives may be
stored for later one-click switching after fresh connectivity checks.

## ADR-012: GenBox Is Licensed Under GPL-3.0-only

**Status:** Accepted
**Date:** 2026-07-16

### Context

GenBox is distributed as source, desktop clients, Docker Compose bundles, and
container images. The project needs a clear copyleft rule for redistributed
modifications while retaining its API, SSH, Docker, and network-adapter
integrations with independently licensed external services.

### Decision

License GenBox under GNU General Public License version 3 only
(`GPL-3.0-only`). This applies to GenBox source and redistributed modified
versions. It does not alter the license of a separately deployed service merely
because GenBox communicates with it over an API, SSH, Docker, or a network.

### Consequences

- A distributor of a modified GenBox must provide corresponding source under
  GPLv3.
- Existing MIT releases remain licensed under MIT; their granted permissions
  are not revoked.
- Release packages include the GPL text and `THIRD_PARTY_NOTICES.md`.
- Bundled third-party code, assets, or service artifacts require documented
  provenance and compatible distribution terms before release.
