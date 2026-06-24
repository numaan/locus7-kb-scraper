from kbscraper.classify import classify, classify_doc_type, resilience_tags


def test_resilience_content_classified_and_tagged():
    text = (
        "Streaming replication keeps a hot standby for high availability. On failover the replica is "
        "promoted automatically. Configure backups and point-in-time recovery (PITR) for disaster recovery."
    )
    category, tags = classify(text, "High Availability, Load Balancing, and Replication")
    assert category == "resilience"
    assert "replication" in tags
    assert "failover" in tags
    assert "backup-recovery" in tags


def test_reference_content():
    text = "Parameter: max_connections. Default value: 100. Configuration option set in postgresql.conf. Syntax: integer."
    category, _ = classify(text, "Server Configuration Reference")
    assert category == "reference"


def test_concept_content():
    text = "Overview. This introduction explains the architecture and how it works at a high level for getting started."
    category, _ = classify(text, "Introduction")
    assert category == "concept"


def test_resilience_tags_empty_for_plain_text():
    assert resilience_tags("the quick brown fox jumps over the lazy dog") == []


# --- doc_type (genre) -------------------------------------------------------

def test_doc_type_runbook():
    text = ("Step 1: stop the primary. Step 2: to promote the standby, run the following command on "
            "each node. Follow these steps to recover the cluster.")
    assert classify_doc_type(text, "Failover Procedure") == "runbook"


def test_doc_type_pattern():
    text = ("Best practice: you should place replicas in separate availability zones. We recommend "
            "avoiding a single point of failure; consider whether a multi-region design is warranted.")
    assert classify_doc_type(text, "High Availability Best Practices") == "pattern"


def test_doc_type_reference():
    text = "Parameter: max_connections. Default value: 100. Syntax: integer. Configuration option."
    assert classify_doc_type(text, "Configuration Reference") == "reference"


def test_doc_type_concept():
    text = "Overview. This introduction explains how it works and the fundamentals of the architecture."
    assert classify_doc_type(text, "Introduction") == "concept"


def test_doc_type_defaults_to_reference_when_no_signal():
    assert classify_doc_type("the quick brown fox jumps over the lazy dog", "Untitled") == "reference"
