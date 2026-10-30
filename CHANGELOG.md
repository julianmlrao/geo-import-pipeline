# Changelog

## 0.1.0 – 2026-11-05

- Import-Pipeline für WFS (GML/GeoJSON, Paginierung) und CSV (Zeichensatz-/Trennzeichenerkennung, WKT, Lon/Lat, Join über Schlüssel).
- Zieldatenmodell `geo_import.metadata/geometries/attributes` in EPSG:4326, Modi `replace` (Standard) und `history`.
- Atomarer Ersatz je Quelle, Fehlerisolation, Diff-Kennzahlen neu/geändert/gelöscht.
- Import-Bericht als JSON und Markdown; CLI und Scheduler (APScheduler).
- Docker Compose (PostGIS, Importer), Prod-Overlay mit Weboberfläche, pg_tileserv, pg_featureserv und Caddy.
- Demo: Landingpage und statische Demo auf GitHub Pages.
