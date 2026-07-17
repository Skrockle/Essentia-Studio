from dataclasses import dataclass
from typing import Literal

from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.tags.protocol import DesiredTags, ManagedTagSnapshot

WriteStatus = Literal["started", "verified", "conflict", "failed", "undone"]
WriteTrigger = Literal["manual", "automation"]


@dataclass(frozen=True, slots=True)
class WriteOperation:
    id: str
    result_id: str
    relative_path: str
    status: WriteStatus
    original_snapshot: ManagedTagSnapshot | None = None
    requested_tags: DesiredTags | None = None
    post_write_fingerprint: TrackFingerprint | None = None
    error_code: str | None = None
    error_message: str | None = None
    trigger: WriteTrigger = "manual"

    @property
    def undo_available(self) -> bool:
        return self.status == "verified" and self.post_write_fingerprint is not None
