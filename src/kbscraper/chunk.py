"""Chunking + Qdrant-ready record assembly. Pure (stdlib only), deterministic.

Splits on paragraph/sentence boundaries (never mid-word) into ~char-bounded chunks with overlap, then
attaches metadata + a STABLE id (uuid5 of url+index) so re-runs upsert in place rather than duplicate."""

from __future__ import annotations

import re
import uuid

from .classify import classify
from .clean import content_hash
from .models import Chunk, CleanDoc

MAX_CHARS = 1200
OVERLAP_CHARS = 150
# Deterministic namespace for stable chunk ids (constant, not time/random-based).
_NS = uuid.UUID("6f9b8a1e-0c2d-4e7a-9b3f-1a2b3c4d5e6f")

_PARA = re.compile(r"\n\s*\n")
_SENT = re.compile(r"(?<=[.!?])\s+")


def _split_units(text: str) -> list[str]:
    """Paragraphs, falling back to sentences for any paragraph longer than MAX_CHARS."""
    units: list[str] = []
    for para in _PARA.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= MAX_CHARS:
            units.append(para)
        else:
            units.extend(s.strip() for s in _SENT.split(para) if s.strip())
    return units


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Greedy-pack units into chunks ≤ max_chars, carrying `overlap` chars of tail context forward."""
    units = _split_units(text)
    chunks: list[str] = []
    cur = ""
    for unit in units:
        if not cur:
            cur = unit
        elif len(cur) + 1 + len(unit) <= max_chars:
            cur = f"{cur}\n{unit}"
        else:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap and len(cur) > overlap else ""
            cur = f"{tail}\n{unit}".strip() if tail else unit
    if cur:
        chunks.append(cur)
    # A single oversized unit (e.g. no sentence breaks) still needs hard splitting.
    out: list[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
        else:
            for i in range(0, len(c), max_chars - overlap):
                out.append(c[i : i + max_chars])
    return [c for c in out if c.strip()]


def build_chunks(doc: CleanDoc, scraped_at: str) -> list[Chunk]:
    """Turn a CleanDoc into Qdrant-ready Chunk records with classification + metadata."""
    chunks: list[Chunk] = []
    pieces = chunk_text(doc.text)
    for i, piece in enumerate(pieces):
        category, tags = classify(piece, doc.title)
        cid = str(uuid.uuid5(_NS, f"{doc.url}#{i}"))
        chunks.append(
            Chunk(
                id=cid,
                text=piece,
                metadata={
                    "component": doc.source.component,
                    "source_id": doc.source.id,
                    "source_name": doc.source.name,
                    "title": doc.title,
                    "url": doc.url,
                    "category": category,
                    "tags": tags,
                    "license": doc.source.license,
                    "chunk_index": i,
                    "content_hash": content_hash(piece),
                    "scraped_at": scraped_at,
                },
            )
        )
    return chunks
