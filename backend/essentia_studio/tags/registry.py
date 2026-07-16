from pathlib import Path

from essentia_studio.tags.mutagen_adapter import MutagenTagAdapter
from essentia_studio.tags.protocol import TagAdapter


class TagAdapterRegistry:
    def __init__(self, adapter: TagAdapter | None = None) -> None:
        self._adapter = adapter or MutagenTagAdapter()

    def for_path(self, _path: Path) -> TagAdapter:
        return self._adapter
