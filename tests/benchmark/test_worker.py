from essentia_studio.benchmark.worker import _analyze_batch
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


def test_benchmark_analyzes_one_prepared_batch_instead_of_repeating_calls() -> None:
    calls: list[list[object]] = []

    class FakeBackend:
        def analyze_prepared_batch(self, prepared, _options):
            calls.append(prepared)
            return [AnalysisResult(model_ids=[str(value)]) for value in prepared]

    results = _analyze_batch(FakeBackend(), "prepared-audio", AnalysisOptions(), 4)

    assert calls == [["prepared-audio"] * 4]
    assert len(results) == 4
