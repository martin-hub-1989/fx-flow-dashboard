"""Loop 12: browser verification gate (run via node, asserted in pytest)."""
import subprocess, os
from pathlib import Path
import pytest


def test_browser_no_overflow_no_errors():
    """Run the node browser check; require exit 0 (no overflow, no console errors)."""
    script = Path(__file__).resolve().parent / "browser_check.js"
    if not script.exists():
        pytest.skip("browser_check.js missing")
    chrome = os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium_headless_shell-1223/"
        "chrome-headless-shell-mac-arm64/chrome-headless-shell")
    if not os.path.exists(chrome):
        pytest.skip("chrome-headless-shell not installed")
    result = subprocess.run(["node", str(script)], capture_output=True,
                            text=True, timeout=180)
    assert result.returncode == 0, f"browser check failed:\n{result.stdout[-1500:]}"


def test_no_at_at_media_in_html():
    """The @@media bug must not recur (valid @media only)."""
    html = Path("reports/fx_flow_dashboard.html").read_text(encoding="utf-8")
    # @@media outside of comments is the bug. Check the CSS block directly.
    import re
    css = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    assert css, "no style block"
    # @media should appear; @@media (double-at) is the bug
    assert "@@media" not in css.group(1), "@@media bug present in CSS"
    assert "@media" in css.group(1), "no @media query in CSS"
