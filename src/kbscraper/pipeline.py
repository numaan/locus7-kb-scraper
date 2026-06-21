"""Orchestrate a source end-to-end: discover URLs → fetch → extract → clean/dedup → chunk+classify →
write JSONL (one Qdrant-ready record per line). Deterministic given a fixed cache; idempotent ids."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .chunk import build_chunks
from .clean import content_hash, is_meaningful
from .extract import extract
from .fetch import Fetcher
from .licensing import is_permitted
from .models import SourceSpec
from .sources import load_sources


@dataclasses.dataclass
class RunStats:
    source_id: str
    urls: int = 0
    pages_kept: int = 0
    pages_skipped: int = 0
    chunks: int = 0
    out_path: str = ""
    blocked: str | None = None  # set when the usage gate refuses the source (nothing fetched)


def run_source(spec: SourceSpec, fetcher: Fetcher | None = None, out_dir: Path | None = None) -> RunStats:
    """Scrape one source to data/out/<id>.jsonl. Returns counts. Refuses non-permitted sources."""
    permitted, reason = is_permitted(spec)
    if not permitted:
        return RunStats(source_id=spec.id, blocked=reason)
    own = fetcher is None
    fetcher = fetcher or Fetcher()
    out_dir = out_dir or config.OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{spec.id}.jsonl"
    scraped_at = datetime.now(timezone.utc).isoformat()

    stats = RunStats(source_id=spec.id, out_path=str(out_path))
    seen_hashes: set[str] = set()
    try:
        urls = fetcher.discover(spec)
        stats.urls = len(urls)
        with out_path.open("w", encoding="utf-8") as fh:
            for url in urls:
                raw = fetcher.fetch_doc(url, spec.rate_limit_s, render=spec.render)
                if raw is None:
                    stats.pages_skipped += 1
                    continue
                doc = extract(raw, spec)
                if not is_meaningful(doc.text):
                    stats.pages_skipped += 1
                    continue
                h = content_hash(doc.text)
                if h in seen_hashes:  # page-level dedup (mirrors, print views, aliases)
                    stats.pages_skipped += 1
                    continue
                seen_hashes.add(h)
                stats.pages_kept += 1
                for ch in build_chunks(doc, scraped_at):
                    fh.write(json.dumps({"id": ch.id, "text": ch.text, "metadata": ch.metadata}, ensure_ascii=False) + "\n")
                    stats.chunks += 1
    finally:
        if own:
            fetcher.close()
    return stats


def run_all(out_dir: Path | None = None) -> list[RunStats]:
    fetcher = Fetcher()
    try:
        return [run_source(spec, fetcher, out_dir) for spec in load_sources()]
    finally:
        fetcher.close()
