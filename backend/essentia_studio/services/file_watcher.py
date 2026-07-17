from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Literal

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers import Observer

WatcherHealth = Literal["disabled", "starting", "ready", "failed"]


@dataclass(slots=True)
class _PendingFile:
    size: int
    mtime_ns: int
    changed_at: float
    verify_on_disk: bool


class _WatchdogHandler(FileSystemEventHandler):
    def __init__(self, record: Callable[[Path], None]) -> None:
        self._record = record

    def on_created(self, event: FileSystemEvent) -> None:
        self._record_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._record_event(event)

    def on_moved(self, event: FileSystemMovedEvent) -> None:
        if not event.is_directory:
            self._record(Path(event.dest_path))

    def _record_event(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._record(Path(event.src_path))


class FileWatcher:
    def __init__(
        self,
        root: Path,
        supported_extensions: set[str],
        quiet_seconds: int,
        on_stable_path: Callable[[Path], None],
        *,
        excluded_roots: set[Path] | None = None,
        clock: Callable[[], float] = time.monotonic,
        observer_factory: Callable[[], Any] = Observer,
        on_fallback: Callable[[str], None] | None = None,
    ) -> None:
        self._root = root.absolute()
        self._supported_extensions = {suffix.lower() for suffix in supported_extensions}
        self._quiet_seconds = quiet_seconds
        self._on_stable_path = on_stable_path
        self._excluded_roots = {
            excluded.absolute() for excluded in (excluded_roots or set())
        }
        self._clock = clock
        self._observer_factory = observer_factory
        self._on_fallback = on_fallback
        self._pending: dict[Path, _PendingFile] = {}
        self._lock = Lock()
        self._stop_event = Event()
        self._flush_thread: Thread | None = None
        self._observer: Any | None = None
        self._health: WatcherHealth = "disabled"
        self._failure_reason: str | None = None
        self._fallback_sent = False

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason

    def health(self) -> WatcherHealth:
        return self._health

    def start(self) -> None:
        if self._health in {"starting", "ready", "failed"}:
            return
        self._health = "starting"
        observer: Any | None = None
        try:
            observer = self._observer_factory()
            observer.schedule(_WatchdogHandler(self.record), str(self._root), recursive=True)
            observer.start()
            self._observer = observer
            self._stop_event.clear()
            self._flush_thread = Thread(
                target=self._flush_loop,
                name="essentia-file-watcher",
                daemon=True,
            )
            self._flush_thread.start()
            self._health = "ready"
        except Exception as error:
            if observer is not None:
                try:
                    observer.stop()
                    observer.join(timeout=2)
                except Exception:
                    pass
            self._fail(str(error))

    def stop(self) -> None:
        self._stop_event.set()
        observer = self._observer
        if observer is not None:
            observer.stop()
            observer.join(timeout=5)
        thread = self._flush_thread
        if thread is not None:
            thread.join(timeout=5)
        self._observer = None
        self._flush_thread = None
        if self._health != "failed":
            self._health = "disabled"

    def record(
        self,
        path: Path,
        *,
        size: int | None = None,
        mtime_ns: int | None = None,
    ) -> None:
        path = path.absolute()
        if not self._accepts(path):
            return

        verify_on_disk = size is None or mtime_ns is None
        if verify_on_disk:
            try:
                stat = path.stat()
            except (FileNotFoundError, OSError):
                return
            size = stat.st_size
            mtime_ns = stat.st_mtime_ns
        assert size is not None and mtime_ns is not None

        with self._lock:
            self._pending[path] = _PendingFile(
                size=size,
                mtime_ns=mtime_ns,
                changed_at=self._clock(),
                verify_on_disk=verify_on_disk,
            )

    def flush_stable(self) -> None:
        now = self._clock()
        stable: list[Path] = []
        with self._lock:
            for path, pending in list(self._pending.items()):
                if now - pending.changed_at < self._quiet_seconds:
                    continue
                if pending.verify_on_disk and self._refresh_if_changed(path, pending, now):
                    continue
                del self._pending[path]
                stable.append(path)

        for path in stable:
            self._on_stable_path(path)

    def _refresh_if_changed(self, path: Path, pending: _PendingFile, now: float) -> bool:
        try:
            stat = path.stat()
        except (FileNotFoundError, OSError):
            del self._pending[path]
            return True
        if stat.st_size == pending.size and stat.st_mtime_ns == pending.mtime_ns:
            return False
        pending.size = stat.st_size
        pending.mtime_ns = stat.st_mtime_ns
        pending.changed_at = now
        return True

    def _accepts(self, path: Path) -> bool:
        if not path.is_relative_to(self._root):
            return False
        if path.suffix.lower() not in self._supported_extensions:
            return False
        if path.is_symlink():
            return False
        return not any(path.is_relative_to(excluded) for excluded in self._excluded_roots)

    def _flush_loop(self) -> None:
        interval = min(max(self._quiet_seconds / 2, 0.5), 5.0)
        while not self._stop_event.wait(interval):
            self.flush_stable()

    def _fail(self, reason: str) -> None:
        self._health = "failed"
        self._failure_reason = reason
        if self._on_fallback is not None and not self._fallback_sent:
            self._fallback_sent = True
            self._on_fallback(reason)
