from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    worker_count: int = Field(default=1, ge=1, le=64)
    max_audio_seconds: int = Field(default=300, ge=1, le=3600)
    genre_threshold: float = Field(default=0.15, ge=0, le=1)
    mood_threshold: float = Field(default=0.005, ge=0, le=1)
    genre_count: int = Field(default=3, ge=1, le=20)
    write_confidence_tags: bool = True
    overwrite_existing: bool = False
    compute_preference: Literal["auto", "cpu", "cuda"] = "auto"


class AppSettingsUpdate(BaseModel):
    worker_count: int | None = Field(default=None, ge=1, le=64)
    max_audio_seconds: int | None = Field(default=None, ge=1, le=3600)
    genre_threshold: float | None = Field(default=None, ge=0, le=1)
    mood_threshold: float | None = Field(default=None, ge=0, le=1)
    genre_count: int | None = Field(default=None, ge=1, le=20)
    write_confidence_tags: bool | None = None
    overwrite_existing: bool | None = None
    compute_preference: Literal["auto", "cpu", "cuda"] | None = None
