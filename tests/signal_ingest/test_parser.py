from pathlib import Path

from app.signal_ingest.parser import parse_feed
from app.signal_ingest.parser import parse_feed_with_report


FIXTURE = Path(__file__).parent / "fixtures" / "register_hpc_sample.xml"


def test_parse_register_rss_fixture() -> None:
    entries = parse_feed(FIXTURE.read_bytes())

    assert len(entries) == 2

    first = entries[0]

    assert first.source_record_id == "https://www.theregister.com/a/9990001"
    assert first.source_url.endswith("/gpu-cooling/9990001")
    assert first.title == "High-density GPU racks push data-center cooling limits"
    assert first.source_category == "hpc"
    assert first.source_kicker == "HPC"
    assert first.published_at is not None
    assert first.published_at.isoformat() == "2026-10-01T12:00:00+02:00"
    assert first.source_modified_at is not None
    assert first.content_html is not None
    assert "Frankfurt" in first.content_html


def test_parser_preserves_original_entry_fields() -> None:
    entries = parse_feed(FIXTURE.read_bytes())

    assert entries[0].raw_payload["id"] == (
        "https://www.theregister.com/a/9990001"
    )
    assert entries[0].raw_payload["title"].startswith(
        "High-density GPU racks"
    )


def test_parser_reports_missing_fields_and_invalid_dates() -> None:
    content = b"""
    <rss version="2.0"><channel>
      <item><title>Missing URL</title><pubDate>not-a-date</pubDate></item>
      <item><guid>valid-1</guid><link>https://example.test/1</link>
        <title>Power capacity article</title><pubDate>not-a-date</pubDate>
      </item>
    </channel></rss>
    """

    result = parse_feed_with_report(content)

    assert len(result.entries) == 1
    assert len(result.issues) == 2
    assert "missing required field" in result.issues[0].reason
    assert result.issues[1].reason == "invalid publication date"
