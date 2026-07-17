from pathlib import Path

import pytest

from essentia_studio.errors import AppError
from essentia_studio.schemas.settings import AnalysisSettings
from essentia_studio.services.settings import SettingsService


def test_load_uses_nested_defaults_and_reports_sources(tmp_path: Path) -> None:
    effective = SettingsService(tmp_path / "settings.yaml", {}).load()

    assert effective.values.analysis.workers == 1
    assert effective.values.analysis.compute == "auto"
    assert effective.values.automation.enabled is False
    assert effective.values.automation.watcher is False
    assert effective.values.benchmark.minimum_track_seconds == 60
    assert effective.sources["analysis.workers"] == "default"
    assert effective.sources["automation.watcher"] == "default"


def test_env_overrides_yaml_and_reports_source(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text(
        "analysis:\n  workers: 2\nautomation:\n  watcher: false\n",
        encoding="utf-8",
    )
    service = SettingsService(
        path,
        {
            "ESSENTIA_ANALYSIS_WORKERS": "4",
            "ESSENTIA_AUTOMATION_WATCHER": "yes",
        },
    )

    effective = service.load()

    assert effective.values.analysis.workers == 4
    assert effective.values.automation.watcher is True
    assert effective.sources["analysis.workers"] == "env"
    assert effective.sources["automation.watcher"] == "env"
    assert effective.sources["analysis.max_audio_seconds"] == "default"


def test_yaml_requires_a_mapping_root(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("- invalid\n- root\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping"):
        SettingsService(path, {}).load()


@pytest.mark.parametrize("value", ["enabled", "on", "2", ""])
def test_invalid_env_boolean_names_the_variable(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValueError, match="ESSENTIA_AUTOMATION_ENABLED"):
        SettingsService(
            tmp_path / "settings.yaml",
            {"ESSENTIA_AUTOMATION_ENABLED": value},
        ).load()


def test_update_writes_yaml_and_preserves_unmodified_file_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("analysis:\n  workers: 2\n  genre_count: 5\n", encoding="utf-8")
    service = SettingsService(path, {})

    effective = service.update({"analysis": {"workers": 3}})

    assert effective.values.analysis.workers == 3
    assert effective.values.analysis.genre_count == 5
    assert effective.sources["analysis.workers"] == "file"
    assert not list(tmp_path.glob("*.tmp"))


def test_update_rejects_fields_locked_by_environment(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    service = SettingsService(path, {"ESSENTIA_ANALYSIS_WORKERS": "4"})

    with pytest.raises(AppError, match="Umgebungsvariable") as error:
        service.update({"analysis": {"workers": 2}})

    assert error.value.code == "setting_locked_by_environment"
    assert not path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_migrate_legacy_writes_once_without_overwriting_yaml(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    service = SettingsService(path, {})

    migrated = service.migrate_legacy(AnalysisSettings(workers=3, max_audio_seconds=180))

    assert migrated.values.analysis.workers == 3
    assert migrated.values.analysis.max_audio_seconds == 180
    path.write_text("analysis:\n  workers: 6\n", encoding="utf-8")

    preserved = service.migrate_legacy(AnalysisSettings(workers=2))

    assert preserved.values.analysis.workers == 6
