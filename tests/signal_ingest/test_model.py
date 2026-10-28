from app.database.models.signal_ingest import SignalIngest


def test_signal_ingest_model_targets_staging_schema() -> None:
    table = SignalIngest.__table__

    assert table.schema == "iris_staging"
    assert table.name == "signal_ingest"
    assert table.c.geometry.type.srid == 25832


def test_signal_ingest_model_has_idempotency_constraints() -> None:
    constraint_names = {
        constraint.name for constraint in SignalIngest.__table__.constraints
    }

    assert "uq_signal_ingest_source_record" in constraint_names
    assert "uq_signal_ingest_source_url" in constraint_names
