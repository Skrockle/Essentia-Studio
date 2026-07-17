from pathlib import Path

from essentia_studio.services.file_watcher import FileWatcher


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_watcher_emits_once_after_file_is_stable(tmp_path: Path) -> None:
    clock = FakeClock()
    emitted: list[Path] = []
    watcher = FileWatcher(tmp_path, {".flac"}, 30, emitted.append, clock=clock)
    path = tmp_path / "song.flac"

    watcher.record(path, size=10, mtime_ns=1)
    clock.advance(20)
    watcher.record(path, size=20, mtime_ns=2)
    clock.advance(29)
    watcher.flush_stable()
    assert emitted == []

    clock.advance(1)
    watcher.flush_stable()
    watcher.flush_stable()

    assert emitted == [path]


def test_watcher_ignores_unsupported_and_playlist_paths(tmp_path: Path) -> None:
    emitted: list[Path] = []
    playlist_dir = tmp_path / "SmartPlaylists"
    watcher = FileWatcher(
        tmp_path,
        {".flac"},
        5,
        emitted.append,
        excluded_roots={playlist_dir},
        clock=lambda: 10,
    )

    watcher.record(tmp_path / "cover.jpg", size=10, mtime_ns=1)
    watcher.record(playlist_dir / "generated.flac", size=10, mtime_ns=1)
    watcher.flush_stable()

    assert emitted == []


def test_observer_start_failure_sets_failed_and_falls_back_once(tmp_path: Path) -> None:
    fallback_reasons: list[str] = []

    class BrokenObserver:
        def schedule(self, *_args, **_kwargs) -> None:
            pass

        def start(self) -> None:
            raise OSError("native watcher unavailable")

        def stop(self) -> None:
            pass

        def join(self, *_args) -> None:
            pass

    watcher = FileWatcher(
        tmp_path,
        {".flac"},
        30,
        lambda _path: None,
        observer_factory=BrokenObserver,
        on_fallback=fallback_reasons.append,
    )

    watcher.start()
    watcher.start()

    assert watcher.health() == "failed"
    assert watcher.failure_reason == "native watcher unavailable"
    assert fallback_reasons == ["native watcher unavailable"]
