# Architektur

## Komponenten

| Modul | Aufgabe |
|---|---|
| `config.py` | Pydantic-Modelle für `config/sources/*.yaml`, Prüfung beim Laden |
| `adapters/wfs.py` | GetFeature mit `STARTINDEX`/`COUNT` (WFS 2.0) bzw. `MAXFEATURES` (1.x), GML und GeoJSON, CRS-Erkennung, Schutz gegen Server, die `STARTINDEX` ignorieren |
| `adapters/csv.py` | URL oder Datei, Zeichensatz (UTF-8/Windows-1252) und Trennzeichen erkannt, Geometrie aus WKT, Lon/Lat oder Join |
| `http.py` | Timeouts, exponentielles Backoff bei Netzfehlern und 429/5xx, lesbare Fehlermeldungen |
| `validate.py` | Schema gegen Konfiguration, Warnungen bei fehlenden/neuen Feldern, leere Antwort ist ein Fehler |
| `transform.py` | Mapping, Typkonvertierung, Reprojektion nach EPSG:4326 (pyproj), Reparatur ungültiger Geometrien (`make_valid`), Dubletten |
| `load.py` | Diff gegen den Bestand und atomarer Ersatz je Quelle (psycopg 3, `COPY`) |
| `report.py` | JSON und Markdown, Ablage unter `reports/<run_id>.*` und in `import_runs` |
| `pipeline.py` | Orchestrierung, Isolation je Quelle |
| `scheduler.py`, `trigger.py` | Cron-Zeitpläne (APScheduler); interner HTTP-Endpunkt für den Import-Knopf der Demo |

## Datenfluss einer Quelle

1. Adapter liefert Rohobjekte (Eigenschaften + Geometrie im Quell-KBS).
2. Prüfung gegen die Konfiguration; eine leere Antwort bricht diese Quelle ab, der Bestand bleibt.
3. Transformation: Mapping, Typen, Reprojektion, Reparatur, Hashes (Geometrie auf ca. 1 cm gerundet, Attribute kanonisch).
4. In **einer Transaktion**: Bestand lesen, Diff (neu/geändert/gelöscht/unverändert über `feature_key` und Hash), Metadaten aktualisieren, alte Zeilen der Quelle ersetzen, neue per `COPY` einfügen.
5. Bei jedem Fehler Rollback nur dieser Quelle; der Fehler steht im Bericht, die übrigen Quellen laufen weiter.

CSV-Quellen mit `join` schreiben nur Attribute unter ihrer eigenen `source_id`, mit dem `feature_key` der Zielgeometrie. Sie laufen nach den Quellen, an die sie anknüpfen; Datensätze ohne passende Geometrie erscheinen als Warnung.

## Ersetzen und Historisieren

Die Vergabestelle bestätigte, dass ein neuer Import die Daten derselben Quelle ersetzt. Das ist der Standard (`mode: replace`). Der optionale Modus `history` schließt geänderte und gelöschte Zeilen über `valid_to` ab und legt neue an; unveränderte Zeilen bleiben. Alle Abfragen und Dienste lesen nur Zeilen mit `valid_to IS NULL`. Bestehende Tabellenstrukturen werden nie verändert; die Spalten `valid_from`/`valid_to` gehören zum eigenen Schema `geo_import`.

## Warum Python statt Node-RED

- Testbarkeit: Transformationen, Diff-Logik und Adapter sind reine Funktionen und per pytest ohne Netz prüfbar; Flows in Node-RED sind schwer zu testen und zu versionieren.
- GDAL/PROJ/Shapely-Ökosystem für Reprojektion und Geometrieprüfung.
- Vorhandene Python-Skripte des Auftraggebers lassen sich als Adapter oder Transformation weiterverwenden.
- Ein Container, keine zusätzliche Laufzeit, Konfiguration als Text in Git.

## Sicherheit der Demo

Nur der Importer schreibt. Weboberfläche, `pg_tileserv` und `pg_featureserv` nutzen die Rolle `geo_reader` (nur SELECT). Der Import-Knopf ruft einen internen, token-geschützten Endpunkt des Importers auf; die Drosselung (1 Lauf je 10 Minuten für die Demo-Rolle) wird dort durchgesetzt. PostgreSQL ist nicht von außen erreichbar.
