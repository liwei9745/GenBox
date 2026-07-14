import subprocess
import sys
import zipfile
import hashlib
import json
from pathlib import Path

from genbox_version import __version__


ROOT = Path(__file__).parents[1]


def test_release_version_is_consistent():
    import main
    import updater

    assert main.app.version == __version__
    assert updater.CURRENT_VERSION == __version__
    assert __version__ in (ROOT / "genbox_version.py").read_text(encoding="utf-8")


def test_compose_release_uses_ghcr_and_safe_internal_port():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_template = (ROOT / ".env.docker.example").read_text(encoding="utf-8")

    assert "ghcr.io/liwei9745/genbox:latest" in compose
    assert '${GENBOX_PORT:-8891}:8891' in compose
    assert 'GENBOX_PORT: "8891"' in compose
    assert "./.env:/app/.env" in compose
    assert "build: ." not in compose
    assert "APP_MODE=prod" in env_template
    assert "GENBOX_PORT=8891" in env_template


def test_release_workflow_smoke_tests_clients_and_packages_compose():
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert workflow.count("scripts/smoke_client.py") == 3
    assert "scripts/package_release.py --output artifacts --docker-only" in workflow
    assert "SHA256SUMS.txt" in workflow


def test_packaged_console_output_avoids_ansi_and_emoji_status_markers():
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")

    assert "use_colors=False" in main_source
    assert 'mode_str = "PRODUCTION" if is_prod_mode() else "DEVELOPMENT"' in main_source
    assert "DEVELOPMENT ⚠" not in main_source


def test_public_documentation_uses_current_sanitized_screenshots():
    readmes = "\n".join(
        (ROOT / filename).read_text(encoding="utf-8")
        for filename in ("README.md", "README_EN.md")
    )
    current = {
        "01-dashboard.png",
        "02-generate-workspace.png",
        "03-extension-center.png",
        "04-onboarding.png",
    }

    for filename in current:
        assert f"screenshots/sanitized/{filename}" in readmes
        assert (ROOT / "screenshots" / "sanitized" / filename).is_file()
    assert "02-generate-t2i.png" not in readmes


def test_readme_lab_content_matches_source_readmes():
    payload = json.loads((ROOT / "static" / "readme-lab-content.json").read_text(encoding="utf-8"))
    expected_assets = {
        "upstream-contributors.svg",
        "star-history.svg",
    }

    for language, filename in (("zh", "README.md"), ("en", "README_EN.md")):
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert payload[language]["sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()
        assert "Star History" in payload[language]["markdown"]
        assert "readme-assets" in payload[language]["markdown"]
        for asset in expected_assets:
            assert f"/static/readme-assets/{asset}" in payload[language]["markdown"]
            assert (ROOT / "static" / "readme-assets" / asset).is_file()


def test_docker_bundle_contains_only_public_deployment_files(tmp_path):
    subprocess.run(
        [sys.executable, "scripts/package_release.py", "--output", str(tmp_path), "--docker-only"],
        cwd=ROOT,
        check=True,
    )
    bundle = tmp_path / f"GenBox-Docker-Compose-v{__version__}.zip"
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {
            "docker-compose.yml",
            ".env.example",
            "README.md",
            "LICENSE",
        }
        env_text = archive.read(".env.example").decode("utf-8")
        assert "APP_MODE=prod" in env_text
        assert "replace-with" not in env_text
