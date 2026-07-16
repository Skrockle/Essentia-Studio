# Windows 11 mit Docker Desktop und WSL2

Empfohlen wird Docker Desktop mit WSL2-Backend. Das Repository sollte innerhalb
des Linux-Dateisystems der WSL-Distribution liegen, damit Dateizugriffe und
Line-Endings zuverlässig bleiben.

```powershell
wsl --update
wsl --install
$env:MUSIC_DIR = "C:\Users\Justus\Music"
$env:DATA_DIR = "C:\Users\Justus\EssentiaStudio\data"
docker login ghcr.io
docker compose up -d
```

Alternativ können die Variablen in WSL gesetzt und Linux-Pfade verwendet werden:

```bash
export MUSIC_DIR=/mnt/c/Users/Justus/Music
export DATA_DIR=/mnt/c/Users/Justus/EssentiaStudio/data
docker compose up -d
```

## NVIDIA CUDA unter Windows

Erforderlich sind ein aktueller NVIDIA-Windows-Treiber mit GPU-PV, aktuelles
WSL2 und aktivierte WSL-Integration in Docker Desktop. CUDA muss vor dem Start
sichtbar sein:

```powershell
wsl --update
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
docker compose -f docker-compose.yml -f compose.cuda.yml up -d
```

Die App hat im lokalen Netz absichtlich keine Anmeldung. Keine Portfreigabe am
Router einrichten und den Dienst nicht öffentlich exponieren.
