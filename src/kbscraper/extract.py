"""HTML → CleanDoc. Uses trafilatura for main-content extraction (strips nav/boilerplate/code-noise
well across docs sites), falling back to a CSS selector + BeautifulSoup when configured or when
trafilatura yields nothing. Title comes from trafilatura metadata, else <h1>/<title>."""

from __future__ import annotations

from .clean import normalize_text
from .models import CleanDoc, RawDoc, SourceSpec


def _title_from_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    if soup.h1 and soup.h1.get_text(strip=True):
        return soup.h1.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return ""


def _fallback_text(html: str, selector: str | None) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()
    root = (soup.select_one(selector) if selector else None) or soup.body or soup
    return root.get_text("\n")


def extract(raw: RawDoc, spec: SourceSpec) -> CleanDoc:
    """Extract title + normalized main text from raw HTML for a source."""
    text = ""
    title = ""
    try:
        import trafilatura

        text = trafilatura.extract(raw.html, include_comments=False, include_tables=True, favor_recall=True) or ""
        meta = trafilatura.extract_metadata(raw.html)
        if meta and meta.title:
            title = meta.title
    except Exception:  # noqa: BLE001 - any extraction error ⇒ fall back to the selector path
        text = ""
    if not text.strip():
        text = _fallback_text(raw.html, spec.content_selector)
    if not title:
        title = _title_from_html(raw.html)
    return CleanDoc(url=raw.url, title=title.strip(), text=normalize_text(text), source=spec)
