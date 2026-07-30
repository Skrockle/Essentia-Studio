from pathlib import Path

from essentia_studio.domain.tracks import ManagedTagInventory
from essentia_studio.services.scanner import scan_music_root
from essentia_studio.tags.protocol import ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


class InventoryAdapter:
    def __init__(self, snapshots: dict[str, ManagedTagSnapshot | Exception]) -> None:
        self.snapshots = snapshots
        self.write_calls = 0

    def read(self, path: Path) -> ManagedTagSnapshot:
        result = self.snapshots[path.name]
        if isinstance(result, Exception):
            raise result
        return result

    def write(self, *_args) -> None:
        self.write_calls += 1


def test_scan_returns_only_supported_files_sorted_by_relative_path(tmp_path) -> None:
    (tmp_path / "B").mkdir()
    (tmp_path / "B" / "two.MP3").write_bytes(b"2")
    (tmp_path / "one.flac").write_bytes(b"1")
    (tmp_path / "cover.jpg").write_bytes(b"x")

    tracks = list(scan_music_root(tmp_path))

    assert [track.relative_path for track in tracks] == ["B/two.MP3", "one.flac"]
    assert [track.fingerprint.size for track in tracks] == [1, 1]


def test_scan_excludes_symbolic_links(tmp_path) -> None:
    original = tmp_path / "original.flac"
    original.write_bytes(b"audio")
    (tmp_path / "linked.flac").symlink_to(original)

    assert [track.relative_path for track in scan_music_root(tmp_path)] == ["original.flac"]


def test_scan_records_managed_tags_without_writing(tmp_path) -> None:
    path = tmp_path / "tagged.flac"
    path.write_bytes(b"audio")
    adapter = InventoryAdapter(
        {
            "tagged.flac": ManagedTagSnapshot(
                "vorbis", {"genres": [" Ｒｏｃｋ ", "rock"], "moods": ["Calm"]}
            )
        }
    )

    [track] = scan_music_root(tmp_path, tag_registry=TagAdapterRegistry(adapter))

    assert track.managed_tags == ManagedTagInventory(["Rock"], ["Calm"], "ok", None)
    assert adapter.write_calls == 0


def test_scan_records_empty_managed_tags_as_successful_read(tmp_path) -> None:
    path = tmp_path / "empty.flac"
    path.write_bytes(b"audio")
    adapter = InventoryAdapter({"empty.flac": ManagedTagSnapshot("vorbis", {})})

    [track] = scan_music_root(tmp_path, tag_registry=TagAdapterRegistry(adapter))

    assert track.managed_tags == ManagedTagInventory([], [], "ok", None)


def test_scan_does_not_treat_tag_read_error_as_empty(tmp_path) -> None:
    path = tmp_path / "broken.flac"
    path.write_bytes(b"audio")
    adapter = InventoryAdapter({"broken.flac": ValueError("invalid")})

    [track] = scan_music_root(tmp_path, tag_registry=TagAdapterRegistry(adapter))

    assert track.managed_tags.status == "error"
    assert track.managed_tags.error_code == "managed_tags_unreadable"
