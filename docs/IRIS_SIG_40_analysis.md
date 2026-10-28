# IRIS-SIG-40 Analysis and Implementation Notes

## Purpose

This document records the interpretation of the IRIS-SIG-40 assignment before implementation. It is intended to make the engineering decisions traceable during review.

## Assignment objective

Build a repeatable ingestion workflow for The Register's data-center, HPC, and AI-infrastructure signals, with particular attention to:

- high-density GPU rack cooling requirements;
- power bottlenecks; and
- AI cluster sizing.

The workflow must load traceable staging records into `iris_staging.signal_ingest` on PostgreSQL 16/PostGIS 3.4.

## Source status

The endpoint named in the brief is:

```text
https://www.theregister.com/data_centre/headlines.atom
```

As of the implementation review, this URL returns HTTP 404. The Register's current feed directory lists topic feeds through `api.theregister.com`. The current HPC feed used for field inspection is:

```text
https://api.theregister.com/api/v1/article?limit=25&orderBy=published&query=tag%3Ahpc&remapper=rss&site_id=2
```

The obsolete URL will remain documented. The current official feed is treated as the justified alternative required by the brief's candidate notes.

## Observed live feed format

The current HPC endpoint returns RSS 2.0, not Atom.

The feed-level fields observed were:

- `channel/title`
- `channel/link`
- `channel/description`

The article-level fields observed were:

- `guid`
- `link`
- `pubDate`
- `title`
- `description`
- `category`
- `dc:modified`
- `content:encoded`
- `lab:kicker`
- `enclosure`
- `media:thumbnail`

The feed returned 25 entries for the inspected request. The `guid` values are stable article identifiers and are marked as permanent links. `pubDate` and `dc:modified` use RFC 822-style date strings with timezone offsets.

## Location findings

The feed does not provide dedicated location fields. No structured `latitude`, `longitude`, `city`, `country`, `address`, `location`, or GeoRSS fields were present in the inspected entries.

Geographic names occur inside the free-text title, summary, and article content. Therefore:

1. source-provided coordinates, if encountered in a future feed variant, may be transformed into EPSG:25832;
2. a precise, authorized location-resolution method may be applied when the source text is sufficiently specific;
3. broad or ambiguous locations remain as text with a null geometry; and
4. no coordinates are invented.

The absence of a geometry is a valid, documented outcome under the assignment requirements.

## Working geographic interpretation

The feed is global rather than Germany-specific. We will ingest globally relevant articles because the brief does not impose a Germany/NRW source filter.

EPSG:25832 is treated as an output coordinate reference system for locations where it is appropriate and sufficiently supported by the source. It is not used to force every global article into a German map projection.

## Proposed staging record

| Column | Origin | Purpose |
| --- | --- | --- |
| `id` | Generated | Internal primary key |
| `source_name` | Constant | Identifies The Register |
| `source_endpoint` | Configuration | Records the feed used |
| `source_record_id` | `guid` | Stable source identity |
| `source_url` | `link` | Traceable article URL |
| `title` | `title` | Article title |
| `summary` | `description` | Short source summary |
| `content_html` | `content:encoded` | Content used for filtering and context |
| `content_text` | Derived from `content:encoded` | HTML-free searchable text |
| `source_category` | `category` | Original feed category |
| `source_kicker` | `lab:kicker` | Optional display/topic label |
| `published_at` | `pubDate` | Publication timestamp |
| `source_modified_at` | `dc:modified` | Source modification timestamp |
| `signal_type` | Derived | Cooling, power, HPC, AI cluster, or related signal |
| `matched_topics` | Derived | All topic classes matched by the rules |
| `matched_terms` | Derived | Exact terms that caused inclusion |
| `geographic_context` | Derived | Location text found in the source |
| `latitude` | Derived/optional | Original or resolved latitude |
| `longitude` | Derived/optional | Original or resolved longitude |
| `geometry` | Derived/optional | EPSG:25832 point geometry |
| `quality_status` | Derived | Valid, unresolved, malformed, or similar status |
| `quality_notes` | Derived | Explains missing or ambiguous values |
| `raw_payload` | Source entry | Preserves the original record for traceability |
| `first_seen_at` | Generated | First ingestion timestamp |
| `last_seen_at` | Generated | Most recent ingestion timestamp |

The idempotency key will be `(source_name, source_record_id)`, with the article URL also indexed and treated as a stable identity fallback.

## Planned implementation shape

```text
app/signal_ingest/
    client.py       Fetch the current feed with timeout/error handling
    parser.py       Parse RSS 2.0 and Atom-shaped entries
    normalizer.py   Map source fields and classify relevant signals
    location.py     Resolve or document location information
    loader.py       Insert/update records idempotently
    pipeline.py     Orchestrate the complete workflow
```

Additional repository changes will include:

- a SQLAlchemy model for `iris_staging.signal_ingest`;
- an explicit Alembic migration;
- fixture-based tests under `tests/signal_ingest/`;
- validation queries and a quality report; and
- assignment-specific run instructions.

## Acceptance mapping

| Assignment requirement | Planned evidence |
| --- | --- |
| Verify source and format | Source-status section and fixture |
| Preserve IDs, titles, dates, URLs | Source-to-column mapping and database constraints |
| Filter the required signal/domain | Deterministic classification tests |
| Normalize for PostgreSQL/PostGIS | Migration, model, and validation queries |
| Use repeatable/idempotent operations | Unique key and rerun test |
| Resolve locations where possible | Location module and quality notes |
| Handle failures and malformed data | Client/parser tests and error report |
| No production access required | Public fixture and mocked tests |

## Current status

- Repository audit: complete.
- Source endpoint review: complete.
- Live field inspection: complete.
- Data contract: drafted above.
- Initial `app/signal_ingest` client and parser: implemented.
- Deterministic topic filtering and normalization: implemented.
- Objective-signal filtering is based on article text, not generic feed tags.
- Malformed source records and invalid publication dates are reported in the
  pipeline result.
- Current-feed pagination and bounded retry handling are implemented.
- `iris_staging.signal_ingest` SQLAlchemy model and migration: implemented.
- Conflict-safe PostgreSQL loader with transaction rollback handling:
  implemented.
- End-to-end pipeline and dry-run/fixture CLI: implemented.
- Conservative coordinate resolver and EPSG:25832 tests: implemented.
- Public RSS fixture: added.
- Parser/client/normalizer/location/model/loader/pipeline tests: 22 passing.
- Live-feed parser smoke test: 25 current entries parsed successfully.
- Dependencies: installed only into a temporary test directory; the repository environment is not yet configured.
- Migration has been compile-validated but not applied to a database yet.
- Database-environment verification and final live validation: pending local
  Docker/PostgreSQL/PostGIS availability.
