#!/usr/bin/env bash
# Idempotent deployment to /opt/geo-import-demo on the server named in .env.deploy.
# Needs: DEPLOY_SSH, DEMO_DOMAIN, ACME_EMAIL (+ optional IMPRESSUM_*). Secrets are generated on the
# server on first run and kept in the server's .env (chmod 600); they are never written to the repo.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env.deploy ] || { echo ".env.deploy fehlt (siehe docs/BETRIEB.md)"; exit 2; }
set -a; . ./.env.deploy; set +a
: "${DEPLOY_SSH:?}" "${DEMO_DOMAIN:?}"
REMOTE=/opt/geo-import-demo
ssh "$DEPLOY_SSH" "mkdir -p $REMOTE"
rsync -az --delete --exclude .git --exclude .venv --exclude .env --exclude .env.deploy \
  --exclude reports --exclude '__pycache__' ./ "$DEPLOY_SSH:$REMOTE/"
ssh "$DEPLOY_SSH" bash -s <<REMOTE_SCRIPT
set -euo pipefail
cd $REMOTE
rand() { openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 20; }
if [ ! -f .env ]; then
  umask 077
  cat > .env <<ENV
POSTGRES_DB=geo
POSTGRES_USER=geo_import
POSTGRES_PASSWORD=\$(rand)
GEO_READER_PASSWORD=\$(rand)
GEO_IMPORT_RUN_ON_START=1
SITE_ADDRESS=${DEMO_DOMAIN}
HTTP_PORT=\${HTTP_PORT:-80}
HTTPS_PORT=\${HTTPS_PORT:-443}
ACME_EMAIL=${ACME_EMAIL:-}
DEMO_USER=demo
DEMO_PASSWORD=\$(rand)
ADMIN_PASSWORD=\$(rand)
SESSION_SECRET=\$(rand)\$(rand)
GEO_IMPORT_TRIGGER_TOKEN=\$(rand)
COOKIE_SECURE=1
ENV
fi
chmod 600 .env
for p in 80 443; do ss -ltn "( sport = :\$p )" | grep -q LISTEN && echo "WARNUNG: Port \$p belegt - siehe deploy/existing-proxy.md" || true; done
set -a; . ./.env; set +a
SITE_MODE=server DEMO_USER=\$DEMO_USER DEMO_PASSWORD=\$DEMO_PASSWORD \
  IMPRESSUM_NAME="${IMPRESSUM_NAME:-}" IMPRESSUM_ANSCHRIFT="${IMPRESSUM_ANSCHRIFT:-}" \
  IMPRESSUM_VERTRETEN="${IMPRESSUM_VERTRETEN:-}" IMPRESSUM_EMAIL="${IMPRESSUM_EMAIL:-}" \
  SITE_URL=https://${DEMO_DOMAIN} python3 scripts/build_site.py
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull --ignore-buildable
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans
for i in \$(seq 1 40); do
  curl -fsS -o /dev/null http://127.0.0.1:\${HTTP_PORT:-80}/demo/login && echo "health: ok" && exit 0
  sleep 3
done
echo "health check failed"; exit 1
REMOTE_SCRIPT
