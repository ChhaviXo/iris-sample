"""Parse RSS and Atom entries into assignment-level source records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser


class FeedParseError(ValueError):
    """Raised when the feed cannot be interpreted as a usable feed."""


@dataclass(frozen=True)
class ParsedEntry:
    """A source record before filtering, location resolution, or loading."""

    source_record_id: str
    source_url: str
    title: str
    summary: str | None
    content_html: str | None
    published_at: datetime | None
    source_modified_at: datetime | None
    source_category: str | None
    source_kicker: str | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ParseIssue:
    """A source-data problem that was visible during parsing."""

    entry_index: int
    reason: str
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ParseResult:
    """Parsed records plus problems found in the source payload."""

    entries: tuple[ParsedEntry, ...]
    issues: tuple[ParseIssue, ...]
    source_entry_count: int


def parse_feed(content: bytes) -> list[ParsedEntry]:
    """Parse RSS or Atom bytes and return valid entries.

    ``parse_feed_with_report`` should be used by the pipeline when parse
    quality information must be retained.
    """

    return list(parse_feed_with_report(content).entries)


def parse_feed_with_report(content: bytes) -> ParseResult:
    """Parse RSS or Atom bytes and retain malformed-record diagnostics."""

    parsed = feedparser.parse(content)

    if parsed.bozo and not parsed.entries:
        problem = getattr(parsed, "bozo_exception", "unknown parse error")
        raise FeedParseError(f"Feed could not be parsed: {problem}")

    entries: list[ParsedEntry] = []
    issues: list[ParseIssue] = []

    for entry_index, entry in enumerate(parsed.entries):
        raw_payload = _json_safe(dict(entry))
        source_record_id = str(
            entry.get("id")
            or entry.get("guid")
            or entry.get("link")
            or ""
        ).strip()
        source_url = str(entry.get("link") or "").strip()
        title = str(entry.get("title") or "").strip()

        if not source_record_id or not source_url or not title:
            missing_fields = ", ".join(
                field_name
                for field_name, field_value in (
                    ("source_record_id", source_record_id),
                    ("source_url", source_url),
                    ("title", title),
                )
                if not field_value
            )
            issues.append(
                ParseIssue(
                    entry_index=entry_index,
                    reason=f"missing required field(s): {missing_fields}",
                    raw_payload=raw_payload,
                )
            )
            continue

        published_value = _optional_text(entry.get("published"))
        published_at = _parse_date(published_value)

        if not published_value:
            issues.append(
                ParseIssue(
                    entry_index=entry_index,
                    reason="missing publication date",
                    raw_payload=raw_payload,
                )
            )
        elif published_at is None:
            issues.append(
                ParseIssue(
                    entry_index=entry_index,
                    reason="invalid publication date",
                    raw_payload=raw_payload,
                )
            )

        modified_value = _optional_text(
            entry.get("modified") or entry.get("dc_modified")
        )
        source_modified_at = _parse_date(modified_value)

        if modified_value and source_modified_at is None:
            issues.append(
                ParseIssue(
                    entry_index=entry_index,
                    reason="invalid source modification date",
                    raw_payload=raw_payload,
                )
            )

        entries.append(
            ParsedEntry(
                source_record_id=source_record_id,
                source_url=source_url,
                title=title,
                summary=_optional_text(entry.get("summary")),
                content_html=_extract_content(entry),
                published_at=published_at,
                source_modified_at=source_modified_at,
                source_category=_extract_category(entry),
                source_kicker=_optional_text(
                    entry.get("lab_kicker") or entry.get("kicker")
                ),
                raw_payload=raw_payload,
            )
        )

    return ParseResult(
        entries=tuple(entries),
        issues=tuple(issues),
        source_entry_count=len(parsed.entries),
    )


def _optional_text(value: Any) -> str | None:
    """Return trimmed text or ``None`` for an empty value."""

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _parse_date(value: Any) -> datetime | None:
    """Parse an RFC 822 feed date without inventing a timezone."""

    text = _optional_text(value)

    if not text:
        return None

    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None


def _extract_content(entry: Any) -> str | None:
    """Extract the first full-content value from RSS or Atom data."""

    content_values = entry.get("content") or []

    if content_values:
        first_value = content_values[0]

        if isinstance(first_value, dict):
            return _optional_text(first_value.get("value"))

    return _optional_text(entry.get("summary_detail", {}).get("value"))


def _extract_category(entry: Any) -> str | None:
    """Extract the first feed category from feedparser's normalized tags."""

    tags = entry.get("tags") or []

    if tags and isinstance(tags[0], dict):
        return _optional_text(tags[0].get("term"))

    return _optional_text(entry.get("category"))


def _json_safe(value: Any) -> Any:
    """Convert feedparser values into JSON-compatible primitives."""

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)
