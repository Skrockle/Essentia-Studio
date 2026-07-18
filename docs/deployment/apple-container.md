# Apple Container (macOS)

Essentia Studio wird als `linux/amd64`-Image veröffentlicht. Apple Container führt
die CPU-Variante auf Apple Silicon deshalb mit `--arch amd64` aus. CUDA steht auf
dem Mac nicht zur Verfügung.

```bash
mkdir -p "$HOME/EssentiaStudio/data"
chmod 0777 "$HOME/EssentiaStudio/data"
container registry login ghcr.io
container run --arch amd64 --rm -d --name essentia-studio \
  --memory 4g \
  -p 127.0.0.1:8080:8000 \
  --volume "$HOME/Music:/music" \
  --volume "$HOME/EssentiaStudio/data:/data" \
  ghcr.io/skrockle/essentia-studio:latest-cpu
```

Zum Schreiben von Tags und Smart Playlists muss auch der Musikordner für die
Container-UID 10001 schreibbar sein. Wer nur analysieren möchte, kann den
Musik-Mount schreibgeschützt lassen; Schreibaktionen bleiben dann deaktiviert.

Für andere Geräte im lokalen Netz kann die Bind-Adresse auf `0.0.0.0` geändert
werden. Es gibt absichtlich kein Login; Port 8080 darf daher nicht ins Internet
weitergeleitet werden.

```bash
container run --arch amd64 --rm -d --name essentia-studio \
  --memory 4g \
  -p 0.0.0.0:8080:8000 \
  --volume "/ABSOLUTER/PFAD/ZUR/MUSIK:/music" \
  --volume "/ABSOLUTER/PFAD/ZU/DATEN:/data" \
  ghcr.io/skrockle/essentia-studio:latest-cpu
```

Status und Logs:

```bash
curl --fail http://127.0.0.1:8080/health
container logs essentia-studio
container stop essentia-studio
```

## Automatik und Benchmark

Für Modelle und parallele Worker sollte der Container zunächst **4 GB** RAM erhalten.
Der Ressourcen-Benchmark unter „Einstellungen“ misst im CPU-Modus einen automatisch
gewählten Titel mit mindestens 60 Sekunden Länge. Er zieht standardmäßig 30 Prozent
Reserve ab und übernimmt seine Empfehlung erst nach Bestätigung. Ändern sich RAM,
Modelle oder Analyseoptionen, wird das gespeicherte Ergebnis als veraltet markiert.
CUDA-Warnungen sind auf dem Mac normal, weil Apple Container keine NVIDIA-GPU
durchreicht; das CPU-Image versucht CUDA gar nicht erst zu messen.

Die Dateiüberwachung funktioniert bei nativen macOS-Bind-Mounts in der Regel direkt.
Falls keine zuverlässigen Dateisystemereignisse ankommen, Watcher in der GUI
ausschalten; dadurch öffnet sich automatisch die Zeitplan-Einstellung. Alle Werte
werden in `/data/settings.yaml` gespeichert oder können über die im README genannten
ENV-Variablen fest vorgegeben werden.
