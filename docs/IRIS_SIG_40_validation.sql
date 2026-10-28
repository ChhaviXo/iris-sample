-- Row count and latest ingestion records.
SELECT COUNT(*) AS total_records
FROM iris_staging.signal_ingest;

SELECT
    source_name,
    source_record_id,
    title,
    published_at,
    signal_type,
    quality_status
FROM iris_staging.signal_ingest
ORDER BY published_at DESC NULLS LAST
LIMIT 20;

-- The idempotency keys must not return any rows.
SELECT source_name, source_record_id, COUNT(*) AS duplicate_count
FROM iris_staging.signal_ingest
GROUP BY source_name, source_record_id
HAVING COUNT(*) > 1;

SELECT source_name, source_url, COUNT(*) AS duplicate_count
FROM iris_staging.signal_ingest
GROUP BY source_name, source_url
HAVING COUNT(*) > 1;

-- Signal distribution and location quality.
SELECT signal_type, COUNT(*) AS record_count
FROM iris_staging.signal_ingest
GROUP BY signal_type
ORDER BY record_count DESC;

SELECT quality_status, COUNT(*) AS record_count
FROM iris_staging.signal_ingest
GROUP BY quality_status
ORDER BY record_count DESC;

-- Coordinates must be either both present and valid or both absent.
SELECT source_record_id, latitude, longitude, quality_status
FROM iris_staging.signal_ingest
WHERE (latitude IS NULL) <> (longitude IS NULL)
   OR latitude NOT BETWEEN -90 AND 90
   OR longitude NOT BETWEEN -180 AND 180;

-- PostGIS geometry must use the assignment SRID.
SELECT source_record_id, ST_SRID(geometry) AS srid
FROM iris_staging.signal_ingest
WHERE geometry IS NOT NULL
  AND ST_SRID(geometry) <> 25832;

-- The source and latest-ingestion timestamps must be populated.
SELECT source_record_id, source_endpoint, first_seen_at, last_seen_at
FROM iris_staging.signal_ingest
WHERE source_endpoint IS NULL
   OR first_seen_at IS NULL
   OR last_seen_at IS NULL;
