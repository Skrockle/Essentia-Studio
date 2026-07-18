# Essentia Studio

Essentia Studio analysiert eine lokal eingebundene Musikmediathek auf Genres und
Moods, zeigt alle Vorschläge vor dem Schreiben und verwaltet vollständige
Navidrome Smart Playlists. Die Weboberfläche ist für ein vertrauenswürdiges
lokales Netz gedacht: Es gibt bewusst **kein Login**.

> **Lizenzhinweis:** Die Anwendung ist MIT-lizenziert. Essentia ist AGPL-3.0.
> Die mitgelieferten vortrainierten Modelle stehen unter **CC BY-NC-ND 4.0** und
> dürfen nur **nichtkommerziell** genutzt werden. Details: [docs/licenses.md](docs/licenses.md).

## Funktionsumfang

- lokale Audioanalyse mit 400 Discogs-Genres und MTG-Jamendo-Moods
- CPU-Image als Standard, separates NVIDIA CUDA Image mit CPU-Fallback
- Vorschau jeder Änderung vor dem Schreiben
- Filter, Multi-Select und „Alle auswählen“ über die gesamte Ergebnismenge
- Genres und Moods manuell hinzufügen oder entfernen
- formatgerechte Tags für MP3, FLAC, Ogg/Opus, MP4/M4A, WMA/ASF, AIFF und WAV
- Konflikterkennung, Schreibprüfung und **Tags wiederherstellen**
- vollständiger Katalog aus dem Navidrome Smart Playlist Generator:
  298 Presets, 111 Felder, 20 „This is“-Methoden und verschachtelte UND/ODER-Regeln
- persistente Jobs, Historie, Einstellungen und Playlists in SQLite

## Schnellstart mit Docker Compose (CPU)

Die Audiodateien werden über `/music` eingebunden. Datenbank und Zustand liegen
unter `/data`. Der `/music`-Mount muss schreibbar sein, wenn Tags oder `.nsp`-Dateien
gespeichert werden sollen.

```bash
docker login ghcr.io
export MUSIC_DIR="$HOME/Music"
export DATA_DIR="$HOME/essentia-studio/data"
mkdir -p "$DATA_DIR"
docker compose up -d
```

Danach `http://localhost:8080` öffnen. Für Zugriff aus dem LAN bindet die
Standardkonfiguration an `0.0.0.0:8080`. Da es kein Login gibt, den Port niemals
über den Router ins Internet freigeben.

## NVIDIA CUDA

Die CUDA-Variante ist explizit und ersetzt das CPU-Image nicht:

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
docker compose -f docker-compose.yml -f compose.cuda.yml up -d
```

Ohne sichtbare NVIDIA-GPU fällt das CUDA-Image bei „Automatisch“ auf CPU zurück.
Bei expliziter CUDA-Auswahl wird ein fehlendes Gerät als Fehler gemeldet.

## Unterstützte Hosts

- [Apple Container](docs/deployment/apple-container.md): CPU mit `--arch amd64`
- [Linux und Docker Compose](docs/deployment/linux-docker.md): CPU oder NVIDIA CUDA
- [Windows 11, Docker Desktop und WSL2](docs/deployment/windows.md): Entwicklung und Betrieb,
  einschließlich NVIDIA GPU-PV

## Arbeitsablauf

1. Unter „Analyse“ die Mediathek scannen und Genres, Moods oder beides analysieren.
2. Ergebnisse filtern, einzelne oder alle Treffer auswählen.
3. Genres/Moods direkt bearbeiten oder über die Sammelaktion ergänzen.
4. „Schreibvorschau“ öffnen und alte/neue Tags sowie Konflikte prüfen.
5. Nur bestätigte Zeilen schreiben. Die Historie enthält den geprüften Rückweg über
   „Tags wiederherstellen“.

Smart Playlists können aus Presets, einem „This is“-Assistenten oder vollständig
eigenen, verschachtelten Regeln erzeugt werden. Essentia Studio schreibt die
`.nsp`-Dateien atomar in `${MUSIC_DIR}/SmartPlaylists`.

## Einstellungen

Die Oberfläche zeigt den aktiven Image-Typ, sichtbare Rechenarten, alle geladenen
Modelle und den Zustand der Mounts. Analysegrenzen, Worker-Zahl und Schreibverhalten
werden unter `/data` gespeichert. CPU ist die sichere Standardeinstellung.

## Updates und Rollback

```bash
docker compose pull
docker compose up -d
```

Für den aktuellen Entwicklungsstand gibt es ein separates CPU-Image. Es wird
bei jedem Push auf `main` automatisch nach GHCR veröffentlicht und überschreibt
keine Release-Tags:

```bash
docker compose -f docker-compose.dev.yml pull
docker compose -f docker-compose.dev.yml up -d
```

Das CUDA-Dev-Image wird im GitHub-Workflow manuell über „Run workflow“ mit der
Variante `cuda` oder `both` gebaut und ist anschließend unter
`ghcr.io/skrockle/essentia-studio:dev-cuda` verfügbar. Für einen stabilen Betrieb
weiterhin `latest-cpu` oder einen festen Release-Tag verwenden.

Releases veröffentlichen unveränderliche Tags wie `v1.2.3-cpu` und
`v1.2.3-cuda`. Für ein Rollback wird in einer lokalen Compose-Erweiterung ein
solcher Tag fest eingetragen; `/data` und `/music` bleiben erhalten.

Status prüfen:

```bash
curl --fail http://127.0.0.1:8080/health
curl --fail http://127.0.0.1:8080/api/capabilities
```

## Lokale Entwicklung

Python 3.10 und Node.js 24 sind auf macOS, Linux sowie Windows/WSL2 der gemeinsame
Entwicklungsvertrag.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm --prefix frontend ci
python scripts/verify.py
python scripts/dev.py all
```

Unter PowerShell verwendet `scripts/dev.py` automatisch `npm.cmd`. Weitere Hinweise
stehen in [docs/development.md](docs/development.md). Regeln für Menschen und
KI-Agenten stehen in [AGENTS.md](AGENTS.md); `CLAUDE.md`, `GEMINI.md`, Copilot,
Cursor und Windsurf verweisen auf denselben kanonischen Vertrag.

## Herkunft und Lizenzen

Essentia Studio führt zwei Projekte zusammen:

- [WB2024/Essentia-to-Metadata](https://github.com/WB2024/Essentia-to-Metadata)
- [WB2024/Navidrome-SmartPlaylist-Generator-nsp](https://github.com/WB2024/Navidrome-SmartPlaylist-Generator-nsp)

Die importierte Playlist-Logik bleibt unter MIT; das vollständige Verzeichnis und
die Modellbedingungen stehen in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Ein kontrolliertes Update von Upstreams beschreibt [docs/upstream-sync.md](docs/upstream-sync.md).

## Fehlerbehebung

- „Mount fehlt“: absolute Hostpfade verwenden und Verzeichnisse vorher anlegen.
- „Nur lesen“: UID/GID 10001 Schreibzugriff auf `/data` und bei Tag-Schreiben auf
  `/music` geben.
- CUDA nicht auswählbar: `nvidia-smi` im Container prüfen und CUDA-Compose-Datei nutzen.
- Modell fehlt: unverändertes Release-Image erneut ziehen; zur Laufzeit werden keine
  ungeprüften Modelle nachgeladen.
