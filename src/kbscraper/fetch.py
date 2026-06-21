"""Polite fetching + URL discovery. Respects robots.txt, rate-limits per host, retries with backoff,
and caches raw HTML on disk so re-runs don't re-hit the network. Discovery prefers sitemaps; falls
back to a bounded same-site crawl. Network-touching — covered by the offline tests via small helpers.

NOTE: you are responsible for honouring each source's Terms of Service and content licence. This
fetcher is deliberately conservative (robots + rate limit + page caps); do not raise those limits to
hammer a site.
"""

from __future__ import annotations

import hashlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from . import config
from .models import RawDoc, SourceSpec

# Client-side redirect stubs (meta-refresh / JS location) — followed once so we index the real page.
_META_REFRESH = re.compile(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>\s]+)', re.I)
_JS_LOCATION = re.compile(r'(?:window\.location(?:\.href)?|location\.(?:href|replace\())\s*=?\s*\(?["\']([^"\']+)["\']', re.I)


def _decode(r: httpx.Response) -> str:
    """Robustly decode a response body. Trust the header charset (strict — a wrong one raises rather
    than yielding �), else detect from bytes, else utf-8 with replacement. Fixes mojibake like © → �."""
    enc = r.charset_encoding  # from the Content-Type header, if any
    if enc:
        try:
            return r.content.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(r.content).best()
        if best is not None:
            return str(best)
    except Exception:  # noqa: BLE001 - detection is best-effort
        pass
    return r.content.decode("utf-8", errors="replace")


def _same_host(a: str, b: str) -> bool:
    return urlparse(a).netloc == urlparse(b).netloc


def _redirect_target(html: str, base_url: str) -> str | None:
    """Resolve a meta-refresh / JS-location redirect URL from a stub page, or None."""
    m = _META_REFRESH.search(html) or _JS_LOCATION.search(html)
    if not m:
        return None
    return urljoin(base_url, m.group(1).strip()).split("#")[0]


def url_allowed(url: str, spec: SourceSpec) -> bool:
    """Same-host + allow/deny path filtering (independent of robots; pure, unit-tested)."""
    if not url.startswith(spec.base_url) and urlparse(url).netloc != urlparse(spec.base_url).netloc:
        return False
    if any(d in url for d in spec.deny):
        return False
    if spec.allow and not any(a in url for a in spec.allow):
        return False
    return url.startswith("http")


def _cache_path(url: str):
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return config.CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".html")


class Fetcher:
    """Stateful over a run: shared httpx client, per-host robots + rate-limit + cache."""

    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_S,
            follow_redirects=True,
        )
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}

    # --- politeness ---
    def _robot(self, url: str) -> RobotFileParser | None:
        host = urlparse(url).netloc
        if host not in self._robots:
            rp = RobotFileParser()
            rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
            try:
                rp.read()
            except Exception:  # noqa: BLE001 - missing/broken robots ⇒ treat as permissive
                rp = None
            self._robots[host] = rp
        return self._robots[host]

    def can_fetch(self, url: str) -> bool:
        if not config.RESPECT_ROBOTS:
            return True
        rp = self._robot(url)
        return rp is None or rp.can_fetch(config.USER_AGENT, url)

    def _throttle(self, url: str, rate_limit_s: float) -> None:
        host = urlparse(url).netloc
        wait = rate_limit_s - (time.monotonic() - self._last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    # --- fetching ---
    def _http_get(self, url: str, rate_limit_s: float) -> str | None:
        for attempt in range(config.MAX_RETRIES):
            self._throttle(url, rate_limit_s)
            try:
                r = self._client.get(url)
                if r.status_code == 200 and "html" in r.headers.get("content-type", "html"):
                    return _decode(r)
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt)
                    continue
                return None
            except httpx.HTTPError:
                time.sleep(2 ** attempt)
        return None

    def _render_get(self, url: str, rate_limit_s: float) -> str | None:
        from .render import render_html  # optional dep; import only when a source opts in

        self._throttle(url, rate_limit_s)
        return render_html(url)

    def get(self, url: str, rate_limit_s: float = 1.0, use_cache: bool = True, render: bool = False, _hops: int = 0) -> str | None:
        cp = _cache_path(url)
        if use_cache and cp.exists():
            return cp.read_text(encoding="utf-8", errors="ignore")
        if not self.can_fetch(url):
            return None
        html = self._render_get(url, rate_limit_s) if render else self._http_get(url, rate_limit_s)
        if html is None:
            return None
        # Follow a single client-side redirect (meta-refresh / JS) for stub pages (static fetch only).
        if not render and _hops < 2:
            target = _redirect_target(html, url)
            if target and target != url and _same_host(target, url):
                followed = self.get(target, rate_limit_s, use_cache, render, _hops + 1)
                if followed:
                    html = followed
        cp.write_text(html, encoding="utf-8")
        return html

    def fetch_doc(self, url: str, rate_limit_s: float = 1.0, render: bool = False) -> RawDoc | None:
        html = self.get(url, rate_limit_s, render=render)
        if html is None:
            return None
        return RawDoc(url=url, html=html, fetched_at=datetime.now(timezone.utc).isoformat())

    # --- discovery ---
    def _sitemap_urls(self, sitemap_url: str, spec: SourceSpec, seen: set[str]) -> list[str]:
        if sitemap_url in seen:
            return []
        seen.add(sitemap_url)
        xml = self.get(sitemap_url, spec.rate_limit_s)
        if not xml:
            return []
        urls: list[str] = []
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return []
        tag = root.tag.lower()
        for loc in root.iter():
            if loc.tag.lower().endswith("loc") and loc.text:
                u = loc.text.strip()
                if "sitemapindex" in tag or u.endswith(".xml"):
                    urls.extend(self._sitemap_urls(u, spec, seen))
                elif url_allowed(u, spec):
                    urls.append(u)
        return urls

    def discover(self, spec: SourceSpec) -> list[str]:
        """Discover content URLs for a source: sitemaps first, else a bounded same-site BFS crawl."""
        found: list[str] = []
        if spec.sitemaps:
            seen: set[str] = set()
            for sm in spec.sitemaps:
                found.extend(self._sitemap_urls(sm, spec, seen))
        if not found:
            found = self._crawl(spec)
        # dedup, keep order, cap
        out, seen2 = [], set()
        for u in found:
            if u not in seen2:
                seen2.add(u)
                out.append(u)
        return out[: spec.max_pages]

    def _crawl(self, spec: SourceSpec) -> list[str]:
        from bs4 import BeautifulSoup  # local import: only needed for the crawl fallback

        queue, seen, out = [spec.base_url], {spec.base_url}, []
        while queue and len(out) < spec.max_pages:
            url = queue.pop(0)
            html = self.get(url, spec.rate_limit_s)
            if not html:
                continue
            if url_allowed(url, spec):
                out.append(url)
            for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
                nxt = urljoin(url, a["href"]).split("#")[0]
                if nxt not in seen and url_allowed(nxt, spec):
                    seen.add(nxt)
                    queue.append(nxt)
        return out

    def close(self) -> None:
        self._client.close()
