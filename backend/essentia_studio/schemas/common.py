from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class PathCapability(BaseModel):
    path: str
    status: Literal["ready", "read_only", "missing"]


class Capabilities(BaseModel):
    image_variant: Literal["cpu", "cuda"]
    available_compute: list[Literal["cpu", "cuda"]]
    music_root: PathCapability
    data_dir: PathCapability
    playlist_dir: PathCapability
    models: list[dict[str, str]]
