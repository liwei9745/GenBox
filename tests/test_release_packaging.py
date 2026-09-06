import subprocess
import sys
import zipfile
import hashlib
import io
import json
import re
import shutil
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

WORKFLOW_ACTION_PINS = {
    "actions/checkout": ("11d5960a326750d5838078e36cf38b85af677262", "v4"),
    "actions/setup-node": ("49933ea5288caeca8642d1e84afbd3f7d6820020", "v4"),
    "actions/setup-python": ("a26af69be951a213d495a4c3e4e4022e16d87065", "v5"),
    "actions/upload-artifact": ("ea165f8d65b6e75b540449e92b4886f43607fa02", "v4"),
    "actions/download-artifact": ("d3f86a106a0bac45b974a628896c90dbdf5c8093", "v4"),
    "docker/login-action": ("c94ce9fb468520275223c153574b00df6fe4bcc9", "v3"),
    "docker/setup-buildx-action": ("8d2750c68a42422c14e847fe6c8ac0403b4cbd6f", "v3"),
    "docker/metadata-action": ("c299e40c65443455700f0fdfc63efafe5b349051", "v5"),
    "docker/build-push-action": ("10e90e3645eae34f1e60eeb005ba3a3d33f178e8", "v6"),
}


def _workflow_job_block(workflow: str, job_name: str) -> str:
    jobs_marker = "\njobs:\n"
    assert jobs_marker in workflow
    jobs_start = workflow.index(jobs_marker) + len(jobs_marker)
    jobs = workflow[jobs_start:]
    match = re.search(rf"(?m)^  {re.escape(job_name)}:\s*$", jobs)
    assert match is not None, f"missing workflow job {job_name!r}"
    next_job = re.search(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs[match.end() :])
    end = match.end() + next_job.start() if next_job else len(jobs)
    return jobs[match.start() : end]


def _workflow_step_block(workflow: str, job_name: str, step_name: str) -> str:
    job = _workflow_job_block(workflow, job_name)
    marker = f"      - name: {step_name}"
    assert job.count(marker) == 1, f"expected one step {step_name!r} in {job_name!r}"
    start = job.index(marker)
    next_step = job.find("\n      - name: ", start + len(marker))
    return job[start:] if next_step < 0 else job[start:next_step]


def _run_mocked_docker_http_smoke(scenario: str) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is required to execute the Docker HTTP smoke contract")
    assert scenario in {
        "connection_reset",
        "container_exited",
        "deadline",
        "sensitive_logs",
        "name_collision",
        "owner_mismatch",
    }
    smoke_script = (
        ROOT / ".github" / "scripts" / "docker-release-http-smoke.sh"
    ).read_text(encoding="utf-8")
    harness = (
        r'''
set -euo pipefail
exec 3>&1
export MOCK_SCENARIO="__SCENARIO__"
export RELEASE_IMAGE_ID="sha256:release-image-id"
export GITHUB_RUN_ID="4242"
export GITHUB_RUN_ATTEMPT="3"
export GENBOX_SMOKE_TIMEOUT_SECONDS="3"
export GENBOX_SMOKE_MAX_DELAY_SECONDS="1"
mock_state_dir="/tmp/genbox-release-smoke-mock-${MOCK_SCENARIO}-$$"
mock_container_id="container-id-4242"
mock_nonce="0011223344556677"
mock_admin_key="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

docker() {
  local command="$1"
  shift
  case "$command" in
    run)
      printf 'MOCK_RUN=%s\n' "$MOCK_SCENARIO" >&3
      if [[ "$MOCK_SCENARIO" == "name_collision" ]]; then
        printf 'container name already exists\n' >&2
        return 125
      fi
      printf '%s\n' "$mock_container_id"
      ;;
    inspect)
      local format="$2"
      case "$format" in
        '{{.Id}}') printf '%s\n' "$mock_container_id" ;;
        '{{.Image}}') printf '%s\n' "$RELEASE_IMAGE_ID" ;;
        *Config.Labels*)
          if [[ "$MOCK_SCENARIO" == "owner_mismatch" ]]; then
            printf 'different-owner\n'
          else
            printf '%s\n' "${GITHUB_RUN_ID}:${GITHUB_RUN_ATTEMPT}:${mock_nonce}"
          fi
          ;;
        '{{.State.Status}}')
          [[ "$MOCK_SCENARIO" == "container_exited" ]] && printf 'exited\n' || printf 'running\n'
          ;;
        '{{.State.Running}}')
          [[ "$MOCK_SCENARIO" == "container_exited" ]] && printf 'false\n' || printf 'true\n'
          ;;
        '{{.State.ExitCode}}')
          [[ "$MOCK_SCENARIO" == "container_exited" ]] && printf '23\n' || printf '0\n'
          ;;
        *State.Health*) printf 'starting\n' ;;
        *) printf 'unexpected inspect format: %s\n' "$format" >&2; return 90 ;;
      esac
      ;;
    port) printf '127.0.0.1:43138\n' ;;
    logs)
      if [[ "$MOCK_SCENARIO" == "sensitive_logs" ]]; then
        printf '%s\n' \
          "raw-admin=${mock_admin_key}" \
          'Bearer ''bearer-secret-1234567890' \
          'https://user:pass@example.test/path' \
          '?api_key=query-secret' \
          '"management_key": "json-secret"' \
          'push_key=field-secret' \
          'sk-1234567890'
      else
        printf 'ordinary startup log\n'
      fi
      ;;
    rm)
      printf 'MOCK_RM=%s\n' "$2" >&3
      rm -rf "$mock_state_dir"
      ;;
    *) printf 'unexpected docker command: %s\n' "$command" >&2; return 91 ;;
  esac
}

openssl() {
  if [[ "$*" == "rand -hex 8" ]]; then
    printf '%s\n' "$mock_nonce"
  elif [[ "$*" == "rand -hex 32" ]]; then
    printf '%s\n' "$mock_admin_key"
  else
    return 92
  fi
}

date() {
  if [[ "$MOCK_SCENARIO" == "deadline" || "$MOCK_SCENARIO" == "sensitive_logs" ]]; then
    mkdir -p "$mock_state_dir"
    local counter_file="$mock_state_dir/date-count"
    local count=0
    [[ -f "$counter_file" ]] && count="$(cat "$counter_file")"
    count=$((count + 1))
    printf '%s' "$count" > "$counter_file"
    [[ "$count" -le 2 ]] && printf '100\n' || printf '104\n'
  else
    printf '100\n'
  fi
}

curl() {
  case "$MOCK_SCENARIO" in
    connection_reset)
      mkdir -p "$mock_state_dir"
      local counter_file="$mock_state_dir/curl-count"
      local count=0
      [[ -f "$counter_file" ]] && count="$(cat "$counter_file")"
      count=$((count + 1))
      printf '%s' "$count" > "$counter_file"
      if [[ "$count" == "1" ]]; then
        return 56
      fi
      printf '{"app_mode":"prod","auth_required":true}\n'
      ;;
    deadline|sensitive_logs) return 56 ;;
    *) return 93 ;;
  esac
}

sleep() {
  printf 'MOCK_SLEEP=%s\n' "$1" >&3
}

python() {
  python3 "$@"
}
'''.replace("__SCENARIO__", scenario)
        + "\n"
        + smoke_script
    )
    result = subprocess.run(
        [bash],
        input=harness.replace("\r\n", "\n").encode("utf-8"),
        capture_output=True,
        check=False,
    )
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        result.stdout.decode("utf-8", errors="replace"),
        result.stderr.decode("utf-8", errors="replace"),
    )


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
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_compose_release_uses_ghcr_and_safe_internal_port():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_template = (ROOT / ".env.docker.example").read_text(encoding="utf-8")

    stable_image = f"ghcr.io/liwei9745/genbox:{__version__}"
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

    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert workflow.count("contents: write") == 1
    assert "permissions:\n      contents: write" in _workflow_job_block(workflow, "release")
    assert workflow.count("scripts/smoke_client.py") == 3
    assert workflow.count("--runtime-import-smoke") == 3
    assert workflow.count("--version") == 3
    assert workflow.count("mktemp -d") == 2
    assert "RUNNER_TEMP" in workflow
    assert workflow.count("Remove-Item Env:PYTHONPATH") == 1
    assert workflow.count("Remove-Item Env:PYTHONHOME") == 1
    assert workflow.count('PYTHONNOUSERSITE = "1"') == 1
    assert '[guid]::NewGuid().ToString("N")' in workflow
    assert "New-Item -ItemType Directory -Path $smoke" in workflow
    assert "finally {" in workflow
    assert "Remove-Item -LiteralPath $smoke -Recurse -Force" in workflow
    assert workflow.count(
        "env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 ./GenBox --version"
    ) == 2
    assert workflow.count(
        "env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 "
        "./GenBox --runtime-import-smoke"
    ) == 2
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


def test_native_runtime_dependencies_are_in_all_distribution_paths():
    from scripts.third_party_licenses import RUNTIME_LICENSES

    runtime_requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    cutout_requirements = (ROOT / "requirements-cutout.txt").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "-r requirements-cutout.txt" in runtime_requirements
    assert "onnxruntime==1.24.3" in cutout_requirements
    assert "numpy==2.4.3" in cutout_requirements
    assert "bcrypt==5.0.0" in runtime_requirements
    for filename in ("requirements-dev.txt", "requirements-build.txt"):
        assert "-r requirements.txt" in (ROOT / filename).read_text(encoding="utf-8")
    assert "COPY requirements.txt requirements-cutout.txt ./" in dockerfile
    assert "pip install -r requirements.txt" in dockerfile
    assert "collect_runtime_licenses" in dockerfile
    assert "storage/" in dockerignore
    assert "!THIRD_PARTY_NOTICES.md" in dockerignore
    assert (
        "| NumPy | 2.4.3 | "
        "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |"
    ) in notices
    assert "| ONNX Runtime | 1.24.3 | MIT |" in notices
    assert "| bcrypt | 5.0.0 | Apache-2.0 |" in notices
    assert "https://github.com/pyca/bcrypt/" in notices
    assert "complete Apache License 2.0 text" in notices
    assert "https://numpy.org" in notices
    assert "https://onnxruntime.ai" in notices
    assert "NumPy Developers" in notices
    assert "Microsoft Corporation" in notices

    requirement_versions = {}
    for requirements in (runtime_requirements, cutout_requirements):
        requirement_versions.update(
            re.findall(
                r"^(bcrypt|numpy|onnxruntime)==([^\s]+)$",
                requirements,
                re.MULTILINE,
            )
        )
    assert requirement_versions == {
        name: contract["version"] for name, contract in RUNTIME_LICENSES.items()
    }
    notice_versions = {
        "numpy": re.search(r"^\| NumPy \| ([^| ]+) \|", notices, re.MULTILINE).group(1),
        "onnxruntime": re.search(
            r"^\| ONNX Runtime \| ([^| ]+) \|", notices, re.MULTILINE
        ).group(1),
        "bcrypt": re.search(
            r"^\| bcrypt \| ([^| ]+) \|", notices, re.MULTILINE
        ).group(1),
    }
    assert notice_versions == requirement_versions


def test_desktop_build_collects_complete_runtime_without_bundling_model(
    tmp_path, monkeypatch
):
    import build as desktop_build
    from image_tools.cutout_onnx import MODEL_FILENAME

    requirement_versions = {}
    requirement_pattern = re.compile(
        r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s#]+)$", re.MULTILINE
    )
    for filename in ("requirements.txt", "requirements-cutout.txt"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        requirement_versions.update(
            (name.lower(), version)
            for name, version in requirement_pattern.findall(text)
        )

    assert desktop_build.PACKAGED_RUNTIME_DISTRIBUTIONS == requirement_versions
    for module in desktop_build.PACKAGED_RUNTIME_IMPORTS:
        assert module in desktop_build.HIDDEN_IMPORTS
    for module in (
        "pydantic_settings",
        "pydantic_core",
        "annotated_types",
        "typing_inspection",
        "python_multipart",
        "bcrypt",
        "bcrypt._bcrypt",
    ):
        assert module in desktop_build.HIDDEN_IMPORTS
    for package in ("numpy", "onnxruntime", "pydantic_core"):
        assert package in desktop_build.COLLECT_ALL_PACKAGES
    assert "pydantic" not in desktop_build.COLLECT_ALL_PACKAGES
    assert "bcrypt" not in desktop_build.COLLECT_ALL_PACKAGES
    for package in ("uvicorn", "pydantic_settings"):
        assert package in desktop_build.COLLECT_SUBMODULE_PACKAGES
    assert set(desktop_build.COPY_METADATA_DISTRIBUTIONS) == set(requirement_versions)
    assert "numpy" not in desktop_build.EXCLUDES
    assert all("storage" not in source.replace("\\", "/").split("/") for source, _ in desktop_build.DATA_FILES)
    assert MODEL_FILENAME not in (ROOT / "build.py").read_text(encoding="utf-8")

    captured = {}
    real_subprocess_run = subprocess.run

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

    for module in desktop_build.HIDDEN_IMPORTS:
        assert f"--hidden-import={module}" in captured["command"]
    for package in desktop_build.COLLECT_ALL_PACKAGES:
        assert f"--collect-all={package}" in captured["command"]
    for package in desktop_build.COLLECT_SUBMODULE_PACKAGES:
        assert f"--collect-submodules={package}" in captured["command"]
    for distribution in desktop_build.COPY_METADATA_DISTRIBUTIONS:
        assert f"--copy-metadata={distribution}" in captured["command"]
    hook_text = captured["runtime_hook"]
    assert "--version" in hook_text
    assert "--runtime-import-smoke" in hook_text
    for module in desktop_build.PACKAGED_RUNTIME_IMPORTS:
        assert repr(module) in hook_text
    for distribution, version in desktop_build.PACKAGED_RUNTIME_DISTRIBUTIONS.items():
        assert repr(distribution) in hook_text
        assert repr(version) in hook_text
    for module, symbols in desktop_build.PACKAGED_RUNTIME_SYMBOLS.items():
        assert repr(module) in hook_text
        for symbol in symbols:
            assert repr(symbol) in hook_text
    smoke_hook = tmp_path / "runtime_smoke_hook.py"
    smoke_hook.write_text(hook_text, encoding="utf-8")
    smoke_result = real_subprocess_run(
        [sys.executable, str(smoke_hook), "--runtime-import-smoke"],
        check=True,
        capture_output=True,
        text=True,
    )
    smoke_payload = json.loads(smoke_result.stdout)
    assert smoke_payload == {
        "encrypted_openssh": "ok",
        "status": "ok",
        "symbols": "ok",
        "versions": requirement_versions,
    }
    assert any("THIRD_PARTY_LICENSES" in argument for argument in captured["command"])
    spec_text = (tmp_path / "GenBox.spec").read_text(encoding="utf-8")
    assert "collect_all" in spec_text
    assert "collect_submodules" in spec_text
    assert "copy_metadata" in spec_text
    expected_hidden_imports = ", ".join(
        repr(module) for module in desktop_build.HIDDEN_IMPORTS
    )
    assert f"hiddenimports = [{expected_hidden_imports}]" in spec_text
    assert f"for package in {desktop_build.COLLECT_ALL_PACKAGES!r}" in spec_text
    assert f"for package in {desktop_build.COLLECT_SUBMODULE_PACKAGES!r}" in spec_text
    assert (
        f"for distribution in {desktop_build.COPY_METADATA_DISTRIBUTIONS!r}"
        in spec_text
    )
    assert "THIRD_PARTY_LICENSES" in spec_text
    assert MODEL_FILENAME not in spec_text
    assert (tmp_path / "dist" / "THIRD_PARTY_LICENSES" / "numpy" / "LICENSE.txt").is_file()
    bcrypt_license = tmp_path / "dist" / "THIRD_PARTY_LICENSES" / "bcrypt" / "LICENSE"
    assert bcrypt_license.is_file()
    assert "Apache License" in bcrypt_license.read_text(encoding="utf-8")
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
    jobs = workflow.split("\njobs:\n", 1)[1]
    assert jobs.index("  release-contract:") < jobs.index("  build:") < jobs.index("  push:")
    assert workflow.index("needs: release-contract") < workflow.index(
        "Log in to Container Registry"
    )
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert "packages: write" not in _workflow_job_block(workflow, "build")
    push_job = _workflow_job_block(workflow, "push")
    assert push_job.count("packages: write") == 1
    assert "contents: read" in push_job


def test_all_workflow_external_actions_are_pinned_to_reviewed_full_shas():
    workflow_paths = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    workflows = {
        path.name: path.read_text(encoding="utf-8") for path in workflow_paths
    }
    action_lines = [
        (path, reference, comment)
        for path, workflow in workflows.items()
        for reference, comment in re.findall(
            r"(?m)^\s*uses:\s*([^\s#]+)(?:\s+#\s*(\S+))?\s*$", workflow
        )
    ]

    assert action_lines
    for path, reference, comment in action_lines:
        if reference.startswith("./"):
            continue
        assert "@" in reference, f"unpinned external action in {path}: {reference}"
        repository, sha = reference.rsplit("@", 1)
        assert repository in WORKFLOW_ACTION_PINS, (
            f"unreviewed external action in {path}: {repository}"
        )
        expected_sha, expected_tag = WORKFLOW_ACTION_PINS[repository]
        assert sha == expected_sha, f"unexpected action commit in {path}: {reference}"
        assert re.fullmatch(r"[0-9a-f]{40}", sha), (
            f"mutable external action reference in {path}: {reference}"
        )
        assert comment == expected_tag, f"missing reviewed tag comment in {path}"

    for repository, (sha, tag) in WORKFLOW_ACTION_PINS.items():
        expected = f"{repository}@{sha} # {tag}"
        assert any(expected in workflow for workflow in workflows.values())


def test_docker_workflow_smokes_and_pushes_one_exact_build():
    workflow = (ROOT / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    smoke_script = (
        ROOT / ".github" / "scripts" / "docker-release-http-smoke.sh"
    ).read_text(encoding="utf-8")

    build_action_sha = WORKFLOW_ACTION_PINS["docker/build-push-action"][0]
    assert workflow.count(f"uses: docker/build-push-action@{build_action_sha}") == 1
    assert "load: true" in workflow
    assert "push: false" in workflow
    assert "docker build " not in workflow
    assert "steps.build.outputs.imageid" in workflow
    assert 'docker run --rm --entrypoint python "$RELEASE_IMAGE_ID"' in workflow
    assert "metadata.version('bcrypt') == '5.0.0'" in workflow
    assert "asyncssh.generate_private_key('ssh-ed25519')" in workflow
    assert "asyncssh.import_private_key(encrypted_key, passphrase)" in workflow
    assert "THIRD_PARTY_LICENSES/bcrypt/LICENSE" in workflow
    assert "THIRD_PARTY_NOTICES.md" in workflow
    assert "assert numpy.__version__ == '2.4.3'" in workflow
    assert "assert onnxruntime.__version__ == '1.24.3'" in workflow
    assert "import main" in workflow
    assert "timeout-minutes: 3" in workflow
    assert "bash .github/scripts/docker-release-http-smoke.sh" in workflow
    assert 'echo "::add-mask::$admin_key"' in smoke_script
    assert "container_created=0" in smoke_script
    assert "container_created=1" in smoke_script
    assert "com.genbox.release-smoke-owner" in smoke_script
    assert 'docker rm -f "$container_id"' in smoke_script
    assert '"$current_id" == "$container_id"' in smoke_script
    assert '"$current_owner" == "$owner_label_value"' in smoke_script
    assert '"http://127.0.0.1:${host_port}/api/setup/status"' in smoke_script
    assert "{{.State.Running}}" in smoke_script
    assert "{{if .State.Health}}{{.State.Health.Status}}" in smoke_script
    assert "data.get('app_mode') == 'prod'" in smoke_script
    assert "data.get('auth_required') is True" in smoke_script
    assert 'docker logs --tail 200 "$container_id"' in smoke_script
    assert "[REDACTED]" in smoke_script
    assert "management[_-]?key" in smoke_script
    assert "push[_-]?key" in smoke_script
    assert "--retry-connrefused" not in smoke_script
    assert 'docker save --output "$RUNNER_TEMP/genbox-release-image.tar"' in workflow
    assert 'docker load --input "$RUNNER_TEMP/genbox-release-image/genbox-release-image.tar"' in workflow
    assert 'docker image inspect --format \'{{.Id}}\' "$tag"' in workflow
    assert 'docker tag "$RELEASE_IMAGE_ID" "$tag"' in workflow
    assert 'docker push "$tag"' in workflow
    runtime_step = _workflow_step_block(
        workflow, "build", "Smoke test exact built image runtime imports"
    )
    http_step = _workflow_step_block(
        workflow, "build", "Smoke test exact built image over HTTP"
    )
    save_step = _workflow_step_block(
        workflow, "build", "Save smoke-tested Docker image without rebuilding"
    )
    push_step = _workflow_step_block(
        workflow, "push", "Push smoke-tested Docker image without rebuilding"
    )
    for step in (runtime_step, http_step, save_step):
        assert "RELEASE_IMAGE_ID: ${{ steps.build.outputs.imageid }}" in step
    assert "RELEASE_IMAGE_ID: ${{ needs.build.outputs.image_id }}" in push_step
    assert "IMAGE_TAGS: ${{ needs.build.outputs.image_tags }}" in push_step
    build_index = workflow.index("Build Docker image once for smoke and publish")
    runtime_smoke_index = workflow.index("Smoke test exact built image runtime imports")
    http_smoke_index = workflow.index("Smoke test exact built image over HTTP")
    save_index = workflow.index("Save smoke-tested Docker image without rebuilding")
    load_index = workflow.index("Load and verify exact smoke-tested Docker image")
    push_index = workflow.index("Push smoke-tested Docker image without rebuilding")
    assert build_index < runtime_smoke_index < http_smoke_index < save_index < load_index < push_index
    assert "FROM python:3.12-slim" in dockerfile
    assert "COPY requirements.txt requirements-cutout.txt ./" in dockerfile
    assert "RUN pip install -r requirements.txt" in dockerfile
    assert "collect_runtime_licenses(Path('THIRD_PARTY_LICENSES'))" in dockerfile


@pytest.mark.parametrize(
    ("scenario", "expected_returncode", "expected_output"),
    [
        ("connection_reset", 0, "HTTP smoke passed after 2 attempts"),
        ("container_exited", 1, "state=exited running=false exit_code=23"),
        ("deadline", 1, "HTTP smoke failed after 1 attempts"),
    ],
)
def test_docker_http_smoke_runtime_paths(scenario, expected_returncode, expected_output):
    result = _run_mocked_docker_http_smoke(scenario)

    assert result.returncode == expected_returncode, result.stdout + result.stderr
    assert expected_output in result.stdout
    assert result.stdout.count("MOCK_RM=container-id-4242") == 1


def test_docker_http_smoke_redacts_sensitive_failure_logs():
    result = _run_mocked_docker_http_smoke("sensitive_logs")

    assert result.returncode == 1, result.stdout + result.stderr
    diagnostic_logs = result.stdout.split(
        "Last 200 credential-redacted container log lines:\n", 1
    )[1].split("MOCK_RM=", 1)[0]
    for secret in (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bearer-secret-1234567890",
        "user:pass",
        "query-secret",
        "json-secret",
        "field-secret",
        "sk-1234567890",
    ):
        assert secret not in diagnostic_logs
    assert diagnostic_logs.count("[REDACTED]") >= 7
    assert result.stdout.count("MOCK_RM=container-id-4242") == 1


def test_docker_http_smoke_name_collision_never_removes_preexisting_container():
    result = _run_mocked_docker_http_smoke("name_collision")

    assert result.returncode != 0
    assert "container name already exists" in result.stderr
    assert "MOCK_RM=" not in result.stdout


def test_docker_http_smoke_owner_mismatch_refuses_cleanup():
    result = _run_mocked_docker_http_smoke("owner_mismatch")

    assert result.returncode != 0
    assert "ownership verification failed" in result.stderr
    assert "MOCK_RM=" not in result.stdout


@pytest.mark.parametrize(
    "metadata_path",
    (
        "bcrypt-5.0.0.dist-info/LICENSE",
        "bcrypt-5.0.0.dist-info/licenses/LICENSE",
    ),
)
def test_bcrypt_license_contract_accepts_supported_wheel_layouts(metadata_path):
    from scripts.third_party_licenses import RUNTIME_LICENSES

    predicate = RUNTIME_LICENSES["bcrypt"]["files"]["LICENSE"]
    assert predicate(metadata_path)
    assert not predicate("bcrypt-5.0.0.dist-info/licenses/COPYING")


def test_pinned_runtime_license_assets_are_collected_from_distribution_metadata(tmp_path):
    from scripts.third_party_licenses import collect_runtime_licenses

    destination = collect_runtime_licenses(tmp_path / "THIRD_PARTY_LICENSES")
    manifest = json.loads((destination / "MANIFEST.json").read_text(encoding="utf-8"))

    assert manifest == {
        "schema_version": 1,
        "distributions": [
            {
                "name": "bcrypt",
                "version": "5.0.0",
                "files": ["bcrypt/LICENSE"],
            },
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
    assert "Apache License" in (destination / "bcrypt" / "LICENSE").read_text(
        encoding="utf-8"
    )
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
    normalized_notes = " ".join(rolling_notes.split())
    version = __version__
    release_date = re.search(
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
        (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    ).group(1)

    assert re.search(
        rf"^# GenBox v{re.escape(version)} Release Notes$",
        rolling_notes,
        re.MULTILINE,
    )
    assert "v2.6.5 tag was pushed" in normalized_notes
    assert "no GitHub Release, release assets, or GHCR image" in normalized_notes
    assert f"release-notes-v{version}.md" in rolling_notes
    assert f"release-notes-v{version}-zh.md" in rolling_notes

    current_notes = {"rolling": rolling_notes}
    for filename in (f"release-notes-v{version}.md", f"release-notes-v{version}-zh.md"):
        notes = (ROOT / filename).read_text(encoding="utf-8")
        current_notes[filename] = notes
        assert version in notes
        assert release_date in notes

    public_release_text = "\n".join(current_notes.values())
    for transient_phrase in (
        "Release Candidate",
        "release-candidate",
        "prepared local candidate",
        "No v" + version + " tag",
        "claimed yet",
        "hosted release CI remains unverified",
        "拟发布候选版",
        "候选日期",
        "尚未创建 v" + version,
    ):
        assert transient_phrase not in public_release_text

    english_notes = current_notes[f"release-notes-v{version}.md"]
    chinese_notes = current_notes[f"release-notes-v{version}-zh.md"]
    normalized_english_notes = " ".join(english_notes.split())
    normalized_chinese_notes = " ".join(chinese_notes.split())
    assert (
        "commercial-use rights are not established"
        in normalized_english_notes
    )
    assert (
        "Automatic update application and restart remain disabled"
        in normalized_english_notes
    )
    assert "does not claim universal support" in normalized_english_notes
    assert "商业使用权不会因为本次发布而自动得到确认" in normalized_chinese_notes
    assert "\u81ea\u52a8\u66f4\u65b0\u5e94\u7528\u548c\u81ea\u52a8\u91cd\u542f\u4ecd\u4fdd\u6301\u7981\u7528" in normalized_chinese_notes
    assert "不代表所有第三方中转端点" in normalized_chinese_notes

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    current_changelog = changelog.split("## [2.6.6]", 1)[0]
    assert f"## [{version}] - {release_date}\n" in current_changelog
    assert "candidate" not in current_changelog.lower()
    assert f"No v{version} tag" not in current_changelog

    for filename in ("release-notes-v2.6.5.md", "release-notes-v2.6.5-zh.md"):
        notes = (ROOT / filename).read_text(encoding="utf-8")
        assert "2.6.5" in notes
        assert "33715658824" in notes
        assert "33715658700" in notes


def test_release_candidate_version_ordering_is_supported():
    from updater import compare_versions

    assert compare_versions("2.6.0-rc.1", "v2.6.0-rc.2")
    assert compare_versions("2.6.0-rc.1", "v2.6.0")
    assert not compare_versions("2.6.0", "v2.6.0-rc.1")


def test_release_tag_must_match_packaged_version_exactly():
    from scripts.package_release import SourcePackagingError, validate_release_tag

    validate_release_tag(f"v{__version__}", __version__)
    with pytest.raises(SourcePackagingError, match="does not match"):
        validate_release_tag("v0.0.0", __version__)
    with pytest.raises(SourcePackagingError, match="canonical v-prefixed"):
        validate_release_tag(__version__, __version__)


def test_readme_lab_content_matches_source_documents():
    payload = json.loads((ROOT / "static" / "readme-lab-content.json").read_text(encoding="utf-8"))
    lab = (ROOT / "static" / "readme-lab.html").read_text(encoding="utf-8")
    expected_assets = {
        "upstream-contributors.svg",
        "star-history.svg",
    }

    sources = {
        "readme": {"zh": "README.md", "en": "README_EN.md"},
        "release": {
            "zh": f"release-notes-v{__version__}-zh.md",
            "en": f"release-notes-v{__version__}.md",
        },
    }
    assert 'id="document"' in lab
    assert "state.payload[state.document][state.language]" in lab
    assert f"Release v{__version__}" in lab
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
            "THIRD_PARTY_LICENSES/bcrypt/LICENSE",
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
        assert "| bcrypt | 5.0.0 | Apache-2.0 |" in packaged_notices
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
        bcrypt_license = archive.read("THIRD_PARTY_LICENSES/bcrypt/LICENSE").decode(
            "utf-8"
        )
        assert "Apache License" in bcrypt_license
        assert archive.getinfo("THIRD_PARTY_LICENSES/numpy/LICENSE.txt").file_size > 0
        assert archive.getinfo("THIRD_PARTY_LICENSES/onnxruntime/LICENSE").file_size > 0
        assert archive.getinfo(
            "THIRD_PARTY_LICENSES/onnxruntime/ThirdPartyNotices.txt"
        ).file_size > 0
        manifest = json.loads(archive.read("THIRD_PARTY_LICENSES/MANIFEST.json"))
        versions = {item["name"]: item["version"] for item in manifest["distributions"]}
        assert versions == {
            "bcrypt": "5.0.0",
            "numpy": "2.4.3",
            "onnxruntime": "1.24.3",
        }


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
