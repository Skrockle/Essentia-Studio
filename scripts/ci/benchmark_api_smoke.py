"""Run the resource benchmark through its public HTTP API without writing tags."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from typing import Any


def request_json(base_url: str, path: str, *, method: str = "GET") -> Any:
    request = urllib.request.Request(f"{base_url}{path}", method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_job(base_url: str, job_id: str, timeout_seconds: int = 900) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = request_json(base_url, f"/api/jobs/{job_id}")
        if job["status"] not in {"queued", "running"}:
            if job["status"] != "completed":
                raise RuntimeError(f"Benchmark job ended as {job['status']}: {job}")
            return job
        time.sleep(1)
    raise TimeoutError(f"Benchmark job {job_id} exceeded {timeout_seconds} seconds")


def run_smoke(base_url: str, *, require_cuda: bool = False) -> dict[str, Any]:
    scan = request_json(base_url, "/api/library/scan", method="POST")
    wait_for_job(base_url, scan["id"])
    writes_before = len(request_json(base_url, "/api/writes"))

    created = request_json(base_url, "/api/benchmarks", method="POST")
    finished_job = wait_for_job(base_url, created["id"])
    run_id = finished_job["configuration"]["run_id"]
    run = next(
        item for item in request_json(base_url, "/api/benchmarks") if item["id"] == run_id
    )
    measurements = {item["compute"]: item for item in run["measurements"]}

    if run["status"] != "completed" or not run["current"]:
        raise RuntimeError(f"Benchmark result is not current and complete: {run}")
    if "cpu" not in measurements:
        raise RuntimeError(f"Benchmark has no CPU reference: {run}")
    if require_cuda and "cuda" not in measurements:
        raise RuntimeError(f"CUDA benchmark was required but not measured: {run}")
    if len(request_json(base_url, "/api/writes")) != writes_before:
        raise RuntimeError("Benchmark unexpectedly created a write operation")

    return {
        "run_id": run_id,
        "sample": run["sample_relative_path"],
        "cpu_seconds": measurements["cpu"]["average_seconds"],
        "cuda_seconds": measurements.get("cuda", {}).get("average_seconds"),
        "recommended_workers": run["recommended_workers"],
        "snapshot": run["snapshot"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--require-cuda", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(run_smoke(arguments.base_url, require_cuda=arguments.require_cuda), indent=2))


if __name__ == "__main__":
    main()
