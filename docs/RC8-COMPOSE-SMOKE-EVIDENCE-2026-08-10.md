# RC8 Compose Smoke Evidence (2026-08-10)

## Scope

- **Evidence class:** `LOCAL` only, using Docker Engine `29.6.1` and Docker
  Compose `v5.3.0` in the isolated evidence worktree.
- **Candidate image:** built from this checkout's `Dockerfile` with
  `docker build --pull=false`, tag `genbox-rc8-cross-platform-ci:9b5ac7c`,
  image digest
  `sha256:c031e9fde728adad56cf46ac02e082e0c69a7261a8740617af9d1be8f0974ecb`.
- **Isolation:** Compose project `genbox-rc8-smoke-fresh-20260810`, container
  `genbox-compose-smoke-rc8-fresh`, fresh temporary storage, and loopback-only
  publication `127.0.0.1:49231 -> 8891`.
- **Synthetic input:** generated 3x2 PNG, 77 bytes, SHA-256
  `1d71cecf2008f8f1adf4f605e6b380cb780c5027a79c967bba6b7aef794c3495`;
  synthetic administrator key, source ID, and Push key only.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Compose startup and health | `VERIFIED` | Container reached Docker health `healthy`; `/api/setup/status` returned HTTP `200`, `app_mode=prod`, `auth_required=true`. |
| Administrator authentication | `VERIFIED` | `/api/gallery` returned `401` without `X-Admin-Key` and `200` with the synthetic key. |
| Push v1 status probe | `VERIFIED` | Authenticated `/api/sync/push/status` returned HTTP `200` with source identity and contract v1. |
| Authenticated first Push | `VERIFIED` | Multipart `/api/sync/push` returned HTTP `200`, `status=imported`, dimensions `3x2`, and the receipt SHA-256 matched the uploaded bytes. |
| Idempotent retry | `VERIFIED` | Identical request returned HTTP `200`, `status=already-imported`, the same local filename, and the same SHA-256. |
| Source retention | `VERIFIED` | The synthetic source remained present and byte-identical after both requests; both receipts returned `safe_to_delete_source=false`. |
| Cleanup disabled | `VERIFIED` | No cleanup/unlink/execute endpoint was called; no source deletion occurred and the receiver did not grant deletion permission. |
| `33010` / `33018` boundary | `VERIFIED` | Only `127.0.0.1:49231` was published or contacted; no protected-port connection or modification was attempted. |

## Build And Limits

- The local build reused the already cached Python base and did not log into,
  pull from, or push to a registry. No image publication was attempted.
- The disposable Compose project, network, container, temporary storage,
  synthetic `.env`, and PNG were removed after capture.
- This record does not claim hosted Docker CI, registry publication, VPS/SSH,
  sender-side E2E, destructive cleanup, or production mutation.
