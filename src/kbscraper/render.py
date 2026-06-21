"""OPTIONAL headless rendering for JS-heavy docs (e.g. sites that serve redirect/templated shells).

Enabled per-source with `render: true`. Uses Playwright (Chromium) — a heavy, separate dependency, so
it's import-guarded and only pulled in when a source opts in:

    pip install -r requirements-render.txt
    playwright install chromium

EXPERIMENTAL: not exercised by the offline test suite (needs a real browser). Prefer static fetch
where it works; only flag `render: true` for sources whose content is genuinely client-rendered.
"""

from __future__ import annotations

from . import config


def render_html(url: str, timeout_s: float | None = None) -> str | None:
    """Fully render a page with a headless browser and return its HTML, or None on failure."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # noqa: BLE001
        raise SystemExit(
            "Render deps missing. Run: pip install -r requirements-render.txt && playwright install chromium"
        ) from e

    timeout_ms = int((timeout_s or config.REQUEST_TIMEOUT_S) * 1000)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=config.USER_AGENT)
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html
    except Exception:  # noqa: BLE001 - render failure ⇒ treat like a failed fetch
        return None
