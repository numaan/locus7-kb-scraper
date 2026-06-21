import httpx

from kbscraper import config, fetch
from kbscraper.fetch import Fetcher, _decode, _redirect_target, _same_host


def _resp(content: bytes, ctype: str = "text/html") -> httpx.Response:
    return httpx.Response(200, headers={"content-type": ctype}, content=content)


def test_decode_utf8_via_header():
    assert "©" in _decode(_resp("Copyright © 2026".encode("utf-8"), "text/html; charset=utf-8"))


def test_decode_latin1_without_header_no_mojibake():
    # No charset header → byte-level detection. The exact non-ASCII glyph for an isolated 0xA9 is
    # ambiguous across single-byte codecs, but the win is decoding cleanly with NO replacement char.
    body = ("Copyright © 2026 The Group. " + "context " * 50).encode("latin-1")
    out = _decode(_resp(body, "text/html"))
    assert "�" not in out and "Copyright" in out


def test_decode_wrong_header_falls_back_to_detection():
    body = ("Información © año nuevo. " + "contenido " * 50).encode("latin-1")
    out = _decode(_resp(body, "text/html; charset=utf-8"))  # header lies (bytes are latin-1)
    assert "�" not in out


def test_redirect_target_meta_refresh_and_js():
    assert _redirect_target('<meta http-equiv="refresh" content="0; url=/docs/real">', "https://x.io/p") == "https://x.io/docs/real"
    assert _redirect_target("<script>window.location.href = 'https://x.io/r'</script>", "https://x.io/p") == "https://x.io/r"
    assert _redirect_target("<p>ordinary content, no redirect</p>", "https://x.io/p") is None


def test_same_host():
    assert _same_host("https://x.io/a", "https://x.io/b")
    assert not _same_host("https://x.io/a", "https://y.io/b")


def test_render_path_routes_to_renderer(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RESPECT_ROBOTS", False)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    import kbscraper.render as render_mod

    monkeypatch.setattr(render_mod, "render_html", lambda url, timeout_s=None: "<html>RENDERED</html>")
    f = Fetcher(httpx.Client())
    html = f.get("https://example.com/p", rate_limit_s=0, use_cache=False, render=True)
    assert html == "<html>RENDERED</html>"
