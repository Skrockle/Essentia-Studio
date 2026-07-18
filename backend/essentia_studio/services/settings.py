from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from essentia_studio.errors import AppError
from essentia_studio.schemas.settings import (
    AnalysisSettings,
    AppSettings,
    EffectiveSettings,
    SettingSource,
)
from essentia_studio.services.schedule import CronSchedule

Parser = Callable[[str, str], Any]


def _parse_string(value: str, _name: str) -> str:
    return value


def _parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


def _parse_float(value: str, name: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error


def _parse_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{name} must be true/false, 1/0, or yes/no")


def _parse_write_mode(value: str, name: str) -> str:
    return "analyze_and_write" if _parse_bool(value, name) else "analyze"


ENV_SETTINGS: dict[str, tuple[str, Parser]] = {
    "ESSENTIA_ANALYSIS_WORKERS": ("analysis.workers", _parse_int),
    "ESSENTIA_MAX_AUDIO_SECONDS": ("analysis.max_audio_seconds", _parse_int),
    "ESSENTIA_GENRE_THRESHOLD": ("analysis.genre_threshold", _parse_float),
    "ESSENTIA_MOOD_THRESHOLD": ("analysis.mood_threshold", _parse_float),
    "ESSENTIA_GENRE_COUNT": ("analysis.genre_count", _parse_int),
    "ESSENTIA_WRITE_CONFIDENCE_TAGS": ("analysis.write_confidence_tags", _parse_bool),
    "ESSENTIA_OVERWRITE_EXISTING": ("analysis.overwrite_existing", _parse_bool),
    "ESSENTIA_COMPUTE": ("analysis.compute", _parse_string),
    "ESSENTIA_AUTOMATION_ENABLED": ("automation.enabled", _parse_bool),
    "ESSENTIA_AUTOMATION_WATCHER": ("automation.watcher", _parse_bool),
    "ESSENTIA_AUTOMATION_SCHEDULE": ("automation.schedule", _parse_string),
    "ESSENTIA_AUTOMATION_TIMEZONE": ("automation.timezone", _parse_string),
    "ESSENTIA_AUTOMATION_WRITE_TAGS": ("automation.mode", _parse_write_mode),
    "ESSENTIA_AUTOMATION_QUIET_SECONDS": ("automation.quiet_seconds", _parse_int),
    "ESSENTIA_BENCHMARK_MINIMUM_TRACK_SECONDS": (
        "benchmark.minimum_track_seconds",
        _parse_int,
    ),
    "ESSENTIA_BENCHMARK_SAFETY_MARGIN_PERCENT": (
        "benchmark.safety_margin_percent",
        _parse_int,
    ),
}


class SettingsService:
    def __init__(
        self,
        path: Path,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._path = path
        self._environment = os.environ if environment is None else environment

    def load(self) -> EffectiveSettings:
        defaults = AppSettings().model_dump(mode="python")
        file_values = self._load_file()
        merged = _deep_merge(defaults, file_values)

        sources: dict[str, SettingSource] = {
            path: "default" for path in _leaf_paths(defaults)
        }
        for path in _leaf_paths(file_values):
            sources[path] = "file"

        for env_name, (path, parser) in ENV_SETTINGS.items():
            if env_name not in self._environment:
                continue
            _set_dotted(merged, path, parser(self._environment[env_name], env_name))
            sources[path] = "env"

        values = _validated_settings(merged)
        return EffectiveSettings(values=values, sources=sources)

    def update(self, patch: Mapping[str, Any] | BaseModel) -> EffectiveSettings:
        patch_values = (
            patch.model_dump(exclude_unset=True, exclude_none=True)
            if isinstance(patch, BaseModel)
            else dict(patch)
        )
        locked = [
            path
            for path in _leaf_paths(patch_values)
            if self._environment_name_for_path(path) is not None
        ]
        if locked:
            raise AppError(
                "setting_locked_by_environment",
                "Diese Einstellung wird durch eine Umgebungsvariable vorgegeben.",
                409,
                {"paths": locked},
            )

        file_values = _deep_merge(self._load_file(), patch_values)
        _validated_settings(_deep_merge(AppSettings().model_dump(), file_values))
        self._write_file(file_values)
        return self.load()

    def migrate_legacy(
        self,
        legacy: AnalysisSettings | Mapping[str, Any],
    ) -> EffectiveSettings:
        if self._path.exists():
            return self.load()

        legacy_values = (
            legacy.model_dump(mode="python")
            if isinstance(legacy, AnalysisSettings)
            else _normalize_legacy(dict(legacy))
        )
        file_values = {"analysis": legacy_values}
        _validated_settings(_deep_merge(AppSettings().model_dump(), file_values))
        self._write_file(file_values)
        return self.load()

    def _load_file(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        loaded = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise ValueError("settings.yaml root must be a mapping")
        return loaded

    def _write_file(self, values: Mapping[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                yaml.safe_dump(dict(values), handle, sort_keys=False, allow_unicode=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self._path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    def _environment_name_for_path(self, path: str) -> str | None:
        for env_name, (mapped_path, _parser) in ENV_SETTINGS.items():
            if mapped_path == path and env_name in self._environment:
                return env_name
        return None


def _deep_merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _leaf_paths(values: Mapping[str, Any], prefix: str = "") -> list[str]:
    paths: list[str] = []
    for key, value in values.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            paths.extend(_leaf_paths(value, path))
        else:
            paths.append(path)
    return paths


def _set_dotted(values: dict[str, Any], path: str, value: Any) -> None:
    section, key = path.split(".", maxsplit=1)
    values[section][key] = value


def _normalize_legacy(values: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "worker_count": "workers",
        "compute_preference": "compute",
    }
    return {aliases.get(key, key): value for key, value in values.items()}


def _validated_settings(values: Mapping[str, Any]) -> AppSettings:
    settings = AppSettings.model_validate(values)
    CronSchedule(settings.automation.schedule, settings.automation.timezone)
    return settings
