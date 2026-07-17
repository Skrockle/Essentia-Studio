from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SettingSource = Literal["default", "file", "env"]


class AnalysisSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workers: int = Field(default=1, ge=1, le=64)
    max_audio_seconds: int = Field(default=300, ge=1, le=3600)
    genre_threshold: float = Field(default=0.15, ge=0, le=1)
    mood_threshold: float = Field(default=0.005, ge=0, le=1)
    genre_count: int = Field(default=3, ge=1, le=20)
    write_confidence_tags: bool = True
    overwrite_existing: bool = False
    compute: Literal["auto", "cpu", "cuda"] = "auto"


class AutomationSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    watcher: bool = False
    schedule: str = "0 * * * *"
    timezone: str = "UTC"
    mode: Literal["analyze", "analyze_and_write"] = "analyze"
    quiet_seconds: int = Field(default=30, ge=5, le=3600)


class BenchmarkSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    minimum_track_seconds: int = Field(default=60, ge=1, le=3600)
    safety_margin_percent: int = Field(default=30, ge=0, le=90)


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    analysis: AnalysisSettings = Field(default_factory=AnalysisSettings)
    automation: AutomationSettings = Field(default_factory=AutomationSettings)
    benchmark: BenchmarkSettings = Field(default_factory=BenchmarkSettings)


class EffectiveSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    values: AppSettings
    sources: dict[str, SettingSource]


class AnalysisSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workers: int | None = Field(default=None, ge=1, le=64)
    max_audio_seconds: int | None = Field(default=None, ge=1, le=3600)
    genre_threshold: float | None = Field(default=None, ge=0, le=1)
    mood_threshold: float | None = Field(default=None, ge=0, le=1)
    genre_count: int | None = Field(default=None, ge=1, le=20)
    write_confidence_tags: bool | None = None
    overwrite_existing: bool | None = None
    compute: Literal["auto", "cpu", "cuda"] | None = None


class AutomationSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    watcher: bool | None = None
    schedule: str | None = None
    timezone: str | None = None
    mode: Literal["analyze", "analyze_and_write"] | None = None
    quiet_seconds: int | None = Field(default=None, ge=5, le=3600)


class BenchmarkSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_track_seconds: int | None = Field(default=None, ge=1, le=3600)
    safety_margin_percent: int | None = Field(default=None, ge=0, le=90)


class AppSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis: AnalysisSettingsUpdate | None = None
    automation: AutomationSettingsUpdate | None = None
    benchmark: BenchmarkSettingsUpdate | None = None
