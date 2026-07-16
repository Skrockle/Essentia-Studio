"""Run one real, bounded Essentia CPU inference inside a built image."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", type=Path)
    arguments = parser.parse_args()
    model_dir = Path(os.environ.get("ESSENTIA_MODEL_DIR", "/app/models"))
    result = EssentiaBackend(model_dir, "cpu").analyze(
        arguments.audio_path,
        AnalysisOptions(genre_threshold=0, mood_threshold=0, max_audio_seconds=30),
    )
    if not result.genres or not result.moods:
        raise RuntimeError("CPU smoke inference returned empty genre or mood predictions")
    print(
        json.dumps(
            {
                "genres": [asdict(item) for item in result.genres],
                "moods": [asdict(item) for item in result.moods],
                "models": result.model_ids,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
