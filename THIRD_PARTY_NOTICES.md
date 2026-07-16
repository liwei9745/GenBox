# Third-Party Notices

GenBox is distributed under **GNU GPL version 3 only**. This file records the
direct runtime and build dependencies included by, or required to build, the
project. Each dependency remains available under its own license; this notice
does not replace the dependency's complete license text.

## Runtime dependencies

| Package | Version | License expression or declared license |
|---|---:|---|
| FastAPI | 0.139.0 | MIT |
| Uvicorn | 0.51.0 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| HTTPX | 0.28.1 | BSD-3-Clause |
| aiofiles | 25.1.0 | Apache-2.0 |
| Requests | 2.34.2 | Apache-2.0 |
| AsyncSSH | 2.24.0 | EPL-2.0 OR GPL-2.0-or-later; GenBox relies on the GPL-compatible option |
| Pillow | 12.3.0 | MIT-CMU |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| Pydantic | 2.13.4 | MIT |
| pydantic-settings | 2.14.2 | MIT |
| psutil | 7.2.2 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.3 | Apache-2.0 |

## Development and build dependencies

| Package | Version | License note |
|---|---:|---|
| pytest | 9.0.2 | MIT |
| PyInstaller | 6.21.0 | GPL-2.0-or-later with the PyInstaller bootloader exception |

## Source and asset provenance

- The reviewed images under `screenshots/sanitized/` are GenBox screenshots
  captured from isolated empty-data clients. See `screenshots/README.md`.
- `screenshots/readme/star-history.svg` is a labelled public GitHub-data
  snapshot maintained by this repository.
- `screenshots/readme/upstream-contributors.svg` is a generated contributor
  graphic for an acknowledged upstream project. It is not GenBox source code.
- The projects named in the README acknowledgements are references or external
  services. They are not redistributed as part of the GenBox source package.

When adding copied code, bundled assets, or a third-party service artifact,
record its exact source, copyright notice, license, and distribution terms here
before publishing it in a GenBox release.
