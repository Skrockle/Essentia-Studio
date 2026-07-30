import pytest

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.tracks import ManagedTagInventory, TrackFingerprint
from essentia_studio.repositories.writes import WriteRepository


@pytest.mark.parametrize("completion", ["finish_verified", "finish_undone"])
def test_verified_completion_rejects_unreadable_inventory(tmp_path, completion) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = WriteRepository(engine)

    with pytest.raises(
        ValueError,
        match="Only successfully read managed tags may replace file state",
    ):
        getattr(repository, completion)(
            "missing-operation",
            TrackFingerprint(10, 100),
            ManagedTagInventory(status="error", error_code="managed_tags_unreadable"),
        )
