"""Heuristic chunk classifier — tags content as resilience / reference / concept and extracts
resilience tags. Pure (stdlib only), deterministic. Keyword-based on purpose: no model/LLM dependency
so the pipeline runs offline and reproducibly; an embedding/LLM classifier can replace this later.

The taxonomy mirrors what Locus 7's resilience grading cares about (HA / DR / scaling / durability …)."""

from __future__ import annotations

import re

Category = str  # "resilience" | "reference" | "concept"

# Resilience signals double as the `tags` surfaced on each chunk.
RESILIENCE_TERMS: dict[str, list[str]] = {
    "high-availability": ["high availability", "high-availability", " ha ", "active-active", "active/active", "active-passive"],
    "failover": ["failover", "fail over", "automatic failover", "switchover", "promote", "leader election"],
    "replication": ["replication", "replica", "read replica", "streaming replication", "logical replication", "sync replication", "async replication"],
    "backup-recovery": ["backup", "restore", "point-in-time recovery", "pitr", "snapshot", "rpo", "rto", "recovery"],
    "clustering": ["cluster", "quorum", "consensus", "raft", "paxos", "split-brain", "split brain", "membership"],
    "scaling": ["scaling", "autoscal", "horizontal scal", "sharding", "shard", "partitioning", "rebalanc"],
    "durability": ["durability", "fsync", "write-ahead", "wal", "acknowledg", "min.insync", "in-sync replica", "isr"],
    "fault-tolerance": ["fault tolerance", "fault-tolerant", "outage", "degrad", "resilien", "disaster recovery", "multi-region", "multi region", "availability zone", "multi-az", "redundan", "standby"],
}

_REFERENCE = re.compile(
    r"\b(parameter|configuration option|config(uration)? reference|api reference|"
    r"cli reference|command(-line)? (option|flag|reference)|default value|syntax|"
    r"options?:|returns?:|deprecated)\b",
    re.IGNORECASE,
)
_CONCEPT = re.compile(
    r"\b(overview|introduction|getting started|concept|what is|architecture|"
    r"how it works|fundamentals|tutorial)\b",
    re.IGNORECASE,
)


def resilience_tags(text: str) -> list[str]:
    """Resilience tags present in the text (deterministic order)."""
    hay = f" {text.lower()} "
    return [tag for tag, terms in RESILIENCE_TERMS.items() if any(t in hay for t in terms)]


def _count(patterns_or_terms, text_lower: str) -> int:
    if isinstance(patterns_or_terms, re.Pattern):
        return len(patterns_or_terms.findall(text_lower))
    return sum(text_lower.count(t) for t in patterns_or_terms)


def classify(text: str, title: str = "") -> tuple[Category, list[str]]:
    """Return (category, resilience_tags). Resilience wins ties (it's the corpus's purpose)."""
    blob = f"{title}\n{text}".lower()
    tags = resilience_tags(blob)
    resilience_score = sum(_count(terms, blob) for terms in RESILIENCE_TERMS.values())
    reference_score = _count(_REFERENCE, blob)
    concept_score = _count(_CONCEPT, blob)

    best: Category = "reference"
    best_score = reference_score
    if concept_score > best_score:
        best, best_score = "concept", concept_score
    # Resilience takes precedence on >= so tagged content is never mislabeled reference/concept.
    if resilience_score >= best_score and resilience_score > 0:
        best = "resilience"
    return best, tags


# --- Document type (genre) — orthogonal to `category` (subject) --------------------------------
# `category` says what a chunk is ABOUT (resilience/reference/concept); `doc_type` says what KIND of
# page it is (runbook/pattern/reference/concept). This is what Locus 7's KB browser splits Patterns
# vs Runbooks on. Heuristic + deterministic (no model), tunable by editing the signal sets below.
DocType = str  # "runbook" | "pattern" | "reference" | "concept"

# Operational, step-by-step / procedural language → a runbook. Deliberately narrow: only genuinely
# procedural cues, NOT the bare "to <verb>" phrasing that pervades reference docs ("to configure X,
# set parameter Y"). Operational verbs are kept only in the recovery/ops sense.
_RUNBOOK = re.compile(
    r"\b(step[-\s]?\d|step[-\s]by[-\s]step|follow these steps|following steps|"
    r"procedure|runbook|troubleshoot(ing)?|run the following|execute the following|"
    r"on each (node|server|host|broker)|recovery (steps|procedure)|"
    r"to (recover|restore|fail ?over|switch ?over|promote|upgrade|migrate|rotate|"
    r"provision|bootstrap|decommission|drain)|walkthrough|how[-\s]?to guide)\b",
    re.IGNORECASE,
)
# Prescriptive design / architecture guidance → a pattern (best practices fold in here). Narrowed
# to genuinely prescriptive phrasing; bare "recommended"/"avoid" alone is weak, so it must out-score
# reference/concept (see the margin rule below) rather than win on a single hit.
_PATTERN = re.compile(
    r"\b(best[-\s]practice|production recommendation|we recommend|it is recommended|"
    r"you should|should not|must not|anti[-\s]?pattern|design pattern|"
    r"rule of thumb|when to use|consider (using|whether)|trade[-\s]?off|"
    r"it is advisable|as a (general )?rule|for production|in production)\b",
    re.IGNORECASE,
)
# Man-page shape — distinctive reference markers that keep command/API pages out of the
# pattern/runbook buckets. Deliberately NOT bare "options"/"--flag" (those pervade every doc and
# would swamp the score); only the structural man-page headings.
_REFMAN = re.compile(
    r"\b(synopsis|usage:|exit status|return value|see also|man(ual)? page)\b",
    re.IGNORECASE,
)

# The page TITLE is the strongest genre cue — docs are organised by purpose. A how-to/quickstart/
# operations title is a runbook; a best-practice/tuning/recommendation title is a pattern. These win
# outright (body keyword counts are noisy and scale with length, drowning genre on long ref pages).
_TITLE_RUNBOOK = re.compile(
    r"\b(quickstarts?|quick start|tutorials?|getting started|how[-\s]?tos?|walkthroughs?|"
    r"step[-\s]by[-\s]step|install(ation|ing)?|deploy(ing|ment)?|set[-\s]?up|configuring|"
    r"migrat(e|ion|ing)|upgrad(e|ing)|backups?|restore|recover(y|ing)|disaster recovery|"
    r"fail[-\s]?over|switch[-\s]?over|operations?|runbooks?|procedures?|maintenance|provisioning|"
    r"bootstrap|getting[-\s]?started)\b",
    re.IGNORECASE,
)
_TITLE_PATTERN = re.compile(
    r"\b(best[-\s]practices?|recommendations?|guidelines?|anti[-\s]?patterns?|"
    r"(performance )?tuning|production (checklist|recommendation|guide|readiness|deployment)|"
    r"hardening|sizing|capacity planning|reference architecture|design (pattern|consideration))\b",
    re.IGNORECASE,
)

# A genre needs at least this many BODY signal hits to override reference/concept when the title is
# neutral (so a lone stray "you should" can't reclassify a reference page).
_MIN_SPECIAL = 3


def classify_doc_type(text: str, title: str = "") -> DocType:
    """Return the document genre (runbook | pattern | reference | concept). Deterministic.

    Title-first: a how-to/quickstart/ops title ⇒ runbook, a best-practice/tuning title ⇒ pattern.
    When the title is neutral, fall back to body signals but only promote to runbook/pattern when
    that signal is strong (>= MIN_SPECIAL) AND beats the reference/concept signal — so man pages and
    API references don't leak into Patterns/Runbooks on a stray 'recommended'."""
    t = title.lower()
    rb_title, pat_title = len(_TITLE_RUNBOOK.findall(t)), len(_TITLE_PATTERN.findall(t))
    if rb_title or pat_title:
        return "runbook" if rb_title >= pat_title else "pattern"

    body = text.lower()
    runbook = _count(_RUNBOOK, body)
    pattern = _count(_PATTERN, body)
    reference = _count(_REFERENCE, body) + _count(_REFMAN, body)
    concept = _count(_CONCEPT, body)

    base = "reference" if reference >= concept else "concept"
    base_score = max(reference, concept)
    special, special_score = ("runbook", runbook) if runbook >= pattern else ("pattern", pattern)
    if special_score >= _MIN_SPECIAL and special_score > base_score:
        return special
    return base if base_score > 0 else "reference"
