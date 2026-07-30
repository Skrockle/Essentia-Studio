# Fehlende Genre- und Mood-Tags gezielt analysieren

**Status:** Approved design

**Datum:** 2026-07-30

## Ziel

Essentia Studio soll rechenintensive Analysen auf Titel beschränken, deren Musikdateien tatsächlich keine Genre- oder Mood-Tags enthalten. Analysevorschläge und bearbeitbare Entwürfe gelten nicht als vorhandene Datei-Tags.

Der Anwender kann die Bibliothek schnell nach fehlenden Genres und fehlenden Moods filtern, die gesamte gefilterte Ergebnismenge auswählen und nur die jeweils fehlenden Informationen berechnen lassen. Bereits vorhandene verwaltete Tags bleiben unverändert.

## Begriffe und Semantik

- **Vorhandenes Genre oder Mood:** Ein nicht leerer verwalteter Tag-Wert, der aus der Musikdatei gelesen wurde.
- **Ohne Genre:** Die zuletzt gelesene Liste der Genre-Tags der Datei ist leer.
- **Ohne Mood:** Die zuletzt gelesene Liste der Mood-Tags der Datei ist leer.
- **Unvollständiger Titel:** Mindestens eine der beiden Listen ist leer.
- **Vollständiger Titel:** Genre- und Mood-Liste enthalten jeweils mindestens einen Wert.

Die Schnellfilter arbeiten auf dem gespeicherten Stand des letzten Bibliotheks-Scans beziehungsweise einer neueren verifizierten Schreib- oder Undo-Operation. Direkt vor dem Start einer Analyse wird der aktuelle Datei-Zustand nochmals geprüft.

## Bedienung

Die Bibliotheksansicht erhält zwei direkt erreichbare Schnellfilter:

- `Ohne Genre`
- `Ohne Mood`

Ein einzelner aktiver Filter zeigt Titel mit dem entsprechenden fehlenden Datei-Tag. Sind beide Filter aktiv, wird die Vereinigungsmenge angezeigt: alle Titel, denen Genre oder Mood oder beides fehlt. Diese Oder-Verknüpfung unterstützt das Ziel, alle unvollständigen Titel in einem Arbeitsgang zu finden.

Die vorhandene Suche und die weiteren Bibliotheksfilter bleiben kombinierbar. Auswahlzähler und `Alle auswählen` beziehen sich auf die vollständige serverseitig gefilterte Ergebnismenge und nicht nur auf die aktuell geladene Seite.

Vollständige Titel können nicht für eine Genre-/Mood-Analyse eingeplant werden. Wenn sich der Datei-Zustand seit dem Scan geändert hat und ein Titel inzwischen vollständig ist, wird er vor der Analyse ausgeschlossen und der Anwender erhält eine verständliche deutsche Statusmeldung.

## Datenmodell und Scan

Der Bibliotheks-Scan liest neben Identitätsmetadaten auch die vom bestehenden Mutagen-Adapter verwalteten Genre- und Mood-Werte. Der Scan bleibt strikt lesend.

Die gelesenen Werte werden als normalisierte JSON-Listen am Bibliothekstitel persistiert. Die Werte und nicht nur Wahrheitswerte werden gespeichert, weil sie für die sichere Vorbelegung von Entwürfen, Schreibvorschauen und spätere Aktualisierungen benötigt werden.

Ein Lesefehler darf nicht als sicher festgestellter leerer Tag-Bestand behandelt werden. Der Titel erhält stattdessen einen stabilen Fehlerzustand für die Tag-Bestandsaufnahme und wird nicht automatisch zur Analyse zugelassen. Ein Fehler bei einem Titel stoppt den restlichen Scan nicht.

## API und Repository-Abfragen

Die Bibliotheksabfrage erhält typisierte Filter für fehlende Genres und Moods. Die Repository-Abfrage setzt die gemeinsame Oder-Semantik um, wenn beide Filter aktiv sind. Dieselbe Filterdefinition wird für query-basierte Auswahl und die Analyseanforderung verwendet, damit sichtbare Menge, Zähler und tatsächlich eingeplante Titel übereinstimmen.

Die Analyse-API akzeptiert weiterhin explizite Titel-IDs oder eine Bibliotheksabfrage. Vor dem Anlegen der Job-Elemente liest sie für die ausgewählten Titel die verwalteten Datei-Tags erneut. Vollständige Titel werden nicht eingeplant. Ist danach kein Titel analysierbar, antwortet die API mit einem stabilen Fehlercode und einer deutschen Erklärung.

## Adaptive Analyse

Für jedes Job-Element wird unveränderlich festgehalten, welche Analysebereiche beim Vorabcheck fehlten:

| Datei-Zustand | Genre-Erkennung | Mood-Erkennung |
|---|---:|---:|
| Genre fehlt, Mood vorhanden | ja | nein |
| Genre vorhanden, Mood fehlt | nein | ja |
| Genre und Mood fehlen | ja | ja |
| Genre und Mood vorhanden | nicht einplanen | nicht einplanen |

Der gemeinsame Audio-Embedding-Schritt wird nur für eingeplante Titel ausgeführt. Nicht benötigte Klassifikationsköpfe werden pro Titel beziehungsweise pro gleichartiger Batch-Gruppe ausgelassen. Die festgehaltene Auswahl verhindert, dass eine spätere Datenbankänderung die Bedeutung eines laufenden Jobs verändert.

## Entwürfe und Schreiben

Der erzeugte Entwurf kombiniert vorhandene Datei-Tags mit Vorschlägen ausschließlich für die zuvor fehlenden Bereiche:

- vorhandene Genres oder Moods werden unverändert übernommen;
- nur fehlende Bereiche erhalten Analysevorschläge;
- manuelle Bearbeitung bleibt wie bisher möglich.

Dadurch enthält die Schreibvorschau den vollständigen beabsichtigten Zustand und ein aktiviertes Überschreiben kann keinen bereits vorhandenen, nicht analysierten Bereich versehentlich leeren.

Nach einem verifizierten Schreibvorgang aktualisiert der Tag-Service den gespeicherten Datei-Tag-Bestand mit den tatsächlich zurückgelesenen Werten. Nach einem verifizierten Undo wird entsprechend der wiederhergestellte Snapshot gespeichert. Fehlgeschlagene oder nicht verifizierte Operationen dürfen den gespeicherten Ist-Zustand nicht als erfolgreich verändert markieren.

## Fehler- und Konsistenzverhalten

- Externe Dateiänderungen werden spätestens beim nächsten Scan erkannt.
- Der Vorabcheck vor der Analyse verhindert unnötige Verarbeitung, wenn Tags nach dem letzten Scan ergänzt wurden.
- Bestehende Fingerprint- und Pfadschutzregeln bleiben verbindlich.
- Tag-Lesefehler, geänderte Dateien und nicht mehr vorhandene Titel werden pro Titel behandelt und stoppen andere Titel nicht.
- Benutzertexte sind deutsch; API-Fehler behalten stabile maschinenlesbare Codes.

## Verifikation

Die Umsetzung wird testgetrieben durch folgende Nachweise abgesichert:

1. Der Scan erfasst tatsächliche Genre- und Mood-Werte für die unterstützten Formatfamilien und bleibt read-only.
2. Tag-Lesefehler werden nicht als leere Tags fehlklassifiziert.
3. `Ohne Genre`, `Ohne Mood` und deren Oder-Kombination liefern korrekte Mengen und Zähler.
4. Query-basierte Auswahl erfasst alle gefilterten Titel über Seitengrenzen hinweg.
5. Die Analyse-API schließt vollständige Titel serverseitig aus.
6. Pro Titel werden nur die fehlenden Klassifikationsköpfe ausgeführt.
7. Entwürfe behalten vorhandene Datei-Tags und ergänzen nur fehlende Bereiche.
8. Verifiziertes Schreiben und Undo aktualisieren den gespeicherten Ist-Zustand; Fehler tun dies nicht.
9. Ein Browser-Test deckt Schnellfilter, Gesamtauswahl und den Analysejob für die gefilterte Bibliothek ab.

Die fokussierten Backend- und Frontendtests werden anschließend durch `python scripts/verify.py` sowie den relevanten Playwright-Workflow ergänzt.
