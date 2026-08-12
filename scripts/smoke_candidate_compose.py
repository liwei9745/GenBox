"""Exercise a loopback-only GenBox candidate container without logging secrets."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import http.client
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

from PIL import Image


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(output, format="PNG")
    return output.getvalue()


def request(url: str, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None):
    request_headers = headers or {}
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, http.client.HTTPException, OSError):
        return 0, b""


def multipart_payload(boundary: str, image: bytes, remote_path: str) -> bytes:
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="image"; filename="candidate.png"\r\n',
        b"Content-Type: image/png\r\n\r\n",
        image,
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="remote_path"\r\n\r\n',
        remote_path.encode("utf-8"),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts)


def wait_for_health(base_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, _ = request(f"{base_url}/api/setup/status")
        if status == 200:
            return
        time.sleep(0.5)
    raise SystemExit("candidate container did not become healthy")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--push-key", required=True)
    parser.add_argument("--admin-key", required=True)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    source_file = args.source_file.resolve()
    image_bytes = png_bytes()
    source_file.write_bytes(image_bytes)
    source_hash = hashlib.sha256(image_bytes).hexdigest()
    wait_for_health(base_url, args.timeout)

    status, _ = request(f"{base_url}/api/status")
    assert status == 401, f"unauthenticated administrator endpoint returned {status}"
    status, _ = request(
        f"{base_url}/api/status",
        headers={"X-Admin-Key": args.admin_key},
    )
    assert status == 200, f"authenticated administrator endpoint returned {status}"

    push_headers = {
        "X-GenBox-Source": args.source_id,
        "X-GenBox-Key": args.push_key,
    }
    status, _ = request(f"{base_url}/api/sync/push/status", headers=push_headers)
    assert status == 200, f"authenticated Push status returned {status}"
    status, _ = request(
        f"{base_url}/api/sync/push/status",
        headers={"X-GenBox-Source": args.source_id, "X-GenBox-Key": "wrong-key"},
    )
    assert status == 401, f"invalid Push credential returned {status}"

    boundary = f"candidate-{uuid4().hex}"
    body = multipart_payload(boundary, image_bytes, "candidate/source.png")
    headers = {
        **push_headers,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    status, response = request(f"{base_url}/api/sync/push", method="POST", body=body, headers=headers)
    assert status == 200, f"first Push returned {status}"
    first = json.loads(response)
    assert first["status"] == "imported", first
    assert first["sha256"] == source_hash, first
    assert first["safe_to_delete_source"] is True, first

    status, response = request(f"{base_url}/api/sync/push", method="POST", body=body, headers=headers)
    assert status == 200, f"idempotent Push returned {status}"
    second = json.loads(response)
    assert second["status"] == "already-imported", second
    assert second["sha256"] == source_hash, second

    # The receiver has no source cleanup operation; retain the local sender fixture.
    assert source_file.read_bytes() == image_bytes
    print("candidate Compose smoke passed: health, admin auth, Push auth, idempotency, source retention, cleanup disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
