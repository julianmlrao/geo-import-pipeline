#!/usr/bin/env bash
# Start the stack, run all sources once and print the report location.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; sed -i.bak "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 12)/" .env && rm -f .env.bak; echo "created .env with a random database password"; }
docker compose up -d --build --wait db importer
docker compose exec importer geo-import run --all || true
latest=$(docker compose exec -T importer sh -c 'ls -t /app/reports/*.md | head -1' | tr -d '\r')
echo "Report (inside the importer container): ${latest}"
echo "Show it with: docker compose exec importer geo-import report"
