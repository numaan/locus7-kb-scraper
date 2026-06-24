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

# Operational, step-by-step / procedural language → a runbook.
_RUNBOOK = re.compile(
    r"\b(step[-\s]?\d|step[-\s]by[-\s]step|follow these steps|procedure|runbook|"
    r"troubleshoot(ing)?|to (configure|install|set up|setup|enable|create|deploy|upgrade|migrate|"
    r"restore|recover|restart|start|stop|run|rotate|scale|provision)|run the following|"
    r"execute the|on each (node|server|host)|checklist|recovery steps|operational)\b",
    re.IGNORECASE,
)
# Prescriptive design / architecture guidance → a pattern (best practices fold in here).
_PATTERN = re.compile(
    r"\b(best[-\s]practice|recommended|we recommend|you should|should not|anti[-\s]?pattern|"
    r"design pattern|guideline|rule of thumb|when to use|consider (using|whether)|trade[-\s]?off|"
    r"do not|prefer|avoid|it is advisable|as a (general )?rule)\b",
    re.IGNORECASE,
)

# Tie-break priority when scores are equal: an operational page reads as a runbook, prescriptive
# guidance as a pattern, then concept, with reference the catch-all default for dense API docs.
_DOCTYPE_PRIORITY = {"runbook": 3, "pattern": 2, "concept": 1, "reference": 0}


def classify_doc_type(text: str, title: str = "") -> DocType:
    """Return the document genre (runbook | pattern | reference | concept). Deterministic; defaults
    to 'reference' when no genre signal is present (the bulk of vendor docs)."""
    blob = f"{title}\n{title}\n{text}".lower()  # title weighted ×2 — it's the strongest genre cue
    scores = {
        "runbook": _count(_RUNBOOK, blob),
        "pattern": _count(_PATTERN, blob),
        "reference": _count(_REFERENCE, blob),
        "concept": _count(_CONCEPT, blob),
    }
    best = max(scores, key=lambda k: (scores[k], _DOCTYPE_PRIORITY[k]))
    return best if scores[best] > 0 else "reference"
