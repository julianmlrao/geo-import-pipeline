#!/bin/sh
# Creates the read-only role used by web UI and tile/feature servers.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
CREATE ROLE geo_reader LOGIN PASSWORD '${GEO_READER_PASSWORD:-reader}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO geo_reader;
SQL
