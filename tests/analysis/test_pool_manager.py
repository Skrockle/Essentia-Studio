from pathlib import Path
from threading import Event, Thread

import pytest

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.errors import AppError
from essentia_studio.schemas.settings import AnalysisSettings


class FakeBackend:
    def __init__(self, workers: int, entered: Event | None = None, release: Event | None = None):
        self.workers = workers
        self.entered = entered
        self.release = release
        self.closed = False

    def analyze(self, _path: Path, _options: AnalysisOptions) -> AnalysisResult:
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            self.release.wait(timeout=2)
        return AnalysisResult()

    def close(self) -> None:
        self.closed = True

    def model_inventory(self):
        return [{"name": "fake"}]

    def available_compute(self):
        return ["cpu"]


def test_reconfigure_closes_old_pool_only_when_idle() -> None:
    created = []

    def factory(settings: AnalysisSettings):
        backend = FakeBackend(settings.workers)
        created.append(backend)
        return backend

    manager = WorkerPoolManager(factory, AnalysisSettings(workers=1))
    manager.reconfigure(AnalysisSettings(workers=2))

    assert [backend.workers for backend in created] == [1, 2]
    assert created[0].closed is True
    assert created[1].closed is False


def test_reconfigure_rejects_active_analysis() -> None:
    entered = Event()
    release = Event()
    backend = FakeBackend(1, entered, release)
    manager = WorkerPoolManager(lambda _settings: backend, AnalysisSettings())
    thread = Thread(target=lambda: manager.analyze(Path("song.flac"), AnalysisOptions()))
    thread.start()
    assert entered.wait(timeout=1)

    with pytest.raises(AppError, match="Analysejob"):
        manager.reconfigure(AnalysisSettings(workers=2))

    release.set()
    thread.join(timeout=2)
    assert manager.is_busy() is False
