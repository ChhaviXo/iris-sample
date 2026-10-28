"""HTTP client for the current official The Register feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.signal_ingest.config import DEFAULT_TIMEOUT_SECONDS
from app.signal_ingest.config import DEFAULT_RETRY_ATTEMPTS
from app.signal_ingest.config import USER_AGENT


class FeedFetchError(RuntimeError):
    """Raised when the source feed cannot be fetched successfully."""


@dataclass(frozen=True)
class FeedResponse:
    """The minimum source response needed by the parser."""

    url: str
    content: bytes
    content_type: str | None
    fetched_at: datetime


class RegisterFeedClient:
    """Fetch a public RSS/Atom feed with explicit error handling."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

        self.session.headers.update(
            {
                "Accept": (
                    "application/atom+xml, application/rss+xml, "
                    "application/xml;q=0.9, text/xml;q=0.8"
                ),
                "User-Agent": USER_AGENT,
            }
        )

        if isinstance(self.session, requests.Session):
            retry_policy = Retry(
                total=DEFAULT_RETRY_ATTEMPTS,
                connect=DEFAULT_RETRY_ATTEMPTS,
                read=DEFAULT_RETRY_ATTEMPTS,
                status=DEFAULT_RETRY_ATTEMPTS,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_policy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def fetch(self, url: str) -> FeedResponse:
        """Fetch ``url`` and return non-empty response bytes."""

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FeedFetchError(
                f"Network error while fetching {url}: {exc}"
            ) from exc

        if response.status_code == 404:
            raise FeedFetchError(
                f"Feed endpoint returned HTTP 404: {url}"
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise FeedFetchError(
                f"Feed endpoint returned HTTP {response.status_code}: {url}"
            ) from exc

        if not response.content:
            raise FeedFetchError(
                f"Feed endpoint returned an empty response: {url}"
            )

        return FeedResponse(
            url=url,
            content=response.content,
            content_type=response.headers.get("Content-Type"),
            fetched_at=datetime.now(timezone.utc),
        )
