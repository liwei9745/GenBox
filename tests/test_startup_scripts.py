"""Static contracts for Windows launcher encoding and bilingual output."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launchers_set_utf8_environment_and_bilingual_labels():
    start_bat = (ROOT / "start.bat").read_text(encoding="utf-8")
    start_ps1 = (ROOT / "start.ps1").read_text(encoding="utf-8")

    for script in (start_bat, start_ps1):
        assert "PYTHONIOENCODING" in script
        assert "GenBox" in script
        assert "启动" in script
        assert "Launcher" in script or "Start GenBox" in script

    assert "chcp 65001" in start_bat
    assert "PYTHONUTF8" in start_bat
    assert "Python not found / 未找到 Python" in start_bat
    assert "OutputEncoding" in start_ps1
    assert "Not found / 未找到" in start_ps1
