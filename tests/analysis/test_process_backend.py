from concurrent.futures import Future
from pathlib import Path

from essentia_studio.analysis.process_backend import ProcessAnalysisBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


class FakeProcess:
    def __init__(self) -> None:
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True


class FakeExecutor:
    def __init__(self) -> None:
        self.process = FakeProcess()
        self.shutdown_called = False

    def submit(self, _function, _path: str, _options: AnalysisOptions) -> Future:
        future: Future = Future()
        future.set_result(AnalysisResult())
        return future

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        assert wait is False
        assert cancel_futures is True
        self.shutdown_called = True


def test_cancel_terminates_executor_processes_and_recreates_pool(monkeypatch) -> None:
    executors: list[FakeExecutor] = []

    def create_executor(*_args, **_kwargs) -> FakeExecutor:
        executor = FakeExecutor()
        executor._processes = {1: executor.process}
        executors.append(executor)
        return executor

    monkeypatch.setattr(
        "essentia_studio.analysis.process_backend.ProcessPoolExecutor",
        create_executor,
    )
    backend = ProcessAnalysisBackend(Path("/models"), "cpu", 1, "cpu")

    backend.analyze(Path("song.flac"), AnalysisOptions())
    backend.cancel()
    backend.analyze(Path("song-2.flac"), AnalysisOptions())

    assert executors[0].process.terminated is True
    assert executors[0].shutdown_called is True
    assert len(executors) == 2
