from __future__ import annotations

from collections.abc import Callable
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from threading import Condition, RLock

from essentia_studio.analysis.protocol import AnalysisBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.errors import AppError
from essentia_studio.schemas.settings import AnalysisSettings

BackendFactory = Callable[[AnalysisSettings], AnalysisBackend]


class WorkerPoolManager:
    def __init__(self, factory: BackendFactory, settings: AnalysisSettings) -> None:
        self._factory = factory
        self._settings = settings
        self._lock = RLock()
        self._idle = Condition(self._lock)
        self._active = 0
        self._backend = factory(settings)

    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult:
        with self._lock:
            self._active += 1
        try:
            return self._analyze_with_recovery(path, options)
        finally:
            with self._idle:
                self._active -= 1
                self._idle.notify_all()

    def _analyze_with_recovery(
        self,
        path: Path,
        options: AnalysisOptions,
    ) -> AnalysisResult:
        for attempt in range(2):
            with self._lock:
                backend = self._backend
            try:
                return backend.analyze(path, options)
            except BrokenProcessPool as error:
                self._discard_broken(backend)
                if attempt == 1:
                    raise AppError(
                        "analysis_worker_crashed",
                        "Der Analyseprozess wurde unerwartet beendet. "
                        "Dieser Titel wurde übersprungen; die übrige Analyse wird fortgesetzt.",
                        500,
                    ) from error
        raise AssertionError("unreachable")

    def reconfigure(self, settings: AnalysisSettings) -> None:
        with self._lock:
            if settings == self._settings:
                return
            if self._active:
                raise AppError(
                    "analysis_pool_busy",
                    "Die Worker können während eines Analysejobs nicht geändert werden.",
                    409,
                )
            previous = self._backend
            self._backend = self._factory(settings)
            self._settings = settings
        self._close_backend(previous)

    def is_busy(self) -> bool:
        with self._lock:
            return self._active > 0

    def model_inventory(self) -> list[dict[str, str]]:
        with self._lock:
            return self._backend.model_inventory()

    def available_compute(self) -> list[str]:
        with self._lock:
            return self._backend.available_compute()

    def close(self) -> None:
        with self._idle:
            while self._active:
                self._idle.wait(timeout=0.5)
            backend = self._backend
        self._close_backend(backend)

    def _discard_broken(self, backend: AnalysisBackend) -> None:
        with self._lock:
            if backend is not self._backend:
                return
            self._backend = self._factory(self._settings)
        self._close_backend(backend)

    @staticmethod
    def _close_backend(backend: AnalysisBackend) -> None:
        close = getattr(backend, "close", None)
        if close is not None:
            close()
