"""SQLAlchemy model for IRIS-SIG-40 staging records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import CheckConstraint
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.entity import BaseEntity


class SignalIngest(BaseEntity):
    """A traceable, normalized signal record in the staging schema."""

    __tablename__ = "signal_ingest"

    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_record_id",
            name="uq_signal_ingest_source_record",
        ),
        UniqueConstraint(
            "source_name",
            "source_url",
            name="uq_signal_ingest_source_url",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) "
            "OR (latitude BETWEEN -90 AND 90 "
            "AND longitude BETWEEN -180 AND 180)",
            name="ck_signal_ingest_coordinate_range",
        ),
        Index(
            "idx_signal_ingest_published_at",
            "published_at",
        ),
        Index(
            "idx_signal_ingest_signal_type",
            "signal_type",
        ),
        Index(
            "idx_signal_ingest_quality_status",
            "quality_status",
        ),
        Index(
            "idx_signal_ingest_geometry",
            "geometry",
            postgresql_using="gist",
        ),
        {
            "schema": "iris_staging",
        },
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source_endpoint: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_record_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content_html: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_kicker: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    signal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    matched_topics: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    matched_terms: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    geographic_context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    geometry: Mapped[str | None] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=25832,
            spatial_index=False,
        ),
        nullable=True,
    )

    quality_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    quality_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
