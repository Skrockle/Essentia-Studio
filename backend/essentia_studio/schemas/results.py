from typing import Annotated, Literal

from pydantic import BaseModel, Field

from essentia_studio.domain.analysis import StoredAnalysis


class ResultQuery(BaseModel):
    job_id: str | None = None
    search: str | None = None
    genre: str | None = None
    mood: str | None = None
    status: str | None = None
    selected: bool | None = None


class IdSelection(BaseModel):
    mode: Literal["ids"]
    ids: list[str]


class QuerySelection(BaseModel):
    mode: Literal["query"]
    query: ResultQuery
    excluded_ids: list[str] = Field(default_factory=list)


SelectionSpec = Annotated[IdSelection | QuerySelection, Field(discriminator="mode")]


class DraftUpdate(BaseModel):
    genres: list[str] | None = None
    moods: list[str] | None = None


class DraftResponse(BaseModel):
    genres: list[str]
    moods: list[str]
    selected: bool
    dirty: bool


class PredictionResponse(BaseModel):
    label: str
    confidence: float


class ResultResponse(BaseModel):
    id: str
    track_id: int
    relative_path: str
    genres: list[PredictionResponse]
    moods: list[PredictionResponse]
    draft: DraftResponse

    @classmethod
    def from_record(cls, result: StoredAnalysis) -> "ResultResponse":
        return cls(
            id=result.id,
            track_id=result.track_id,
            relative_path=result.relative_path,
            genres=[
                PredictionResponse.model_validate(value, from_attributes=True)
                for value in result.result.genres
            ],
            moods=[
                PredictionResponse.model_validate(value, from_attributes=True)
                for value in result.result.moods
            ],
            draft=DraftResponse.model_validate(result.draft, from_attributes=True),
        )


class ResultPage(BaseModel):
    items: list[ResultResponse]
    total: int
    page: int
    page_size: int
    selected_count: int


class SelectionUpdate(BaseModel):
    selection: SelectionSpec
    selected: bool


class BulkDraftUpdate(BaseModel):
    selection: SelectionSpec
    operation: Literal["add_genre", "remove_genre", "add_mood", "remove_mood"]
    value: str


class AffectedResponse(BaseModel):
    affected: int
