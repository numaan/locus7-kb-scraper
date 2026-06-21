"""Usage gate — only fetch docs that are publicly available AND whose usage is known to permit it.

A source is permitted only when its `usage` is:
  - "open"      and its declared licence is a RECOGNISED open licence (validated here), or
  - "permitted" meaning YOU have reviewed the source's ToS/licence and attest it's allowed.
Anything "unknown" (the default) or "restricted" is BLOCKED. Non-commercial (NC) / no-derivatives
(ND) licences are treated as restricted for an indexing/redistribution use case.

Robots.txt + public-URL access (the "publicly available" half) is enforced in fetch.py.
"""

from __future__ import annotations

from .models import SourceSpec

# Recognised open licences (substring match on a normalised licence string). Permissive + the
# attribution/share-alike Creative Commons + open documentation licences. NOT NC/ND/proprietary.
KNOWN_OPEN_LICENSES = (
    "apache-2.0", "apache 2.0", "mit", "bsd", "isc", "mpl-2.0", "postgresql",
    "cc0", "public-domain", "public domain", "unlicense",
    "cc-by-4.0", "cc-by 4.0", "cc-by-3.0", "cc-by-sa-4.0", "cc-by-sa", "gfdl", "cc-by-2.0",
)
# Markers that disqualify a licence even if it otherwise looks open.
_DISQUALIFY = ("-nc", " nc", "noncommercial", "non-commercial", "-nd", " nd", "no-deriv",
               "proprietary", "all rights reserved", "check", "tbd", "unknown")

VALID_USAGE = ("open", "permitted", "unknown", "restricted")


def _normalise(license_str: str) -> str:
    return f" {license_str.lower().strip()} "


def is_recognised_open(license_str: str) -> bool:
    s = _normalise(license_str)
    if any(bad in s for bad in _DISQUALIFY):
        return False
    return any(lic in s for lic in KNOWN_OPEN_LICENSES)


def is_permitted(spec: SourceSpec) -> tuple[bool, str]:
    """Return (permitted, reason). The pipeline only scrapes permitted sources."""
    usage = (spec.usage or "unknown").lower()
    if usage == "restricted":
        return False, "usage=restricted (licence/ToS disallows indexing)"
    if usage == "permitted":
        return True, "usage=permitted (you attested the ToS allows this)"
    if usage == "open":
        if is_recognised_open(spec.license):
            return True, f"usage=open, recognised licence ({spec.license})"
        return False, (
            f"usage=open but licence '{spec.license}' is not a recognised open licence — "
            "fix the licence, or set usage: permitted to attest you've cleared the ToS"
        )
    return False, (
        "usage=unknown — review the source's ToS/licence, then set usage: open (recognised licence) "
        "or usage: permitted (attested). Blocked until then."
    )
