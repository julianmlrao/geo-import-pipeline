# Datenmodell (Schema `geo_import`)

Angelegt durch `db/migrations/*.sql` (idempotent, wird beim Start des Importers angewendet).

## `metadata` – eine Zeile je Quelle

`source_id` (PK), `title`, `source_type` (`wfs`/`csv`), `url`, `layer`, `license`, `attribution`, `crs_source`, `crs_target` (`EPSG:4326`), `last_import_at`, `last_run_id`, `record_count`, `details jsonb` (freie Zusatzangaben wie `theme`, `publisher`, `keywords`; bei Join-Quellen `join_target`).

## `geometries`

`id`, `source_id` (FK), `feature_key`, `geom geometry(Geometry, 4326)`, `geom_hash`, `imported_at`, `valid_from`, `valid_to`.
Indizes: GIST auf `geom`; eindeutig auf (`source_id`, `feature_key`) für aktuelle Zeilen (`valid_to IS NULL`).

## `attributes` (Long-Format)

`id`, `source_id`, `feature_key`, `key`, `value_text`, `value_num`, `value_date`, `unit`, `valid_from`, `valid_to`.
Indizes: (`source_id`, `feature_key`) und (`key`). Beliebige Attributschemata passen ohne Schemaänderung.

## Betrieb: `import_runs`, View `features`

`import_runs(run_id, started_at, ended_at, status, report jsonb)`; die View `features` liefert aktuelle Geometrien mit den Attributen der eigenen Quelle als JSON.

## Beispielabfragen

Attribute einer Gemeinde samt per AGS angehängter CSV-Werte:

```sql
SELECT a.source_id, a.key, COALESCE(a.value_num::text, a.value_date::text, a.value_text) AS value, a.unit
FROM geo_import.attributes a
WHERE a.feature_key = '12054000' AND a.valid_to IS NULL
ORDER BY a.source_id, a.key;
```

Gemeinden mit Einwohnerzahl (Geometrie ↔ Attribut):

```sql
SELECT g.feature_key, n.value_text AS name, e.value_num AS einwohner, g.geom
FROM geo_import.geometries g
JOIN geo_import.attributes n ON n.source_id = g.source_id AND n.feature_key = g.feature_key AND n.key = 'name'
JOIN geo_import.attributes e ON e.feature_key = g.feature_key AND e.key = 'einwohner'
WHERE g.source_id = 'bb_gemeinden' AND g.valid_to IS NULL
ORDER BY e.value_num DESC LIMIT 10;
```

Vektorkacheln einer Quelle für `pg_tileserv`: Funktion `geo_import.source_tile(z, x, y, src)`:
`/geo_import.source_tile/{z}/{x}/{y}.pbf?src=bb_gemeinden`.
