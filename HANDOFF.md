# GenBox Development Handoff

**Updated:** 2026-08-12
**Candidate source commit:** `c7c514b4bcfbd3c06eca6414605e85b619319dc9`
**Candidate branch:** `codex/v251-candidate-20260812-2`
**Candidate tag:** `v2.5.1-candidate.20260812.2`

The candidate branch contains explicit candidate Compose pinning, administrator
authentication coverage, candidate-safe GitHub Release workflow behavior, and
candidate-only Docker metadata. Final local assets are bound to this source:
Windows SHA-256 `B3C129455957507492753A0125730184ABFDF84E6AD146036B0ED9C852896D9F`,
Compose bundle SHA-256 `C6CD8E979D5EEC71B42B431742E6E50399FF62FAF6D1FB77FFE8B43D44E676AB`,
and local image ID `sha256:ff260a9295efe25602883b11e066dc1294e5644470f6fd1286b78f4ca383ba36`.
The released candidate is a GitHub Pre-release. Its GHCR-only reference is
`ghcr.io/liwei9745/genbox:v2.5.1-candidate.20260812.2` with remote digest
`sha256:b1cd55e40dd772dca739aca44280f78b3568f23e6ab244c1d2a92dd60a7f6405`.
The Desktop Clients Actions run `31570745302` passed on the tagged source;
candidate Docker workflow run `31570745304` was intentionally skipped. Do not
use `latest`, `stable`, VPS/SSH, or restricted ports. Await only a sanitized
handoff from the separate seven-gate task; do not claim its Design Gate or
Phase 6 as complete.

Phase 6-9 remain Planned or In Progress according to `docs/STATUS.md`; local
receiver smoke is not sender, private-network, cleanup, clean-redeployment,
upstream, or adapter evidence.
