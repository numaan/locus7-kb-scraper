from kbscraper.licensing import is_permitted, is_recognised_open
from kbscraper.models import SourceSpec
from kbscraper.pipeline import run_source


def _spec(usage="unknown", license="Apache-2.0"):
    return SourceSpec(id="x", name="X", component="x", base_url="https://x/", license=license, usage=usage)


def test_recognised_open_licences():
    assert is_recognised_open("Apache-2.0")
    assert is_recognised_open("CC-BY-4.0")
    assert is_recognised_open("PostgreSQL License")
    assert is_recognised_open("MIT")


def test_non_open_licences_rejected():
    assert not is_recognised_open("CC-BY-NC-SA-4.0")  # non-commercial
    assert not is_recognised_open("CC-BY-ND-4.0")  # no-derivatives
    assert not is_recognised_open("proprietary")
    assert not is_recognised_open("CHECK-SOURCE-TOS")
    assert not is_recognised_open("All rights reserved")


def test_permitted_matrix():
    assert is_permitted(_spec("open", "Apache-2.0"))[0] is True
    assert is_permitted(_spec("open", "proprietary"))[0] is False  # open claimed, licence not recognised
    assert is_permitted(_spec("permitted", "proprietary"))[0] is True  # explicit attestation
    assert is_permitted(_spec("unknown"))[0] is False  # default blocked
    assert is_permitted(_spec("restricted", "Apache-2.0"))[0] is False  # explicitly restricted


def test_pipeline_refuses_blocked_source_without_fetching():
    # usage=unknown ⇒ run_source returns a blocked stat before any network/Fetcher is created.
    stats = run_source(_spec("unknown"))
    assert stats.blocked is not None
    assert stats.chunks == 0 and stats.urls == 0

    stats2 = run_source(_spec("restricted", "Apache-2.0"))
    assert stats2.blocked is not None
