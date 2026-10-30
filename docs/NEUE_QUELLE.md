# Neue Quelle anbinden (fünf Schritte)

Beispiel: ein weiterer WFS-Layer, hier die Landkreise.

1. **Dienst prüfen.** `GetCapabilities` aufrufen, Layername (`typeName`) und Standard-KBS notieren, mit `COUNT=5` eine Stichprobe holen und die Feldnamen ansehen.
2. **Datei anlegen:** `config/sources/bb_kreise.yaml`.
3. **Felder eintragen:**

   ```yaml
   source_id: bb_kreise
   title: Landkreise Brandenburg
   type: wfs
   url: https://isk.geobasis-bb.de/ows/vg_wfs
   layer: app:krs
   crs_source: EPSG:25833
   feature_key: krss            # stabiler Schlüssel
   mapping:
     krs_name: name
     krs_kfz: kfz
   license: dl-de/by-2-0
   attribution: "© GeoBasis-DE/LGB, dl-de/by-2-0 (Daten geändert)"
   schedule: "0 4 * * 1"
   ```

4. **Prüfen:** `geo-import validate-config`, dann `geo-import run -s bb_kreise`. Der Bericht zeigt Warnungen, z. B. nicht abgebildete Felder.
5. **Betrieb:** `docker compose restart importer`, damit der Scheduler die Datei kennt. Kein Code wurde geändert.

**CSV-Quelle:** `type: csv`, `url` (Datei oder `https://`), optional `delimiter`, `encoding`, `decimal`, `skip_rows`. Geometrie genau eine Variante: `wkt_column`, `lon_column` + `lat_column` oder `join: { target_source: bb_gemeinden, on: AGS }` (`feature_key` muss dann dieselbe Spalte sein). Typen je Zielattribut unter `types` (`text`, `number`, `date`, optional `unit`).

Hinweis: YAML liest ein unquotiertes `on:` als Wahrheitswert; die Konfiguration akzeptiert das, `"on"` in Anführungszeichen ist trotzdem sauberer.

**Einschränkung:** Der WFS-Adapter liest einfache Features (Eigenschaften direkt unter dem Objekt). Verschachtelte Schemata wie INSPIRE-Dienste liefern keine flachen Attribute und brauchen einen eigenen Adapter oder einen flachen Dienst.
