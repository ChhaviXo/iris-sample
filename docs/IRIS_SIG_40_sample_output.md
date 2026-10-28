# IRIS-SIG-40 Sample Output

## Fixture dry run

Command:

```bash
python -m app.signal_ingest.pipeline \
  --feed-file tests/signal_ingest/fixtures/register_hpc_sample.xml \
  --dry-run
```

Expected output:

```text
Source URL       : https://api.theregister.com/api/v1/article?orderBy=published&query=tag%3Ahpc&remapper=rss&site_id=2&limit=25&start=0
Parsed records   : 2
Malformed issues : 0
Fetched pages    : 1
Pagination done  : True
Relevant records : 1
Inserted records : 0
Updated records  : 0
Database loaded  : False
```

## Database validation

After applying the migration and running a database load, execute
`docs/IRIS_SIG_40_validation.sql`. The queries check:

- total records and latest source records;
- duplicate source IDs and URLs;
- signal and quality distributions;
- coordinate completeness and ranges;
- EPSG:25832 geometry SRIDs; and
- source and ingestion timestamps.
