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


def test_packaged_first_run_and_generation_quantity_paths_are_bilingual_and_safe():
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    app_source = (ROOT / "static" / "js" / "app-all.js").read_text(encoding="utf-8")

    assert "GenBox first-run setup / GenBox 首次启动设置" in main_source
    assert "Select deployment mode (1/2/3) / 选择部署模式" in main_source
    assert "sys.stdout.reconfigure(encoding=\"utf-8\"" in main_source
    assert "var visibleQty = parseInt(document.getElementById('selQty').value, 10);" in app_source
    assert "Math.max(1, Math.min(10, visibleQty))" in app_source
