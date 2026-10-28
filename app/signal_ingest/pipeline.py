"""End-to-end IRIS-SIG-40 ingestion pipeline and CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from app.signal_ingest.client import FeedResponse
from app.signal_ingest.client import RegisterFeedClient
from app.signal_ingest.config import DEFAULT_FEED_URL
from app.signal_ingest.config import DEFAULT_MAX_PAGES
from app.signal_ingest.config import DEFAULT_PAGE_SIZE
from app.signal_ingest.config import DEFAULT_TIMEOUT_SECONDS
from app.signal_ingest.config import PAGINATION_PARAMETER
from app.signal_ingest.loader import LoadResult
from app.signal_ingest.loader import SignalLoader
from app.signal_ingest.normalizer import normalize_entries
from app.signal_ingest.parser import parse_feed_with_report


@dataclass(frozen=True)
class PipelineResult:
    """Summary of one complete or dry-run pipeline execution."""

    source_url: str
    fetched_at: datetime
    parsed_count: int
    malformed_count: int
    malformed_reasons: tuple[str, ...]
    fetched_pages: int
    pagination_complete: bool
    relevant_count: int
    inserted_count: int
    updated_count: int
    loaded: bool


class FileFeedClient:
    """Read a saved public-source fixture using the client interface."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self, url: str) -> FeedResponse:
        return FeedResponse(
            url=url,
            content=self.path.read_bytes(),
            content_type="application/rss+xml",
            fetched_at=datetime.now().astimezone(),
        )


class SignalIngestPipeline:
    """Coordinate source fetching, parsing, filtering, and loading."""

    def __init__(
        self,
        feed_url: str = DEFAULT_FEED_URL,
        client: RegisterFeedClient | FileFeedClient | None = None,
        session_factory: Callable[[], object] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")

        self.feed_url = feed_url
        self.client = client or RegisterFeedClient()
        self.session_factory = session_factory
        self.page_size = page_size
        self.max_pages = max_pages

    def run(self, load: bool = True) -> PipelineResult:
        """Execute the pipeline, optionally stopping before database loading."""

        first_response: FeedResponse | None = None
        entries_by_id = {}
        parse_issues = []
        fetched_pages = 0
        pagination_complete = False

        for page_number in range(self.max_pages):
            page_url = _page_url(
                self.feed_url,
                page_size=self.page_size,
                page_number=page_number,
            )
            response = self.client.fetch(page_url)

            if first_response is None:
                first_response = response

            parse_result = parse_feed_with_report(response.content)
            fetched_pages += 1
            parse_issues.extend(parse_result.issues)

            new_entry_count = 0

            for entry in parse_result.entries:
                if entry.source_record_id not in entries_by_id:
                    entries_by_id[entry.source_record_id] = entry
                    new_entry_count += 1

            if parse_result.source_entry_count == 0:
                pagination_complete = True
                break

            if page_number > 0 and new_entry_count == 0:
                pagination_complete = True
                break

            if parse_result.source_entry_count < self.page_size:
                pagination_complete = True
                break

        if first_response is None:
            raise RuntimeError("The feed client returned no response pages.")

        entries = list(entries_by_id.values())
        signals = normalize_entries(entries)

        inserted_count = 0
        updated_count = 0

        if load:
            if self.session_factory is None:
                raise RuntimeError(
                    "A database session factory is required when load=True."
                )

            session = self.session_factory()

            try:
                load_result = SignalLoader(
                    session=session,
                    source_endpoint=self.feed_url,
                ).load(signals)
                inserted_count = load_result.inserted
                updated_count = load_result.updated
            finally:
                session.close()

        return PipelineResult(
            source_url=first_response.url,
            fetched_at=first_response.fetched_at,
            parsed_count=len(entries),
            malformed_count=len(parse_issues),
            malformed_reasons=tuple(issue.reason for issue in parse_issues),
            fetched_pages=fetched_pages,
            pagination_complete=pagination_complete,
            relevant_count=len(signals),
            inserted_count=inserted_count,
            updated_count=updated_count,
            loaded=load,
        )


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline from the command line."""

    parser = argparse.ArgumentParser(
        description="Run the IRIS-SIG-40 signal-ingest pipeline."
    )
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help="RSS or Atom endpoint to fetch.",
    )
    parser.add_argument(
        "--feed-file",
        type=Path,
        help="Use a saved RSS/Atom fixture instead of making a network request.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and filter records without writing to PostgreSQL.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds when fetching a live feed.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="Number of source records requested per page.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Safety limit for paginated source requests.",
    )
    args = parser.parse_args(argv)

    client = (
        FileFeedClient(args.feed_file)
        if args.feed_file
        else RegisterFeedClient(timeout=args.timeout)
    )

    session_factory = None

    if not args.dry_run:
        # Importing the project database session lazily keeps fixture-only and
        # dry-run executions independent from DATABASE_URL configuration.
        from app.database.session import SessionLocal

        session_factory = SessionLocal

    result = SignalIngestPipeline(
        feed_url=args.feed_url,
        client=client,
        session_factory=session_factory,
        page_size=args.page_size,
        max_pages=args.max_pages,
    ).run(load=not args.dry_run)

    print(f"Source URL       : {result.source_url}")
    print(f"Parsed records   : {result.parsed_count}")
    print(f"Malformed issues  : {result.malformed_count}")
    for reason in result.malformed_reasons:
        print(f"  - {reason}")
    print(f"Fetched pages    : {result.fetched_pages}")
    print(f"Pagination done   : {result.pagination_complete}")
    print(f"Relevant records : {result.relevant_count}")
    print(f"Inserted records : {result.inserted_count}")
    print(f"Updated records  : {result.updated_count}")
    print(f"Database loaded  : {result.loaded}")

    return 0


def _page_url(base_url: str, page_size: int, page_number: int) -> str:
    """Add the current source API's limit/start pagination parameters."""

    parsed = urlsplit(base_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"limit", "offset", "start"}
    ]
    query.extend(
        (
            ("limit", str(page_size)),
            (PAGINATION_PARAMETER, str(page_number * page_size)),
        )
    )

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
