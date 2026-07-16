"""Prove that Essentia creates a TensorFlow GPU device during real inference."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.analysis.tensorflow_devices import (
    detect_tensorflow_devices,
    select_compute,
)
from essentia_studio.domain.analysis import AnalysisOptions


def run_smoke(audio_path: Path, model_dir: Path) -> dict[str, object]:
    device_report = detect_tensorflow_devices()
    selected = select_compute(
        "cuda",
        image_variant="cuda",
        gpu_devices=device_report.gpu_devices,
    )
    result, evidence = _run_inference_probe(audio_path, model_dir)
    if not result["genres"] or not result["moods"]:
        raise RuntimeError("GPU smoke inference returned empty genre or mood predictions")
    return {
        "device_report": asdict(device_report),
        "selected_compute": selected,
        "tensorflow_gpu_evidence": evidence,
        **result,
    }


def _run_inference_probe(audio_path: Path, model_dir: Path) -> tuple[dict[str, Any], list[str]]:
    with tempfile.TemporaryDirectory(prefix="essentia-gpu-smoke-") as temporary_dir:
        output_path = Path(temporary_dir) / "inference.json"
        environment = os.environ.copy()
        environment["CUDA_VISIBLE_DEVICES"] = environment.get("CUDA_VISIBLE_DEVICES", "0")
        environment["TF_CPP_MIN_LOG_LEVEL"] = "0"
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                str(audio_path),
                "--model-dir",
                str(model_dir),
                "--probe-output",
                str(output_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
            env=environment,
        )
        if completed.returncode:
            diagnostic = (completed.stderr or completed.stdout)[-4000:]
            raise RuntimeError(f"GPU inference process failed:\n{diagnostic}")
        evidence = _tensorflow_gpu_evidence(completed.stdout, completed.stderr)
        if not evidence:
            diagnostic = (completed.stderr + completed.stdout)[-4000:]
            raise RuntimeError(
                "Inference completed without TensorFlow GPU placement evidence.\n"
                f"{diagnostic}"
            )
        return json.loads(output_path.read_text(encoding="utf-8")), evidence


def _tensorflow_gpu_evidence(stdout: str, stderr: str) -> list[str]:
    evidence = []
    for line in (stderr + "\n" + stdout).splitlines():
        normalized = line.casefold()
        if "created" in normalized and "device" in normalized and "gpu:" in normalized:
            evidence.append(line.strip())
    return evidence


def _write_probe(audio_path: Path, model_dir: Path, output_path: Path) -> None:
    result = EssentiaBackend(model_dir, "cuda").analyze(
        audio_path,
        AnalysisOptions(genre_threshold=0, mood_threshold=0, max_audio_seconds=30),
    )
    output_path.write_text(
        json.dumps(
            {
                "genres": [asdict(item) for item in result.genres],
                "moods": [asdict(item) for item in result.moods],
                "models": result.model_ids,
            }
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", type=Path)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(os.environ.get("ESSENTIA_MODEL_DIR", "/app/models")),
    )
    parser.add_argument("--probe-output", type=Path)
    arguments = parser.parse_args()
    if arguments.probe_output:
        _write_probe(arguments.audio_path, arguments.model_dir, arguments.probe_output)
        return 0
    print(json.dumps(run_smoke(arguments.audio_path, arguments.model_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
