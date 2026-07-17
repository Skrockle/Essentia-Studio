# Hierarchische Genres und Tag-Auswahllisten – Produktdesign

**Status:** Vom Nutzer freigegebener Entwurf

**Datum:** 2026-07-17

## 1. Ziel

Essentia Studio behandelt die hierarchischen Discogs-Genrelabels als einzelne
Metadatenwerte und unterstützt die manuelle Genre- und Mood-Bearbeitung mit einer
filterbaren, barrierefrei bedienbaren Auswahlliste. Freie eigene Werte bleiben
weiterhin erlaubt.

## 2. Genre-Aufbereitung

Das Discogs-Modell liefert hierarchische Labels im Format
`Elterngenre---Untergenre`. Ein solches Label erzeugt zwei getrennte Tags. Aus
`Funk / Soul---Contemporary R&B` werden daher `Funk / Soul` und
`Contemporary R&B`.

Die Aufteilung findet an der bestehenden Analyse-Servicegrenze statt, bevor der
Entwurf gespeichert wird. Die rohen Modellvorhersagen und ihre Konfidenzwerte
bleiben unverändert erhalten. Leere Segmente werden verworfen; anschließend sorgt
die vorhandene Normalisierung für Unicode-Normalisierung, stabile Reihenfolge und
case-insensitive Deduplizierung.

`genre_count` begrenzt weiterhin die Zahl ausgewählter Modellvorhersagen. Eine
hierarchische Vorhersage darf daraus zwei Metadatenwerte erzeugen. Moodlabels
werden weiterhin auf ihr letztes `---`-Segment reduziert und als einzelne Tags
behandelt.

## 3. Bestehende Analyseergebnisse

Beim Start führt die Anwendung eine idempotente Bestandskorrektur für vorhandene
Entwürfe aus. Für jedes Ergebnis wird aus den gespeicherten rohen
Genrevorhersagen eine exakte Zuordnung vom alten kombinierten Anzeigewert zu den
neuen Einzelwerten erzeugt.

Nur ein Entwurfswert, der dieser Zuordnung exakt entspricht, wird ersetzt. Andere
Werte, insbesondere frei eingegebene Texte mit Semikolon, bleiben unverändert.
Ausgewählt-, Dirty- und Statuszustand des Entwurfs bleiben erhalten. Die
Korrektur läuft in einer kurzen Datenbanktransaktion, ist wiederholbar und
verändert keine Audiodatei.

## 4. Tagkatalog

Ein read-only API-Endpunkt liefert zwei sortierte, deduplizierte Listen:

- `genres`: alle Eltern- und Untergenres aus dem gebündelten Discogs-Katalog;
- `moods`: alle formatierten Moodwerte aus dem gebündelten MTG-Jamendo-Katalog.

Die Anwendung liest ausschließlich die bereits geprüften JSON-Modelldateien aus
dem konfigurierten Modellverzeichnis. Fehlende oder ungültige Katalogdateien
liefern einen stabilen deutschen Fehler mit maschinenlesbarem Code; sie lösen
keinen Netzwerkzugriff aus. Der Endpunkt verändert weder Einstellungen noch
Mediendateien.

## 5. Manuelle Auswahlliste

Der bestehende Inline-Editor wird zu einer filterbaren Combobox erweitert. Beim
Fokus oder Tippen öffnet sich eine Liste passender Werte. Bereits ausgewählte
Tags werden ausgeblendet. Die Suche ist unabhängig von Groß-/Kleinschreibung und
priorisiert Präfixtreffer vor sonstigen Teiltreffern. Die sichtbare Liste ist auf
eine überschaubare Zahl von Einträgen begrenzt; der vollständige Katalog bleibt
durch weiteres Tippen erreichbar.

Bedienung:

- Mausklick übernimmt einen Vorschlag.
- `Pfeil hoch` und `Pfeil runter` bewegen die aktive Option.
- `Enter` übernimmt die aktive Option.
- Ist keine Option aktiv, übernimmt `Enter` den getrimmten freien Eingabewert.
- `Escape` schließt die Liste, ohne den Eingabetext zu verändern.
- Nach erfolgreicher Übernahme wird das Feld geleert und der Fokus bleibt im
  Eingabefeld.
- Doppelte Werte werden case-insensitive verhindert.

Die Combobox verwendet `role="combobox"`, `role="listbox"` und `role="option"`
sowie `aria-expanded`, `aria-controls`, `aria-activedescendant` und einen
programmatisch verbundenen Namen. Die Liste schließt bei Fokusverlust. Ein leerer
Katalog verhindert freie Eingaben nicht.

## 6. Oberfläche

Die Vorschlagsliste erscheint als schwebende Fläche direkt unter dem Eingabefeld
und verändert weder Tabellenzeilenhöhe noch Spaltenbreite. Sie verwendet nur die
bestehenden Theme-Tokens für Fläche, Text, Rahmen, Auswahl und Schatten. Die
aktive Option ist in hellem und dunklem Farbschema deutlich sichtbar. Lange Werte
brechen kontrolliert um; die Liste hat eine maximale Höhe und scrollt intern.

Genre verwendet weiterhin den blauen, Mood den violetten Akzent. Der Plus-Button
behält seine Funktion für freie Eingaben und ist deaktiviert, wenn das Feld leer
ist.

## 7. Datenfluss und Grenzen

Die API liefert ausschließlich Katalogwerte. Auswahl, freie Eingabe und Entfernen
ändern wie bisher nur den Datenbankentwurf über den vorhandenen Draft-Endpunkt.
Erst der bestehende explizite Vorschau- und Schreibablauf darf Audiodateien
verändern. Bulk-Ergänzungen bleiben unverändert; diese Spezifikation betrifft den
Inline-Editor pro Titel.

Die Katalogaufbereitung liegt in einem eigenen Service und verwendet dieselben
reinen Label-Funktionen wie die Analyse-Aufbereitung und Bestandskorrektur. React
erhält einen kleinen Katalog-Hook und eine eigenständige Combobox-Komponente; die
Ergebnistabelle bleibt für Auswahl und Speichern verantwortlich.

## 8. Fehlerverhalten

- Ein fehlerhafter Katalog zeigt eine nicht-blockierende deutsche Meldung; freie
  Tag-Eingabe bleibt verfügbar.
- Leere oder nur aus Leerzeichen bestehende Werte werden nicht gespeichert.
- Werte über 120 Zeichen werden bereits im Client abgewiesen und weiterhin vom
  Backend validiert.
- Ein Fehler bei der Bestandskorrektur bricht den Start mit einem eindeutigen
  Fehler ab, statt einen teilweise migrierten Zustand zu verbergen.
- Die Bestandskorrektur schreibt keine Entwürfe um, deren kombinierter Wert nicht
  exakt aus den rohen Modelllabels abgeleitet werden kann.

## 9. Verifikation

Automatisierte Tests belegen:

- ein hierarchisches Modelllabel erzeugt zwei deduplizierte Genre-Tags;
- nicht-hierarchische Genres und Moods behalten ihr bisheriges Verhalten;
- die idempotente Bestandskorrektur ersetzt nur exakt ableitbare kombinierte
  Modellwerte und bewahrt manuelle Semikolon-Werte;
- der API-Katalog enthält normalisierte, sortierte Genre- und Moodwerte;
- fehlende Katalogdateien liefern den vereinbarten Fehler;
- die Combobox filtert Vorschläge, versteckt ausgewählte Werte und akzeptiert
  weiterhin freie Eingaben;
- Maus, Pfeiltasten, `Enter`, `Escape`, Fokusverlust und ARIA-Zustände funktionieren;
- die Vorschlagsliste ist in hellem und dunklem Farbschema lesbar und verändert
  die Tabellengeometrie nicht;
- der vollständige Source-Gate und der relevante Playwright-Workflow bleiben grün.

Nach erfolgreicher Verifikation wird das lokale CPU-Image neu gebaut, der Apple-
Container auf Port `8090` mit unveränderten Mounts ersetzt und der Ablauf im
integrierten Browser mit den vorhandenen Testdateien geprüft.
