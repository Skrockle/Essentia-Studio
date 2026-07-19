# ONNX CPU/GPU Pipeline Design

**Status:** Approved

**Date:** 2026-07-19

## Goal

Increase CUDA analysis throughput by assigning decode, resampling, mel-feature extraction,
aggregation, and result selection to CPU work while reserving the single NVIDIA worker for
batched Discogs EffNet inference. The `dev-cuda-onnx` image must no longer initialize or run
TensorFlow models.

## Model decisions

- `discogs-effnet-bsdynamic-1.onnx` remains the GPU model. Its official metadata defines
  `PartitionedCall:0` as sigmoid predictions for all 400 Discogs classes and
  `PartitionedCall:1` as 1280-dimensional embeddings.
- The separate TensorFlow Discogs400 classification head is removed from the ONNX runtime.
- `mtg_jamendo_moodtheme-discogs-effnet-1.onnx` replaces the TensorFlow mood head and runs
  with ONNX Runtime's CPU provider. It is small enough that using CPU avoids competing with
  EffNet for GPU execution time.
- Existing class metadata, thresholds, maximum visible tags, and per-track averaging remain
  unchanged. Small floating-point differences between TensorFlow and ONNX are accepted.
- The CPU image and the regular CUDA TensorFlow image remain unchanged.

## Runtime architecture

The ONNX backend separates preparation from inference.

1. Job coordinator threads submit selected tracks concurrently.
2. The bounded CUDA pipeline starts up to the configured CPU-worker count of preparations.
3. Each preparation loads and resamples one track to 16 kHz, truncates it to the configured
   maximum duration, and creates the `[patches, 128, 96]` mel-feature array.
4. Prepared feature arrays enter a bounded queue. The queue still limits retained prepared
   audio, while active preparation has its own CPU-worker limit so a queue size of eight does
   not silently reduce sixteen CPU workers to eight.
5. The dispatcher concatenates up to the configured GPU batch size and submits one dynamic
   batch to the persistent ONNX CUDA session.
6. The GPU returns 400-class genre scores and 1280-dimensional embeddings. The persistent
   CPU-provider mood session consumes those embeddings.
7. Predictions are split by the original per-track patch counts, averaged, filtered by the
   existing thresholds, and returned in input order.

Only one CUDA execution process is used. Models are initialized once and reused for normal
analysis and the isolated benchmark.

## Concurrency and memory

- CPU preparation capacity equals `analysis.cpu_workers`.
- Prepared-feature queue capacity equals `analysis.gpu_queue_size`.
- GPU micro-batch size remains selectable as 1, 2, 4, or 8 titles.
- Callers waiting for preparation do not consume prepared-queue capacity.
- Cancellation prevents new GPU submission and releases both preparation and queue capacity.
- CUDA allocation failures retain the existing recursive batch reduction down to one title.
- A failed title remains an item-level failure and does not terminate unrelated tracks.

## Benchmark behavior

CUDA batch measurements must call the backend's real batch API with the configured number of
prepared feature arrays. Repeating `backend.analyze()` serially is not a batch measurement and
is removed. Measurements continue to include initialization, warm-up, repeated execution,
worker memory, and model identifiers.

## Image contract

`Dockerfile.cuda-onnx` downloads and checksum-verifies:

- `discogs-effnet-bsdynamic-1.onnx`
- `mtg_jamendo_moodtheme-discogs-effnet-1.onnx`
- the existing genre and mood class metadata

The ONNX model manifest contains no `.pb` files. Startup integrity checks reject missing or
modified ONNX files before the API becomes ready. The image keeps CUDA 11.8 and ONNX Runtime
GPU 1.18.1 for compatibility with the deployed GTX 1050 Ti.

## Verification

- Unit tests prove CPU preparation happens before the inference callback and that configured
  CPU preparation can exceed queue capacity without deadlock.
- ONNX tests prove output selection by semantic dimensions (400 genre scores and 1280
  embeddings), CPU-provider mood inference, per-track splitting, and preserved thresholds.
- Benchmark tests prove one real batch call replaces serial pseudo-batching.
- The full source gate must pass on macOS, Linux, and Windows.
- The published `dev-cuda-onnx` image must complete startup integrity, normal analysis,
  write/undo, and benchmark smoke tests.
- Final CUDA performance and model-result validation requires a real run on the user's NVIDIA
  GTX 1050 Ti; GitHub's hosted runner is not evidence of CUDA execution.

## Sources

- https://essentia.upf.edu/models.html
- https://essentia.upf.edu/models/feature-extractors/discogs-effnet/discogs-effnet-bsdynamic-1.json
- https://essentia.upf.edu/models/classification-heads/mtg_jamendo_moodtheme/
