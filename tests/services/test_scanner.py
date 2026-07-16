from essentia_studio.services.scanner import scan_music_root


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
