# Essentia Studio Delivery and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package, test, document, publish, and release Essentia Studio as private CPU and NVIDIA CUDA images from the private `Skrockle/Essentia-Studio` repository.

**Architecture:** Reproducible multi-stage OCI builds compile the React app and install a locked Python environment; image-specific runtime stages supply CPU or CUDA libraries but expose the same API. Cross-platform CI proves source behavior, container CI proves image behavior, Release Please owns SemVer/GitHub Releases, and one gated release job publishes all private GHCR tags.

**Tech Stack:** Apple Container 1.0.0, Docker/BuildKit, Docker Compose, NVIDIA CUDA 11.8/cuDNN 8, GitHub Actions, Release Please v5, GHCR, OCI attestations.

## Global Constraints

- Production images are `linux/amd64`; CPU is the unqualified default and CUDA is always explicitly suffixed.
- CPU uses Python 3.10 and `essentia-tensorflow==2.1b6.dev1389`.
- Model downloads are checksum-verified at build time; runtime never silently downloads a different model.
- Process runs as an unprivileged user, binds port `8000`, reads `/music`, and persists only under mounted `/music` and `/data`.
- Apple Container CPU verification uses `--arch amd64`; it cannot prove CUDA.
- Windows 11 uses Docker Desktop/WSL2; CUDA additionally requires current WSL2 and NVIDIA Windows drivers with GPU-PV support.
- All GitHub Actions are pinned to immutable commit SHAs.
- `GITHUB_TOKEN` permissions are job-scoped and minimal.
- GHCR packages remain private and linked to the private repository.
- A CUDA build/start smoke test is not equivalent to real GPU inference; release acceptance records one real NVIDIA inference run.
- Delivery scripts and workflows use descriptive steps and small helpers; hand-written Python/TypeScript still passes the shared complexity limit of 10 and the same readability review as application code.

---

### Task 1: Locked production dependencies, model manifest, and CPU image

**Files:**
- Create: `requirements/runtime.in`
- Create: `requirements/runtime.lock`
- Create: `requirements/analysis.in`
- Create: `requirements/analysis.lock`
- Create: `scripts/download_models.py`
- Create: `docker/__init__.py`
- Create: `docker/entrypoint.py`
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `tests/container/test_runtime_contract.py`

**Interfaces:**
- Consumes: built frontend, app factory, analysis model manifest.
- Produces: `essentia-studio:dev-cpu`; `/app/models`; entrypoint startup preflight.

- [ ] **Step 1: Write model checksum and runtime-contract tests**

```python
# tests/container/test_runtime_contract.py
import json
from pathlib import Path

from docker.entrypoint import validate_runtime


def test_model_manifest_has_sha256_for_every_file() -> None:
    manifest = json.loads(Path("backend/essentia_studio/analysis/models.json").read_text())
    assert len(manifest) == 5
    assert all(len(item["sha256"]) == 64 for item in manifest)
    assert all(item["url"].startswith("https://") for item in manifest)


def test_entrypoint_rejects_missing_models(tmp_path) -> None:
    result = validate_runtime(model_dir=tmp_path, music_root=tmp_path, data_dir=tmp_path)
    assert result.code == "models_missing"
```

- [ ] **Step 2: Run tests and verify missing entrypoint validator**

Run: `python -m pytest tests/container/test_runtime_contract.py -q`

Expected: FAIL importing `validate_runtime`.

- [ ] **Step 3: Lock Python inputs and implement checksum downloader**

`runtime.in` contains FastAPI, Pydantic, SQLAlchemy, Uvicorn, Mutagen, and NumPy constrained to a version proven compatible with the Essentia wheel. `analysis.in` adds exactly `essentia-tensorflow==2.1b6.dev1389`. Generate hashes with:

```bash
uv pip compile requirements/runtime.in --python-version 3.10 --python-platform x86_64-manylinux_2_17 --generate-hashes -o requirements/runtime.lock
uv pip compile requirements/analysis.in --python-version 3.10 --python-platform x86_64-manylinux_2_17 --generate-hashes -o requirements/analysis.lock
```

`download_models.py` loads the committed manifest, downloads to a temporary sibling using `urllib.request.urlopen`, streams SHA-256, rejects a mismatch, and replaces the final path only after verification. Existing files are reused only when their checksum matches.

- [ ] **Step 4: Implement the CPU multi-stage image**

```dockerfile
# Dockerfile
FROM node:24-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim-bookworm AS runtime
ARG VERSION=0.0.0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    ESSENTIA_MUSIC_ROOT=/music ESSENTIA_DATA_DIR=/data \
    ESSENTIA_MODEL_DIR=/app/models ESSENTIA_IMAGE_VARIANT=cpu \
    ESSENTIA_FRONTEND_DIR=/app/frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libfftw3-3 libsamplerate0 libtag1v5 libyaml-0-2 libchromaprint1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --home-dir /app --create-home app
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.10.9
COPY requirements/analysis.lock /app/requirements.lock
RUN uv pip install --system --require-hashes -r /app/requirements.lock
COPY pyproject.toml /src/pyproject.toml
COPY backend /src/backend
RUN uv pip install --system --no-deps /src
COPY scripts/download_models.py backend/essentia_studio/analysis/models.json /tmp/models/
RUN python /tmp/models/download_models.py --manifest /tmp/models/models.json --output /app/models
COPY --from=frontend /src/frontend/dist /app/frontend
COPY docker/entrypoint.py /app/entrypoint.py
RUN mkdir -p /music /data && chown -R app:app /app /music /data
USER app
EXPOSE 8000
VOLUME ["/music", "/data"]
LABEL org.opencontainers.image.source="https://github.com/Skrockle/Essentia-Studio" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.licenses="MIT"
ENTRYPOINT ["python", "/app/entrypoint.py"]
CMD ["python", "-m", "uvicorn", "essentia_studio.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

`entrypoint.py` validates manifests, mount readability, data writability, and CPU capability, prints one structured summary, then calls `os.execvp(command[0], command)` with the CMD arguments.

- [ ] **Step 5: Build and smoke-test with Apple Container**

Run:

```bash
container build --arch amd64 -t essentia-studio:dev-cpu -f Dockerfile .
container run --arch amd64 --rm -d --name essentia-studio-cpu -p 127.0.0.1:18000:8000 --volume /tmp/essentia-music:/music --volume /tmp/essentia-data:/data essentia-studio:dev-cpu
curl --fail http://127.0.0.1:18000/health
container stop essentia-studio-cpu
```

Expected: build succeeds through Rosetta; health returns `{"status":"ok","version":"0.0.0"}`; logs report `image_variant=cpu` and no missing model.

Commit:

```bash
git add requirements scripts/download_models.py docker/entrypoint.py Dockerfile .dockerignore tests/container
git commit -m "feat: package CPU container image"
```

### Task 2: NVIDIA CUDA image and real GPU capability contract

**Files:**
- Create: `Dockerfile.cuda`
- Create: `backend/essentia_studio/analysis/tensorflow_devices.py`
- Create: `tests/analysis/test_tensorflow_devices.py`
- Create: `scripts/gpu_smoke.py`

**Interfaces:**
- Consumes: same app/artifacts as CPU image.
- Produces: `essentia-studio:dev-cuda`; `detect_tensorflow_devices() -> DeviceReport`; real inference smoke command.

- [ ] **Step 1: Write CPU fallback and required-CUDA tests**

```python
# tests/analysis/test_tensorflow_devices.py
import pytest

from essentia_studio.analysis.tensorflow_devices import select_compute
from essentia_studio.errors import AppError


def test_auto_uses_cpu_when_cuda_image_has_no_visible_gpu() -> None:
    assert select_compute("auto", image_variant="cuda", gpu_devices=[]) == "cpu"


def test_explicit_cuda_requires_visible_tensorflow_gpu() -> None:
    with pytest.raises(AppError) as error:
        select_compute("cuda", image_variant="cuda", gpu_devices=[])
    assert error.value.code == "cuda_device_unavailable"
```

- [ ] **Step 2: Run tests and verify missing selector**

Run: `python -m pytest tests/analysis/test_tensorflow_devices.py -q`

Expected: FAIL during import.

- [ ] **Step 3: Implement device detection isolated from ordinary imports**

`detect_tensorflow_devices` lazy-imports TensorFlow only inside the function and returns physical GPU names plus build CUDA/cuDNN metadata. `select_compute` permits CPU in both variants, rejects CUDA in CPU images, rejects explicit CUDA without devices, and lets auto fall back to CPU while exposing the diagnostic.

- [ ] **Step 4: Build CUDA from the same production application**

```dockerfile
# Dockerfile.cuda
FROM node:24-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS runtime
ARG VERSION=0.0.0
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    ESSENTIA_MUSIC_ROOT=/music ESSENTIA_DATA_DIR=/data \
    ESSENTIA_MODEL_DIR=/app/models ESSENTIA_IMAGE_VARIANT=cuda \
    ESSENTIA_FRONTEND_DIR=/app/frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.10 python3-pip ffmpeg libfftw3-3 libsamplerate0 libtag1v5 libyaml-0-2 libchromaprint1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --home-dir /app --create-home app
WORKDIR /app
RUN python3.10 -m pip install --no-cache-dir uv==0.10.9
COPY requirements/analysis.lock /app/requirements.lock
RUN uv pip install --system --python /usr/bin/python3.10 --require-hashes -r /app/requirements.lock
COPY pyproject.toml /src/pyproject.toml
COPY backend /src/backend
RUN uv pip install --system --python /usr/bin/python3.10 --no-deps /src
COPY scripts/download_models.py backend/essentia_studio/analysis/models.json /tmp/models/
RUN python3.10 /tmp/models/download_models.py --manifest /tmp/models/models.json --output /app/models
COPY --from=frontend /src/frontend/dist /app/frontend
COPY docker/entrypoint.py /app/entrypoint.py
COPY scripts/gpu_smoke.py /app/scripts/gpu_smoke.py
RUN mkdir -p /music /data && chown -R app:app /app /music /data
USER app
EXPOSE 8000
VOLUME ["/music", "/data"]
LABEL org.opencontainers.image.source="https://github.com/Skrockle/Essentia-Studio" \
      org.opencontainers.image.version="$VERSION" org.opencontainers.image.licenses="MIT"
ENTRYPOINT ["python3.10", "/app/entrypoint.py"]
CMD ["python3.10", "-m", "uvicorn", "essentia_studio.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Build/start without GPU, then run real NVIDIA smoke**

GitHub hosted runner command:

```bash
docker build -f Dockerfile.cuda -t essentia-studio:dev-cuda .
docker run --rm -d --name essentia-studio-cuda-smoke -p 18001:8000 -v /tmp/essentia-music:/music -v /tmp/essentia-data:/data essentia-studio:dev-cuda
curl --fail http://127.0.0.1:18001/api/capabilities
docker stop essentia-studio-cuda-smoke
```

NVIDIA host command:

```bash
docker run --rm --gpus all -v "$PWD/test-music:/music:ro" essentia-studio:dev-cuda python3.10 /app/scripts/gpu_smoke.py /music/tone.wav
```

Expected: hosted runner reports no GPU and CPU fallback; NVIDIA run reports at least one TensorFlow GPU, selected compute `cuda`, and nonempty real genre/mood inference.

Commit:

```bash
git add Dockerfile.cuda backend/essentia_studio/analysis/tensorflow_devices.py tests/analysis/test_tensorflow_devices.py scripts/gpu_smoke.py
git commit -m "feat: package NVIDIA CUDA image"
```

### Task 3: Linux Compose, Apple Container, and Windows deployment documentation

**Files:**
- Replace: `docker-compose.yml`
- Create: `compose.cuda.yml`
- Create: `docs/deployment/apple-container.md`
- Create: `docs/deployment/linux-docker.md`
- Create: `docs/deployment/windows.md`
- Create: `tests/docs/test_commands.py`

**Interfaces:**
- Consumes: CPU/CUDA image contracts.
- Produces: copy-paste deployment commands and CPU-default/CUDA-explicit Compose behavior.

- [ ] **Step 1: Write config and documentation command tests**

```python
# tests/docs/test_commands.py
from pathlib import Path
import yaml


def test_default_compose_uses_cpu_image_and_required_mounts() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    service = compose["services"]["essentia-studio"]
    assert service["image"].endswith(":latest-cpu")
    assert "${MUSIC_DIR}:/music" in service["volumes"]
    assert "${DATA_DIR}:/data" in service["volumes"]


def test_windows_docs_include_wsl_and_powershell_paths() -> None:
    text = Path("docs/deployment/windows.md").read_text(encoding="utf-8")
    assert "wsl --update" in text
    assert "$env:MUSIC_DIR" in text
    assert "--gpus all" in text
```

- [ ] **Step 2: Run and verify old Compose contract fails**

Run: `python -m pytest tests/docs/test_commands.py -q`

Expected: FAIL because the current Compose file describes only the legacy CLI.

- [ ] **Step 3: Implement CPU-default and CUDA-explicit Compose files**

```yaml
# docker-compose.yml
services:
  essentia-studio:
    image: ghcr.io/skrockle/essentia-studio:latest-cpu
    ports:
      - "${ESSENTIA_BIND:-0.0.0.0}:8000:8000"
    volumes:
      - "${MUSIC_DIR}:/music"
      - "${DATA_DIR}:/data"
    restart: unless-stopped
```

```yaml
# compose.cuda.yml
services:
  essentia-studio:
    image: ghcr.io/skrockle/essentia-studio:latest-cuda
    gpus: all
```

Start CUDA only with `docker compose -f docker-compose.yml -f compose.cuda.yml up -d`.

- [ ] **Step 4: Document exact host-specific commands**

Apple documentation uses `container run --arch amd64`, absolute host mount paths, a persistent data directory, and both loopback and LAN publish examples. Windows documentation recommends a clone inside WSL2, includes PowerShell environment-variable syntax, Docker Desktop WSL2 enablement, `wsl --update`, CPU Compose, CUDA Compose, current NVIDIA Windows drivers, and `docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi` preflight. Linux documentation covers Docker Engine, NVIDIA Container Toolkit, directory ownership for UID/GID 10001, private GHCR login, upgrades, and rollbacks.

- [ ] **Step 5: Validate Compose/docs and commit**

Run:

```bash
docker compose config
docker compose -f docker-compose.yml -f compose.cuda.yml config
python -m pytest tests/docs/test_commands.py -q
```

Expected: both Compose configurations parse; default has no GPU reservation; CUDA has `gpus: all`; documentation contract tests PASS.

Commit:

```bash
git add docker-compose.yml compose.cuda.yml docs/deployment tests/docs/test_commands.py
git commit -m "docs: add cross-platform container deployment"
```

### Task 4: Cross-platform CI and container verification workflows

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/gpu-smoke.yml`
- Create: `scripts/ci/generate_fixture.py`

**Interfaces:**
- Consumes: `scripts/verify.py`, both Dockerfiles, real GPU smoke.
- Produces: Linux/macOS/Windows source checks, CPU/CUDA image checks, manually dispatched self-hosted GPU acceptance.

- [ ] **Step 1: Add a workflow-policy test before workflow files**

```python
# tests/ci/test_workflows.py
from pathlib import Path
import re


def test_actions_are_sha_pinned() -> None:
    for workflow in Path(".github/workflows").glob("*.yml"):
        for line in workflow.read_text().splitlines():
            if "uses:" in line and not line.lstrip().startswith("#"):
                ref = line.split("uses:", 1)[1].strip()
                if ref.startswith("./"):
                    continue
                assert re.search(r"@[0-9a-f]{40}(?:\s+#.*)?$", ref), (workflow, line)
```

- [ ] **Step 2: Run and verify workflow tests fail until files exist**

Add an assertion that `ci.yml`, `gpu-smoke.yml`, and later `release.yml` exist, then run `python -m pytest tests/ci/test_workflows.py -q`.

Expected: FAIL listing missing workflows.

- [ ] **Step 3: Implement immutable action pins and OS matrix**

Use these resolved SHAs exactly:

- `actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10` (`v6`)
- `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1` (`v6`)
- `actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38` (`v6`)
- `actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4` (`v5`)
- `docker/setup-buildx-action@bb05f3f5519dd87d3ba754cc423b652a5edd6d2c` (`v4`)
- `docker/login-action@af1e73f918a031802d376d3c8bbc3fe56130a9b0` (`v4`)
- `docker/metadata-action@dc802804100637a589fabce1cb79ff13a1411302` (`v6`)
- `docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a` (`v7`)
- `googleapis/release-please-action@0dfd8538845b8e92600d271a895a5372865d4062` (`v5`)

`ci.yml` has:

- source matrix `ubuntu-latest`, `macos-latest`, `windows-latest`; Python 3.10, Node 24, `python scripts/verify.py`;
- Linux browser job installing Playwright Chromium and running both E2E specs with fake analysis;
- CPU image build/load, generated fixture mount, health, real CPU inference, write/undo API smoke;
- CUDA image build/load and no-GPU capability smoke.

No pull-request job receives `packages: write` or `contents: write`.

- [ ] **Step 4: Add manually dispatched real GPU workflow**

`gpu-smoke.yml` runs only on `workflow_dispatch` and a self-hosted runner labeled `[self-hosted, linux, x64, nvidia]`. It checks out the selected ref, builds the CUDA image, verifies `nvidia-smi`, runs `scripts/gpu_smoke.py` with `--gpus all`, and uploads the JSON report. Give it only `contents: read`.

- [ ] **Step 5: Lint workflows, run policy test, and commit**

Run:

```bash
python -m pytest tests/ci/test_workflows.py -q
python -m yamllint .github/workflows
```

Expected: every external action has a 40-character SHA; matrix and permission tests PASS; YAML lint exits 0.

Commit:

```bash
git add .github/workflows/ci.yml .github/workflows/gpu-smoke.yml scripts/ci tests/ci
git commit -m "ci: verify source and container variants"
```

### Task 5: Release Please, GitHub Release, private GHCR images, SBOM, and provenance

**Files:**
- Create: `release-please-config.json`
- Create: `.release-please-manifest.json`
- Create: `.github/workflows/release.yml`
- Create: `CHANGELOG.md`
- Modify: `tests/ci/test_workflows.py`

**Interfaces:**
- Consumes: successful main branch, both Dockerfiles.
- Produces: release PR, `vX.Y.Z` tag, GitHub Release, CPU/CUDA private packages and documented tags.

- [ ] **Step 1: Extend workflow tests for release outputs and tags**

```python
def test_release_workflow_publishes_all_required_tags() -> None:
    text = Path(".github/workflows/release.yml").read_text()
    for tag in ["latest", "latest-cpu", "latest-cuda", "${{ needs.release.outputs.tag_name }}", "${{ needs.release.outputs.tag_name }}-cpu", "${{ needs.release.outputs.tag_name }}-cuda"]:
        assert tag in text
    assert "release_created" in text
    assert "packages: write" in text
```

- [ ] **Step 2: Run and verify missing release workflow**

Run: `python -m pytest tests/ci/test_workflows.py -q`

Expected: FAIL because `release.yml` is absent.

- [ ] **Step 3: Configure simple manifest releases**

```json
{
  "packages": { ".": { "release-type": "simple", "package-name": "essentia-studio" } },
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json"
}
```

`.release-please-manifest.json` is `{ ".": "0.0.0" }`. The release workflow triggers on pushes to `main`. Its `release` job grants `contents: write`, `pull-requests: write`, and `issues: write`; it exposes `release_created`, `tag_name`, `version`, and `sha` from the Release Please step as job outputs.

- [ ] **Step 4: Publish both images in the same workflow run**

The `publish` job needs `release`, runs only when `needs.release.outputs.release_created == 'true'`, grants `contents: read`, `packages: write`, `attestations: write`, and `id-token: write`, logs into `ghcr.io`, and builds a matrix:

```yaml
strategy:
  matrix:
    include:
      - variant: cpu
        dockerfile: Dockerfile
        tags: |
          ghcr.io/skrockle/essentia-studio:latest
          ghcr.io/skrockle/essentia-studio:latest-cpu
          ghcr.io/skrockle/essentia-studio:${{ needs.release.outputs.tag_name }}
          ghcr.io/skrockle/essentia-studio:${{ needs.release.outputs.tag_name }}-cpu
      - variant: cuda
        dockerfile: Dockerfile.cuda
        tags: |
          ghcr.io/skrockle/essentia-studio:latest-cuda
          ghcr.io/skrockle/essentia-studio:${{ needs.release.outputs.tag_name }}-cuda
```

`docker/build-push-action` uses `push: true`, `platforms: linux/amd64`, `provenance: mode=max`, `sbom: true`, version build arg, and OCI labels. This same run avoids the `GITHUB_TOKEN` recursive-trigger limitation.

- [ ] **Step 5: Validate release configuration and commit**

Run:

```bash
python -m json.tool release-please-config.json
python -m json.tool .release-please-manifest.json
python -m pytest tests/ci/test_workflows.py -q
```

Expected: JSON valid; all actions SHA-pinned; release outputs and six tag contracts PASS.

Commit:

```bash
git add release-please-config.json .release-please-manifest.json .github/workflows/release.yml CHANGELOG.md tests/ci/test_workflows.py
git commit -m "ci: automate releases and private images"
```

### Task 6: Final documentation, private repository publication, and verified first release

**Files:**
- Replace: `README.md`
- Create: `docs/licenses.md`
- Create: `docs/upstream-sync.md`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `tests/docs/test_readme.py`
- Modify: `frontend/src/features/settings/AboutView.tsx`
- Create: `frontend/src/features/settings/AboutView.test.tsx`

**Interfaces:**
- Consumes: complete product and workflows.
- Produces: private `origin`, pushed history, first release PR/release, private GHCR images, full operator documentation.

- [ ] **Step 1: Write documentation coverage tests**

```python
# tests/docs/test_readme.py
from pathlib import Path


def test_readme_covers_required_deployments_and_licenses() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    for phrase in [
        "Apple Container", "Windows 11", "WSL2", "Docker Compose", "NVIDIA CUDA",
        "/music", "/data", "kein Login", "CC BY-NC-ND 4.0", "nichtkommerziell",
        "Navidrome Smart Playlists", "Tags wiederherstellen",
    ]:
        assert phrase in text
```

The About-view test mocks `/health` and `/api/capabilities`, then asserts that version, image variant, both upstream repositories, MIT, AGPL-3.0, CC BY-NC-ND 4.0, and the noncommercial model warning are visible links/text.

- [ ] **Step 2: Run and verify legacy README lacks product contracts**

Run: `python -m pytest tests/docs/test_readme.py -q`

Expected: FAIL for multiple required phrases.

- [ ] **Step 3: Write operator, licensing, and upstream documentation**

README includes a screenshot, CPU quick start first, mount permission warning, Apple Container command, Windows/WSL2 steps, Linux Compose, CUDA override, settings, analysis/review/write/undo, full playlist features, update/rollback, health checks, and troubleshooting. `docs/licenses.md` distinguishes project MIT, imported playlist MIT, Essentia AGPL-3.0, and model CC BY-NC-ND 4.0 noncommercial constraints. `docs/upstream-sync.md` uses `git fetch upstream`, review branch, tests, and merge/cherry-pick without force-pushing. `AboutView.tsx` renders the runtime version/image variant plus links and plain-language license warnings from one typed `LICENSE_NOTICES` constant; it does not hide the noncommercial model limitation behind a modal.

- [ ] **Step 4: Create the private standalone repository and push**

First verify authentication and visibility:

```bash
gh auth status
gh repo view Skrockle/Essentia-Studio --json nameWithOwner,visibility
```

If the repository does not exist, authenticate interactively through the user's GitHub session, then run:

```bash
gh repo create Skrockle/Essentia-Studio --private --source=. --remote=origin --description "Local Essentia genre/mood analysis and Navidrome smart playlist studio"
git push -u origin main
```

Verify `origin` is private through the GitHub API and `upstream` remains `https://github.com/WB2024/Essentia-to-Metadata.git`. Never create a public fork and never change upstream's push URL to the private repository.

- [ ] **Step 5: Run full verification and create the first release**

Run local gates:

```bash
python scripts/verify.py
npm --prefix frontend run e2e
container build --arch amd64 -t essentia-studio:release-candidate -f Dockerfile .
```

Push a Conventional Commit if documentation changed, wait for green CI, review and merge the Release Please PR, then verify:

```bash
gh release view --json tagName,isDraft,isPrerelease,url
gh api /user/packages/container/essentia-studio/versions
```

Pull and smoke the exact CPU release tag through Apple Container. Run the manually dispatched GPU workflow on an NVIDIA runner and retain its JSON artifact URL in the GitHub Release notes. Confirm the package visibility is private and tags include `latest`, `latest-cpu`, `latest-cuda`, `vX.Y.Z`, `vX.Y.Z-cpu`, and `vX.Y.Z-cuda` for the actual released version.

- [ ] **Step 6: Commit documentation before release publication**

```bash
git add README.md docs THIRD_PARTY_NOTICES.md tests/docs/test_readme.py frontend/src/features/settings/AboutView.tsx frontend/src/features/settings/AboutView.test.tsx
git commit -m "docs: complete deployment and licensing guide"
git push origin main
```

## Delivery completion evidence

- Apple Container builds/runs the CPU image and completes real CPU inference.
- Docker CI builds and starts both images.
- A real NVIDIA run records TensorFlow GPU detection and inference.
- Windows CI runs source/path/line-ending tests; Windows deployment docs include CPU and GPU paths.
- The GitHub repository and GHCR package are observed as private.
- The merged Release Please PR produces the GitHub Release and every required image tag.
- README, About, notices, and image labels expose provenance and licensing constraints.
