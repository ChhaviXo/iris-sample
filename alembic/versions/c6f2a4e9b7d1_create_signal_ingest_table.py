"""create IRIS-SIG-40 signal ingestion staging table"""

from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c6f2a4e9b7d1"
down_revision: Union[str, Sequence[str], None] = "b18ad888465f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the staging schema and signal-ingest table."""

    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE SCHEMA IF NOT EXISTS iris_staging")

    op.create_table(
        "signal_ingest",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "source_endpoint",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "source_record_id",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "content_html",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "content_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "source_category",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "source_kicker",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "source_modified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "signal_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "matched_topics",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "matched_terms",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "geographic_context",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry(
                geometry_type="POINT",
                srid=25832,
                spatial_index=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "quality_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "quality_notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "source_record_id",
            name="uq_signal_ingest_source_record",
        ),
        sa.UniqueConstraint(
            "source_name",
            "source_url",
            name="uq_signal_ingest_source_url",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) "
            "OR (latitude BETWEEN -90 AND 90 "
            "AND longitude BETWEEN -180 AND 180)",
            name="ck_signal_ingest_coordinate_range",
        ),
        schema="iris_staging",
    )

    op.create_index(
        "idx_signal_ingest_published_at",
        "signal_ingest",
        ["published_at"],
        schema="iris_staging",
    )
    op.create_index(
        "idx_signal_ingest_signal_type",
        "signal_ingest",
        ["signal_type"],
        schema="iris_staging",
    )
    op.create_index(
        "idx_signal_ingest_quality_status",
        "signal_ingest",
        ["quality_status"],
        schema="iris_staging",
    )
    op.create_index(
        "idx_signal_ingest_geometry",
        "signal_ingest",
        ["geometry"],
        schema="iris_staging",
        postgresql_using="gist",
    )


def downgrade() -> None:
    """Drop only the signal-ingest objects owned by this migration."""

    op.drop_index(
        "idx_signal_ingest_geometry",
        table_name="signal_ingest",
        schema="iris_staging",
        postgresql_using="gist",
    )
    op.drop_index(
        "idx_signal_ingest_quality_status",
        table_name="signal_ingest",
        schema="iris_staging",
    )
    op.drop_index(
        "idx_signal_ingest_signal_type",
        table_name="signal_ingest",
        schema="iris_staging",
    )
    op.drop_index(
        "idx_signal_ingest_published_at",
        table_name="signal_ingest",
        schema="iris_staging",
    )
    op.drop_table("signal_ingest", schema="iris_staging")
