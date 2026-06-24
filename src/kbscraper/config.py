"""Runtime settings (env-overridable). No secrets here; the optional push step reads QDRANT_* / the
embedding model from the environment. Mirrors Locus 7's convention of plain env defaults."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Where scraped HTML is cached and JSONL output is written.
DATA_DIR = Path(os.environ.get("KB_DATA_DIR", ROOT / "data"))
CACHE_DIR = DATA_DIR / "cache"
OUT_DIR = DATA_DIR / "out"

# Polite crawling defaults (per-source values in the YAML override rate_limit_s / max_pages).
USER_AGENT = os.environ.get(
    "KB_USER_AGENT",
    "locus7-kb-scraper/0.1 (+https://github.com/numaan/locus7; documentation indexing for RAG)",
)
REQUEST_TIMEOUT_S = float(os.environ.get("KB_TIMEOUT_S", "30"))
MAX_RETRIES = int(os.environ.get("KB_MAX_RETRIES", "3"))
RESPECT_ROBOTS = os.environ.get("KB_RESPECT_ROBOTS", "true").lower() != "false"
# TLS verification (default on). Set KB_TLS_VERIFY=false only behind a trusted intercepting proxy
# (e.g. a corporate / sandboxed network with a MITM cert you cannot install). Never for untrusted nets.
TLS_VERIFY = os.environ.get("KB_TLS_VERIFY", "true").lower() != "false"

# Optional push step (qdrant_push.py).
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "locus7_kb")
EMBED_MODEL = os.environ.get("KB_EMBED_MODEL", "BAAI/bge-small-en-v1.5")  # fastembed model id
