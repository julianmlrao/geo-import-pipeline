#!/usr/bin/env bash
# Regenerate THIRD_PARTY_LICENSES.md from a clean environment with runtime dependencies only.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
uv venv -q --python 3.12 "$tmp/venv"
uv pip install -q --python "$tmp/venv/bin/python" ".[web]" pip-licenses
{
  echo "# Lizenzen der Drittkomponenten"
  echo
  echo "Eigener Code: Apache-2.0. Erzeugt mit \`scripts/gen_licenses.sh\` (pip-licenses, nur Laufzeitabhängigkeiten inkl. Web-Erweiterung)."
  echo
  echo "## Python-Pakete"
  echo
  "$tmp/venv/bin/pip-licenses" --from=mixed --format=markdown --order=license \
    --ignore-packages geo-import-pipeline pip-licenses prettytable wcwidth tomli
  echo
  echo "Hinweis: \`psycopg\` steht unter LGPL-3.0 und wird als unveränderte Bibliothek dynamisch genutzt; \`psycopg-binary\` bringt \`libpq\` (PostgreSQL-Lizenz) mit."
  echo
  cat <<'EOT'
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
EOT
} > THIRD_PARTY_LICENSES.md
rm -rf "$tmp"
