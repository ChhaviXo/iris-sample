# IRIS-SIG-40 Assignment Handover

## Summary

This repository contains a repeatable ingestion pipeline for The Register's
data-centre, HPC, and AI-infrastructure articles. The pipeline reads the
official current Register feed, identifies relevant signals, preserves the
source information, and stores the results in PostgreSQL 16 with PostGIS 3.4.

## What was implemented

- A feed client with timeouts, bounded retries, HTTP-error handling, and empty-feed handling.
- A parser for RSS 2.0 and Atom-style feeds.
- Pagination using the current Register API's `start` parameter.
- Deterministic filtering for cooling, power, and AI-cluster signals.
- Preservation of source IDs, URLs, titles, dates, summaries, content, and raw payloads.
- Conservative location handling, including EPSG:25832 points when reliable coordinates are available.
- Explicit quality statuses for missing, ambiguous, or unresolved locations.
- PostgreSQL/PostGIS staging storage in `iris_staging.signal_ingest`.
- Idempotent insert/update behavior, so rerunning the pipeline does not create duplicates.
- Docker, Alembic migrations, fixtures, automated tests, validation scripts, and run instructions.

## Source note

The endpoint named in the assignment returned HTTP 404 during verification. The
implementation therefore uses The Register's currently available official HPC
API endpoint and documents the original endpoint and fallback in
[`IRIS_SIG_40_analysis.md`](IRIS_SIG_40_analysis.md).

The source is global rather than Germany-specific. EPSG:25832 is used only
when a location can be resolved reliably; the pipeline does not invent German
coordinates for articles without sufficient location information.

## Validation completed

- PostgreSQL: 16.15
- PostGIS: 3.4.6
- Python validation: 7/7 checks passed
- Assignment test suite: 22 tests passed
- Live full-feed dry run: 1,708 records parsed across 69 pages; 325 relevant records identified
- Fixture load and rerun: successful; the rerun updated the existing record without creating a duplicate
- No duplicate source IDs or source URLs were detected

## How to reproduce

See [`IRIS_SIG_40_runbook.md`](IRIS_SIG_40_runbook.md) for setup and execution
commands. The main entry point is:

```bash
uv run python -m app.signal_ingest.pipeline
```

The validation command is:

```bash
uv run python scripts/validate_signal_ingest.py
```

## Repository contents

- [`IRIS_SIG_40_analysis.md`](IRIS_SIG_40_analysis.md): assignment interpretation and data contract
- [`IRIS_SIG_40_runbook.md`](IRIS_SIG_40_runbook.md): setup and execution instructions
- [`IRIS_SIG_40_quality_report.md`](IRIS_SIG_40_quality_report.md): source and data-quality findings
- [`IRIS_SIG_40_validation.sql`](IRIS_SIG_40_validation.sql): database validation queries
- [`IRIS_SIG_40_sample_output.md`](IRIS_SIG_40_sample_output.md): example pipeline output
