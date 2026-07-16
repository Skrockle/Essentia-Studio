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

Für ein festes Rollback die `image:`-Zeile in einer lokalen Compose-Erweiterung
auf den gewünschten `vX.Y.Z-cpu`- oder `vX.Y.Z-cuda`-Tag setzen. Die Datenbank
bleibt im `/data`-Mount; Audiodateien und Playlists liegen im `/music`-Mount.
