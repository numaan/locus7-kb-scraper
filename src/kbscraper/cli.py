"""Command-line entry point.

  python -m kbscraper list                      # list configured sources
  python -m kbscraper scrape --source postgresql
  python -m kbscraper scrape --source all
  python -m kbscraper push --collection locus7_kb   # optional: embed + upsert to Qdrant
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config
from .licensing import is_permitted
from .pipeline import run_all, run_source
from .sources import get_source, load_sources


def _cmd_list(_args) -> None:
    print("  use  id              name                  usage       licence")
    for s in load_sources():
        ok, _ = is_permitted(s)
        print(f"  {'OK ' if ok else '-- '} {s.id:14}  {s.name:20}  {s.usage:10}  {s.license}")
    print("\n  OK = will scrape (publicly available + usage permitted) | -- = blocked by the usage gate")


def _cmd_scrape(args) -> None:
    out_dir = Path(args.out) if args.out else config.OUT_DIR
    runs = run_all(out_dir) if args.source == "all" else [run_source(get_source(args.source), out_dir=out_dir)]
    total = 0
    for r in runs:
        if r.blocked:
            print(f"[{r.source_id}] BLOCKED — {r.blocked}")
            continue
        print(f"[{r.source_id}] urls={r.urls} kept={r.pages_kept} skipped={r.pages_skipped} chunks={r.chunks} -> {r.out_path}")
        total += r.chunks
    print(f"Total chunks: {total}")


def _cmd_push(args) -> None:
    from .qdrant_push import push  # imported lazily so scrape works without push deps

    push(in_dir=Path(args.in_dir) if args.in_dir else None, collection=args.collection, url=args.url)


def _cmd_backfill(args) -> None:
    from .qdrant_push import backfill_doc_type  # lazy import (Qdrant dep)

    backfill_doc_type(collection=args.collection, url=args.url)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="kbscraper", description="Scrape component docs into Qdrant-ready chunks.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list configured sources").set_defaults(func=_cmd_list)

    sc = sub.add_parser("scrape", help="scrape a source (or all) to JSONL")
    sc.add_argument("--source", required=True, help="source id, or 'all'")
    sc.add_argument("--out", default=None, help="output dir (default data/out)")
    sc.set_defaults(func=_cmd_scrape)

    ps = sub.add_parser("push", help="embed + upsert JSONL to Qdrant (optional deps)")
    ps.add_argument("--in", dest="in_dir", default=None, help="input dir of JSONL (default data/out)")
    ps.add_argument("--collection", default=None, help="Qdrant collection (default $QDRANT_COLLECTION)")
    ps.add_argument("--url", default=None, help="Qdrant URL (default $QDRANT_URL)")
    ps.set_defaults(func=_cmd_push)

    bf = sub.add_parser("backfill", help="re-classify doc_type on an existing collection (no re-embed)")
    bf.add_argument("--collection", default=None, help="Qdrant collection (default $QDRANT_COLLECTION)")
    bf.add_argument("--url", default=None, help="Qdrant URL (default $QDRANT_URL)")
    bf.set_defaults(func=_cmd_backfill)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
