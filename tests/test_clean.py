from kbscraper.clean import content_hash, is_meaningful, normalize_text


def test_normalize_collapses_whitespace_and_blank_runs():
    out = normalize_text("a\t\t b  c\n\n\n\nd")
    assert out == "a b c\n\nd"


def test_normalize_drops_boilerplate_lines():
    out = normalize_text("Real content here.\nEdit this page\nWas this helpful?\nMore content.")
    assert "Edit this page" not in out
    assert "Was this helpful" not in out
    assert "Real content here." in out and "More content." in out


def test_is_meaningful_threshold():
    assert not is_meaningful("too short")
    assert is_meaningful("x" * 250)


def test_content_hash_stable_and_whitespace_insensitive_at_edges():
    assert content_hash("  hello world  ") == content_hash("hello world")
    assert content_hash("a") != content_hash("b")
