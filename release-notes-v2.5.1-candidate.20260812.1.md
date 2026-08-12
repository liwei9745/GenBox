# GenBox v2.5.1 Candidate 20260812.1

## Experimental Candidate

This is a pre-release candidate for local validation. It is not a stable
release, does not update the `latest` or `stable` container tags, and should
not be used to infer completion of the chatgpt2api sender or remote-deployment
roadmap phases.

## Included Candidate Checks

- Windows packaged-client startup smoke test on a dynamically chosen loopback
  port.
- Docker image and Docker Compose loopback verification with production
  administrator authentication and an independently scoped Push credential.
- Authenticated Push health check, rejected invalid Push credential, idempotent
  image retry, retained local source fixture, and no source-cleanup action.
- Reproducible Docker Compose bundle with published SHA-256 checksum.

## Boundaries

- No VPS, SSH, production chatgpt2api instance, real account, or real image is
  used by candidate verification.
- The candidate image is published only under the candidate tag associated with
  this pre-release; no `latest` or `stable` tag is published.
- The chatgpt2api sender, batch and scheduled Push, receipt-gated source
  cleanup, clean GitHub redeployment, upstream delivery, and additional service
  adapters remain subject to their documented phase gates.

See `docs/STATUS.md` for dated evidence and remaining external gates.
