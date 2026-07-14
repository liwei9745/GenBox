from pathlib import Path

import updater


def _release(*names: str) -> dict:
    return {
        "assets": [
            {"name": name, "browser_download_url": f"https://example.invalid/{name}"}
            for name in names
        ]
    }


def test_windows_asset_prefers_executable_over_zip() -> None:
    release = _release("GenBox-Windows.zip", "SHA256SUMS.txt", "GenBox.exe")

    assert updater.get_asset_url(release, "win32") == "https://example.invalid/GenBox.exe"


def test_asset_fallback_never_selects_archive() -> None:
    release = _release("custom-windows.zip", "custom-windows.exe")

    assert updater.get_asset_url(release, "win32") == "https://example.invalid/custom-windows.exe"


def test_asset_returns_none_when_only_archive_exists() -> None:
    assert updater.get_asset_url(_release("GenBox-Windows.zip"), "win32") is None


def test_windows_restart_script_replaces_after_stopping_process() -> None:
    target = Path("C:/GenBox/GenBox.exe")
    staged = Path("C:/GenBox/.GenBox.exe.update")
    script = updater._windows_restart_script(
        target,
        staged,
        Path("C:/GenBox/GenBox.exe.bak"),
        4321,
    )

    assert "taskkill /PID 4321 /T /F" in script
    assert script.index("taskkill") < script.index(f'move /Y "{target}"')
    assert f'move /Y "{staged}" "{target}"' in script
