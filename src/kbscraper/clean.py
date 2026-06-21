"""Text cleaning + dedup helpers. Pure (stdlib only), deterministic, unit-tested without network."""

from __future__ import annotations

import hashlib
import re

# Boilerplate lines common to docs sites that carry no knowledge value.
_BOILERPLATE = re.compile(
    r"^(edit this page|was this (page )?helpful|on this page|table of contents|"
    r"copyright ?©|all rights reserved|cookie|skip to (main )?content|"
    r"last modified|previous|next)\b",
    re.IGNORECASE,
)

_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")

MIN_TEXT_CHARS = 200  # below this a page is treated as nav/stub, not content


def normalize_text(text: str) -> str:
    """Collapse whitespace, drop boilerplate lines, and squeeze blank runs. Deterministic."""
    if not text:
        return ""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = _MULTISPACE.sub(" ", raw).strip()
        if not line:
            lines.append("")
            continue
        if _BOILERPLATE.match(line):
            continue
        lines.append(line)
    out = _MULTINEWLINE.sub("\n\n", "\n".join(lines)).strip()
    return out


def is_meaningful(text: str, min_chars: int = MIN_TEXT_CHARS) -> bool:
    """True if the cleaned text is long enough to be worth indexing."""
    return len(text.strip()) >= min_chars


def content_hash(text: str) -> str:
    """Stable hash of normalized content for cross-page dedup."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
