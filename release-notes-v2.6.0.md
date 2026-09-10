# GenBox v2.6.0 - Extension Center and Image Push

> v2.6.0 is the stable release for the Extension Center and the authenticated
> image Push receiver. It includes guided chatgpt2api deployment, managed
> Push-source provisioning with an optional encrypted local vault, and single,
> batch, and scheduled incremental image Push receiving into the GenBox media
> library. This release does not include source-file cleanup.

## Which File Should I Download?

| Your system | Recommended download | What to do next |
|---|---|---|
| Windows 10/11 | [GenBox-Windows.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-Windows.zip) | Extract and double-click `GenBox.exe` |
| macOS | [GenBox-macOS.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-macOS.zip) | Extract and run `GenBox-macOS` |
| Linux | [GenBox-Linux-x64.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-Linux-x64.zip) | Extract, add execute permission, and run |
| NAS / VPS / Docker | [GenBox-Docker-Compose-v2.6.0.zip](https://github.com/liwei9745/GenBox/releases/download/v2.6.0/GenBox-Docker-Compose-v2.6.0.zip) | Extract, configure `.env`, and start Compose |

Desktop archives include the runtime; Python is not required. After startup,
open `http://localhost:8891`.

## Included

- Single-image Push receiving into the GenBox media library.
- Manual batch Push receiving with idempotent and deduplicated import.
- Scheduled incremental Push receiving with persisted progress and late-image
  handling.
- Extension Center guided deployment for isolated `chatgpt2api` instances.
- Managed Push-source provisioning: a deployed instance can open its GenBox
  Push configuration, copy it, and keep a newly issued Push key show-once by
  default. Explicit opt-in can save the key, source ID, and URL in the
  encrypted local credential vault; local deletion never changes the remote
  source.
- Packaged-client improvements, including pre-release version ordering for the
  in-app updater.

## Important Limits

- Source-file cleanup is NOT included in this release and remains disabled.
  Push receipts do not grant source-deletion permission.
- Sender-side and upstream delivery for the chatgpt2api integration, and clean
  redeployment evidence, remain pending. This release does not claim an
  end-to-end sender cleanup feature.
- Receiver-side Push verification is recorded in `docs/STATUS.md`; isolated
  sender-side and clean-deployment evidence are separate release gates.

## Evaluation Notes

- Reproduce verification with the local test, JavaScript syntax, README Lab,
  and packaged-client build procedures recorded in `docs/STATUS.md`.
- The rc.1 through rc.8 candidate notes remain historical and do not describe a
  stable release.
- Release artifacts are published when the `v2.6.0` tag is authorized by the
  release coordinator.

## References

- [Changelog](CHANGELOG.md)
- [Current verification status](docs/STATUS.md)