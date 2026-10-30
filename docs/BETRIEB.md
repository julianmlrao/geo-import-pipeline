# Betrieb

## Docker

`docker compose up -d --build` startet `db` (PostGIS 16) und `importer` (Scheduler). Der Importer legt das Schema an, plant die Läufe aus den Cron-Angaben der Quellen und bietet `geo-import` als Kommando an:

```bash
docker compose exec importer geo-import run --all         # alle Quellen
docker compose exec importer geo-import run -s bb_gemeinden
docker compose exec importer geo-import report            # letzter Bericht
```

Berichte liegen im Volume `reports` unter `/app/reports/<run_id>.{json,md}` und in `geo_import.import_runs`.

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | Verbindung des Importers (Schreibrolle) |
| `GEO_IMPORT_DSN` | vollständige DSN, überschreibt die Einzelwerte |
| `GEO_IMPORT_CONFIG_DIR` | Ordner mit Quellkonfigurationen (Standard `config/sources`) |
| `GEO_IMPORT_REPORTS_DIR` | Ablage der Berichte (Standard `reports`) |
| `GEO_IMPORT_RUN_ON_START` | `1` = beim Start einmal alle Quellen laufen lassen, wenn die Datenbank leer ist |
| `GEO_IMPORT_DEFAULT_CRON` | Zeitplan für Quellen ohne eigenes `schedule` |
| `GEO_IMPORT_LOG_JSON`, `GEO_IMPORT_LOG_LEVEL` | Logformat und -stufe |
| `GEO_IMPORT_TRIGGER_TOKEN` | aktiviert den internen Endpunkt für den Import-Knopf |

## Scheduler

Jede Quelle kann `schedule` (Cron, 5 Felder, Zeitzone des Containers: `Europe/Berlin`) tragen. Quellen mit gleichem Ausdruck laufen in einem Lauf. Änderungen an den YAML-Dateien greifen nach `docker compose restart importer`.

## Logs

`docker compose logs -f importer` (JSON-Zeilen). Docker rotiert Logs (10 MB × 3).

## Sicherung

Das Prod-Overlay enthält einen Container `backup`, der täglich `pg_dump -Fc` in das Volume `backups` schreibt und 7 Tage aufbewahrt. Wiederherstellen: `pg_restore -d geo --clean /backups/geo-<Datum>.dump`.

## Demo mit Weboberfläche

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Dienste: `web` (`/demo/`), `pg_tileserv` (`/tiles/`), `pg_featureserv` (`/api/`), `caddy` (HTTPS, Landingpage unter `/`). Pflichtvariablen siehe `.env.example` (`DEMO_PASSWORD`, `ADMIN_PASSWORD`, `SESSION_SECRET`, `GEO_IMPORT_TRIGGER_TOKEN`). Für HTTPS `SITE_ADDRESS` auf die Domain setzen, `HTTP_PORT=80`, `HTTPS_PORT=443`, `COOKIE_SECURE=1`. Ist Port 80/443 belegt: [deploy/existing-proxy.md](../deploy/existing-proxy.md).
Deployment auf einen Server: `scripts/deploy.sh` (liest `.env.deploy`).

Nutzer: `demo` (lesen, Import höchstens einmal je 10 Minuten global) und `admin` (ohne Drosselung). Die Datenbankrolle der Weboberfläche ist `geo_reader` (nur lesend).
