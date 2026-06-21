"""Load source specs from the sources/ registry (one YAML per source). Adding a source is data, not
code. Validation is strict so a malformed entry fails fast rather than silently scraping nothing."""

from __future__ import annotations

from pathlib import Path

import yaml

from .licensing import VALID_USAGE
from .models import SourceSpec

SOURCES_DIR = Path(__file__).resolve().parents[2] / "sources"

_REQUIRED = ("id", "name", "component", "base_url", "license")


def _to_spec(data: dict, path: Path) -> SourceSpec:
    missing = [k for k in _REQUIRED if not data.get(k)]
    if missing:
        raise ValueError(f"{path.name}: missing required field(s): {', '.join(missing)}")
    usage = str(data.get("usage", "unknown")).lower()
    if usage not in VALID_USAGE:
        raise ValueError(f"{path.name}: invalid usage '{usage}' (expected one of {', '.join(VALID_USAGE)})")
    return SourceSpec(
        id=data["id"],
        name=data["name"],
        component=data["component"],
        base_url=data["base_url"].rstrip("/") + "/",
        license=data["license"],
        usage=usage,
        license_url=data.get("license_url"),
        sitemaps=list(data.get("sitemaps", [])),
        allow=list(data.get("allow", [])),
        deny=list(data.get("deny", [])),
        content_selector=data.get("content_selector"),
        render=bool(data.get("render", False)),
        max_pages=int(data.get("max_pages", 200)),
        rate_limit_s=float(data.get("rate_limit_s", 1.0)),
        enabled=bool(data.get("enabled", True)),
    )


def load_sources(sources_dir: Path | None = None) -> list[SourceSpec]:
    """All enabled source specs, sorted by id. Files starting with '_' (templates) are skipped."""
    d = sources_dir or SOURCES_DIR
    specs: list[SourceSpec] = []
    for path in sorted(d.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        spec = _to_spec(data, path)
        if spec.enabled:
            specs.append(spec)
    return sorted(specs, key=lambda s: s.id)


def get_source(source_id: str, sources_dir: Path | None = None) -> SourceSpec:
    for s in load_sources(sources_dir):
        if s.id == source_id:
            return s
    raise KeyError(f"unknown source: {source_id}")
