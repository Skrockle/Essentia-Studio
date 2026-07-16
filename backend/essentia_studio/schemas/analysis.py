from pydantic import BaseModel, Field, model_validator

from essentia_studio.domain.analysis import AnalysisOptions


class LibrarySelectionQuery(BaseModel):
    search: str | None = None
    present: bool | None = True
    extension: str | None = None


class AnalysisJobRequest(BaseModel):
    track_ids: list[int] | None = None
    query: LibrarySelectionQuery | None = None
    enable_genres: bool = True
    enable_moods: bool = True
    genre_threshold: float | None = Field(default=None, ge=0, le=1)
    mood_threshold: float | None = Field(default=None, ge=0, le=1)
    genre_count: int | None = Field(default=None, ge=1, le=20)
    max_audio_seconds: int | None = Field(default=None, ge=1, le=3600)

    @model_validator(mode="after")
    def validate_selection_and_heads(self) -> "AnalysisJobRequest":
        if bool(self.track_ids) == bool(self.query):
            raise ValueError("Genau eine Titelauswahl oder Abfrage ist erforderlich.")
        if not self.enable_genres and not self.enable_moods:
            raise ValueError("Genre- oder Mood-Analyse muss aktiviert sein.")
        return self

    def options(self, defaults) -> AnalysisOptions:
        return AnalysisOptions(
            enable_genres=self.enable_genres,
            enable_moods=self.enable_moods,
            genre_threshold=(
                self.genre_threshold
                if self.genre_threshold is not None
                else defaults.genre_threshold
            ),
            mood_threshold=(
                self.mood_threshold
                if self.mood_threshold is not None
                else defaults.mood_threshold
            ),
            genre_count=self.genre_count if self.genre_count is not None else defaults.genre_count,
            max_audio_seconds=(
                self.max_audio_seconds
                if self.max_audio_seconds is not None
                else defaults.max_audio_seconds
            ),
        )
