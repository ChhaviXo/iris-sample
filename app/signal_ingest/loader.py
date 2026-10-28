"""Idempotent database loader for normalized signal records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database.models.signal_ingest import SignalIngest
from app.signal_ingest.config import SOURCE_NAME
from app.signal_ingest.normalizer import NormalizedSignal


@dataclass(frozen=True)
class LoadResult:
    """Counts returned by one loader execution."""

    inserted: int
    updated: int


class SignalLoader:
    """Insert or update normalized signals without creating duplicates."""

    def __init__(
        self,
        session: Session,
        source_endpoint: str,
        source_name: str = SOURCE_NAME,
    ) -> None:
        self.session = session
        self.source_endpoint = source_endpoint
        self.source_name = source_name

    def load(self, signals: list[NormalizedSignal]) -> LoadResult:
        """Load a batch and commit it atomically."""

        if isinstance(self.session, Session):
            return self._load_with_postgres_upsert(signals)

        # Lightweight test doubles use the ORM path below. Real PostgreSQL
        # sessions use the conflict-safe path above.
        return self._load_with_orm_lookup(signals)

    def _load_with_orm_lookup(
        self,
        signals: list[NormalizedSignal],
    ) -> LoadResult:
        """Load through the lookup path used by lightweight test doubles."""

        inserted = 0
        updated = 0
        batch_entities: dict[tuple[str, str], SignalIngest] = {}

        try:
            for signal in signals:
                values = self._values_for(signal)
                identity = (
                    self.source_name,
                    signal.source_record_id,
                )

                existing = batch_entities.get(identity)

                if existing is None:
                    existing = self._find_existing(signal)

                if existing is None:
                    existing = SignalIngest(**values)
                    self.session.add(existing)
                    batch_entities[identity] = existing
                    inserted += 1
                else:
                    self._update(existing, values)
                    batch_entities[identity] = existing
                    updated += 1

            self.session.commit()

        except Exception:
            self.session.rollback()
            raise

        return LoadResult(
            inserted=inserted,
            updated=updated,
        )

    def _load_with_postgres_upsert(
        self,
        signals: list[NormalizedSignal],
    ) -> LoadResult:
        """Use PostgreSQL conflict handling so concurrent runs remain safe."""

        inserted = 0
        updated = 0

        try:
            for signal in signals:
                values = self._values_for(signal)
                existing = self._find_existing(signal)

                if existing is not None:
                    self._update(existing, values)
                    self.session.flush()
                    updated += 1
                    continue

                statement = (
                    pg_insert(SignalIngest)
                    .values(**values)
                    .on_conflict_do_nothing()
                    .returning(SignalIngest.id)
                )
                inserted_id = self.session.execute(statement).scalar_one_or_none()

                if inserted_id is not None:
                    inserted += 1
                    continue

                # A concurrent transaction inserted the same source ID or URL
                # after the lookup. Fetch that row and apply the latest values.
                existing = self._find_existing(signal)

                if existing is None:
                    raise RuntimeError(
                        "A conflicting signal row was inserted but could not "
                        "be retrieved."
                    )

                self._update(existing, values)
                self.session.flush()
                updated += 1

            self.session.commit()

        except Exception:
            self.session.rollback()
            raise

        return LoadResult(
            inserted=inserted,
            updated=updated,
        )

    def _find_existing(
        self,
        signal: NormalizedSignal,
    ) -> SignalIngest | None:
        """Find a record by source ID or stable article URL."""

        statement = select(SignalIngest).where(
            SignalIngest.source_name == self.source_name,
            or_(
                SignalIngest.source_record_id == signal.source_record_id,
                SignalIngest.source_url == signal.source_url,
            ),
        )

        return self.session.scalar(statement)

    def _values_for(self, signal: NormalizedSignal) -> dict[str, object]:
        """Map a normalized signal to model constructor values."""

        return {
            "source_name": self.source_name,
            "source_endpoint": self.source_endpoint,
            "source_record_id": signal.source_record_id,
            "source_url": signal.source_url,
            "title": signal.title,
            "summary": signal.summary,
            "content_html": signal.content_html,
            "content_text": signal.content_text,
            "source_category": signal.source_category,
            "source_kicker": signal.source_kicker,
            "published_at": signal.published_at,
            "source_modified_at": signal.source_modified_at,
            "signal_type": signal.signal_type,
            "matched_topics": list(signal.matched_topics),
            "matched_terms": list(signal.matched_terms),
            "geographic_context": signal.geographic_context,
            "latitude": signal.latitude,
            "longitude": signal.longitude,
            "geometry": signal.geometry,
            "quality_status": signal.quality_status,
            "quality_notes": signal.quality_notes,
            "raw_payload": signal.raw_payload,
        }

    @staticmethod
    def _update(
        existing: SignalIngest,
        values: dict[str, object],
    ) -> None:
        """Update mutable source values while preserving first-seen time."""

        for key, value in values.items():
            setattr(existing, key, value)

        existing.last_seen_at = datetime.now(timezone.utc)
