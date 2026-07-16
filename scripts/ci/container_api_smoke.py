"""Exercise scan, real analysis, preview, verified write, and undo over HTTP."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from typing import Any


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_job(base_url: str, job_id: str, timeout_seconds: int = 300) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = request_json(base_url, f"/api/jobs/{job_id}")
        if job["status"] not in {"queued", "running"}:
            if job["status"] != "completed":
                raise RuntimeError(f"Job {job_id} ended as {job['status']}: {job}")
            return job
        time.sleep(0.5)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout_seconds} seconds")


def run_smoke(base_url: str) -> dict[str, Any]:
    scan = request_json(base_url, "/api/library/scan", method="POST", payload={})
    wait_for_job(base_url, scan["id"])
    tracks = request_json(base_url, "/api/library/tracks")["items"]
    if not tracks:
        raise RuntimeError("Container scan did not find the mounted fixture")

    analysis = request_json(
        base_url,
        "/api/analysis/jobs",
        method="POST",
        payload={"track_ids": [tracks[0]["id"]]},
    )
    wait_for_job(base_url, analysis["id"])
    result = request_json(base_url, "/api/results")["items"][0]
    genres = [*result["draft"]["genres"], "Container Smoke"]
    request_json(
        base_url,
        f"/api/results/{result['id']}/draft",
        method="PATCH",
        payload={"genres": genres},
    )

    selection = {"selection": {"mode": "ids", "ids": [result["id"]]}}
    preview = request_json(base_url, "/api/writes/preview", method="POST", payload=selection)
    if preview["writable"] != 1 or preview["conflicts"]:
        raise RuntimeError(f"Unexpected write preview: {preview}")
    operation = request_json(base_url, "/api/writes", method="POST", payload=selection)[
        "operations"
    ][0]
    if operation["status"] != "verified" or not operation["undo_available"]:
        raise RuntimeError(f"Write was not verified: {operation}")
    undone = request_json(
        base_url,
        f"/api/writes/{operation['id']}/undo",
        method="POST",
        payload={},
    )
    if undone["status"] != "undone":
        raise RuntimeError(f"Undo was not verified: {undone}")
    return {"scan": "completed", "analysis": "completed", "write": "verified", "undo": "undone"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    arguments = parser.parse_args()
    print(json.dumps(run_smoke(arguments.base_url), indent=2))


if __name__ == "__main__":
    main()
