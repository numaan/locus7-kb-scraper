from kbscraper.classify import classify, resilience_tags


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
