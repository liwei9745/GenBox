# GenBox Development Handoff

**Updated:** 2026-07-22
**Current phase:** Phase 4 Single-Image Push — **In Progress**

Read `AGENTS.md`, then `docs/STATUS.md`, the Phase 4 section of
`docs/ROADMAP.md`, and its explicit topic contracts. The immediate blocker is
local implementation of [Deployment Safety Contract v3](docs/deployment-invariants.md)
against GenBox candidate `21972ff89419acb80288efdfdaa8750b7809a136`.

The candidate is locally self-checked but independently **BLOCKED** pending the
contract-driven safety fixes and focused tests. The sender implementation exists
at `f4a327d5599b020c66d4aab041a5fa0035d5effe`; real isolated-VPS/browser
single-image E2E remains **UNVERIFIED**. Do not deploy, discover a VPS, mutate
production, push, release, or publish without separate authorization.

Phase 4 does not include batch/scheduling (Phase 5), cleanup (Phase 6), or
clean redeploy/upstream publication. Preserve host-key verification, production
read-only treatment, isolated resources, secret hygiene, separate keys, and
receipt/SHA-256/`safe_to_delete_source`/opt-in deletion gating.
