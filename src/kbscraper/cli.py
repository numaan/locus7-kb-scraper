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
from .pipeline import run_all, run_source
from .sources import get_source, load_sources


def _cmd_list(_args) -> None:
    for s in load_sources():
        print(f"  {s.id:16}  {s.name:22}  {s.base_url}")


def _cmd_scrape(args) -> None:
    out_dir = Path(args.out) if args.out else config.OUT_DIR
    runs = run_all(out_dir) if args.source == "all" else [run_source(get_source(args.source), out_dir=out_dir)]
    total = 0
    for r in runs:
        print(f"[{r.source_id}] urls={r.urls} kept={r.pages_kept} skipped={r.pages_skipped} chunks={r.chunks} -> {r.out_path}")
        total += r.chunks
    print(f"Total chunks: {total}")


def _cmd_push(args) -> None:
    from .qdrant_push import push  # imported lazily so scrape works without push deps

    push(in_dir=Path(args.in_dir) if args.in_dir else None, collection=args.collection, url=args.url)


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

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
