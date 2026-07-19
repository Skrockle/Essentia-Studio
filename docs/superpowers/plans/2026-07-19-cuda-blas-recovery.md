# CUDA BLAS Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent CUDA inference failures on low-memory NVIDIA GPUs when TensorFlow classification heads allocate cuBLAS workspaces.

**Architecture:** Keep the existing single CUDA worker and apply the fix at the shared classification-head boundary used by both the regular Essentia backend and the ONNX backend. TensorFlow receives the GPU memory-growth environment before model construction, while each genre/mood head processes at most 16 embedding rows per cuBLAS call.

**Tech Stack:** Python 3.10, NumPy, Essentia TensorFlow, ONNX Runtime, Docker CUDA 11.8.

## Global Constraints

- Preserve the approved CPU/CUDA image split and Linux amd64 target.
- Analysis remains read-only and one item failure must not stop unrelated items.
- Verify source tests before publishing an image.
- CUDA claims require a real inference run on an NVIDIA host; image build success alone is insufficient.

### Task 1: Protect TensorFlow GPU allocation

**Files:**
- Modify: `backend/essentia_studio/analysis/worker.py`
- Modify: `backend/essentia_studio/benchmark/worker.py`
- Modify: `Dockerfile.cuda`
- Modify: `Dockerfile.cuda-onnx`

- [x] Set `TF_FORCE_GPU_ALLOW_GROWTH=true` in both CUDA Docker images and before CUDA worker model creation.
- [x] Keep CPU workers unchanged.

### Task 2: Bound classification-head workspace size

**Files:**
- Modify: `backend/essentia_studio/analysis/essentia_backend.py`
- Test: `tests/analysis/test_essentia_backend.py`

- [x] Add a regression test with 32 embeddings and assert genre/mood calls are split into two 16-row chunks.
- [x] Route both classification heads through a shared 16-row chunk helper.
- [ ] Run focused and full source verification.

### Task 3: Recognize the resulting CUDA allocation errors

**Files:**
- Modify: `backend/essentia_studio/analysis/process_backend.py`

- [x] Treat cuBLAS allocation and xGEMM launch failures as CUDA memory errors for the existing batch fallback path.
- [ ] Run process-backend regression tests.

### Task 4: Publish and validate the CUDA-ONNX image

**Files:**
- No source files; use GitHub CI and GHCR workflow.

- [ ] Commit and push the isolated branch.
- [ ] Wait for source CI and the CUDA-ONNX image build/smoke workflow.
- [ ] Confirm normal analysis and benchmark smoke tests pass.
- [ ] Ask the user to pull the new tag and run a real GTX 1050 Ti inference; inspect for absence of `CUBLAS_STATUS_ALLOC_FAILED` and successful result completion.
