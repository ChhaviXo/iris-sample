from pathlib import Path

from app.signal_ingest.normalizer import normalize_entries
from app.signal_ingest.parser import ParsedEntry
from app.signal_ingest.parser import parse_feed


FIXTURE = Path(__file__).parent / "fixtures" / "register_hpc_sample.xml"


def test_normalizer_keeps_relevant_entries_only() -> None:
    entries = parse_feed(FIXTURE.read_bytes())

    signals = normalize_entries(entries)

    assert len(signals) == 1
    assert signals[0].source_record_id.endswith("9990001")
    assert signals[0].signal_type == "cooling"
    assert "cooling" in signals[0].matched_topics
    assert "ai_cluster" in signals[0].matched_topics
    assert "liquid cooling" in signals[0].matched_terms
    assert "Frankfurt" in signals[0].content_text
    assert signals[0].geographic_context == "source text: in Frankfurt"


def test_normalizer_preserves_multiple_matching_topics() -> None:
    entries = parse_feed(FIXTURE.read_bytes())

    signal = normalize_entries(entries)[0]

    assert signal.matched_topics == ("cooling", "ai_cluster")


def test_normalizer_does_not_keep_generic_hpc_only_articles() -> None:
    entry = ParsedEntry(
        source_record_id="hpc-only",
        source_url="https://example.test/hpc-only",
        title="A new supercomputer enters service",
        summary="The HPC system is ready for scientific workloads.",
        content_html="The supercomputer will support research workloads.",
        published_at=None,
        source_modified_at=None,
        source_category="hpc",
        source_kicker="HPC",
        raw_payload={},
    )

    assert normalize_entries([entry]) == []
