# IRIS-SIG-40 Data Quality Report

## Source verification

- The endpoint named in the brief returns HTTP 404.
- The current official HPC feed returns RSS 2.0.
- The inspected live response contained 25 entries.
- Stable `guid`, article URL, title, publication date, category, summary, and full content were available.

## Filtering result

The fixture contains two records:

- one relevant HPC/data-center infrastructure record;
- one irrelevant consumer-technology record.

The normalizer retained one relevant record and recorded its matched signal topics and terms.

## Location result

The inspected live feed contains no dedicated latitude, longitude, address, city, country, or GeoRSS fields. Geographic names appear in free-text content.

The implementation therefore:

- transforms explicitly labelled coordinates to EPSG:25832;
- retains clearly identified textual location context when coordinates are absent;
- rejects invalid coordinates;
- leaves broad or ambiguous locations unresolved; and
- records a quality status and explanation instead of inventing coordinates.

Parser records with missing required fields or invalid publication dates are
reported as quality issues rather than silently disappearing from the run
summary.

The live-feed client uses bounded retries for transient HTTP failures and the
pipeline follows bounded `start` pagination.

## Database status

The model and migration compile successfully, and the idempotent loader is covered by tests. A real `alembic upgrade head` and database validation run are pending until a PostgreSQL/PostGIS service is available locally.

## Test status

The assignment-specific test suite currently passes 22 tests covering:

- RSS parsing;
- malformed-record and invalid-date diagnostics;
- HTTP error handling;
- retry policy configuration and paginated pipeline orchestration;
- topic filtering;
- normalization;
- EPSG:25832 coordinate handling;
- model metadata;
- idempotent insert/update behavior;
- transaction rollback; and
- dry-run and loaded pipeline orchestration.
