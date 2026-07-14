"""Generate deterministic README lab content and public image assets."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
ASSET_DIR = STATIC_DIR / "readme-assets"
OUTPUT = STATIC_DIR / "readme-lab-content.json"
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\((screenshots/sanitized/([^)]+))\)")
README_ASSETS = {
    "https://contrib.rocks/image?repo=basketikun/chatgpt2api": (
        ROOT / "screenshots" / "readme" / "upstream-contributors.svg",
        "upstream-contributors.svg",
    ),
    "https://api.star-history.com/svg?repos=liwei9745/GenBox&type=Date": (
        ROOT / "screenshots" / "readme" / "star-history.svg",
        "star-history.svg",
    ),
}


def prepare(markdown_path: Path) -> tuple[str, str]:
    source = markdown_path.read_text(encoding="utf-8")

    def replace_image(match: re.Match[str]) -> str:
        source_path = ROOT / match.group(1)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        destination = ASSET_DIR / match.group(2)
        shutil.copy2(source_path, destination)
        return match.group(0).replace(match.group(1), f"/static/readme-assets/{destination.name}")

    rewritten = IMAGE_PATTERN.sub(replace_image, source)
    for remote_url, (source_path, filename) in README_ASSETS.items():
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        shutil.copy2(source_path, ASSET_DIR / filename)
        rewritten = rewritten.replace(remote_url, f"/static/readme-assets/{filename}")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return rewritten, digest


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for existing in ASSET_DIR.iterdir():
        if existing.is_file():
            existing.unlink()

    documents = {
        "readme": {"zh": ROOT / "README.md", "en": ROOT / "README_EN.md"},
        "release": {
            "zh": ROOT / "release-notes-v2.5.0-zh.md",
            "en": ROOT / "release-notes-v2.5.0.md",
        },
    }
    payload = {}
    for document, language_paths in documents.items():
        payload[document] = {}
        for language, markdown_path in language_paths.items():
            markdown, digest = prepare(markdown_path)
            payload[document][language] = {"sha256": digest, "markdown": markdown}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
