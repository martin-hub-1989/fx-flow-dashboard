"""Loop 14: PNG/CSV export browser verification."""
import subprocess, os
from pathlib import Path
import pytest


def test_export_png_csv_works():
    script = Path(__file__).resolve().parent.parent / "tests" / "test_loop14_export_check.js"
    if not script.exists():
        pytest.skip("export check script missing")
    chrome = os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium_headless_shell-1223/"
        "chrome-headless-shell-mac-arm64/chrome-headless-shell")
    if not os.path.exists(chrome):
        pytest.skip("chrome-headless-shell not installed")
    result = subprocess.run(["node", str(script)], capture_output=True,
                            text=True, timeout=120, cwd=os.getcwd())
    assert result.returncode == 0, f"export check failed:\n{result.stdout[-1500:]}"
