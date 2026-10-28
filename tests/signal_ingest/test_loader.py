from pathlib import Path

from app.signal_ingest.loader import SignalLoader
from app.signal_ingest.normalizer import normalize_entries
from app.signal_ingest.parser import parse_feed


FIXTURE = Path(__file__).parent / "fixtures" / "register_hpc_sample.xml"
ENDPOINT = "https://example.test/current-feed"


class FakeSession:
    def __init__(self, existing=None, fail_commit=False) -> None:
        self.existing = existing
        self.fail_commit = fail_commit
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def scalar(self, statement):
        return self.existing

    def add(self, entity) -> None:
        self.added.append(entity)

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("commit failed")
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def normalized_signal():
    entries = parse_feed(FIXTURE.read_bytes())
    return normalize_entries(entries)[0]


def test_loader_inserts_new_signal() -> None:
    session = FakeSession()
    loader = SignalLoader(session, source_endpoint=ENDPOINT)

    result = loader.load([normalized_signal()])

    assert result.inserted == 1
    assert result.updated == 0
    assert len(session.added) == 1
    assert session.added[0].source_name == "The Register"
    assert session.added[0].quality_status == "unresolved_location"
    assert session.commits == 1


def test_loader_updates_existing_signal() -> None:
    existing = type("Existing", (), {})()
    session = FakeSession(existing=existing)
    loader = SignalLoader(session, source_endpoint=ENDPOINT)

    result = loader.load([normalized_signal()])

    assert result.inserted == 0
    assert result.updated == 1
    assert existing.title.startswith("High-density GPU racks")
    assert existing.signal_type == "cooling"
    assert session.added == []
    assert session.commits == 1


def test_loader_deduplicates_records_within_one_batch() -> None:
    session = FakeSession()
    loader = SignalLoader(session, source_endpoint=ENDPOINT)
    signal = normalized_signal()

    result = loader.load([signal, signal])

    assert result.inserted == 1
    assert result.updated == 1
    assert len(session.added) == 1


def test_loader_rolls_back_when_commit_fails() -> None:
    session = FakeSession(fail_commit=True)
    loader = SignalLoader(session, source_endpoint=ENDPOINT)

    try:
        loader.load([normalized_signal()])
    except RuntimeError as exc:
        assert str(exc) == "commit failed"
    else:
        raise AssertionError("Expected the commit error to be re-raised")

    assert session.rollbacks == 1
