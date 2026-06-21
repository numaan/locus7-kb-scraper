from kbscraper.chunk import build_chunks, chunk_text
from kbscraper.models import CleanDoc, SourceSpec

SPEC = SourceSpec(id="postgresql", name="PostgreSQL", component="postgresql", base_url="https://x/", license="BSD")


def test_chunk_text_respects_max_chars():
    text = "\n\n".join(f"Paragraph number {i} with some words in it." for i in range(60))
    chunks = chunk_text(text, max_chars=300, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_chunk_text_hard_splits_oversized_unit():
    chunks = chunk_text("x" * 5000, max_chars=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert len(chunks) >= 5


def test_build_chunks_stable_ids_and_metadata():
    doc = CleanDoc(url="https://x/page", title="Replication and Failover", text="High availability via replication.\n\n" + "detail. " * 80, source=SPEC)
    a = build_chunks(doc, "2026-06-21T00:00:00Z")
    b = build_chunks(doc, "2026-06-21T00:00:00Z")
    assert [c.id for c in a] == [c.id for c in b]  # deterministic ids → idempotent upsert
    first = a[0]
    assert first.metadata["component"] == "postgresql"
    assert first.metadata["url"] == "https://x/page"
    assert first.metadata["category"] == "resilience"
    assert first.metadata["chunk_index"] == 0
    assert "content_hash" in first.metadata


def test_build_chunks_ids_differ_by_index():
    doc = CleanDoc(url="https://x/p", title="t", text="word " * 1000, source=SPEC)
    ids = [c.id for c in build_chunks(doc, "t0")]
    assert len(ids) == len(set(ids))
