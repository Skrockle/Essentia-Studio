from pydantic import BaseModel

from essentia_studio.domain.writes import WriteOperation
from essentia_studio.schemas.results import SelectionSpec


class WriteSelectionRequest(BaseModel):
    selection: SelectionSpec


class WritePreviewItem(BaseModel):
    result_id: str
    relative_path: str
    before_genres: list[str]
    after_genres: list[str]
    before_moods: list[str]
    after_moods: list[str]
    conflict: bool


class WritePreviewResponse(BaseModel):
    total: int
    writable: int
    conflicts: int
    items: list[WritePreviewItem]


class WriteOperationResponse(BaseModel):
    id: str
    result_id: str
    relative_path: str
    status: str
    error_code: str | None
    error_message: str | None
    undo_available: bool

    @classmethod
    def from_record(cls, operation: WriteOperation) -> "WriteOperationResponse":
        return cls(
            id=operation.id,
            result_id=operation.result_id,
            relative_path=operation.relative_path,
            status=operation.status,
            error_code=operation.error_code,
            error_message=operation.error_message,
            undo_available=operation.undo_available,
        )


class WriteBatchResponse(BaseModel):
    operations: list[WriteOperationResponse]
