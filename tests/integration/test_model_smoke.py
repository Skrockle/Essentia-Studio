import math
import os
import struct
import wave
from pathlib import Path

import pytest

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions


@pytest.mark.model
def test_real_cpu_models_analyze_generated_tone(tmp_path) -> None:
    model_dir_value = os.environ.get("ESSENTIA_MODEL_DIR")
    if not model_dir_value:
        pytest.skip("ESSENTIA_MODEL_DIR is only required in image model tests")

    tone_path = tmp_path / "tone.wav"
    _write_tone(tone_path)
    result = EssentiaBackend(Path(model_dir_value)).analyze(
        tone_path,
        AnalysisOptions(genre_threshold=0, mood_threshold=0),
    )

    assert result.genres
    assert result.moods


def _write_tone(path: Path) -> None:
    sample_rate = 16000
    samples = [
        int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
        for index in range(sample_rate * 10)
    ]
    with wave.open(str(path), "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(sample_rate)
        audio_file.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
