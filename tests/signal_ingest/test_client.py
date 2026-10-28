import pytest
import requests

from app.signal_ingest.client import FeedFetchError
from app.signal_ingest.client import RegisterFeedClient


class FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"Content-Type": "application/rss+xml"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: float) -> FakeResponse:
        return self.response


def test_client_returns_non_empty_feed() -> None:
    session = FakeSession(FakeResponse(200, b"<rss />"))
    client = RegisterFeedClient(session=session, timeout=5)

    result = client.fetch("https://example.test/feed")

    assert result.content == b"<rss />"
    assert result.content_type == "application/rss+xml"
    assert session.headers["User-Agent"].startswith("IRIS-SIG-40")


def test_client_rejects_404() -> None:
    session = FakeSession(FakeResponse(404, b"not found"))
    client = RegisterFeedClient(session=session)

    with pytest.raises(FeedFetchError, match="HTTP 404"):
        client.fetch("https://example.test/obsolete-feed")


def test_client_rejects_empty_response() -> None:
    session = FakeSession(FakeResponse(200, b""))
    client = RegisterFeedClient(session=session)

    with pytest.raises(FeedFetchError, match="empty response"):
        client.fetch("https://example.test/empty-feed")


def test_real_requests_session_has_retry_policy() -> None:
    client = RegisterFeedClient(session=requests.Session())

    retry_policy = client.session.get_adapter("https://").max_retries

    assert retry_policy.total == 3
    assert retry_policy.backoff_factor == 0.5
