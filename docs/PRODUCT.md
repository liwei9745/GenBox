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
