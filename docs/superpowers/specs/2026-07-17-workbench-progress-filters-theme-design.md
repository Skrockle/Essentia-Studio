# Workbench-Fortschritt, Filter und Theme

## Ziel

Essentia Studio soll lange Analyse- und Schreibvorgänge nachvollziehbar darstellen,
Tabellen anpassbar machen und in einem dauerhaft gewählten hellen oder dunklen Theme
bedienbar sein. Vollständig und verifiziert geschriebene Titel werden bei späteren
Scans weiterhin erfasst, aber in der Analyseauswahl standardmäßig ausgeblendet.

## Festgestellter Ausgangszustand

- Analysejobs liefern bereits Live-Ereignisse mit Gesamtzahl, erledigten und
  fehlgeschlagenen Einträgen. Die Workbench zeigt davon bisher nur „Analyse läuft …“.
- Die zuletzt gestarteten lokalen Analysejobs mit einem beziehungsweise zwei Titeln
  wurden erfolgreich abgeschlossen. Ein älterer Job mit 222 Titeln scheiterte nach
  dem Abbruch des Prozesspools; dieser Zustand bleibt korrekt in der Datenbank erhalten.
- Schreibvorgänge laufen synchron in einem HTTP-Aufruf und können deshalb nur den
  unbestimmten Text „Schreibe …“ anzeigen.
- Interpret und Titel werden aus eingebetteten Metadaten beziehungsweise dem
  Dateinamen korrekt getrennt. Der Dateipfad wird zusätzlich in der Titelzelle
  gerendert und soll in eine eigene Spalte wechseln.
- Der primäre Bestätigungsbutton ist im Schreibdialog wegen zu geringem Kontrast
  nicht zuverlässig lesbar.

## Workbench-Ansicht

### Fortschritt

Ein gemeinsamer Fortschrittsbaustein stellt Scan-, Analyse- und Schreibjobs dar. Für
Analyse und Schreiben zeigt er:

- einen determinierten Fortschrittsbalken,
- Prozentwert und „X von Y verarbeitet“,
- Anzahl erfolgreicher und fehlgeschlagener Einträge,
- einen eindeutigen laufenden Zustand,
- eine Abschlussmeldung und bei Fehlern eine verständliche Zusammenfassung.

Die Workbench übernimmt `completed_items`, `total_items` und `failed_items` direkt
aus den vorhandenen Server-Sent Events. Ein Ereignis aktualisiert die Anzeige, ohne
die Auswahl- oder Filteransicht zurückzusetzen.

### Schreibjobs

`POST /api/writes/jobs` löst die bisherige synchrone Batch-Schreiboperation für das
Webinterface ab und liefert einen regulären Job zurück. Jeder aufgelöste Result-Datensatz
ist ein Job-Eintrag. Der vorhandene `JobCoordinator` verarbeitet Schreibjobs seriell,
damit eine große Mediathek keine parallelen Dateischreibzugriffe erzeugt.

Der Handler ruft weiterhin `TagOperationService.write_one` auf. Verifizierte Writes
gelten als erfolgreich. Konflikte und fehlgeschlagene Operationen werden als
fehlgeschlagene Job-Einträge gezählt. Die bestehenden atomaren Snapshots und Undo-
Informationen bleiben unverändert.

Ein schreibgeschützter Job-Detail-Endpunkt liefert pro Eintrag Wert, Status, Ergebnis
und Fehler. Der Dialog verwendet ihn nach dem Terminal-Ereignis für die konkrete
Dateiliste. Die bisherige synchrone Route kann für Kompatibilität bestehen bleiben,
wird vom neuen Webinterface aber nicht mehr verwendet.

Der Dialog bleibt während des Jobs geöffnet. Abbrechen schließt ihn vor dem Start;
nach ausdrücklicher Bestätigung ist Schließen weiterhin möglich, beendet den Job aber
nicht. Beim erneuten Öffnen der Jobansicht bleibt der Fortschritt über den globalen
Jobverlauf nachvollziehbar.

### Filter und Spalten

Die gescannte Bibliothek erhält eine kompakte Ansichtsleiste mit:

- Volltextsuche,
- Statusfilter für Neu, Verändert, Analysiert, Geschrieben und Fehler,
- Formatfilter aus den tatsächlich vorhandenen Audioformaten,
- einem expliziten Schalter „Vollständig geschriebene anzeigen“,
- einer Spaltenauswahl.

Die Standardansicht blendet `written` aus. `current` bleibt sichtbar, weil erfolgreich
analysierte, aber noch nicht verifiziert geschriebene Titel weiter bearbeitet werden
sollen. `new`, `changed` und `failed` bleiben ebenfalls sichtbar. Ein neuer Scan löscht
keine Daten und verändert diese Voreinstellung nicht.

Die Bibliothek bietet die Spalten Auswahl, Interpret, Titel, Datei, Album, Format und
Status. Die Ergebnisansicht bietet Auswahl, Interpret, Titel, Datei, Genres, Moods und
Status. Auswahl bleibt immer sichtbar; alle übrigen fachlichen Spalten können ein-
oder ausgeblendet werden. Der Pfad steht ausschließlich in „Datei“ und nicht mehr
unter dem Titel.

Filter gelten vor „Alle auswählen“, sodass nur die sichtbare Ergebnismenge ausgewählt
wird. Eine leere Filtermenge zeigt einen erklärenden Leerzustand und eine Möglichkeit,
die Filter zurückzusetzen.

## Persistente UI-Präferenzen

Theme, Filter und Spaltensichtbarkeit werden als versioniertes JSON unter getrennten
`localStorage`-Schlüsseln gespeichert. Der Code validiert geladene Werte gegen bekannte
Themes, Stati, Formate und Spalten. Unbekannte oder beschädigte Werte werden ignoriert
und durch sichere Standardwerte ersetzt. Serverweite Analyse-, Automatik- und Pfadwerte
bleiben weiterhin in YAML beziehungsweise Umgebungsvariablen; Browserpräferenzen werden
nicht mit ihnen vermischt.

## Theme und Kontrast

Die Navigation bietet die Auswahl System, Hell und Dunkel. Ohne gespeicherte Auswahl
folgt die Anwendung `prefers-color-scheme`; eine explizite Auswahl hat Vorrang. Der
Wechsel erfolgt ohne Neuladen.

Alle Oberflächenfarben werden über semantische CSS-Variablen definiert. Beide Themes
decken Hintergrund, Panels, Text, Sekundärtext, Rahmen, Eingabefelder, Tabellen,
Overlays, Tags, Statusanzeigen sowie primäre und sekundäre Buttons ab. Der Text des
primären Buttons erhält in Normal-, Hover-, Focus- und Disabled-Zuständen ausreichenden
Kontrast. Sichtbare Fokusrahmen und `color-scheme` unterstützen Tastaturbedienung und
native Controls.

## Erklärungen und Modellnamen

`SettingField` unterstützt eine optionale Erklärung. Ein kleines Info-Steuerelement
hinter dem Label ist per Maus, Tastaturfokus und Klick erreichbar und über eine
ARIA-Beziehung mit seinem Hilfetext verbunden. Erklärungen werden mindestens für
folgende Werte angeboten:

- Worker: gleichzeitige Analyseprozesse und RAM-Auswirkung,
- maximale Audiolänge: höchstens analysierter Ausschnitt pro Titel,
- Anzahl Genres: maximale Zahl zurückgegebener Genre-Vorschläge,
- Genre-Schwelle: minimale Modellwahrscheinlichkeit; höhere Werte liefern weniger,
  typischerweise sicherere Vorschläge,
- Mood-Schwelle: entsprechende Mindestwahrscheinlichkeit für Mood-Vorschläge.

Die Modellübersicht gruppiert den Bestand nach Rolle und zeigt verständliche Namen:

- Klangmerkmale (Discogs EffNet),
- Genre-Erkennung (Discogs 400),
- Mood-Erkennung (MTG Jamendo),
- zugehörige Labelkataloge als technische Zusatzinformation.

Rohdateinamen und Prüfsummen bleiben in einem aufklappbaren Detailbereich verfügbar,
sind aber nicht mehr die primäre Beschreibung.

## Fehlerbehandlung

- Ein unterbrochener Event-Stream lässt den Job nicht verschwinden. Die UI fragt den
  Jobstatus erneut ab und zeigt bei weiter bestehender Verbindungslosigkeit einen
  konkreten Hinweis.
- Teilweise fehlgeschlagene Jobs zeigen sowohl erfolgreiche als auch fehlgeschlagene
  Zahlen und werden niemals als pauschaler Erfolg bezeichnet.
- Schreibfehler enthalten den relativen Dateipfad und den vom Backend normalisierten
  Fehlertext; technische Tracebacks erscheinen nicht in der Workbench.
- Ein beschädigter Browserpräferenzwert blockiert die Anwendung nicht.
- Filter ändern keine Datenbank- oder Dateiinhalte.

## Tests und Abnahme

Die Implementierung folgt Test-Driven Development. Vor Produktivcode werden mindestens
folgende fehlschlagende Tests ergänzt:

- Analysefortschritt aktualisiert Prozent, Zähler und Fehlerzahl aus Events.
- Ein verifizierter Write-Job liefert Fortschritt und Einzelergebnisse; Konflikte und
  Fehler werden korrekt gezählt.
- Geschriebene Titel sind standardmäßig ausgeblendet und explizit wieder einblendbar.
- „Alle auswählen“ bezieht sich nur auf gefilterte Titel.
- Spaltenauswahl, Filter und Theme überleben ein erneutes Rendern aus `localStorage`.
- Ungültige gespeicherte Präferenzen fallen auf Defaults zurück.
- Der Dateipfad erscheint in einer eigenen Spalte und nicht in der Titelzelle.
- Erklärungen sind per Tastatur erreichbar und Modellnamen sind verständlich.

Danach laufen Backend-, Frontend-, Lint-, TypeScript-, Produktions-Build- und Browser-
Tests. Die visuelle Browserabnahme prüft Hell, Dunkel, Desktop und schmale Ansicht,
Dialogkontrast, Fokusführung, Filter, Spalten, Analysefortschritt, Schreibfortschritt,
Console und fehlgeschlagene Netzwerkaufrufe.

Zum Schluss wird das lokale `linux/amd64`-CPU-Image neu gebaut. Der bestehende Apple-
Container auf Port 8090 wird mit den unveränderten `/music`- und `/data`-Mounts ersetzt
und der vollständige Ablauf mit realen Audiodateien überprüft.
