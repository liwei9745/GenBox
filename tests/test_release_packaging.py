import subprocess
import sys
import zipfile
import hashlib
import io
import json
import re
from pathlib import Path

import pytest

from genbox_version import __version__


ROOT = Path(__file__).parents[1]

SOURCE_IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
SOURCE_IMAGE_PREFIXES = ("docs/screenshots/", "screenshots/", "static/")
SOURCE_IMAGE_METADATA_KEYS = {"jfif", "jfif_density", "jfif_unit", "jfif_version"}
SOURCE_FORBIDDEN_BINARY_SUFFIXES = {
    ".7z",
    ".bin",
    ".db",
    ".dll",
    ".dylib",
    ".exe",
    ".gz",
    ".onnx",
    ".pyc",
    ".so",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".zip",
}
SOURCE_RUNTIME_DATA_NAMES = {
    "credential_vault.json",
    "gallery.json",
    "media_index.json",
    "providers.json",
    "sync_manifest.json",
    "vault.json",
}
SOURCE_SYNTHETIC_USERS = {
    "changed-user",
    "deploy-user",
    "operator",
    "private",
    "sentinel-user",
    "someone",
    "ubuntu",
}
SOURCE_TEST_PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"
SOURCE_TEST_WINDOWS_ROOT = "C:" + "\\Users\\"
SOURCE_LOCAL_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}(?P<user>[A-Za-z0-9._-]+)[^\s`\"<>]*"),
    re.compile(r"/(?:home|Users)/(?P<user>[A-Za-z0-9._-]+)[^\s`\"<>]*"),
)
SOURCE_SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "openai_token": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}"),
    "tailscale_key": re.compile(r"tskey-[A-Za-z0-9_-]{20,}"),
    "bearer_literal": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "url_credential": re.compile(
        r"https?://[^\s\"']*[?&](?:key|token|api_key|access_token|password)="
        r"[^&\s\"']{8,}"
    ),
}


def _is_controlled_archive_fixture(category, archive_name, value):
    if not archive_name.startswith("tests/"):
        return False
    if category == "private_key":
        return (
            archive_name == "tests/test_extension_task_store.py"
            and value == SOURCE_TEST_PRIVATE_KEY_MARKER
        )
    if category == "bearer_literal":
        return archive_name == "tests/test_provider_error_safety.py" and value.startswith(
            "Bearer synthetic"
        )
    if category == "url_credential":
        return any(
            marker in value
            for marker in (".example/", ".invalid/", ".test/", "synthetic", "redirect-secret")
        )
    return False


def _assert_source_archive_sanitized(archive_path):
    from PIL import Image

    violations = []
    scanned_text_files = 0
    scanned_images = 0
    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        assert not any(name.startswith("docs/PHASE10") for name in names)
        assert not any(name.startswith("docs/PHASE7-SCAN-REPORT-") for name in names)
        assert not any(
            name == ".env"
            or name.startswith((".planning/", ".pytest", "storage/"))
            or Path(name).name in {"HANDOFF.md", "REVIEW.md"}
            or Path(name).name in SOURCE_RUNTIME_DATA_NAMES
            for name in names
        )

        for name in names:
            suffix = Path(name).suffix.lower()
            data = archive.read(name)
            if suffix in SOURCE_IMAGE_SUFFIXES:
                assert name.startswith(SOURCE_IMAGE_PREFIXES)
                with Image.open(io.BytesIO(data)) as image:
                    assert not image.getexif(), name
                    assert set(image.info) <= SOURCE_IMAGE_METADATA_KEYS, name
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                scanned_images += 1
                continue
            if suffix in SOURCE_FORBIDDEN_BINARY_SUFFIXES:
                violations.append(f"forbidden_binary:{name}")
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                violations.append(f"unexpected_binary:{name}")
                continue

            scanned_text_files += 1
            for pattern in SOURCE_LOCAL_PATH_PATTERNS:
                for match in pattern.finditer(text):
                    if not (
                        name.startswith("tests/")
                        and match.group("user") in SOURCE_SYNTHETIC_USERS
                    ):
                        violations.append(f"local_path:{name}")
            for category, pattern in SOURCE_SECRET_PATTERNS.items():
                for match in pattern.finditer(text):
                    if not _is_controlled_archive_fixture(category, name, match.group(0)):
                        violations.append(f"{category}:{name}")

    assert not violations, sorted(set(violations))
    return {"images": scanned_images, "text_files": scanned_text_files}


def test_release_version_is_consistent():
    import main
    import updater

    assert main.app.version == __version__
    assert updater.CURRENT_VERSION == __version__
    assert __version__ in (ROOT / "genbox_version.py").read_text(encoding="utf-8")
    assert __version__ == "2.6.5"


def test_compose_release_uses_ghcr_and_safe_internal_port():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_template = (ROOT / ".env.docker.example").read_text(encoding="utf-8")

    stable_image = "ghcr.io/liwei9745/genbox:2.6.5"
    assert f"GENBOX_IMAGE:-{stable_image}" in compose
    assert f"GENBOX_IMAGE={stable_image}" in env_template
    assert "ghcr.io/liwei9745/genbox:latest" not in compose
    assert "ghcr.io/liwei9745/genbox:latest" not in env_template
    assert '${GENBOX_PORT:-8891}:8891' in compose
    assert 'GENBOX_PORT: "8891"' in compose
    assert "./.env:/app/.env" in compose
    assert "build: ." not in compose
    assert "APP_MODE=prod" in env_template
    assert "GENBOX_PORT=8891" in env_template
    assert "\nADMIN_KEY=\n" in env_template


def test_docker_quickstart_requires_user_supplied_admin_key_without_log_delivery():
    guide = (ROOT / "docs" / "DOCKER-QUICKSTART.md").read_text(encoding="utf-8")
    normalized = guide.lower()

    assert "defaults to production mode" in normalized
    assert "user-supplied `admin_key`" in normalized
    assert "missing or blank value fails closed" in normalized
    assert "refuses to start" in normalized
    assert "does not generate or deliver this key" in normalized
    assert "loopback interface" in normalized
    assert "not the docker default" in normalized
    assert "first startup creates an administrator key" not in normalized
    assert "generated key" not in normalized
    assert re.search(
        r"(?:administrator key|admin_key).{0,120}docker compose logs|"
        r"docker compose logs.{0,120}(?:administrator key|admin_key)",
        normalized,
        re.DOTALL,
    ) is None


def test_release_workflow_smoke_tests_clients_and_packages_compose():
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert workflow.count("scripts/smoke_client.py") == 3
    assert workflow.count("--runtime-import-smoke") == 3
    assert workflow.count("--version") == 3
    assert workflow.count("mktemp -d") == 2
    assert "RUNNER_TEMP" in workflow
    assert "needs: release-contract" in workflow
    assert workflow.count("needs: [release-contract, quality]") == 3
    assert "needs: [release-contract, build-windows, build-macos, build-linux]" in workflow
    assert '--validate-release-tag "${{ github.ref_name }}"' in workflow
    assert "scripts/package_release.py --output artifacts" in workflow
    assert '--source-commit "${{ github.sha }}"' in workflow
    assert '"${{ env.APP_NAME }}-Source-"*.zip' in workflow
    assert "artifacts/${{ env.APP_NAME }}-Source-*.zip" in workflow
    assert "SHA256SUMS.txt" in workflow
    assert workflow.count("cp COPYRIGHT") == 3
    assert workflow.count("cp THIRD_PARTY_NOTICES.md") == 3
    for platform_name, artifact_name in (
        ("windows", "release-windows"),
        ("macos", "release-macos"),
        ("linux", "release-linux"),
    ):
        assert f"cp -R artifacts/{platform_name}/THIRD_PARTY_LICENSES " in workflow
        assert f"artifacts/{artifact_name}/" in workflow
    assert workflow.count("dist/THIRD_PARTY_LICENSES") == 3
    assert "--licenses-dir artifacts/linux/THIRD_PARTY_LICENSES" in workflow


def test_cutout_runtime_dependencies_are_in_all_distribution_paths():
    from scripts.third_party_licenses import RUNTIME_LICENSES

    runtime_requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    cutout_requirements = (ROOT / "requirements-cutout.txt").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "-r requirements-cutout.txt" in runtime_requirements
    assert "onnxruntime==1.24.3" in cutout_requirements
    assert "numpy==2.4.3" in cutout_requirements
    for filename in ("requirements-dev.txt", "requirements-build.txt"):
        assert "-r requirements.txt" in (ROOT / filename).read_text(encoding="utf-8")
    assert "COPY requirements.txt requirements-cutout.txt ./" in dockerfile
    assert "pip install -r requirements.txt" in dockerfile
    assert "storage/" in dockerignore
    assert (
        "| NumPy | 2.4.3 | "
        "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |"
    ) in notices
    assert "| ONNX Runtime | 1.24.3 | MIT |" in notices
    assert "https://numpy.org" in notices
    assert "https://onnxruntime.ai" in notices
    assert "NumPy Developers" in notices
    assert "Microsoft Corporation" in notices

    requirement_versions = dict(
        re.findall(r"^(numpy|onnxruntime)==([^\s]+)$", cutout_requirements, re.MULTILINE)
    )
    assert requirement_versions == {
        name: contract["version"] for name, contract in RUNTIME_LICENSES.items()
    }
    notice_versions = {
        "numpy": re.search(r"^\| NumPy \| ([^| ]+) \|", notices, re.MULTILINE).group(1),
        "onnxruntime": re.search(
            r"^\| ONNX Runtime \| ([^| ]+) \|", notices, re.MULTILINE
        ).group(1),
    }
    assert notice_versions == requirement_versions


def test_desktop_build_collects_cutout_runtime_without_bundling_model(tmp_path, monkeypatch):
    import build as desktop_build
    from image_tools.cutout_onnx import MODEL_FILENAME

    assert "numpy" in desktop_build.HIDDEN_IMPORTS
    assert "onnxruntime" in desktop_build.HIDDEN_IMPORTS
    assert "onnxruntime" in desktop_build.COLLECT_ALL_PACKAGES
    assert "numpy" in desktop_build.COLLECT_ALL_PACKAGES
    assert "numpy" not in desktop_build.EXCLUDES
    assert all("storage" not in source.replace("\\", "/").split("/") for source, _ in desktop_build.DATA_FILES)
    assert MODEL_FILENAME not in (ROOT / "build.py").read_text(encoding="utf-8")

    captured = {}

    def fake_run(command, capture_output=False):
        captured["command"] = command
        captured["capture_output"] = capture_output
        runtime_hook_argument = next(
            argument for argument in command if argument.startswith("--runtime-hook=")
        )
        captured["runtime_hook"] = Path(runtime_hook_argument.split("=", 1)[1]).read_text(
            encoding="utf-8"
        )
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(desktop_build.subprocess, "run", fake_run)
    desktop_build.build()

    assert "--hidden-import=numpy" in captured["command"]
    assert "--hidden-import=onnxruntime" in captured["command"]
    assert "--collect-all=onnxruntime" in captured["command"]
    assert "--collect-all=numpy" in captured["command"]
    hook_text = captured["runtime_hook"]
    assert "--version" in hook_text
    assert "--runtime-import-smoke" in hook_text
    for module in desktop_build.PACKAGED_RUNTIME_IMPORTS:
        assert repr(module) in hook_text
    assert '"numpy": "2.4.3"' in hook_text
    assert '"onnxruntime": "1.24.3"' in hook_text
    assert any("THIRD_PARTY_LICENSES" in argument for argument in captured["command"])
    spec_text = (tmp_path / "GenBox.spec").read_text(encoding="utf-8")
    assert "collect_all" in spec_text
    assert "THIRD_PARTY_LICENSES" in spec_text
    assert MODEL_FILENAME not in spec_text
    assert (tmp_path / "dist" / "THIRD_PARTY_LICENSES" / "numpy" / "LICENSE.txt").is_file()
    assert (tmp_path / "dist" / "THIRD_PARTY_LICENSES" / "onnxruntime" / "LICENSE").is_file()
    assert (
        tmp_path
        / "dist"
        / "THIRD_PARTY_LICENSES"
        / "onnxruntime"
        / "ThirdPartyNotices.txt"
    ).is_file()


def test_failed_desktop_build_leaves_no_license_sidecar(tmp_path, monkeypatch):
    import build as desktop_build

    def fake_run(command, capture_output=False):
        return type("Completed", (), {"returncode": 1})()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(desktop_build.subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        desktop_build.build()

    assert not (tmp_path / "dist" / "THIRD_PARTY_LICENSES").exists()


def test_docker_workflow_validates_release_identity_before_build_and_push():
    workflow = (ROOT / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8")

    assert "release-contract:" in workflow
    assert "name: Validate release identity" in workflow
    assert "if: github.ref_type == 'tag'" in workflow
    assert '--validate-release-tag "${{ github.ref_name }}"' in workflow
    assert "needs: release-contract" in workflow
    assert workflow.index("release-contract:") < workflow.index("  build:")
    assert workflow.index("needs: release-contract") < workflow.index(
        "Log in to Container Registry"
    )


def test_docker_workflow_smokes_and_pushes_one_exact_build():
    workflow = (ROOT / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert workflow.count("uses: docker/build-push-action@v6") == 1
    assert "load: true" in workflow
    assert "push: false" in workflow
    assert "docker build " not in workflow
    assert "steps.build.outputs.imageid" in workflow
    assert 'docker run --rm --entrypoint python "$RELEASE_IMAGE_ID"' in workflow
    assert "assert numpy.__version__ == '2.4.3'" in workflow
    assert "assert onnxruntime.__version__ == '1.24.3'" in workflow
    assert "import main" in workflow
    assert 'docker inspect --format \'{{.Image}}\'' in workflow
    assert '"http://127.0.0.1:${host_port}/api/setup/status"' in workflow
    assert 'docker image inspect --format \'{{.Id}}\' "$tag"' in workflow
    assert 'docker push "$tag"' in workflow
    build_index = workflow.index("Build Docker image once for smoke and publish")
    runtime_smoke_index = workflow.index("Smoke test exact built image runtime imports")
    http_smoke_index = workflow.index("Smoke test exact built image over HTTP")
    push_index = workflow.index("Push smoke-tested Docker image without rebuilding")
    assert build_index < runtime_smoke_index < http_smoke_index < push_index
    assert workflow.index("RELEASE_IMAGE_ID: ${{ steps.build.outputs.imageid }}") < workflow.index(
        'docker push "$tag"'
    )
    assert "FROM python:3.12-slim" in dockerfile
    assert "COPY requirements.txt requirements-cutout.txt ./" in dockerfile
    assert "RUN pip install -r requirements.txt" in dockerfile


def test_pinned_runtime_license_assets_are_collected_from_distribution_metadata(tmp_path):
    from scripts.third_party_licenses import collect_runtime_licenses

    destination = collect_runtime_licenses(tmp_path / "THIRD_PARTY_LICENSES")
    manifest = json.loads((destination / "MANIFEST.json").read_text(encoding="utf-8"))

    assert manifest == {
        "schema_version": 1,
        "distributions": [
            {
                "name": "numpy",
                "version": "2.4.3",
                "files": ["numpy/LICENSE.txt"],
            },
            {
                "name": "onnxruntime",
                "version": "1.24.3",
                "files": [
                    "onnxruntime/LICENSE",
                    "onnxruntime/ThirdPartyNotices.txt",
                ],
            },
        ],
    }
    assert "NumPy Developers" in (destination / "numpy" / "LICENSE.txt").read_text(
        encoding="utf-8"
    )
    assert "Microsoft Corporation" in (destination / "onnxruntime" / "LICENSE").read_text(
        encoding="utf-8"
    )
    assert (destination / "onnxruntime" / "ThirdPartyNotices.txt").stat().st_size > 0


def test_runtime_license_collection_rejects_version_drift(tmp_path, monkeypatch):
    import scripts.third_party_licenses as licenses

    real_distribution = licenses.importlib.metadata.distribution

    class DriftedDistribution:
        def __init__(self, distribution):
            self._distribution = distribution
            self.metadata = distribution.metadata
            self.version = "0.0.0"

    def drift_numpy(name):
        distribution = real_distribution(name)
        return DriftedDistribution(distribution) if name == "numpy" else distribution

    monkeypatch.setattr(licenses.importlib.metadata, "distribution", drift_numpy)
    with pytest.raises(RuntimeError, match="numpy==2.4.3"):
        licenses.collect_runtime_licenses(tmp_path / "THIRD_PARTY_LICENSES")


def test_runtime_license_collection_checks_release_platform(monkeypatch):
    import scripts.third_party_licenses as licenses

    assert licenses.MINIMUM_PYTHON == (3, 11)
    monkeypatch.setattr(licenses.platform, "system", lambda: "UnsupportedOS")
    with pytest.raises(RuntimeError, match="unsupported release platform"):
        licenses.validate_build_platform()


def test_packaged_console_output_avoids_ansi_and_emoji_status_markers():
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")

    assert "use_colors=False" in main_source
    assert 'mode_str = "PRODUCTION" if is_prod_mode() else "DEVELOPMENT"' in main_source
    assert "DEVELOPMENT ⚠" not in main_source


def test_public_documentation_uses_current_sanitized_screenshots():
    expected = {
        "README.md": {
            "01-dashboard.png",
            "02-generate-workspace.png",
            "03-extension-center.png",
            "04-onboarding.png",
        },
        "README_EN.md": {
            "en-01-dashboard.png",
            "en-02-generate-workspace.png",
            "en-03-extension-center.png",
            "en-04-onboarding.png",
        },
    }

    for readme_name, screenshots in expected.items():
        readme = (ROOT / readme_name).read_text(encoding="utf-8")
        for filename in screenshots:
            assert f"screenshots/sanitized/{filename}" in readme
            assert (ROOT / "screenshots" / "sanitized" / filename).is_file()
        assert "02-generate-t2i.png" not in readme

    assert "en-01-dashboard.png" not in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "screenshots/sanitized/01-dashboard.png" not in (ROOT / "README_EN.md").read_text(encoding="utf-8")


def test_release_notes_lead_with_download_and_first_run_guidance():
    for filename in ("release-notes-v2.5.0-zh.md", "release-notes-v2.5.0.md"):
        notes = (ROOT / filename).read_text(encoding="utf-8")
        visible_lead = notes.split("<details>", 1)[0]
        assert "GenBox-Windows.zip" in visible_lead
        assert "GenBox-macOS.zip" in visible_lead
        assert "GenBox-Linux-x64.zip" in visible_lead
        assert "GenBox-Docker-Compose-v2.5.0.zip" in visible_lead
        assert "http://localhost:8891" in visible_lead
        assert "v2.4.1" in visible_lead


def test_current_release_notes_are_versioned_and_linked_from_the_rolling_page():
    rolling_notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")

    release_state = re.search(
        r"^# GenBox v2\.6\.5 \((Release Candidate|Stable)\)$",
        rolling_notes,
        re.MULTILINE,
    )
    assert release_state is not None
    unreleased_claim = "No v2.6.5 tag or GitHub Release is claimed yet"
    assert (unreleased_claim in rolling_notes) is (
        release_state.group(1) == "Release Candidate"
    )
    assert "release-notes-v2.6.5.md" in rolling_notes
    assert "release-notes-v2.6.5-zh.md" in rolling_notes

    for filename in ("release-notes-v2.6.5.md", "release-notes-v2.6.5-zh.md"):
        notes = (ROOT / filename).read_text(encoding="utf-8")
        assert "2.6.5" in notes
        assert "2026-09-03" in notes


def test_release_candidate_version_ordering_is_supported():
    from updater import compare_versions

    assert compare_versions("2.6.0-rc.1", "v2.6.0-rc.2")
    assert compare_versions("2.6.0-rc.1", "v2.6.0")
    assert not compare_versions("2.6.0", "v2.6.0-rc.1")


def test_release_tag_must_match_packaged_version_exactly():
    from scripts.package_release import SourcePackagingError, validate_release_tag

    validate_release_tag("v2.6.5", "2.6.5")
    with pytest.raises(SourcePackagingError, match="does not match"):
        validate_release_tag("v2.6.6", "2.6.5")
    with pytest.raises(SourcePackagingError, match="canonical v-prefixed"):
        validate_release_tag("2.6.5", "2.6.5")


def test_readme_lab_content_matches_source_documents():
    payload = json.loads((ROOT / "static" / "readme-lab-content.json").read_text(encoding="utf-8"))
    lab = (ROOT / "static" / "readme-lab.html").read_text(encoding="utf-8")
    expected_assets = {
        "upstream-contributors.svg",
        "star-history.svg",
    }

    sources = {
        "readme": {"zh": "README.md", "en": "README_EN.md"},
        "release": {"zh": "release-notes-v2.6.0-zh.md", "en": "release-notes-v2.6.0.md"},
    }
    assert 'id="document"' in lab
    assert "state.payload[state.document][state.language]" in lab
    assert "Release v2.6.0" in lab
    for document, languages in sources.items():
        for language, filename in languages.items():
            source = (ROOT / filename).read_text(encoding="utf-8")
            item = payload[document][language]
            assert item["sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()
            if document == "readme":
                assert "readme-assets" in item["markdown"]

    for language in ("zh", "en"):
        markdown = payload["readme"][language]["markdown"]
        assert "Star History" in markdown
        for asset in expected_assets:
            assert f"/static/readme-assets/{asset}" in markdown
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
        expected_license_assets = {
            "THIRD_PARTY_LICENSES/MANIFEST.json",
            "THIRD_PARTY_LICENSES/numpy/LICENSE.txt",
            "THIRD_PARTY_LICENSES/onnxruntime/LICENSE",
            "THIRD_PARTY_LICENSES/onnxruntime/ThirdPartyNotices.txt",
        }
        assert set(archive.namelist()) == {
            "docker-compose.yml",
            ".env.example",
            "README.md",
            "LICENSE",
            "COPYRIGHT",
            "THIRD_PARTY_NOTICES.md",
            *expected_license_assets,
        }
        assert not any(name.lower().endswith(".onnx") for name in archive.namelist())
        env_text = archive.read(".env.example").decode("utf-8")
        assert "APP_MODE=prod" in env_text
        assert "replace-with" not in env_text
        packaged_notices = archive.read("THIRD_PARTY_NOTICES.md").decode("utf-8")
        assert "| NumPy | 2.4.3 |" in packaged_notices
        assert "| ONNX Runtime | 1.24.3 | MIT |" in packaged_notices
        for name in expected_license_assets:
            assert archive.getinfo(name).file_size > 0

    second_output = tmp_path / "repeat"
    subprocess.run(
        [sys.executable, "scripts/package_release.py", "--output", str(second_output), "--docker-only"],
        cwd=ROOT,
        check=True,
    )
    repeated_bundle = second_output / bundle.name
    assert hashlib.sha256(bundle.read_bytes()).digest() == hashlib.sha256(
        repeated_bundle.read_bytes()
    ).digest()


def _git_fixture(tmp_path, files):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Packaging Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "packaging-test@example.invalid"],
        cwd=repo,
        check=True,
    )
    for name, contents in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, bytes):
            path.write_bytes(contents)
        else:
            path.write_text(contents, encoding="utf-8")
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=repo, check=True)
    return repo, subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_source_export_policy_excludes_internal_evidence_and_scans_archive(
    tmp_path, monkeypatch
):
    from PIL import Image
    from scripts import package_release

    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for rule in (
        ".planning/ export-ignore",
        "HANDOFF.md export-ignore",
        "REVIEW.md export-ignore",
        "docs/PHASE10*.md export-ignore",
        "docs/PHASE7-SCAN-REPORT-*.md export-ignore",
    ):
        assert rule in attributes

    image_buffer = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(image_buffer, format="PNG")
    repo, frozen_commit = _git_fixture(
        tmp_path,
        {
            ".gitattributes": attributes,
            ".planning/STATE.md": SOURCE_TEST_WINDOWS_ROOT + "release-user\\private.txt\n",
            "HANDOFF.md": "ghp_" + "a" * 30 + "\n",
            "REVIEW.md": SOURCE_TEST_PRIVATE_KEY_MARKER + "\n",
            "docs/PHASE10-EVIDENCE-REVIEW-20260823.md": (
                SOURCE_TEST_WINDOWS_ROOT + "release-user\\AppData\\Local\\evidence\n"
            ),
            "docs/PHASE10B-EVIDENCE-MATRIX-20260823.md": "tskey-secret-material\n",
            "docs/PHASE7-SCAN-REPORT-20260820.md": SOURCE_TEST_PRIVATE_KEY_MARKER + "\n",
            "docs/PHASE5-EVIDENCE-2026-08-01.md": "retained historical evidence\n",
            "docs/PRODUCT.md": "public product contract\n",
            "docs/ARCHITECTURE.md": "public architecture contract\n",
            "docs/ROADMAP.md": "public roadmap\n",
            "docs/STATUS.md": "public status\n",
            "docs/RELEASE-PACKAGING.md": "public release contract\n",
            "static/assets/test.png": image_buffer.getvalue(),
            "tests/synthetic_paths.py": (
                'WINDOWS = r"C:\\Users\\someone\\image.png"\n'
                'UNIX = "/home/deploy-user/image.png"\n'
            ),
        },
    )
    monkeypatch.setattr(package_release, "ROOT", repo)
    sidecar = tmp_path / "license.txt"
    sidecar.write_text("license\n", encoding="utf-8")
    archive_path = tmp_path / "source.zip"
    package_release.write_source_archive(
        archive_path,
        frozen_commit,
        [(sidecar, "THIRD_PARTY_LICENSES/license.txt")],
    )

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        for public_document in (
            "docs/PRODUCT.md",
            "docs/ARCHITECTURE.md",
            "docs/ROADMAP.md",
            "docs/STATUS.md",
            "docs/RELEASE-PACKAGING.md",
            "docs/PHASE5-EVIDENCE-2026-08-01.md",
        ):
            assert public_document in names
        assert not any(name.startswith("docs/PHASE10") for name in names)

    scan = _assert_source_archive_sanitized(archive_path)
    assert scan == {"images": 1, "text_files": 9}


@pytest.mark.parametrize(
    ("archive_name", "contents"),
    [
        (
            "docs/leaked-path.md",
            SOURCE_TEST_WINDOWS_ROOT + "release-user\\private.txt\n",
        ),
        ("docs/leaked-secret.md", "ghp_" + "a" * 30 + "\n"),
        ("storage/credential_vault.json", "{}\n"),
        ("models/cutout.onnx", b"\x00onnx"),
    ],
)
def test_source_archive_scan_rejects_private_or_runtime_payloads(
    tmp_path, archive_name, contents
):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(archive_name, contents)

    with pytest.raises(AssertionError):
        _assert_source_archive_sanitized(archive_path)


def test_source_bundle_includes_pinned_runtime_license_assets(tmp_path):
    from scripts import package_release
    from scripts.third_party_licenses import collect_runtime_licenses

    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    licenses = collect_runtime_licenses(tmp_path / "THIRD_PARTY_LICENSES")
    package_release.write_source_archive(
        tmp_path / f"GenBox-Source-v{__version__}.zip",
        source_commit,
        package_release.license_entries(licenses),
    )
    bundle = tmp_path / f"GenBox-Source-v{__version__}.zip"
    with zipfile.ZipFile(bundle) as archive:
        assert not any(name.lower().endswith(".onnx") for name in archive.namelist())
        assert archive.getinfo("THIRD_PARTY_LICENSES/numpy/LICENSE.txt").file_size > 0
        assert archive.getinfo("THIRD_PARTY_LICENSES/onnxruntime/LICENSE").file_size > 0
        assert archive.getinfo(
            "THIRD_PARTY_LICENSES/onnxruntime/ThirdPartyNotices.txt"
        ).file_size > 0
        manifest = json.loads(archive.read("THIRD_PARTY_LICENSES/MANIFEST.json"))
        versions = {item["name"]: item["version"] for item in manifest["distributions"]}
        assert versions == {"numpy": "2.4.3", "onnxruntime": "1.24.3"}


def test_source_packaging_rejects_dirty_worktree(tmp_path, monkeypatch, capsys):
    from scripts import package_release

    repo, source_commit = _git_fixture(tmp_path, {"tracked.txt": "base\n"})
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    monkeypatch.setattr(package_release, "ROOT", repo)
    output = tmp_path / "artifacts"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "package_release.py",
            "--output",
            str(output),
            "--source-commit",
            source_commit,
        ],
    )

    assert package_release.main() == 2
    assert "source archive requires a clean worktree" in capsys.readouterr().err
    assert not output.exists()


def test_source_packaging_requires_explicit_frozen_commit():
    from scripts import package_release

    with pytest.raises(package_release.SourcePackagingError, match="--source-commit <sha>"):
        package_release.resolve_source_commit(None)


def test_source_packaging_rejects_head_omitting_new_uncommitted_file(
    tmp_path, monkeypatch, capsys
):
    from scripts import package_release

    repo, source_commit = _git_fixture(tmp_path, {"tracked.txt": "base\n"})
    (repo / "new-release-file.txt").write_text("must be committed\n", encoding="utf-8")
    monkeypatch.setattr(package_release, "ROOT", repo)
    output = tmp_path / "artifacts"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "package_release.py",
            "--output",
            str(output),
            "--source-commit",
            source_commit,
        ],
    )

    assert package_release.main() == 2
    error = capsys.readouterr().err
    assert "--source-commit <sha>" in error
    assert "new-release-file.txt" in error
    assert not output.exists()


def test_source_packaging_rejects_revision_that_is_not_current_head(tmp_path, monkeypatch):
    from scripts import package_release

    repo, first_commit = _git_fixture(tmp_path, {"tracked.txt": "base\n"})
    (repo / "tracked.txt").write_text("second\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "second"], cwd=repo, check=True)
    monkeypatch.setattr(package_release, "ROOT", repo)

    with pytest.raises(package_release.SourcePackagingError, match="does not match HEAD"):
        package_release.resolve_source_commit(first_commit)


def test_source_packaging_accepts_frozen_commit_with_new_files(tmp_path, monkeypatch):
    from scripts import package_release

    repo, _ = _git_fixture(tmp_path, {"tracked.txt": "base\n"})
    (repo / "new-release-file.txt").write_text("frozen\n", encoding="utf-8")
    subprocess.run(["git", "add", "new-release-file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "freeze"], cwd=repo, check=True)
    frozen_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    monkeypatch.setattr(package_release, "ROOT", repo)

    assert package_release.resolve_source_commit(frozen_commit) == frozen_commit
    sidecar = tmp_path / "license.txt"
    sidecar.write_text("license\n", encoding="utf-8")
    archive_path = tmp_path / "source.zip"
    package_release.write_source_archive(
        archive_path,
        frozen_commit,
        [(sidecar, "THIRD_PARTY_LICENSES/license.txt")],
    )

    with zipfile.ZipFile(archive_path) as archive:
        expected = subprocess.check_output(
            ["git", "cat-file", "blob", f"{frozen_commit}:new-release-file.txt"], cwd=repo
        )
        assert archive.read("new-release-file.txt") == expected
        assert archive.read("THIRD_PARTY_LICENSES/license.txt") == sidecar.read_bytes()


def test_source_zip_matches_frozen_commit_tree_plus_license_sidecar(tmp_path, monkeypatch):
    from scripts import package_release

    repo, frozen_commit = _git_fixture(
        tmp_path,
        {"README.txt": "readme\n", "nested/source.py": "print('ok')\n"},
    )
    monkeypatch.setattr(package_release, "ROOT", repo)
    sidecar = tmp_path / "license.txt"
    sidecar.write_text("license\n", encoding="utf-8")
    archive_path = tmp_path / "source.zip"
    package_release.write_source_archive(
        archive_path,
        package_release.resolve_source_commit(frozen_commit),
        [(sidecar, "THIRD_PARTY_LICENSES/license.txt")],
    )

    reference_archive = tmp_path / "reference.zip"
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "archive",
            "--format=zip",
            f"--output={reference_archive}",
            frozen_commit,
        ],
        cwd=repo,
        check=True,
    )
    with zipfile.ZipFile(reference_archive) as reference, zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == set(reference.namelist()) | {
            "THIRD_PARTY_LICENSES/license.txt"
        }
        for path in reference.namelist():
            assert archive.read(path) == reference.read(path)


def test_gpl_only_license_and_public_notices_are_present():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "GNU GENERAL PUBLIC LICENSE" in license_text[:100]
    assert "Version 3, 29 June 2007" in license_text[:100]
    assert "GNU General Public License" in (ROOT / "COPYRIGHT").read_text(encoding="utf-8")
    assert "GNU GPL version 3 only" in notices
    assert "AsyncSSH" in notices
    assert "PyInstaller" in notices
