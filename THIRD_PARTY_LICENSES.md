# Lizenzen der Drittkomponenten

Eigener Code: Apache-2.0. Erzeugt mit `scripts/gen_licenses.sh` (pip-licenses, nur Laufzeitabhängigkeiten inkl. Web-Erweiterung).

## Python-Pakete

| Name               | Version    | License                                            |
|--------------------|------------|----------------------------------------------------|
| requests           | 2.34.2     | Apache Software License                            |
| opentelemetry-api  | 1.45.2     | Apache-2.0                                         |
| python-multipart   | 0.0.32     | Apache-2.0                                         |
| Jinja2             | 3.1.6      | BSD License                                        |
| itsdangerous       | 2.2.0      | BSD License                                        |
| Pygments           | 2.21.0     | BSD-2-Clause                                       |
| Markdown           | 3.11.2     | BSD-3-Clause                                       |
| MarkupSafe         | 3.0.4      | BSD-3-Clause                                       |
| click              | 8.5.0      | BSD-3-Clause                                       |
| idna               | 3.20       | BSD-3-Clause                                       |
| lxml               | 6.1.3      | BSD-3-Clause                                       |
| shapely            | 2.2.0      | BSD-3-Clause                                       |
| starlette          | 1.10.0     | BSD-3-Clause                                       |
| uvicorn            | 0.54.0     | BSD-3-Clause                                       |
| numpy              | 2.5.4      | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| shellingham        | 1.5.4      | ISC License (ISCL)                                 |
| psycopg            | 3.3.6      | LGPL-3.0-only                                      |
| psycopg-binary     | 3.3.6      | LGPL-3.0-only                                      |
| annotated-doc      | 0.0.5      | MIT                                                |
| annotated-types    | 0.8.0      | MIT                                                |
| anyio              | 4.15.1     | MIT                                                |
| charset-normalizer | 3.5.2      | MIT                                                |
| fastapi            | 0.162.0    | MIT                                                |
| pydantic           | 2.14.2     | MIT                                                |
| pydantic_core      | 2.50.2     | MIT                                                |
| pyproj             | 3.8.0      | MIT                                                |
| typer              | 0.27.3     | MIT                                                |
| typing-inspection  | 0.4.4      | MIT                                                |
| tzlocal            | 5.4.5      | MIT                                                |
| urllib3            | 2.8.0      | MIT                                                |
| APScheduler        | 3.11.3     | MIT License                                        |
| PyYAML             | 6.0.3      | MIT License                                        |
| h11                | 0.16.0     | MIT License                                        |
| markdown-it-py     | 4.2.0      | MIT License                                        |
| mdurl              | 0.1.2      | MIT License                                        |
| rich               | 15.0.0     | MIT License                                        |
| certifi            | 2026.10.23 | Mozilla Public License 2.0 (MPL 2.0)               |
| typing_extensions  | 4.16.0     | PSF-2.0                                            |

Hinweis: `psycopg` steht unter LGPL-3.0 und wird als unveränderte Bibliothek dynamisch genutzt; `psycopg-binary` bringt `libpq` (PostgreSQL-Lizenz) mit.

## Vendorte Frontend-Bibliothek

| Name | Version | Lizenz |
|---|---|---|
| MapLibre GL JS | 4.7.1 | BSD-3-Clause (`site/vendor/maplibre/LICENSE.txt`) |

## Docker-Basis-Images

| Image | Lizenz |
|---|---|
| `python:3.12-slim` (Debian, CPython) | PSF-2.0; Debian-Pakete mit jeweils eigener Lizenz |
| `postgis/postgis:16-3.4` | PostgreSQL (PostgreSQL License), PostGIS (GPL-2.0-or-later, läuft als eigener Datenbankdienst), GEOS (LGPL-2.1), PROJ (MIT), GDAL (MIT/X) |
| `pramsey/pg_tileserv` | MIT |
| `pramsey/pg_featureserv` | MIT |
| `caddy:2` | Apache-2.0 |

PostGIS (GPL) wird ausschließlich als separat laufender Dienst über das PostgreSQL-Protokoll genutzt und nicht in den eigenen Code gelinkt.
