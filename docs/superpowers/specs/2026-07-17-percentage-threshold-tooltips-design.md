# Prozent-Schwellen und Overlay-Hilfetexte – Produktdesign

**Status:** Vom Nutzer freigegebener Entwurf

**Datum:** 2026-07-17

## 1. Ziel

Die Genre- und Mood-Schwellen werden in den Einstellungen als verständliche ganze
Prozentwerte dargestellt. Hilfetexte erscheinen als schwebende, barrierefrei
bedienbare Overlays, ohne die Höhe oder Ausrichtung des Analyseformulars zu ändern.

## 2. Werte und Kompatibilität

- Die Oberfläche zeigt beide Schwellen als ganze Werte zwischen `0 %` und `100 %`.
- Die Eingaben verwenden Schritte von einem Prozentpunkt.
- Genre startet bei einer neuen Installation mit `25 %`.
- Mood startet bei einer neuen Installation mit `10 %`.
- API, YAML-Datei, Umgebungsvariablen und Analyse-Domain behalten den bestehenden
  Wertebereich von `0` bis `1`.
- Das Frontend zeigt einen gespeicherten Wert durch Multiplikation mit `100` an und
  teilt die Eingabe vor dem Speichern durch `100`.
- Bereits gespeicherte Werte werden nur dargestellt und nicht stillschweigend durch
  die neuen Standardwerte ersetzt.
- `ESSENTIA_GENRE_THRESHOLD` und `ESSENTIA_MOOD_THRESHOLD` bleiben Dezimalwerte im
  Bereich `0` bis `1`, damit bestehende Deployments kompatibel bleiben.

## 3. Oberfläche

Genre- und Mood-Schwelle verwenden jeweils ein numerisches Feld mit festem
Prozent-Suffix. Die Felder akzeptieren ausschließlich ganze Zahlen von `0` bis `100`.
Browser- und Backend-Validierung verhindern Werte außerhalb dieses Bereichs.

Das Prozent-Suffix gehört visuell zum Eingabefeld, ist aber kein Bestandteil des
editierbaren Werts. Durch ENV gesetzte Schwellen bleiben deaktiviert und zeigen den
umgerechneten Prozentwert.

## 4. Hilfetext-Overlay

Das vorhandene Info-Symbol bleibt direkt hinter dem Einstellungsnamen. Der Hilfetext
wird absolut über dem Formularfluss positioniert und verändert daher weder Zeilenhöhe
noch Spaltenausrichtung.

Das Overlay öffnet:

- beim Überfahren des Info-Bereichs mit der Maus;
- beim Tastaturfokus auf dem Info-Button;
- durch Klick oder Tippen auf Touch-Geräten.

Es schließt bei Fokusverlust, wenn die Maus den Info-Bereich verlässt, beim erneuten
Klick und mit `Escape`. Button und Overlay bleiben über `aria-describedby`,
`aria-expanded` und `role="tooltip"` semantisch verbunden. Ein sichtbarer Fokusring
bleibt erhalten.

Das Overlay verwendet ausschließlich die bestehenden Theme-Variablen für Fläche,
Text, Rahmen und Schatten. Es muss in hellem und dunklem Farbschema lesbar sein und
oberhalb benachbarter Felder erscheinen.

## 5. Datenfluss

Eine kleine Frontend-Funktion übernimmt die Prozentumrechnung an einer zentralen
Stelle. Die Settings-Ansicht verwendet sie beim Rendern und beim Aktualisieren des
Entwurfs. Der bestehende Save-Flow sendet weiterhin das unveränderte API-Schema.

Die Backend-Standardwerte werden auf `genre_threshold=0.25` und
`mood_threshold=0.10` geändert. Analysejobs, Automatik und Benchmark konsumieren
weiterhin dieselben normalisierten Dezimalwerte und benötigen keine neue Schnittstelle.

## 6. Fehlerverhalten

- Leere oder ungültige Prozentwerte dürfen keinen `NaN`-Wert in den Settings-Entwurf
  schreiben.
- Werte unter `0` oder über `100` werden nicht gespeichert.
- Die Backend-Validierung von `0` bis `1` bleibt die letzte Sicherheitsgrenze.
- ENV-gesperrte Felder bleiben vollständig unveränderbar.

## 7. Verifikation

Automatisierte Tests belegen:

- `0.25` wird als `25 %` und `0.10` als `10 %` dargestellt;
- eine Eingabe von `25` sendet `0.25` und eine Eingabe von `10` sendet `0.10`;
- neue Backend-Einstellungen verwenden die Standards `0.25` und `0.10`;
- bestehende Datei- und ENV-Werte bleiben unverändert;
- Hover, Fokus, Klick und `Escape` steuern das Tooltip korrekt;
- das Tooltip ist über ARIA erreichbar und im Darkmode lesbar;
- der Settings-Speicherfluss, Typprüfung, Produktionsbuild und Browser-Test bleiben
  grün.

Der lokale Apple-Container wird danach neu gebaut und auf Port `8090` ersetzt. Die
Prozentwerte und Tooltips werden abschließend in der integrierten Browseransicht
geprüft.
