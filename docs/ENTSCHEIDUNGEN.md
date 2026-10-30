# Entscheidungen

Stand 30.10.2026. Bei Unklarheit wurde die konservativste sinnvolle Variante gewählt.

1. **WFS 1 = `vg_wfs`/`app:gem` statt INSPIRE-Dienst.** Der INSPIRE-Dienst `au_bdlm_wfs` liefert verschachtelte Features, nur GML, und braucht für drei Objekte über 60 s. `vg_wfs` liefert flache Features mit dem 8-stelligen AGS.
2. **WFS 2 = `gaz_wfs`/`app:Hauskoordinaten` (Punkte), begrenzt auf 3.000 Adressen aus Potsdam.** Anderer Geometrietyp und anderes Attributschema; die komplette Schicht hat 1,26 Mio. Objekte und ist für eine Demo ungeeignet. Die Begrenzung steht in der Konfiguration (`max_features`).
3. **CSV: Destatis-Gemeindeverzeichnis statt INKAR.** Für INKAR und das Amt für Statistik gab es keinen stabilen anonymen CSV-Link (siehe `docs/QUELLEN.md`). Statt Daten zu erfinden, wurde ein amtlicher, lizenzfreier Auszug (Brandenburg) als CSV abgelegt. Das Format (Semikolon, Dezimalkomma) entspricht dem, was INKAR-Exporte typischerweise liefern.
4. **Keine zweite CSV (optional laut Auftrag)**, da keine abrufbare Quelle verifiziert werden konnte.
5. **Diff in Python statt Staging-Tabellen.** Bestandsstand und Neuzustand werden im Speicher verglichen (Hash je Schlüssel), dann in derselben Transaktion ersetzt (`COPY`). Gleiches Ergebnis wie ein SQL-Staging, einfacher zu testen. Bei sehr großen Quellen (Millionen Objekte) wäre Staging in der Datenbank der nächste Schritt.
6. **`replace` ersetzt auch unveränderte Zeilen** (löschen und neu einfügen), die Kennzahlen kommen aus dem Hash-Diff. `imported_at` ist deshalb der Zeitpunkt des letzten Laufs.
7. **Zusatzspalten `valid_from`/`valid_to`** in `geometries` und `attributes` für den optionalen Modus `history`. Der Eindeutigkeits-Index gilt nur für aktuelle Zeilen.
8. **Hash der Geometrie auf 1e-7 Grad (ca. 1 cm) gerundet**, damit Fließkommarauschen keine „Änderung“ erzeugt.
9. **Eigene Weboberfläche ruft den Importer über einen token-geschützten internen Endpunkt auf**, damit nur der Importer Schreibrechte hat. Drosselung (1 Lauf je 10 Minuten, global) wird dort erzwungen und ist nach einem Neustart zurückgesetzt.
10. **Kein Server-Zugang (`.env.deploy` fehlt) → Ausweichlösung GitHub Pages.** Die statische Demo zeigt Karte, Berichte und Konfiguration aus einem echten Importlauf. Der Server-Weg (Compose-Overlay, Caddy, `scripts/deploy.sh`) ist fertig und lokal getestet, aber nicht produktiv ausgerollt.
11. **Impressum/Datenschutz:** Angaben fehlen (`IMPRESSUM_*` nicht gesetzt), die Seiten enthalten deutlich markierte Platzhalter.
12. **Commit-Identität:** GitHub-noreply-Adresse statt der Arbeits-E-Mail, weil das Repository öffentlich ist.
13. **psycopg (LGPL-3.0) als Datenbanktreiber.** Dynamisch gelinkte Python-Bibliothek ohne Copyleft-Wirkung auf den eigenen Code; Alternative wäre asyncpg (Apache-2.0) mit anderer COPY-API.
14. **Dienstzeiten:** Die LGB-Dienste antworten sehr unterschiedlich schnell (0,7 s bis über 150 s je Seite). Seitengrößen sind klein gewählt, Timeout 300 s, Wiederholungen mit Backoff.
