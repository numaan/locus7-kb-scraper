"""Core data shapes for the ingestion pipeline.

Plain dataclasses (stdlib only) so the pure pipeline stages (clean/classify/chunk) and their tests
have no third-party import. Network/extraction stages add httpx/trafilatura on top of these.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceSpec:
    """A documentation source, declared as data in sources/<id>.yaml."""

    id: str  # stable slug, e.g. "postgresql"
    name: str  # human label, e.g. "PostgreSQL"
    component: str  # canonical component key used in the chunk metadata
    base_url: str
    license: str  # the source's content licence (your responsibility to honour)
    # Usage gate (see licensing.py): "open" (recognised open licence) | "permitted" (you attested the
    # ToS allows this) | "restricted" (disallowed) | "unknown" (default — BLOCKED until cleared).
    usage: str = "unknown"
    license_url: str | None = None  # link to the licence / terms of service
    sitemaps: list[str] = field(default_factory=list)  # preferred URL discovery
    allow: list[str] = field(default_factory=list)  # substring/prefix filters a URL must match
    deny: list[str] = field(default_factory=list)  # substrings that exclude a URL
    content_selector: str | None = None  # CSS selector for main content (extractor fallback)
    render: bool = False  # headless-render this source (JS-heavy docs); needs the render extra
    max_pages: int = 200
    rate_limit_s: float = 1.0
    enabled: bool = True


@dataclass
class RawDoc:
    url: str
    html: str
    fetched_at: str


@dataclass
class CleanDoc:
    url: str
    title: str
    text: str
    source: SourceSpec


@dataclass
class Chunk:
    """A Qdrant-ready record: a stable id, the text, and a flat payload of metadata."""

    id: str
    text: str
    metadata: dict
