# Datenquellen

Abruf geprüft am 30.10.2026.

| Quelle | Herkunft | Lizenz | Hinweis |
|---|---|---|---|
| `bb_gemeinden` | WFS `https://isk.geobasis-bb.de/ows/vg_wfs`, Layer `app:gem` (413 Gemeinden), Landesvermessung und Geobasisinformation Brandenburg (LGB), „Digitale Verwaltungsgrenzen“ | Datenlizenz Deutschland – Namensnennung – 2.0; „© GeoBasis-DE/LGB, dl-de/by-2-0 (Daten geändert)“ | KBS EPSG:25833; Schlüssel `ags` (8-stellig) |
| `bb_hausadressen_potsdam` | WFS `https://isk.geobasis-bb.de/ows/gaz_wfs`, Layer `app:Hauskoordinaten`, Filter `gemeindeschluessel = 12054000`, auf 3.000 Objekte begrenzt (Ausschnitt) | dl-de/by-2-0; „© GeoBasis-DE/LGB“ | Punktgeometrie, anderes Attributschema |
| `destatis_gemeinden_bevoelkerung` | Statistisches Bundesamt, Gemeindeverzeichnis GV-ISys „Gemeinden in Deutschland nach Fläche, Bevölkerung und Postleitzahl“, Gebietsstand 30.06.2026, Bevölkerung Stand 31.12.2024 (Zensus 2022); Auszug Brandenburg (Satzart 60, 413 Gemeinden) als `data/samples/gemeinden_bevoelkerung.csv` | dl-de/by-2-0; „© Statistische Ämter des Bundes und der Länder (Destatis)“ | Join über AGS |

Hintergrundkarte der Demo: basemap.de Web Raster (BKG), dl-de/by-2-0.

## Abweichung von der Planung

Die Leistungsbeschreibung nennt INKAR (BBSR) und das Amt für Statistik Berlin-Brandenburg. Für beide fand sich am 30.10.2026 kein stabiler, anonym abrufbarer CSV-Direktlink (die Download-URLs des Amts liefern die Webanwendung statt einer Datei; INKAR verlangt eine interaktive Auswahl). Der Demonstrator nutzt deshalb ein amtliches, frei abrufbares Gemeindeverzeichnis als CSV-Quelle. Die Konfiguration ist identisch aufgebaut: ein INKAR-Export lässt sich mit einer weiteren YAML-Datei einbinden (`delimiter: ";"`, `decimal: ","`, `encoding` wird erkannt, `join` über den Gemeindeschlüssel).
