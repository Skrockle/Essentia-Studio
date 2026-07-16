# Benchmark, Metadaten und Automatik

## Ziel

Essentia Studio soll die Mediathek verständlich darstellen, die sichere lokale
Parallelität anhand der tatsächlich zugewiesenen Ressourcen empfehlen und neue
oder veränderte Titel optional automatisch verarbeiten. Die Funktionen müssen
im CPU- und CUDA-Image, in Docker auf Linux und Windows sowie mit Apple
Container auf macOS vorhersehbar funktionieren.

Die Umsetzung umfasst drei zusammengehörige Funktionsblöcke:

1. Medienmetadaten und ein eindeutiger Verarbeitungsstatus pro Titel.
2. Ein manueller Benchmark für Worker-Empfehlung und CPU-/CUDA-Vergleich.
3. Eine konfigurierbare Automatik mit Watcher oder Zeitplan sowie eine
   dateibasierte, per Umgebungsvariablen überschreibbare Konfiguration.

## Leitlinien

- Analysieren und Schreiben bleiben getrennte Aktionen.
- Automatisches Schreiben ist eine ausdrückliche Opt-in-Option.
- Ein Benchmark übernimmt Einstellungen niemals selbstständig.
- Der Container-RAM ist maßgeblich, nicht der Arbeitsspeicher des Hosts.
- CUDA wird nur angeboten, wenn TensorFlow im laufenden Container tatsächlich
  eine GPU erkennt.
- Bestehende Analyse-, Schreib- und Undo-Daten bleiben erhalten.
- Plattformabhängige Dateisystemereignisse erhalten immer einen verständlichen
  Zeitplan-Fallback.

## 1. Medienbibliothek und Metadaten

### Gespeicherte Metadaten

`library_tracks` wird um folgende optionale Werte ergänzt:

- `artist`
- `title`
- `album`
- `duration_seconds`
- `metadata_source`

`metadata_source` enthält `embedded`, `filename`, `directory` oder `fallback`.
Der Scanner liest Metadaten nur lokal und verändert beim Scan keine Audiodatei.

### Auflösungsreihenfolge

Interpret und Titel werden deterministisch in dieser Reihenfolge bestimmt:

1. Eingebettete Tags über Mutagen (`artist`, `title`, optional `album`).
2. Dateinamensmuster wie `Interpret - 01 - Titel.ext` oder
   `Interpret - Titel.ext`; eine reine Tracknummer wird verworfen.
3. Ordnerstruktur `Interpret/Album/Datei.ext`; der erste relevante Ordner wird
   Interpret, der unmittelbar über der Datei liegende Albumordner wird Album.
4. `Unbekannter Interpret` und Dateiname ohne Endung als sicherer Fallback.

Eingebettete Tags haben immer Vorrang. Der Fallback ersetzt keine vorhandenen
gültigen Felder. Mehrwertige Künstler-Tags werden für die Anzeige lesbar
zusammengeführt, bleiben beim Tag-Schreiben aber im vorhandenen Formatadapter.

### Unterstützte Audioformate

Der Scanner behält die derzeit unterstützten Endungen bei:

`aac`, `aif`, `aiff`, `ape`, `dsf`, `flac`, `m4a`, `m4b`, `mp+`, `mp3`, `mp4`,
`mpc`, `oga`, `ogg`, `opus`, `wav`, `wma` und `wv`.

Eine akzeptierte Dateiendung garantiert nicht, dass eine beschädigte oder vom
lokalen Decoder nicht unterstützte Datei analysiert werden kann. Solche Dateien
erhalten einen sichtbaren Fehlerstatus, ohne den restlichen Scan abzubrechen.

### Verarbeitungsstatus

Der API-Status wird aus Bibliothek, letzter erfolgreicher Analyse und letztem
Schreibvorgang abgeleitet:

- `new`: noch keine erfolgreiche Analyse für den aktuellen Fingerprint.
- `current`: Analyse-Fingerprint und aktueller Datei-Fingerprint stimmen überein.
- `changed`: eine frühere Analyse existiert, die Datei hat sich danach geändert.
- `written`: der aktuelle Analyseentwurf wurde erfolgreich und verifiziert
  geschrieben.
- `failed`: der letzte passende Analyse- oder Schreibversuch ist fehlgeschlagen.

Für jeden Titel zeigt die Standard-Ergebnisansicht nur die neueste relevante
Analyse. Historische Jobs und Schreibvorgänge bleiben in „Jobs & Verlauf“
erhalten. Eine erneute Analyse desselben unveränderten Titels wird von der
Automatik übersprungen, kann aber weiterhin manuell erzwungen werden.

### Oberfläche

Bibliotheks- und Ergebnistabellen zeigen Interpret und Titel als primäre Spalten.
Album, Format, Verarbeitungsstatus und relativer Pfad sind sekundäre Angaben.
Die Suche berücksichtigt Interpret, Titel, Album und Pfad. Die getrennten
Auswahlen für Analyse und Tag-Schreiben bleiben erhalten.

## 2. Ressourcen- und Compute-Benchmark

### Bedienung

Der Benchmark befindet sich in den Einstellungen und wird nur durch den Button
„Benchmark starten“ ausgelöst. Während ein Analyse- oder Schreibjob aktiv ist,
ist der Start gesperrt. Das Ergebnis zeigt:

- verwendeten Beispieltitel und Ausschnitt,
- Container-RAM und verfügbare CPU-Kerne,
- Basisspeicher und gemessenen Worker-Spitzenverbrauch,
- Sekunden pro Audiominute für CPU und, falls verfügbar, CUDA,
- Initialisierungszeit je Compute-Modus,
- empfohlene Worker-Zahl und Begründung,
- Modellkennungen und Zeitpunkt der Messung.

„Empfehlung übernehmen“ ist eine separate Aktion. Sie ändert nur die
Worker-Einstellung und baut den Worker-Pool kontrolliert neu auf, sobald kein
Analysejob aktiv ist.

### Auswahl des Beispieltitels

Der Dienst sucht automatisch einen vorhandenen, lesbaren Titel mit mindestens
60 Sekunden Dauer. Bevorzugt wird der kürzeste geeignete Titel, damit der
Benchmark reproduzierbar und begrenzt bleibt. Gemessen wird ein fester
60-Sekunden-Ausschnitt. Ist kein geeigneter Titel vorhanden, endet der Benchmark
mit einer Handlungsanweisung statt mit einer leeren Messung.

### Messverfahren

Jeder Compute-Modus erhält einen Aufwärmlauf und zwei gemessene Läufe mit
demselben Titel, Ausschnitt, Modellstand und Analyseoptionen. Die Messung läuft
isoliert vom produktiven Worker-Pool und schreibt keine Analyseergebnisse oder
Tags.

Für CPU wird ein vollständig initialisierter Worker gemessen. Die Empfehlung
verwendet das cgroup-/Container-Speicherlimit, den gemessenen Basisspeicher und
den Spitzenverbrauch eines Workers. Vom nutzbaren Speicher werden 30 Prozent
Sicherheitsreserve abgezogen. Das Ergebnis wird zusätzlich durch die sichtbaren
CPU-Kerne und die konfigurierte Obergrenze beschränkt. Mindestens ein Worker
wird nur dann empfohlen, wenn der gemessene Lauf erfolgreich war.

Ein CPU-Image misst ausschließlich CPU. Ein CUDA-Image misst CUDA nur, wenn
TensorFlow eine GPU meldet. CPU und CUDA werden als Durchsatz und Verhältnis
angezeigt. GPU-Speicher wird separat ausgewiesen; freie Host-RAM-Kapazität führt
nicht automatisch zu mehreren GPU-Workern. Ohne belastbare Mehrfach-GPU-Messung
lautet die sichere CUDA-Empfehlung ein Worker pro sichtbarer GPU.

### Persistenz und Gültigkeit

Benchmark-Läufe werden in SQLite gespeichert. Ein Ergebnis gilt als veraltet,
wenn sich Container-RAM, CPU-/GPU-Geräte, Image-Variante, Modellkennungen oder
relevante Analyseoptionen ändern. Alte Ergebnisse bleiben vergleichbar, werden
aber nicht mehr als aktuelle Empfehlung angeboten.

Ein abgebrochener oder fehlgeschlagener Benchmark verändert keine Einstellung.
Speicherbedingte Worker-Abbrüche werden ausdrücklich als Ressourcenfehler
angezeigt und senken die mögliche Empfehlung.

## 3. Konfiguration und Automatik

### Konfigurationsquellen

Die kanonische, menschenlesbare Datei liegt unter `/data/settings.yaml`.
SQLite enthält danach keine veränderbaren Anwendungseinstellungen mehr, sondern
nur Bibliothek, Jobs, Ergebnisse, Benchmarks und Schreibverlauf.

Die Priorität lautet:

1. Umgebungsvariable
2. `/data/settings.yaml`
3. dokumentierter Standardwert

Die Migration liest bestehende Werte einmalig aus SQLite und erzeugt daraus
`settings.yaml`, sofern noch keine Datei vorhanden ist. Danach bleibt der alte
SQLite-Datensatz nur als Migrationsquelle und wird nicht mehr beschrieben.

Die Datei wird validiert und atomar über eine temporäre Datei plus Umbenennung
geschrieben. Bei ungültigem YAML oder ungültigen Werten startet die API mit
einer präzisen Konfigurationsdiagnose; die bestehende Datei wird nicht
automatisch überschrieben.

### Umgebungsvariablen

Alle GUI-Einstellungen erhalten eine dokumentierte ENV-Entsprechung, darunter:

- `ESSENTIA_ANALYSIS_WORKERS`
- `ESSENTIA_MAX_AUDIO_SECONDS`
- `ESSENTIA_COMPUTE`
- `ESSENTIA_AUTOMATION_ENABLED`
- `ESSENTIA_AUTOMATION_WATCHER`
- `ESSENTIA_AUTOMATION_SCHEDULE`
- `ESSENTIA_AUTOMATION_WRITE_TAGS`
- `ESSENTIA_BENCHMARK_MINIMUM_TRACK_SECONDS`
- `ESSENTIA_BENCHMARK_SAFETY_MARGIN_PERCENT`

Die Settings-API liefert neben dem effektiven Wert dessen Quelle. Ein per ENV
gesetztes Feld ist in der GUI sichtbar, mit „Durch Umgebungsvariable festgelegt“
markiert und nicht editierbar. Nicht per ENV gesetzte Felder bleiben über die
GUI änderbar.

### Automatikmodi

Beim Aktivieren wählt der Benutzer ausdrücklich:

- `analyze`: automatisch analysieren, Entwürfe manuell prüfen und schreiben.
- `analyze_and_write`: automatisch analysieren und erfolgreiche Entwürfe direkt
  schreiben.

Automatisches Schreiben ist standardmäßig aus. Jeder automatische
Schreibvorgang verwendet dieselbe Vorschau-, Verifikations- und Undo-Infrastruktur
wie ein manueller Vorgang und wird im Verlauf als automatisch ausgelöst markiert.

### Watcher und Zeitplan

Die GUI besitzt den Toggle „Dateiüberwachung“:

- Ein: Der Dienst beobachtet den Musik-Mount, bündelt Ereignisse und verarbeitet
  eine Datei erst, nachdem Größe und Änderungszeit für die Ruhezeit stabil sind.
- Aus: Der Bereich „Zeitplan“ öffnet sich automatisch.

Der Watcher prüft seine Funktionsfähigkeit praktisch auf dem Mount. Der
Container läuft unabhängig vom Host immer unter Linux; eine Betriebssystemabfrage
allein ist deshalb nicht ausreichend. Kommen Bind-Mount-Ereignisse nicht
zuverlässig an, zeigt die GUI eine Warnung, deaktiviert den Watcher und öffnet
die Zeitplaneinstellung.

Die verständliche Zeitplan-GUI bietet Intervalle, Uhrzeiten und Wochentage.
Ein optionaler Bereich „Erweitert“ akzeptiert einen Cron-Ausdruck und zeigt
dessen lesbare Bedeutung sowie die nächsten Ausführungszeiten. Der gespeicherte
Zeitplan verwendet die konfigurierte Zeitzone, standardmäßig die lokale
Container-Zeitzone.

Watcher- und Zeitplan-Auslöser laufen durch dieselbe deduplizierende Pipeline:

1. Bibliothek scannen und Metadaten aktualisieren.
2. Nur `new` und `changed` auswählen.
3. Bereits laufende oder bereits eingeplante Fingerprints überspringen.
4. Analysejob mit unveränderlichem Konfigurationssnapshot starten.
5. Im Schreibmodus nur erfolgreiche aktuelle Ergebnisse schreiben.
6. Erfolg oder Fehler pro Datei protokollieren.

Mehrere Ereignisse oder ein gleichzeitig fälliger Zeitplan dürfen für denselben
Fingerprint höchstens einen Analysejob erzeugen.

## API und Komponenten

Die Umsetzung wird in klar getrennte Dienste aufgeteilt:

- `MetadataService`: Tags, Dauer und Fallback-Metadaten lesen.
- `TrackStateService`: Status aus Fingerprints, Analysen und Schreibvorgängen
  ableiten.
- `SettingsService`: YAML laden, ENV überlagern, Quellen melden und atomar
  speichern.
- `BenchmarkService`: Beispiel auswählen, isolierte Messungen ausführen und
  Empfehlungen berechnen.
- `AutomationService`: Watcher, Zeitplan, Ruhezeit und Deduplizierung steuern.
- `WorkerPoolManager`: Pool anhand effektiver Einstellungen sicher neu aufbauen.

Neue API-Flächen:

- `GET /api/settings` liefert effektive Werte und Quellen.
- `PUT /api/settings` schreibt ausschließlich nicht gesperrte YAML-Werte.
- `POST /api/benchmarks` startet einen manuellen Benchmark.
- `GET /api/benchmarks` listet Läufe und markiert den aktuellen Lauf.
- `POST /api/benchmarks/{id}/apply` übernimmt eine gültige Empfehlung.
- `GET /api/automation/status` liefert Modus, Watcher-Zustand, nächsten Lauf und
  letzte Ausführung.
- Bibliotheks- und Ergebnisantworten enthalten Metadaten und Verarbeitungsstatus.

Benchmarks verwenden das vorhandene Jobmodell oder ein kompatibles
Job-Untermodell, damit Fortschritt, Abbruch und terminale Zustände einheitlich
bleiben. Die Oberfläche darf `completed_with_errors` nie als erfolgreichen
Abschluss darstellen.

## Fehlerbehandlung

- Fehler einzelner Audiodateien brechen einen Batch nicht ab.
- Worker-Abstürze werden mit der betroffenen Datei und dem technischen Grund
  gespeichert; ein beschädigter Prozesspool wird vor dem nächsten Job neu
  erstellt.
- OOM-nahe Benchmark-Ergebnisse werden nicht als Empfehlung angeboten.
- Ein nicht funktionsfähiger Watcher fällt sichtbar auf den Zeitplan zurück.
- Ein fehlerhafter Cron-Ausdruck kann nicht gespeichert werden.
- Automatisches Schreiben stoppt für eine Datei bei Fingerprint-Konflikt und
  überschreibt keine zwischenzeitlich geänderten Tags.
- Ungültige ENV-Werte verhindern einen mehrdeutigen Start und nennen den
  Variablennamen sowie den erwarteten Wertebereich.

## Tests und Verifikation

### Backend

- Metadaten aus Tags, Dateinamen, Ordnern und Fallbacks.
- Dauerermittlung und Fehler bei beschädigten Dateien.
- Statusableitung für neue, aktuelle, veränderte, geschriebene und
  fehlgeschlagene Titel.
- Deduplizierung der neuesten Ergebnisansicht.
- YAML-Migration, atomisches Schreiben, Validierung und ENV-Priorität.
- Worker-Empfehlung mit Containerlimit, Reserve und CPU-Grenze.
- Benchmark-Abbruch und Ressourcenfehler ohne Einstellungsänderung.
- CPU-/CUDA-Auswahl mit und ohne sichtbare GPU.
- Watcher-Ruhezeit, Zeitplan und Deduplizierung konkurrierender Auslöser.
- Automatischer Analysemodus und ausdrücklich aktivierter Schreibmodus.

### Frontend

- Interpret-/Titelanzeige und Suche.
- Statusdarstellung und sichtbare Dateifehler.
- Benchmark starten, Fortschritt anzeigen und Empfehlung ausdrücklich
  übernehmen.
- CPU-only- und CPU/CUDA-Ergebnisdarstellung.
- ENV-gesperrte Settings-Felder.
- Watcher-Toggle öffnet bei „Aus“ den Zeitplan.
- Verständlicher Zeitplan sowie erweiterte Cron-Validierung.
- `completed_with_errors` erzeugt eine Warnung statt „Analyse abgeschlossen“.

### Plattform und Container

- CPU-Image-Smoke mit begrenztem RAM und echtem 60-Sekunden-Fixture.
- CUDA-Smoke auf einem NVIDIA-Runner; ohne GPU wird der Vergleich sauber
  ausgelassen.
- Linux-Watcher-Integration auf einem nativen Bind-Mount.
- Zeitplan-Fallback als plattformneutrale Standardverifikation für macOS,
  Windows und Linux.
- Dokumentierte Mindestempfehlung von 4 GB Container-RAM für reale CPU-Inferenz;
  der Benchmark ersetzt diese Startvoraussetzung nicht.

## Nicht im Umfang

- Verteilte Worker über mehrere Hosts.
- Unterstützung anderer GPU-Plattformen als NVIDIA CUDA.
- Automatisches Löschen historischer Jobs, Analysen oder Benchmarks.
- Unbeaufsichtigte Änderung der Worker-Zahl ohne Benutzerbestätigung.
- Internetbasierte Metadatenanreicherung.
