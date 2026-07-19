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

Docker Desktop sollte dem Container zum Start mindestens **4 GB** RAM bereitstellen.
Der Ressourcen-Benchmark berücksichtigt das tatsächlich sichtbare Limit, lässt 30
Prozent Reserve und übernimmt die Worker-Empfehlung nur nach Bestätigung.

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

## Dateiüberwachung und Zeitplan

Bei Windows-Bind-Mounts und besonders bei Pfaden unter `/mnt/c` können
Dateisystemereignisse verzögert oder unvollständig ankommen. Wenn der Watcher in der
GUI keinen stabilen Zustand meldet, ihn ausschalten; die Zeitplan-Einstellung öffnet
sich dann automatisch und übernimmt die Suche nach neuen oder geänderten Titeln.
Die Entwicklung innerhalb des WSL2-Linux-Dateisystems liefert zuverlässigere Events.

Der Benchmark nutzt automatisch einen Titel mit mindestens 60 Sekunden und schreibt
keine Tags. CPU wird immer gemessen; CUDA nur im CUDA-Image mit sichtbarer NVIDIA-GPU.
Im CUDA-Image werden Batch 1, 2 und 4 nacheinander gemessen. Die laufende Analyse
verwendet einen persistenten GPU-Prozess, CPU-Vorbereitungsworker und eine bounded
Queue; bei VRAM-Mangel wird auf kleinere Batches zurückgefallen. Nach Änderungen
an Docker-RAM, Modellen oder Analyseoptionen ist eine alte Messung nicht mehr
gültig und wird in der Oberfläche entsprechend markiert.
