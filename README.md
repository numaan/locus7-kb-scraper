# locus7-kb-scraper

Scrape component documentation → clean it → classify + chunk it → emit **Qdrant-ready JSONL**.

This feeds the vector knowledge base behind **[Locus 7](https://github.com/numaan/locus7)**'s RAG
(resilience patterns / runbooks / reference architectures), but the output is generic and usable by
any RAG stack.

## What it does

```
sources/*.yaml  ──▶  discover (sitemap/crawl)  ──▶  fetch (robots-aware, rate-limited, cached)
                ──▶  extract (trafilatura)  ──▶  clean + dedup  ──▶  chunk + classify
                ──▶  data/out/<source>.jsonl   (one record per line)
                              └──▶ (optional) embed + upsert to Qdrant
```

Each output record is a ready Qdrant payload:

```json
{
  "id": "uuid5(url#index)",            // stable → re-runs upsert in place, never duplicate
  "text": "…chunk text…",
  "metadata": {
    "component": "kubernetes",
    "source_id": "kubernetes",
    "title": "Pod Disruption Budgets",
    "url": "https://kubernetes.io/docs/…",
    "category": "resilience",          // resilience | reference | concept
    "tags": ["high-availability", "fault-tolerance"],
    "license": "CC-BY-4.0",
    "chunk_index": 0,
    "content_hash": "…",
    "scraped_at": "2026-…Z"
  }
}
```

`category` + `tags` let you filter the corpus to resilience-relevant content (what Locus 7's grading
cares about) while still keeping concept/reference material.

## Install & run

```bash
python -m venv .venv && . .venv/Scripts/activate     # (Windows Git Bash; use bin/activate on *nix)
pip install -r requirements.txt

python -m kbscraper list                              # configured sources
python -m kbscraper scrape --source kubernetes       # → data/out/kubernetes.jsonl
python -m kbscraper scrape --source all
```

Or via Docker (no local Python needed):

```bash
docker build -t locus7-kb-scraper .
docker run --rm -v "$PWD/data:/app/data" locus7-kb-scraper scrape --source kubernetes
```

### Optional: push to Qdrant

```bash
pip install -r requirements-push.txt
QDRANT_URL=http://localhost:6333 python -m kbscraper push --collection locus7_kb
```

Embeddings use **fastembed** (lightweight ONNX, no torch); the collection is created with the model's
vector size. Point this at the same Qdrant that Locus 7 uses.

## Adding a source

`sources/` is a config-driven registry — **adding a source is data, not code**. Copy
[`_TEMPLATE.yaml`](sources/_TEMPLATE.yaml) to `sources/<id>.yaml`, set `base_url` +
`sitemaps`/`allow`/`deny` + `content_selector`, declare the `license`, then scrape it. Working
exemplars: `postgresql`, `kubernetes`, `kafka`. [`SOURCES.md`](sources/SOURCES.md) maps your full
component list (Oracle, MySQL, MongoDB, Cassandra, Couchbase, Elasticsearch, OpenShift, Rancher,
Docker, Podman, F5 GTM/LTM/AFM, AWS, Azure, Confluent, RabbitMQ, Istio, Kong, WSO2, Apigee, NGINX,
Envoy, HAProxy, …) to start URLs + licence notes.

## Architecture

| module | role |
|--------|------|
| `models.py` | dataclasses (`SourceSpec`, `RawDoc`, `CleanDoc`, `Chunk`) |
| `sources.py` | load + validate `sources/*.yaml` |
| `fetch.py` | robots.txt + rate-limit + retry + on-disk cache; sitemap / bounded-crawl discovery |
| `extract.py` | HTML → title + main text (trafilatura, BeautifulSoup fallback) |
| `clean.py` | normalize, strip boilerplate, dedup hash *(pure)* |
| `classify.py` | resilience/reference/concept + resilience tags *(pure)* |
| `chunk.py` | boundary-aware chunking + Qdrant record assembly *(pure)* |
| `pipeline.py` | orchestrate a source end-to-end → JSONL |
| `qdrant_push.py` | optional embed + upsert |

The pure stages (`clean`/`classify`/`chunk`) are deterministic and unit-tested without network:

```bash
pip install -r requirements-dev.txt && pytest -q
```

## ⚠️ Legal / etiquette

You are responsible for complying with each source's **Terms of Service and content licence**. The
fetcher is deliberately conservative — it honours `robots.txt`, rate-limits per host, caps pages per
source, and records the declared `license` on every chunk — but that does not grant you the right to
redistribute scraped text. Licences in your list range from permissive (Apache-2.0, CC-BY) to
proprietary and non-commercial; clear each one before indexing or sharing. Do not crawl large clouds
(AWS/Azure) wholesale — scope them tightly with `allow` + `max_pages`.
