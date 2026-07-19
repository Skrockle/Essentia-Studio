# Developing Essentia Studio

Essentia Studio supports native development on macOS, Windows 11, and Linux. The production runtime is an OCI container; local source checks do not require Docker or Apple Container.

## Prerequisites

- Python 3.10.x. Other Python versions are intentionally unsupported because the analysis wheel is validated on 3.10.
- Node.js 24.x and npm.
- Git with LF checkout for source files. The repository `.gitattributes` handles line endings.

## macOS and Linux

From the repository root:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm --prefix frontend install
python scripts/dev.py all
```

Open `http://localhost:5173`. Vite forwards `/api` to the backend on port 8000.

Use writable local folders while developing without a container:

```bash
export ESSENTIA_MUSIC_ROOT="$HOME/Music"
export ESSENTIA_DATA_DIR="$PWD/.local-data"
export ESSENTIA_PLAYLIST_DIR="$HOME/Music/SmartPlaylists"
python scripts/dev.py all
```

The application is designed for a trusted local network and has no login. Do not expose the development server to the internet.

## Windows PowerShell

Run these commands in PowerShell from the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
npm --prefix frontend install
python scripts/dev.py all
```

Environment variables for the current PowerShell session use `$env:`:

```powershell
$env:ESSENTIA_MUSIC_ROOT = "D:\Music"
$env:ESSENTIA_DATA_DIR = "$PWD\.local-data"
$env:ESSENTIA_PLAYLIST_DIR = "D:\Music\SmartPlaylists"
python scripts/dev.py all
```

If PowerShell blocks virtual-environment activation, set an appropriate execution policy for your user or invoke `.venv\Scripts\python.exe` directly. Core launchers use subprocess argument lists and never require Bash.

## Windows with WSL2

WSL2 is the recommended Windows environment for container work. Clone the repository below the Linux home directory, for example `~/src/Essentia-Studio`, rather than under `/mnt/c`. The Linux filesystem provides faster dependency installation, file watching, and bind mounts.

Inside WSL2, follow the macOS/Linux commands above. Docker Desktop should use its WSL2 backend. Native Windows and WSL2 environments need separate `.venv` and `frontend/node_modules` directories; do not share generated dependencies between them.

## Focused and full checks

Run a focused test while implementing:

```bash
python -m pytest tests/api/test_settings.py -q
npm --prefix frontend test -- --run src/app/App.test.tsx
```

Run the complete source gate before every commit or pull request:

```bash
python scripts/verify.py
```

The command runs backend tests and Ruff, then frontend lint, component tests, type checking, and a production build. It is the same contract on PowerShell, WSL2, macOS, Linux, and CI.

### CUDA-Analysepipeline

Im CUDA-Image lädt genau ein persistenter GPU-Prozess die Essentia-/TensorFlow-
Modelle. `ESSENTIA_ANALYSIS_CPU_WORKERS` steuert die CPU-Vorbereitung; die
GPU-Prozesszahl bleibt aus VRAM-Gründen auf `ESSENTIA_GPU_WORKERS=1` begrenzt.
`ESSENTIA_GPU_BATCH_SIZE` akzeptiert `1`, `2`, `4` oder `8`, und
`ESSENTIA_GPU_QUEUE_SIZE` begrenzt die Zahl vorbereiteter Anfragen. Eine volle
Queue erzeugt Backpressure statt unbeschränkt RAM zu belegen. Bei CUDA-OOM wird
die Batchgröße schrittweise halbiert; scheitert auch Batch 1, endet der Titel mit
einem verständlichen CUDA-Fehler.

Der Benchmark misst im CUDA-Image die Batchgrößen 1, 2 und 4 nacheinander und
weist Durchsatz, Initialisierungszeit und Fallbacks aus. CPU misst weiterhin nur
die Referenz mit Batch 1. Benchmarks laufen nie parallel.

## Running the production build locally

Build the frontend, configure local paths, and start the same-origin application:

```bash
npm --prefix frontend run build
export ESSENTIA_FRONTEND_DIR=frontend/dist
python -m uvicorn essentia_studio.main:create_app --factory --port 8000
```

On PowerShell, set `$env:ESSENTIA_FRONTEND_DIR = "frontend/dist"` before the same Python command.

## Platform-specific runtime notes

- Apple Container instructions and the required `linux/amd64` Rosetta settings are added with the delivery images.
- Docker Desktop runs the default CPU image on Windows. CUDA requires its WSL2 backend, compatible NVIDIA hardware, and current drivers.
- Native macOS development is CPU-only. Apple Metal is outside the first release.
- Real CUDA support is not considered verified until inference succeeds on an NVIDIA host.
