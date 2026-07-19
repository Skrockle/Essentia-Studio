# Linux mit Docker

Melde Docker an der privaten GitHub Container Registry an. Das Token benötigt
`read:packages` und Zugriff auf das private Repository.

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u Skrockle --password-stdin
mkdir -p "$HOME/essentia-studio/data"
sudo chown -R 10001:10001 "$HOME/essentia-studio/data"
export MUSIC_DIR="$HOME/Music"
export DATA_DIR="$HOME/essentia-studio/data"
docker compose up -d
```

Compose weist standardmäßig **4 GB** als sinnvollen Startwert zu. Bei einer lokalen
Override-Datei kann der Wert angepasst werden; nach jeder Änderung von RAM oder CPU
den Ressourcen-Benchmark erneut ausführen. Er hält 30 Prozent Reserve und ändert die
Workerzahl erst nach ausdrücklicher Übernahme.

Für NVIDIA CUDA werden ein aktueller NVIDIA-Treiber und das NVIDIA Container
Toolkit benötigt. Erst den Zugriff prüfen, dann die explizite CUDA-Erweiterung
starten:

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
docker compose -f docker-compose.yml -f compose.cuda.yml up -d
```

Update und Rollback:

```bash
docker compose pull
docker compose up -d
```

Der Entwicklungsstand wird als separates CPU-Image unter `dev-cpu` veröffentlicht.
Nach einem Push auf `main` kannst du es aktualisieren mit:

```bash
docker compose -f docker-compose.dev.yml pull
docker compose -f docker-compose.dev.yml up -d
```

Das CUDA-Dev-Image wird im GitHub-Workflow manuell gestartet und verwendet den Tag
`ghcr.io/skrockle/essentia-studio:dev-cuda`. Für ein Update des CUDA-Servers werden
beide Compose-Dateien ergänzt:

```bash
docker compose -f docker-compose.yml -f compose.cuda.yml -f compose.cuda.dev.yml pull
docker compose -f docker-compose.yml -f compose.cuda.yml -f compose.cuda.dev.yml up -d
```

Für produktive Nutzung bitte einen Release-Tag verwenden.

Für ein festes Rollback die `image:`-Zeile in einer lokalen Compose-Erweiterung
auf den gewünschten `vX.Y.Z-cpu`- oder `vX.Y.Z-cuda`-Tag setzen. Die Datenbank
bleibt im `/data`-Mount; Audiodateien und Playlists liegen im `/music`-Mount.

## Automatik, Watcher und Benchmark

Auf Linux nutzt die Automatik Dateisystemereignisse für neue und geänderte Titel.
Ist der Watcher deaktiviert oder meldet einen Fehler, wechselt die Anwendung auf den
in der GUI erklärten Zeitplan. Automatisches Tag-Schreiben bleibt standardmäßig aus.

Der Benchmark analysiert einen mindestens 60 Sekunden langen Titel isoliert und
schreibt keine Tags. Im CPU-Image gibt es nur eine CPU-Messung. Im CUDA-Image wird
CUDA nur bei einer tatsächlich sichtbaren NVIDIA-GPU verglichen; Meldungen über
fehlendes CUDA sind beim CPU-Betrieb unkritisch. GPU-Worker werden konservativ auf
sichtbare Geräte begrenzt. Der CUDA-Benchmark misst Batch 1, 2 und 4, während die
Analyse einen persistenten GPU-Prozess mit bounded Queue und separaten CPU-
Vorbereitungsworkern nutzt. Bei VRAM-Mangel wird automatisch auf kleinere Batches
zurückgefallen. Ein Ergebnis wird veraltet, sobald Ressourcen, Modelle oder
relevante Analyseoptionen nicht mehr zum gespeicherten Snapshot passen.
