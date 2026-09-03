# Third-Party Notices

GenBox is distributed under **GNU GPL version 3 only**. This file records the
direct runtime and build dependencies included by, or required to build, the
project. Each dependency remains available under its own license; this notice
does not replace the dependency's complete license text.

## Runtime dependencies

| Package | Version | License expression or declared license |
|---|---:|---|
| CPython | 3.12.x release build runtime | Python Software Foundation License Version 2 and included historical notices |
| FastAPI | 0.139.0 | MIT |
| Uvicorn | 0.51.0 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| HTTPX | 0.28.1 | BSD-3-Clause |
| aiofiles | 25.1.0 | Apache-2.0 |
| Requests | 2.34.2 | Apache-2.0 |
| AsyncSSH | 2.24.0 | EPL-2.0 OR GPL-2.0-or-later; GenBox relies on the GPL-compatible option |
| bcrypt | 5.0.0 | Apache-2.0 |
| Pillow | 12.3.0 | MIT-CMU |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| Pydantic | 2.13.4 | MIT |
| pydantic-settings | 2.14.2 | MIT |
| psutil | 7.2.2 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.3 | Apache-2.0 |
| NumPy | 2.4.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| ONNX Runtime | 1.24.3 | MIT |

The bcrypt homepage is <https://github.com/pyca/bcrypt/>. Its installed
distribution includes the complete Apache License 2.0 text. GenBox uses bcrypt
through AsyncSSH to import passphrase-protected OpenSSH private keys. The NumPy
homepage is <https://numpy.org>. Its bundled license identifies
Copyright (c) 2005-2025, NumPy Developers, and records the separately licensed
components included in binary distributions. The ONNX Runtime homepage is
<https://onnxruntime.ai>; its bundled MIT license identifies Copyright (c)
Microsoft Corporation, and its distribution includes additional third-party
notices. Release artifacts carry these installed license files under
`THIRD_PARTY_LICENSES/`; a release build fails if the pinned distributions or
required license assets are missing.

Packaged GenBox builds carry the Python runtime, NumPy, and ONNX Runtime needed
by the local cutout adapter. They do **not** carry the
`u2net_human_seg.onnx` checkpoint. In v2.6.6, production network download and
installation are disabled and fail closed because the checkpoint's provenance
and commercial-use rights remain unverified. The UI and API expose only the
disabled capability/status framework; the browser cannot choose a download URL
or filesystem destination. An operator may manually place the expected model
file, which GenBox accepts only after checking the fixed size, SHA-256, and MD5
values recorded by the local adapter.

The matching fingerprints establish byte identity with the pinned remote asset;
they do not establish the checkpoint's complete conversion history, training-
data provenance, or commercial-use rights. Those three matters remain
**UNVERIFIED**. Users are responsible for confirming that the checkpoint and
its training-data rights are suitable for their intended use before acquiring
or using it. A future network installer must remain disabled until its source
and authorization receive separate approval. The checkpoint remains an external
user-acquired asset and is not redistributed in GenBox source or release
packages.

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
