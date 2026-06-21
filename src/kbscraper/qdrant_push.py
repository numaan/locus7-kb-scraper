"""OPTIONAL final step: embed the JSONL chunks and upsert them into Qdrant.

Kept separate from the scrape so the pipeline runs with zero ML/Qdrant dependencies (the deliverable is
the cleaned JSONL). Install the extra to use this:  pip install -r requirements-push.txt

Embeddings use fastembed (lightweight ONNX, no torch); the vector size is taken from the model so the
collection is created correctly. Payload = chunk text + metadata, matching what Locus 7's RAG reads."""

from __future__ import annotations

import json
from pathlib import Path

from . import config


def _iter_records(in_dir: Path):
    for path in sorted(in_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def push(in_dir: Path | None = None, collection: str | None = None, url: str | None = None, batch: int = 128) -> int:
    """Embed + upsert all JSONL records under in_dir into Qdrant. Returns the count upserted."""
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
    client.recreate_collection(collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))

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
