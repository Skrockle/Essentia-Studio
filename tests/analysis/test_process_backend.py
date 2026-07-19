import multiprocessing
from concurrent.futures import Future
from pathlib import Path
from threading import Event, Thread

from essentia_studio.analysis.process_backend import ProcessAnalysisBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.errors import AppError


def test_cuda_worker_submits_prepared_batch_to_backend_once(monkeypatch) -> None:
    calls: list[list[object]] = []

    class FakeBackend:
        def analyze_prepared_batch(self, prepared, _options):
            calls.append(prepared)
            return [AnalysisResult(model_ids=[str(value)]) for value in prepared]

    monkeypatch.setattr("essentia_studio.analysis.worker._backend", FakeBackend())

    from essentia_studio.analysis.worker import analyze_prepared_batch_in_worker

    results = analyze_prepared_batch_in_worker(["one", "two"], AnalysisOptions())

    assert calls == [["one", "two"]]
    assert [result.model_ids for result in results] == [["one"], ["two"]]


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


def test_cancel_returns_when_worker_future_does_not_resolve(monkeypatch) -> None:
    submitted = Event()
    cancellation = Event()
    future: Future = Future()

    class BlockingExecutor:
        _processes = {1: FakeProcess()}

        def submit(self, _function, _path: str, _options: AnalysisOptions) -> Future:
            submitted.set()
            return future

        def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
            assert wait is False
            assert cancel_futures is True

    executor = BlockingExecutor()
    monkeypatch.setattr(
        "essentia_studio.analysis.process_backend.ProcessPoolExecutor",
        lambda *_args, **_kwargs: executor,
    )
    backend = ProcessAnalysisBackend(Path("/models"), "cpu", 1, "cpu")
    errors: list[AppError] = []

    def run_analysis() -> None:
        try:
            backend.analyze(Path("song.flac"), AnalysisOptions(), cancellation)
        except AppError as error:
            errors.append(error)

    thread = Thread(target=run_analysis)
    thread.start()
    assert submitted.wait(timeout=1)
    cancellation.set()
    backend.cancel()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert [error.code for error in errors] == ["analysis_cancelled"]


def test_cuda_backend_uses_one_gpu_process_and_configured_cpu_pipeline(monkeypatch) -> None:
    created = []

    class FakePipeline:
        def __init__(self, settings, **_callbacks) -> None:
            created.append(settings)

        def analyze(self, _path, _options, _cancellation=None):
            return AnalysisResult(model_ids=["persistent-cuda"])

        def close(self):
            pass

        cancel = close

    monkeypatch.setattr(
        "essentia_studio.analysis.process_backend.CudaInferencePipeline",
        FakePipeline,
    )
    backend = ProcessAnalysisBackend(
        Path("/models"),
        "cuda",
        4,
        "cuda",
        ["cpu", "cuda"],
        cpu_workers=3,
        gpu_batch_size=4,
        gpu_queue_size=8,
    )

    result = backend.analyze(Path("song.flac"), AnalysisOptions())

    assert result.model_ids == ["persistent-cuda"]
    assert created[0].cpu_workers == 3
    assert created[0].batch_size == 4
    assert created[0].queue_size == 8


def test_cuda_executor_uses_spawn_context(monkeypatch) -> None:
    created: list[dict[str, object]] = []

    class SpawnSafeExecutor(FakeExecutor):
        pass

    def create_executor(*_args, **kwargs) -> SpawnSafeExecutor:
        created.append(kwargs)
        executor = SpawnSafeExecutor()
        executor._processes = {1: executor.process}
        return executor

    monkeypatch.setattr(
        "essentia_studio.analysis.process_backend.ProcessPoolExecutor",
        create_executor,
    )
    backend = ProcessAnalysisBackend(Path("/models"), "cuda", 1, "cuda", ["cpu", "cuda"])

    backend._get_executor()

    context = created[0]["mp_context"]
    assert isinstance(context, multiprocessing.context.BaseContext)
    assert context.get_start_method() == "spawn"


def test_cuda_batch_falls_back_to_smaller_batches_on_oom() -> None:
    class OomExecutor:
        def __init__(self) -> None:
            self.calls = []

        def submit(self, _function, prepared, _options):
            self.calls.append(len(prepared))
            if len(prepared) > 1:
                raise RuntimeError("CUDA out of memory")
            future = Future()
            future.set_result([AnalysisResult(model_ids=[str(prepared[0])])])
            return future

    backend = ProcessAnalysisBackend(Path("/models"), "cuda", 1, "cuda")
    executor = OomExecutor()
    backend._executor = executor

    result = backend._infer_batch(["one", "two", "three", "four"], AnalysisOptions())

    assert [item.model_ids for item in result] == [["one"], ["two"], ["three"], ["four"]]
    assert executor.calls == [4, 2, 1, 1, 2, 1, 1]
    assert backend.cuda_oom_fallbacks == 3
