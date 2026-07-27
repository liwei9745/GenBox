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

## ADR-013: AI Repair Is Advisory-First And Deterministically Bounded

**Status:** Accepted
**Date:** 2026-07-17

### Context

Future Store apps need useful diagnosis and repair guidance without exposing
credentials, turning model output into shell, or allowing unreviewed operational
history to become trusted automation.

### Decision

Run deterministic checks and fallback guidance before AI diagnosis. Send only
minimal sanitized evidence to a dedicated user-selected diagnostic model. AI
returns a structured proposal and cannot execute arbitrary shell or obtain direct
root access. Any mutation requires explicit authorization for the exact owned
target and an adapter-defined allowlisted action, followed by rollback-aware
deterministic health verification.

Sanitized experience records progress through `draft`, `reviewed`, `verified`,
and `deprecated`. Human review and reproducible evidence are required before an
experience becomes `verified`; raw logs are never used for self-training or
automatic promotion.

### Consequences

- Model unavailability or low confidence falls back to deterministic guidance.
- External instances remain advisory/read-only until ownership and adoption are
  explicitly verified.
- Repair automation grows through reviewed adapter capabilities, not free-form
  model commands or accumulated raw logs.

## ADR-014: Deployment, SSH Session, And Private-Network Completion Are Separate States

**Status:** Accepted
**Date:** 2026-07-18

### Context

A deployed remote service can be healthy while the VPS-to-GenBox private route
is still incomplete. SSH credentials are session secrets and may be cleared or
lost across refresh and restart, while the confirmed public host fingerprint is
safe target metadata. Treating these facts as one wizard step caused false
completion, repeated SSH tests, concurrent authentication attempts, and unsafe
one-time credential delivery.

### Decision

Track service deployment, SSH session verification, and private-network
verification independently. A historical completed deployment resumes at
network selection unless an unclaimed one-time service credential must first be
shown visibly. The final step requires a completed network task and its
application-level probe; a service console URL can never satisfy the GenBox
private-URL check.

SSH and sudo credentials remain session-only unless a future explicit encrypted
target-vault flow is separately accepted. Exactly one SSH authentication method
is required before any SSH or network-task side effect. Confirmed public host
fingerprints may be persisted with target metadata. A Phase 3 network task may
perform the credential-bearing SSH connection directly, so a separate SSH test
is needed only to establish or change the host fingerprint or to diagnose SSH.

### Consequences

- Browser actions use single-flight locks and discard stale authentication
  responses after target, account, port, authentication mode, or credential
  changes.
- Restart recovery cannot infer private-network success from deployment history.
- Credentials cleared after task creation must be re-entered, with explicit UI
  notice; they do not enter target files, task stores, URLs, or browser storage.
- Network-task persistence remains a follow-up requirement so an interrupted
  Phase 3 task can be restored independently of deployment history.

## ADR-015: Local Lab Processes Require Owned Runtime Identity

**Status:** Accepted
**Date:** 2026-07-18

### Context

A browser can retain a GenBox page after the Python backend stops, and static
files can be newer than a still-running backend. The previous Windows scripts
also used conflicting ports and terminated whichever process happened to own a
port. These conditions made runtime failures look like SSH password failures.

### Decision

Manage the development Lab through one external launcher on port `8892`. The
launcher writes an atomic, non-secret ownership record containing PID, process
creation time, repository, mode, port, Git HEAD, and source fingerprint. It may
stop only a process whose record, process identity, port ownership, and GenBox
runtime health all match. Any ambiguity fails closed.

Expose a no-store runtime identity only in development mode. Local browser
heartbeats use it to display the loaded runtime and to lock backend-dependent
Extension Center controls when the page is cached, the backend is stopped, or
the loaded source differs. Browser HTTP routes do not stop or restart GenBox.

### Consequences

- A foreign service on `8892`, a reused PID, a corrupt record, or an old source
  snapshot is reported and left untouched.
- One legacy manually started Lab may require explicit identity verification
  and one-time shutdown before the launcher takes ownership.
- Runtime identity contains no credentials, configuration paths, providers, or
  remote host facts and is unavailable in production. Local production UI uses
  the existing non-secret setup-status contract for heartbeat instead.
- Source edits require a Lab restart before their backend behavior can be
  accepted, even when Git HEAD has not changed.

## ADR-016: Tailscale Serve Destinations Use Validated MagicDNS

**Status:** Accepted
**Date:** 2026-07-19

### Context

Tailscale exposes both a node `100.x` address and a MagicDNS name. GenBox
initially discarded the URL returned by `tailscale serve` and rebuilt an HTTP
destination from the raw IP. Peer connectivity succeeded, but the Serve HTTP
router returned 404 because the request did not use the expected MagicDNS host.

### Decision

Use the validated local `100.64.0.0/10` IPv4 address only for peer identity and
reachability. Use the exact validated `.ts.net` MagicDNS name and the configured
Serve port for the VPS application probe, the saved GenBox destination, and all
future Push configuration. The destination validator rejects loopback, public
hosts, raw Tailscale IP URLs, credentials, paths, query strings, fragments,
wrong ports, and MagicDNS names that do not match the current local node.

Do not silently fall back to an IP URL when MagicDNS resolution fails. Report a
DNS-specific recovery action instead, because a fallback could pass a transport
check while saving a destination that later HTTP clients cannot use correctly.

### Consequences

- Phase 4 sender work consumes a stable MagicDNS base URL from Phase 3.
- Device renames, Tailnet changes, disabled MagicDNS, or DNS-policy changes
  require fresh application-level verification before replacing the saved URL.
- Node IPs and DNS names remain non-secret runtime metadata, but real values are
  excluded from stable documentation and public examples.

## ADR-017: Deployment Safety Contract Owns Phase 4 Execution Invariants

**Status:** Accepted
**Date:** 2026-07-22

### Decision

`docs/deployment-invariants.md` is the versioned normative owner for Phase 4
deployment field classification, evidence handling, ownership lifecycle, and
side-effect ordering. Architecture and lifecycle documents link to it rather
than restating its rules. A contract revision requires implementation and a
new independent fixed-commit review before it can support acceptance evidence.

### Consequences

Local/mock results cannot replace isolated-VPS evidence, and no public task,
diagnostic, or browser surface may become an alternate store for operational
identities or secrets.

## ADR-018: Personal Users Pair Through An Existing Trusted SSH Session

**Status:** Accepted
**Date:** 2026-07-23

### Context

The current local Phase 4 implementation requires a user to manually confirm a
canonical SSH host-key algorithm plus `SHA256:` fingerprint before credentials
can be used. That remains a valid fail-closed safety boundary, but asking a
personal user to understand and independently compare a long fingerprint is a
poor default experience. SSH credentials alone cannot prove that GenBox reached
the intended host.

### Decision

The next Phase 4 local increment will implement trusted SSH-session pairing as
the personal-user default for first-time host trust. After the user saves a
target host, port, and username, GenBox will create a short-lived, single-use,
in-memory challenge bound to the saved target identity version and candidate
host-key algorithm/fingerprint pair. The user runs a GenBox-generated fixed,
versioned one-line helper in an SSH terminal session they already trust and
pastes its one-line response into GenBox.

Pairing completion re-probes the host and rejects mismatched identity, expired
or replayed challenge, edited target, unsupported algorithm, malformed response,
or conflict with an existing saved trust record. It persists only the canonical
algorithm/fingerprint pair and never weakens host-key verification. Start and
completion endpoints accept no SSH credential and cause no GenBox remote
command. The helper is backend-owned, never browser-provided shell.

The trusted terminal session or known-host record is an external trust anchor
supplied by the user. It is neither evidence of VPS ownership nor a substitute
for SSH credentials. The existing manual provider-console or known-host check
remains an advanced fallback for users without an accessible, readable,
OpenSSH-compatible trusted session or with custom host-key paths. Cancellation
persists nothing. Provider-account verification is out of scope.

### Consequences

The primary UI can say that server identity has been verified and reserve the
algorithm/fingerprint for advanced details. The pairing challenge, helper,
response, credentials, raw pairing observations, and command text may travel
only through future dedicated authenticated, CSRF-protected pairing endpoints;
their names and paths are unspecified and unimplemented. They must not enter
public task, status, instance, or diagnostic projections; durable target,
TaskStore, or runtime records; ordinary logs; browser storage; screenshots,
URLs; or Git. The canonical trust pair is the only permitted saved outcome.
This is an accepted future implementation contract; it does not claim that
pairing endpoints or a helper exist today. It requires local tests and an
independent fixed-commit review before separately authorized isolated
VPS/browser single-image E2E work resumes.

## ADR-019: Message Channels Are Event-Driven Adapters With Capability-Scoped Commands

**Status:** Accepted
**Date:** 2026-07-23

### Context

Future users want to receive GenBox events and trigger selected actions through
message channels such as Telegram, Feishu, or later approved platforms. These
platforms do not share one auth or delivery model: some favor consumer bot and
login flows, others require tenant or administrator approval, and some separate
their bot and login ecosystems entirely. If GenBox treats them as interchangeable
"chat login" providers or lets them submit free-form commands, message-channel
support would erode the same safety boundaries already established for
deployment, Push, and repair.

### Decision

Future message-channel support will use an event-driven adapter model with four
separate responsibilities:

- a versioned channel registry for capability and risk metadata
- a channel-specific auth broker for binding users or workspaces to external
  message identities
- an outbound event outbox for non-secret notifications
- an authenticated inbound gateway that maps validated callbacks to fixed
  backend-owned GenBox intents

Message-channel identity is not GenBox administrator identity. A channel binding
grants only its explicit capabilities and must not imply deployment ownership,
Push source identity, or repair authorization. Inbound channel actions may call
existing workflows such as saved generation presets, task status lookup, or a
bounded import request, but they may not submit arbitrary shell, unrestricted
VPS commands, or free-form repair mutations.

Platform-specific auth models remain distinct. GenBox must not force Telegram,
Feishu, QQ, or later channels into a fake universal OAuth abstraction that
hides their trust and review differences. The first implementation should prove
one independently verified channel end to end before expanding to additional
channels.

### Consequences

- Message channels become a separate future phase, not a shortcut around Phase 4
  image-transfer evidence.
- Channel tokens, app secrets, signing secrets, callback payloads, and bound
  user identities follow the same secret, logging, browser-storage, and Git
  restrictions as other GenBox credentials.
- Unsupported channels remain explicit planned states until their auth, webhook,
  media, rate-limit, and recovery contracts are implemented.
- High-risk actions may require an additional GenBox confirmation layer even
  after the message channel itself is authenticated.

## ADR-020: Server Connector Is The Future Default, SSH Remains A Working Fallback

**Status:** Accepted
**Date:** 2026-07-27

### Context

The current deployment path can operate through SSH after host identity is
confirmed and a session-only credential is supplied. This is deploy-capable but
asks a beginner to manage a trusted terminal and a temporary credential. A
server connector can eventually offer a simpler model: an agent installed by
the user on the intended server initiates a restricted, authenticated connection
back to GenBox and accepts only capability-scoped operations.

There is no installable agent, authenticated relay/private-network transport,
device enrollment, or allowlisted connector-operation adapter in this release.
Calling a visual placeholder "connected" would block the working Phase 4 path
and create a false security claim.

### Decision

Present the server connector as the preferred future path, with its actual
availability shown explicitly. Until all connector prerequisites exist, the UI
must expose a single obvious SSH continuation and preserve the current SSH
deployment, discovery, safety-plan, and private-network sequence unchanged.

A deploy-capable connector requires all of the following before it can replace
SSH for a target:

- an installable, versioned agent with an independently identifiable device key
- one-time enrollment, expiry, rotation, revocation, and target binding
- an authenticated outbound relay or an established private-network transport
- signed, capability-scoped backend intents and agent-side allowlisted actions
- redacted audit events and no secret-bearing command/output persistence
- adapter-level discovery, deployment, recovery, and local/isolated-VPS tests

GenBox will not embed an interactive web terminal. Browser requests remain
unable to submit arbitrary shell commands. OAuth may be a future cloud-provider
selection or ownership signal for a particular provider, but it is not a
generic replacement for access to arbitrary existing SSH servers.

Whenever SSH is used, canonical host-key algorithm and SHA-256 fingerprint
verification remain mandatory. The connector may simplify credentials, but it
must not silently change the SSH trust model or weaken the existing fail-closed
host-key checks.

### Consequences

The current increment is an honest UI and protocol boundary, not a connector
implementation and not end-to-end server evidence. It makes the primary
product direction visible without delaying Phase 4's existing deploy-capable
route. Connector implementation becomes a separate, testable milestone; its
availability cannot be inferred from copy, a catalog item, an enrollment code,
or a mock state.
