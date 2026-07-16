from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlaylistDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=500)
    comment: str | None = Field(default=None, max_length=500)
    all: list[dict] | None = None
    any: list[dict] | None = None
    sort: str | None = Field(default=None, max_length=500)
    order: Literal["asc", "desc"] | None = None
    limit: int | None = Field(default=None, ge=1, le=100_000)
