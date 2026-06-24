"""OPTIONAL final step: embed the JSONL chunks and upsert them into Qdrant.

Kept separate from the scrape so the pipeline runs with zero ML/Qdrant dependencies (the deliverable is
the cleaned JSONL). Install the extra to use this:  pip install -r requirements-push.txt

Embeddings use fastembed (lightweight ONNX, no torch); the vector size is taken from the model so the
collection is created correctly. Payload = chunk text + metadata, matching what Locus 7's RAG reads."""

from __future__ import annotations

import json
from pathlib import Path

from . import config


def backfill_doc_type(collection: str | None = None, url: str | None = None, batch: int = 256) -> dict:
    """Add/refresh the `doc_type` payload on EVERY point in an existing collection (P10-06) — no
    re-fetch, no re-embed. doc_type is a DOCUMENT-level genre: chunks are voted per-url and every
    chunk of a url gets the document's majority genre, so a page lands in exactly one genre view.
    Returns the per-doc_type chunk counts. Used to upgrade a corpus ingested before doc_type existed.
    """
    try:
        from qdrant_client import QdrantClient
    except ImportError as e:  # noqa: BLE001
        raise SystemExit("Push deps missing. Run: pip install -r requirements-push.txt") from e

    from collections import Counter

    from .classify import classify_doc_type

    collection = collection or config.QDRANT_COLLECTION
    url = url or config.QDRANT_URL
    client = QdrantClient(url=url)

    # Pass 1: scroll the whole collection, tallying a per-document (url) genre vote + ids.
    votes: dict[str, Counter] = {}
    ids_by_url: dict[str, list] = {}
    offset = None
    scanned = 0
    while True:
        points, offset = client.scroll(
            collection, limit=batch, offset=offset, with_payload=True, with_vectors=False
        )
        if not points:
            break
        for p in points:
            payload = p.payload or {}
            doc_url = payload.get("url") or payload.get("source_id") or str(p.id)
            dt = classify_doc_type(payload.get("text", ""), payload.get("title", ""))
            votes.setdefault(doc_url, Counter())[dt] += 1
            ids_by_url.setdefault(doc_url, []).append(p.id)
        scanned += len(points)
        if offset is None:
            break

    # Pass 2: resolve each document's majority genre and stamp it on all of its chunks.
    counts: dict[str, int] = {}
    for doc_url, ids in ids_by_url.items():
        # most_common is deterministic on ties by insertion order; sort for stability.
        genre = max(sorted(votes[doc_url]), key=lambda g: votes[doc_url][g])
        client.set_payload(collection, payload={"doc_type": genre}, points=ids)
        counts[genre] = counts.get(genre, 0) + len(ids)
    print(f"Done: {scanned} chunks across {len(ids_by_url)} docs re-typed in '{collection}' -> {counts}")
    return counts


def _iter_records(in_dir: Path):
    for path in sorted(in_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def push(in_dir: Path | None = None, collection: str | None = None, url: str | None = None, batch: int = 128, recreate: bool = True) -> int:
    """Embed + upsert all JSONL records under in_dir into Qdrant. Returns the count upserted.

    recreate=True (default) rebuilds the collection from scratch — a full re-ingest. recreate=False
    APPENDS: create the collection only if missing, then upsert (stable chunk ids dedupe re-runs),
    so new sources add to the corpus without wiping it."""
    try:
        from fastembed import TextEmbedding
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams
    except ImportError as e:  # noqa: BLE001
        raise SystemExit("Push deps missing. Run: pip install -r requirements-push.txt") from e

    in_dir = in_dir or config.OUT_DIR
    collection = collection or config.QDRANT_COLLECTION
    url = url or config.QDRANT_URL

    records = list(_iter_records(in_dir))
    if not records:
        print(f"No records under {in_dir}. Run a scrape first.")
        return 0

    embedder = TextEmbedding(model_name=config.EMBED_MODEL)
    dim = len(next(iter(embedder.embed(["dimension probe"]))))

    client = QdrantClient(url=url)
    if recreate:
        client.recreate_collection(collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
    elif not client.collection_exists(collection):
        client.create_collection(collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))

    upserted = 0
    for i in range(0, len(records), batch):
        block = records[i : i + batch]
        vectors = list(embedder.embed([r["text"] for r in block]))
        points = [
            PointStruct(id=r["id"], vector=vec.tolist(), payload={"text": r["text"], **r["metadata"]})
            for r, vec in zip(block, vectors)
        ]
        client.upsert(collection, points=points)
        upserted += len(points)
        print(f"  upserted {upserted}/{len(records)}")
    print(f"Done: {upserted} points in '{collection}' ({config.EMBED_MODEL}, dim={dim}).")
    return upserted
