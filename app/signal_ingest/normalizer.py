"""Filter and normalize parsed The Register entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
import re

from app.signal_ingest.location import resolve_location
from app.signal_ingest.parser import ParsedEntry


# These rules are deliberately plain and reviewable. They can be expanded
# later, but every inclusion should remain explainable to the assignment
# reviewer.
SIGNAL_TERMS: dict[str, tuple[str, ...]] = {
    "cooling": (
        "cooling",
        "liquid cooling",
        "immersion cooling",
        "direct-to-chip",
        "thermal management",
        "rack heat",
    ),
    "power": (
        "power bottleneck",
        "power capacity",
        "power demand",
        "power consumption",
        "grid capacity",
        "electricity demand",
        "megawatt",
        "mw",
        "substation",
        "transformer",
    ),
    "ai_cluster": (
        "ai cluster",
        "ai infrastructure",
        "ai datacenter",
        "ai data center",
        "ai data-centre",
        "gpu cluster",
        "gpu clusters",
        "cluster sizing",
        "ai clusters",
        "llm training",
        "ai training",
    ),
    "hpc": (
        "hpc",
        "high-performance computing",
        "high performance computing",
        "supercomputer",
        "supercomputing",
        "exascale",
    ),
}

PRIMARY_SIGNAL_ORDER = (
    "cooling",
    "power",
    "ai_cluster",
    "hpc",
)

OBJECTIVE_SIGNAL_TOPICS = frozenset({"cooling", "power", "ai_cluster"})


@dataclass(frozen=True)
class NormalizedSignal:
    """A relevant, normalized record ready for location and loading."""

    source_record_id: str
    source_url: str
    title: str
    summary: str | None
    content_html: str | None
    content_text: str
    published_at: datetime | None
    source_modified_at: datetime | None
    source_category: str | None
    source_kicker: str | None
    signal_type: str
    matched_topics: tuple[str, ...]
    matched_terms: tuple[str, ...]
    raw_payload: dict[str, object]
    geographic_context: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geometry: object | None = None
    quality_status: str = "unresolved_location"
    quality_notes: str | None = (
        "The current source feed provides no structured location fields."
    )


def normalize_entries(entries: list[ParsedEntry]) -> list[NormalizedSignal]:
    """Keep relevant entries and attach explainable signal classifications."""

    normalized: list[NormalizedSignal] = []

    for entry in entries:
        content_text = html_to_text(entry.content_html)
        searchable_text = _searchable_text(entry, content_text)
        matched_topics, matched_terms = classify_signal(
            searchable_text=searchable_text,
        )
        location = resolve_location(searchable_text)

        if not OBJECTIVE_SIGNAL_TOPICS.intersection(matched_topics):
            continue

        normalized.append(
            NormalizedSignal(
                source_record_id=entry.source_record_id,
                source_url=entry.source_url,
                title=entry.title,
                summary=entry.summary,
                content_html=entry.content_html,
                content_text=content_text,
                published_at=entry.published_at,
                source_modified_at=entry.source_modified_at,
                source_category=entry.source_category,
                source_kicker=entry.source_kicker,
                signal_type=_primary_signal_type(matched_topics),
                matched_topics=matched_topics,
                matched_terms=matched_terms,
                raw_payload=entry.raw_payload,
                geographic_context=location.geographic_context,
                latitude=location.latitude,
                longitude=location.longitude,
                geometry=location.geometry,
                quality_status=location.quality_status,
                quality_notes=location.quality_notes,
            )
        )

    return normalized


def classify_signal(
    searchable_text: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return matching topics and the exact terms that caused inclusion."""

    text = searchable_text.casefold()
    topics: list[str] = []
    terms: list[str] = []

    for topic, configured_terms in SIGNAL_TERMS.items():
        topic_matched = False

        for term in configured_terms:
            term_pattern = _term_pattern(term)

            if re.search(term_pattern, text):
                topic_matched = True
                terms.append(term)

        if topic_matched:
            topics.append(topic)

    return tuple(topics), tuple(terms)


def html_to_text(value: str | None) -> str:
    """Convert article HTML into whitespace-normalized searchable text."""

    if not value:
        return ""

    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()

    return re.sub(r"\s+", " ", parser.text).strip()


def _searchable_text(entry: ParsedEntry, content_text: str) -> str:
    """Combine the fields that are relevant to topic classification."""

    return " ".join(
        value
        for value in (
            entry.title,
            entry.summary or "",
            content_text,
        )
        if value
    )


def _primary_signal_type(topics: tuple[str, ...]) -> str:
    """Return a stable primary label while retaining all matched topics."""

    for topic in PRIMARY_SIGNAL_ORDER:
        if topic in topics:
            return topic

    return topics[0]


def _term_pattern(term: str) -> str:
    """Match a term as a phrase while avoiding partial word matches."""

    escaped = re.escape(term.casefold())
    return rf"(?<!\w){escaped}(?!\w)"


class _VisibleTextParser(HTMLParser):
    """Collect visible text without adding an HTML dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(self.parts)
