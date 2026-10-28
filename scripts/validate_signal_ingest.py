"""Validate the live IRIS-SIG-40 PostgreSQL/PostGIS staging data."""

from __future__ import annotations

from dataclasses import dataclass
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


@dataclass(frozen=True)
class CheckResult:
    """Result of one validation check."""

    name: str
    passed: bool
    detail: str


def main() -> int:
    """Run all database checks and return a shell-friendly exit code."""

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("FAIL DATABASE_URL is not set")
        return 1

    engine = create_engine(database_url)
    checks: list[CheckResult] = []

    try:
        with engine.connect() as connection:
            postgres_version, postgis_version = connection.execute(
                text("SELECT version(), postgis_full_version()")
            ).one()
            print(f"PostgreSQL: {postgres_version}")
            print(f"PostGIS   : {postgis_version}")

            table_name = connection.scalar(
                text("SELECT to_regclass('iris_staging.signal_ingest')")
            )
            checks.append(
                CheckResult(
                    name="target table exists",
                    passed=table_name is not None,
                    detail=str(table_name),
                )
            )

            total_records = connection.scalar(
                text("SELECT COUNT(*) FROM iris_staging.signal_ingest")
            )
            checks.append(
                CheckResult(
                    name="at least one record loaded",
                    passed=bool(total_records),
                    detail=f"{total_records} records",
                )
            )

            duplicate_source_ids = connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT source_name, source_record_id
                        FROM iris_staging.signal_ingest
                        GROUP BY source_name, source_record_id
                        HAVING COUNT(*) > 1
                    ) duplicates
                    """
                )
            )
            checks.append(
                CheckResult(
                    name="no duplicate source IDs",
                    passed=duplicate_source_ids == 0,
                    detail=f"{duplicate_source_ids} duplicate groups",
                )
            )

            duplicate_urls = connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT source_name, source_url
                        FROM iris_staging.signal_ingest
                        GROUP BY source_name, source_url
                        HAVING COUNT(*) > 1
                    ) duplicates
                    """
                )
            )
            checks.append(
                CheckResult(
                    name="no duplicate source URLs",
                    passed=duplicate_urls == 0,
                    detail=f"{duplicate_urls} duplicate groups",
                )
            )

            missing_traceability = connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM iris_staging.signal_ingest
                    WHERE source_name IS NULL
                       OR source_record_id IS NULL
                       OR source_url IS NULL
                       OR title IS NULL
                       OR source_endpoint IS NULL
                    """
                )
            )
            checks.append(
                CheckResult(
                    name="required traceability fields present",
                    passed=missing_traceability == 0,
                    detail=f"{missing_traceability} invalid rows",
                )
            )

            invalid_coordinates = connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM iris_staging.signal_ingest
                    WHERE (latitude IS NULL) <> (longitude IS NULL)
                       OR (latitude IS NOT NULL AND
                           latitude NOT BETWEEN -90 AND 90)
                       OR (longitude IS NOT NULL AND
                           longitude NOT BETWEEN -180 AND 180)
                    """
                )
            )
            checks.append(
                CheckResult(
                    name="coordinates are complete and valid",
                    passed=invalid_coordinates == 0,
                    detail=f"{invalid_coordinates} invalid rows",
                )
            )

            invalid_geometry = connection.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM iris_staging.signal_ingest
                    WHERE geometry IS NOT NULL
                      AND (
                          ST_SRID(geometry) <> 25832
                          OR GeometryType(geometry) <> 'POINT'
                      )
                    """
                )
            )
            checks.append(
                CheckResult(
                    name="geometry uses EPSG:25832 POINTs",
                    passed=invalid_geometry == 0,
                    detail=f"{invalid_geometry} invalid geometries",
                )
            )

            status_rows = connection.execute(
                text(
                    """
                    SELECT quality_status, COUNT(*) AS record_count
                    FROM iris_staging.signal_ingest
                    GROUP BY quality_status
                    ORDER BY quality_status
                    """
                )
            ).all()
            print("Quality statuses:")
            for quality_status, record_count in status_rows:
                print(f"  {quality_status}: {record_count}")

    except SQLAlchemyError as exc:
        print(f"FAIL database validation could not run: {exc}")
        return 1
    finally:
        engine.dispose()

    print("Validation checks:")
    for check in checks:
        state = "PASS" if check.passed else "FAIL"
        print(f"{state} {check.name}: {check.detail}")

    failed_checks = [check for check in checks if not check.passed]
    print(
        f"Validation result: {'PASS' if not failed_checks else 'FAIL'} "
        f"({len(checks) - len(failed_checks)}/{len(checks)} checks passed)"
    )
    return 1 if failed_checks else 0


if __name__ == "__main__":
    sys.exit(main())
