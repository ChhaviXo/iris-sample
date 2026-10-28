# IRIS-SIG-40 Runbook

## Local environment

The assignment target is PostgreSQL 16 with PostGIS 3.4. The repository includes an assignment-specific Compose file so the existing project Compose configuration is not changed.

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.sig40.yml up -d --build
```

The Compose file builds and uses a locally tagged image containing the pinned
PostgreSQL 16 base image and PostGIS 3.4.6 source build. Verify the runtime
versions after startup:

```bash
docker compose --env-file .env -f docker-compose.sig40.yml exec postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version(), postgis_full_version();"'
```

The feed client requests 25 records per page and follows the current API's
`start` pagination until an incomplete, repeated, or empty page is returned.
It allows 100 pages by default; use `--page-size` and `--max-pages` to change
those limits.

Install the project environment with the repository's package manager:

```bash
uv sync
```

## Apply the schema

```bash
alembic upgrade head
```

This creates `iris_staging.signal_ingest`.

## Run without a database

The fixture path is useful for demonstrations and tests:

```bash
python -m app.signal_ingest.pipeline \
  --feed-file tests/signal_ingest/fixtures/register_hpc_sample.xml \
  --dry-run
```

## Run against the current official feed without loading

```bash
python -m app.signal_ingest.pipeline --dry-run
```

## Run the complete database workflow

```bash
python -m app.signal_ingest.pipeline
```

## Run tests

```bash
python -m pytest -q tests/signal_ingest
```

## Validate the live database with Python

```bash
uv run python scripts/validate_signal_ingest.py
```

The script checks the PostgreSQL/PostGIS versions, target table, loaded rows,
duplicate source identities and URLs, required traceability fields, coordinate
ranges, and EPSG:25832 point geometries. It exits with status 1 if any check
fails.

## Operational behavior

- The obsolete endpoint from the brief is retained in configuration for traceability.
- The current official feed is the default source.
- Dry runs never open a database session.
- Database loads are idempotent by source record ID or stable article URL.
- Records without reliable coordinates remain in the staging table with a quality status explaining why geometry is absent.
