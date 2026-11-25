"""Headless Chromium for e2e tests and screenshots.

Uses Playwright's own browser when it is installed. On machines where only an older
Playwright Chromium build exists (we avoid a 150 MB download onto a full system drive),
the newest installed headless shell is used instead. ``PDC_CHROMIUM`` overrides both.
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import Browser, Error, Playwright


def _fallback_executable() -> str | None:
    if env := os.environ.get("PDC_CHROMIUM"):
        return env
    root = Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path.home() / "AppData/Local/ms-playwright"
    )
    if not root.exists():
        root = Path.home() / ".cache" / "ms-playwright"
    candidates = sorted(
        root.glob("chromium_headless_shell-*/*/chrome-headless-shell*"), reverse=True
    )
    candidates = [c for c in candidates if c.suffix in ("", ".exe")]
    return str(candidates[0]) if candidates else None


def launch(p: Playwright) -> Browser:
    executable = os.environ.get("PDC_CHROMIUM")
    if not executable:
        try:
            return p.chromium.launch(headless=True)
        except Error:
            executable = _fallback_executable()
            if not executable:
                raise
    return p.chromium.launch(headless=True, executable_path=executable)
