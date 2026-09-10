# GenBox v2.6.1 - Controlled Source Deletion Grant (Receiver)

> v2.6.1 is a narrow-scope patch on top of the stable v2.6.0 release. It adds an
> "allow authorized source-image deletion" toggle for managed Push sources in
> the Extension Center, off by default. This release covers only that receiver
> capability and does not include sender-side cleanup.

## Included

- Each managed Push source in the Extension Center gains an "allow authorized
  source-image deletion" toggle, off by default, bilingual (zh-CN/en), with a
  browser-contract test.
- Deletion is granted only when the source is authorized, the receipt carries
  `safe_to_delete_source=true`, and that receipt committed this exact path and
  content for this source (`imported` / `already-imported`).
- `duplicate-local` (same content, different path) never grants deletion.

## Important Limits

- Source files are still not deleted by default; without the grant enabled,
  receipts grant no deletion permission.
- The sender side must still require per-run user selection and re-verify the
  live SHA-256 before any deletion.
- Sender-side / upstream (chatgpt2api) delivery is out of scope for this
  release.
- Evidence that production instances are unchanged is recorded in
  `docs/STATUS.md`.

## Evaluation Notes

- Reproduce verification with the local test, JavaScript syntax, README Lab,
  and packaging build procedures recorded in `docs/STATUS.md`.
- Release artifacts are published when the `v2.6.1` tag is authorized by the
  release coordinator.

## References

- [Changelog](CHANGELOG.md)
- [Current verification status](docs/STATUS.md)
