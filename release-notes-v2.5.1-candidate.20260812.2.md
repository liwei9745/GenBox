# GenBox v2.5.1 Candidate 20260812.2

## Experimental Candidate

This is a candidate-only pre-release for local validation. It is not a stable
release and must not be used to infer completion of the chatgpt2api sender,
private-network deployment, cleanup, clean redeployment, upstream delivery, or
additional adapter phases.

Source commit: `37f6191bfccc0c890e4c747b5ba6d930a88e5e3b`.

## Included Candidate Checks

- Windows packaged-client startup smoke on a dynamically selected loopback port.
- Candidate Docker image with explicit OCI source revision and candidate tag.
- Loopback-only Compose smoke covering setup health, administrator
  authentication, Push authentication and rejection, idempotent retry, source
  retention, non-root execution, and cleanup disabled.
- Candidate Compose bundle pinned to the candidate image tag and reproducible
  SHA-256 output.

## Boundaries

- No VPS, SSH, production chatgpt2api instance, real account, real credential,
  real image, or restricted production port was used.
- Only the unique `candidate.20260812.2` GHCR tag is eligible for publication;
  no `latest` or `stable` tag is used.
- Phase 6-9 remain gated by their documented external acceptance criteria.

See `docs/STATUS.md` for the dated evidence ledger and known limitations.
