from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.schemas.settings import AnalysisSettings


def test_settings_round_trip(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = SettingsRepository(engine)
    updated = AnalysisSettings(workers=3, max_audio_seconds=180)

    assert repository.replace(updated) == updated
    assert repository.get() == updated
