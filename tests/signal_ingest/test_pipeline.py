from pathlib import Path
from datetime import datetime, timezone

from app.signal_ingest.client import FeedResponse
from app.signal_ingest.pipeline import SignalIngestPipeline


FIXTURE = Path(__file__).parent / "fixtures" / "register_hpc_sample.xml"


class FakeClient:
    def fetch(self, url: str) -> FeedResponse:
        return FeedResponse(
            url=url,
            content=FIXTURE.read_bytes(),
            content_type="application/rss+xml",
            fetched_at=datetime.now(timezone.utc),
        )


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def scalar(self, statement):
        return None

    def add(self, entity) -> None:
        self.added.append(entity)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


class SequencedClient:
    def __init__(self, pages: list[bytes]) -> None:
        self.pages = pages
        self.urls: list[str] = []

    def fetch(self, url: str) -> FeedResponse:
        self.urls.append(url)
        content = self.pages.pop(0) if self.pages else b"<rss />"
        return FeedResponse(
            url=url,
            content=content,
            content_type="application/rss+xml",
            fetched_at=datetime.now(timezone.utc),
        )


def rss_page(record_id: str, title: str, description: str) -> bytes:
    return f"""
    <rss version="2.0"><channel>
      <item>
        <guid>{record_id}</guid>
        <link>https://example.test/{record_id}</link>
        <title>{title}</title>
        <description>{description}</description>
        <pubDate>Thu, 01 Oct 2026 12:00:00 +0000</pubDate>
      </item>
    </channel></rss>
    """.encode()


def test_pipeline_dry_run_parses_and_filters_without_database() -> None:
    pipeline = SignalIngestPipeline(
        feed_url="https://example.test/feed",
        client=FakeClient(),
    )

    result = pipeline.run(load=False)

    assert result.parsed_count == 2
    assert result.malformed_count == 0
    assert result.malformed_reasons == ()
    assert result.relevant_count == 1
    assert result.inserted_count == 0
    assert result.updated_count == 0
    assert result.loaded is False


def test_pipeline_fetches_pages_until_the_source_is_empty() -> None:
    client = SequencedClient(
        [
            rss_page("record-1", "Liquid cooling for GPU racks", "Cooling"),
            rss_page("record-2", "Power bottleneck in AI cluster", "Power"),
            b"<rss version=\"2.0\"><channel></channel></rss>",
        ]
    )
    pipeline = SignalIngestPipeline(
        feed_url="https://example.test/feed?limit=25",
        client=client,
        page_size=1,
    )

    result = pipeline.run(load=False)

    assert result.parsed_count == 2
    assert result.relevant_count == 2
    assert result.fetched_pages == 3
    assert result.pagination_complete is True
    assert "start=0" in client.urls[0]
    assert "start=1" in client.urls[1]


def test_pipeline_loads_through_injected_session_factory() -> None:
    created_sessions = []

    def session_factory():
        session = FakeSession()
        created_sessions.append(session)
        return session

    pipeline = SignalIngestPipeline(
        feed_url="https://example.test/feed",
        client=FakeClient(),
        session_factory=session_factory,
    )

    result = pipeline.run(load=True)

    assert len(created_sessions) == 1
    assert result.inserted_count == 1
    assert result.updated_count == 0
    assert result.loaded is True
    assert created_sessions[0].commits == 1
