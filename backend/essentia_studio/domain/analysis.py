from dataclasses import dataclass, field

from essentia_studio.domain.tracks import TrackFingerprint, TrackMetadata


@dataclass(frozen=True, slots=True)
class Prediction:
    label: str
    confidence: float


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    enable_genres: bool = True
    enable_moods: bool = True
    genre_threshold: float = 0.25
    mood_threshold: float = 0.10
    genre_count: int = 3
    max_audio_seconds: int = 300


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    genres: list[Prediction] = field(default_factory=list)
    moods: list[Prediction] = field(default_factory=list)
    model_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TagDraft:
    genres: list[str]
    moods: list[str]
    selected: bool = False
    dirty: bool = False


@dataclass(frozen=True, slots=True)
class StoredAnalysis:
    id: str
    track_id: int
    relative_path: str
    metadata: TrackMetadata
    fingerprint: TrackFingerprint
    result: AnalysisResult
    draft: TagDraft
