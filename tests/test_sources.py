from pathlib import Path

import pytest

from kbscraper.fetch import url_allowed
from kbscraper.models import SourceSpec
from kbscraper.sources import get_source, load_sources

REPO = Path(__file__).resolve().parents[1]


def test_exemplar_sources_load_and_validate():
    specs = load_sources(REPO / "sources")
    ids = {s.id for s in specs}
    assert {"postgresql", "kubernetes", "kafka"} <= ids
    for s in specs:
        assert s.base_url.startswith("http") and s.base_url.endswith("/")
        assert s.license  # licence must be declared


def test_template_is_ignored():
    specs = load_sources(REPO / "sources")
    assert "example" not in {s.id for s in specs}  # _TEMPLATE.yaml skipped


def test_get_source_unknown_raises():
    with pytest.raises(KeyError):
        get_source("nope", REPO / "sources")


def test_url_allowed_filters():
    spec = SourceSpec(
        id="k", name="K", component="k", base_url="https://kubernetes.io/docs/", license="CC-BY-4.0",
        allow=["/docs/concepts/"], deny=["/zh-cn/"],
    )
    assert url_allowed("https://kubernetes.io/docs/concepts/overview/", spec)
    assert not url_allowed("https://kubernetes.io/docs/reference/glossary/", spec)  # not in allow
    assert not url_allowed("https://kubernetes.io/zh-cn/docs/concepts/x/", spec)  # denied
    assert not url_allowed("https://example.com/docs/concepts/x/", spec)  # different host
