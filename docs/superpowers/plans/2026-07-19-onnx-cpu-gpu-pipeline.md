# ONNX CPU/GPU Pipeline Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Move audio preparation and mel-feature extraction onto the configured CPU workers, keep one persistent CUDA EffNet worker for true title batches, and replace both TensorFlow classification graphs in the CUDA-ONNX image.

**Architecture:** `CudaInferencePipeline` runs preparation independently of its bounded prepared-feature queue. `OnnxBackend.prepare()` returns mel patches, while `analyze_prepared_batch()` concatenates those patches for one dynamic EffNet ONNX call, consumes its genre and embedding outputs, and runs the small mood ONNX head on CPU. The CUDA-ONNX image contains only checksum-verified ONNX models and class metadata.

**Tech Stack:** Python 3.10, FastAPI, Essentia TensorFlow algorithms for audio/mel preparation, NumPy, ONNX Runtime GPU 1.18.1, pytest, Docker, GitHub Actions/GHCR.

**Global constraints:** Preserve cancellation, item-level failures, recursive CUDA OOM batch reduction, output thresholds, ordering, CPU/TensorFlow images, and unrelated user changes. A hosted image smoke test does not prove real CUDA execution.

---

### Task 1: Separate CPU preparation capacity from prepared queue capacity

**Files:**
- Modify: `tests/analysis/test_cuda_pipeline.py`
- Modify: `backend/essentia_studio/analysis/cuda_pipeline.py`

1. Add a concurrency test with `cpu_workers=2` and `queue_size=1` that blocks inference and proves two preparations can start before the first prepared request is consumed.
2. Run `uv run --cache-dir /tmp/essentia-uv-cache --extra dev python -m pytest tests/analysis/test_cuda_pipeline.py -q` and confirm the new test fails for the current shared semaphore.
3. Replace the shared pre-preparation queue semaphore with independent preparation-worker capacity and bounded queue insertion. Ensure cancellation and shutdown unblock waiting callers and release every acquired capacity exactly once.
4. Re-run the focused pipeline tests and commit the passing change.

### Task 2: Move mel preparation before GPU inference and consume native EffNet outputs

**Files:**
- Modify: `tests/analysis/test_onnx_backend.py`
- Modify: `backend/essentia_studio/analysis/onnx_backend.py`

1. Add failing tests proving `prepare()` returns `[patches,128,96]` features, model sessions are not needed during preparation, EffNet output dimensions 400 and 1280 are selected semantically, prepared title batches are split in input order, and mood inference uses only `CPUExecutionProvider`.
2. Run `uv run --cache-dir /tmp/essentia-uv-cache --extra dev python -m pytest tests/analysis/test_onnx_backend.py -q` and confirm the new expectations fail.
3. Override `prepare()` to decode/resample/truncate through the existing audio path and create per-title mel features using per-call Essentia algorithm instances safe for concurrent CPU workers.
4. Load one persistent EffNet ONNX session and one persistent mood ONNX CPU session. Remove TensorFlow prediction graph initialization.
5. Implement batch concatenation, semantic output selection, mood inference, per-title splitting, averaging, threshold filtering, and output ordering. Skip disabled classifiers without changing the API contract.
6. Re-run ONNX backend tests and commit the passing change.

### Task 3: Preserve process backend, benchmark, cancellation, and OOM behavior

**Files:**
- Modify: `tests/analysis/test_process_backend.py`
- Modify: `tests/benchmark/test_worker.py`
- Modify only if required: `backend/essentia_studio/analysis/process_backend.py`
- Modify only if required: `backend/essentia_studio/benchmark/worker.py`

1. Add or update tests showing the process backend submits prepared feature arrays to the persistent one-process inference executor, recursively splits OOM batches, and the benchmark invokes one real prepared batch rather than serial title calls.
2. Run `uv run --cache-dir /tmp/essentia-uv-cache --extra dev python -m pytest tests/analysis/test_process_backend.py tests/benchmark/test_worker.py -q` and identify only contract mismatches introduced by the new prepared value.
3. Make the smallest compatibility changes needed; retain current behavior where existing tests already cover the approved design.
4. Re-run the focused tests and commit the compatibility change if source changes were needed.

### Task 4: Replace CUDA-ONNX image model inventory

**Files:**
- Modify: `backend/essentia_studio/analysis/onnx-models.json`
- Modify: `backend/essentia_studio/analysis/onnx-download.json`
- Modify: `Dockerfile.cuda-onnx`
- Modify: `tests/analysis/test_manifest.py`
- Modify: `tests/scripts/test_download_models.py`
- Modify: `tests/container/test_runtime_contract.py`

1. Download the official mood ONNX model to a temporary location, verify its published byte size, calculate SHA-256, and inspect its input/output contract before recording it.
2. Add failing manifest/runtime tests requiring EffNet ONNX, mood ONNX, both JSON metadata files, no `.pb` entries, and installation of the ONNX manifest at `/app/models/onnx-models.json`.
3. Run the focused manifest, download, and container-contract tests and confirm they fail against the current TensorFlow model inventory.
4. Update the download and integrity manifests with official URLs and verified SHA-256 values. Change `Dockerfile.cuda-onnx` to download exactly that inventory and remove the shared TensorFlow graph archive from this image.
5. Re-run focused tests, run the model download against an empty temporary directory, validate every checksum, and commit the image-contract change.

### Task 5: Full source and container verification

**Files:**
- Modify only defects proven by tests.

1. Run all focused analysis, benchmark, manifest, script, and container tests together.
2. Run `uv run --cache-dir /tmp/essentia-uv-cache --extra dev python scripts/verify.py` and fix only failures caused by this branch.
3. Build `Dockerfile.cuda-onnx` locally for `linux/amd64` when the local container runtime supports it, then run the CUDA-ONNX image smoke tests that do not require a physical NVIDIA device.
4. Inspect the diff for accidental TensorFlow graph use, lifecycle leaks, broad formatting, secrets, and unrelated changes.
5. Use the requesting-code-review and verification-before-completion skills, address confirmed findings, and commit final fixes.

### Task 6: Publish and merge

**Files:**
- No source changes unless CI exposes a confirmed defect.

1. Push `codex/onnx-cpu-gpu-pipeline`, create a ready pull request referencing the approved design, and wait for every required GitHub check.
2. Diagnose and fix confirmed CI defects in the same worktree; re-run the corresponding local gate before pushing.
3. Merge the green pull request without rewriting history.
4. Dispatch the development image workflow for the ONNX CUDA variant and wait for build, publish, integrity, normal-analysis, write/undo, and benchmark smoke jobs to complete.
5. Verify the GHCR tag resolves to the newly published digest.
6. Tell the user that `ghcr.io/skrockle/essentia-studio:dev-cuda-onnx` is ready, provide the exact Unraid update/test commands, and clearly reserve the final real-GPU performance claim for their GTX 1050 Ti run.
