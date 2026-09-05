# GenBox Documentation Maintenance Map

## Purpose

Keep documentation useful without turning README or release notes into an
unlimited development diary. The audience-facing hub is
[`docs/README.md`](README.md); this file defines ownership and update rules.

## Documentation Classes

| Class | Audience | Source-of-truth rule | Examples |
|---|---|---|---|
| User guide | People installing or operating GenBox | Describe shipped workflows and current limitations in task language | [README](../README.md), [client quick start](CLIENT-QUICKSTART.md), [Docker quick start](DOCKER-QUICKSTART.md) |
| Release-frozen record | People installing or reviewing one exact release | Freeze after publication except for factual corrections | [v2.6.6 Chinese notes](../release-notes-v2.6.6-zh.md), [English notes](../release-notes-v2.6.6.md) |
| Pinned product or developer contract | Maintainers, contributors, and integrators | Change only when a durable product, architecture, protocol, or safety boundary changes | [product](PRODUCT.md), [architecture](ARCHITECTURE.md), [decisions](DECISIONS.md), [integration](INTEGRATION.md) |
| Rolling current state | Maintainers and auditors | Replace stale claims with dated evidence; do not infer live state from a plan | [status](STATUS.md), [roadmap](ROADMAP.md), [changelog](../CHANGELOG.md) |
| Historical evidence | Auditors and people resuming earlier work | Preserve the original scope and evidence label; never use it as the current product claim | Dated `PHASE*`, preflight, review, and handoff documents |

## User And Release Documents

| Document | Owns | Update trigger |
|---|---|---|
| [`README.md`](../README.md) / [`README_EN.md`](../README_EN.md) | Product positioning, stable release, installation choices, documentation links | A shipped capability, installation path, or stable release changes |
| [`docs/CLIENT-QUICKSTART.md`](CLIENT-QUICKSTART.md) | Windows, macOS, and Linux client startup and local data handling | Client names, startup, first-run flow, or storage location changes |
| [`docs/DOCKER-QUICKSTART.md`](DOCKER-QUICKSTART.md) | Compose configuration, administrator key handling, startup, status, and update | Docker defaults, required environment, image name, or operator commands change |
| [`docs/CUTOUT-MODEL-GUIDE.md`](CUTOUT-MODEL-GUIDE.md) | U²-Net default model installation, fixed fingerprint, upstream sources, and conservative use boundary | Model identity, supported installation paths, verification contract, or rights evidence changes |
| [`docs/MODNET-USER-IMPORT-GUIDE.md`](MODNET-USER-IMPORT-GUIDE.md) | MODNet technically runnable local experiment, user-provided checkpoint import, runtime probe, and non-redistribution boundary | MODNet adapter, manifest, import endpoint, runtime probe, or weight-rights evidence changes |
| [`docs/CUTOUT-ALGORITHM-FEASIBILITY-20260904.md`](CUTOUT-ALGORITHM-FEASIBILITY-20260904.md) | Cross-algorithm status matrix: U²-Net default, MODNet local-only experiment, and fail-closed candidates | Algorithm capability, quality evidence, authorization boundary, or Release packaging decision changes |
| [`docs/CUTOUT-INSPYRENET-FEASIBILITY-20260904.md`](CUTOUT-INSPYRENET-FEASIBILITY-20260904.md) | InSPyReNet candidate evidence and fail-closed integration boundary | InSPyReNet checkpoint, dependency, quality, or authorization evidence changes |
| [`RELEASE_NOTES.md`](../RELEASE_NOTES.md) | Rolling pointer to the latest stable bilingual release notes | A stable release is published or a failed candidate is superseded |
| [`release-notes-v2.6.6-zh.md`](../release-notes-v2.6.6-zh.md) / [`release-notes-v2.6.6.md`](../release-notes-v2.6.6.md) | Frozen v2.6.6 changes, verification scope, packaging, and limitations | Factual correction only after publication |
| In-app Precision Edit `文档说明` | Task-oriented Precision Edit operation help | Workbench interaction or user terminology changes; keep release scope in the current release notes |

Precision Edit documentation must identify U²-Net as the default verified path.
It must not imply that U²-Net or MODNet checkpoints are bundled or available for
production network installation. MODNet may be technically runnable only after a
user-provided import and runtime probe; its real-photo quality and any
commercial/re-distribution rights remain **UNVERIFIED**. InSPyReNet, BiRefNet,
and BRIA RMBG-2.0 remain fail-closed candidates. Local UI or fixture tests do
not establish real Provider, cutout quality, or cross-environment E2E.

## Pinned Contracts

| Document | Owns | Update trigger |
|---|---|---|
| [`docs/PRODUCT.md`](PRODUCT.md) | Product goals, users, journeys, scope, and non-goals | Product direction changes |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Repository boundaries and system architecture | A durable architecture boundary changes |
| [`docs/DECISIONS.md`](DECISIONS.md) | Accepted and superseded technical or security decisions | Add or supersede an ADR; never silently rewrite history |
| [`docs/INTEGRATION.md`](INTEGRATION.md) | GenBox/chatgpt2api protocol and responsibility contract | Identity, request, receipt, cleanup, or cross-project acceptance changes |
| [`docs/chatgpt2api-push-integration.md`](chatgpt2api-push-integration.md) | Push v1 sender/receiver design | Push transport, retry, scheduling, or cleanup design changes |
| [`docs/extensions-deployment-contract.md`](extensions-deployment-contract.md) | Extension deployment acceptance and delivery behavior | Deployment workflow or adapter contract changes |
| [`docs/deployment-invariants.md`](deployment-invariants.md) | Deployment field, evidence, ownership, and side-effect rules | A deployment safety invariant changes |
| [`docs/DEVELOPMENT-LIFECYCLE.md`](DEVELOPMENT-LIFECYCLE.md) | Isolation, sanitization, clean deployment, release, and upstream gates | Delivery authority, environment, release, or safety policy changes |
| [`docs/precision-edit-v4-research.md`](precision-edit-v4-research.md) | Precision Edit submit semantics, interaction contract, capability gates, and tests | Precision Edit request, authorization, interaction, or acceptance rules change |
| [`docs/RELEASE-PACKAGING.md`](RELEASE-PACKAGING.md) | Immutable source packaging, exact-image Docker publication, licenses, and workflow checks | Release build, package contents, provenance, or CI contract changes |

## Rolling And Historical Documents

| Document | Owns | Maintenance rule |
|---|---|---|
| [`docs/STATUS.md`](STATUS.md) | Dated current evidence, blockers, boundaries, and resume point | Compare claims with code/tests; label external facts `VERIFIED`, `UNVERIFIED`, or `USER-CONFIRMED` |
| [`docs/ROADMAP.md`](ROADMAP.md) | Phase order, topic contracts, deliverables, and acceptance criteria | Change phase status only when evidence satisfies its gate |
| [`CHANGELOG.md`](../CHANGELOG.md) | Version-level user-visible changes and `Unreleased` | Add product changes; avoid session narration |
| [`HANDOFF.md`](../HANDOFF.md) | Immediate objective and short resume context | Rewrite after substantial work; never treat it as product truth |

Dated `PHASE*` documents, preflight reports, review matrices, campaign notes,
handoffs, and `.planning/` are historical inputs. They prove only their stated
scope. Local or mocked tests do not establish a real Provider, VPS, source
cleanup, or cross-project E2E result. When historical evidence conflicts with
current sources, use [`PRODUCT.md`](PRODUCT.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md), and especially
[`STATUS.md`](STATUS.md).

## Release Documentation Checklist

1. Update `genbox_version.py` and move completed changelog items into the version.
2. Create Chinese and English versioned release notes.
3. Update README and [`docs/README.md`](README.md) with the stable release and honest capability boundaries.
4. Confirm client and Docker quick starts match the packaged files.
5. Update `docs/STATUS.md` with tests, builds, hosted runs, hashes, and blockers.
6. Update `HANDOFF.md` with the next objective.
7. Run secret, personal-data, link, package-content, license, and clean-install checks.
8. Freeze versioned release notes after publication.
