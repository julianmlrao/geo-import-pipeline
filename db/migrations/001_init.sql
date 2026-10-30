-- Target data model: three core tables plus run log.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS geo_import;

CREATE TABLE IF NOT EXISTS geo_import.metadata (
    source_id      text PRIMARY KEY,
    title          text NOT NULL,
    source_type    text NOT NULL CHECK (source_type IN ('wfs', 'csv')),
    url            text,
    layer          text,
    license        text,
    attribution    text,
    crs_source     text,
    crs_target     text NOT NULL DEFAULT 'EPSG:4326',
    last_import_at timestamptz,
    last_run_id    text,
    record_count   integer NOT NULL DEFAULT 0,
    details        jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS geo_import.geometries (
    id          bigserial PRIMARY KEY,
    source_id   text NOT NULL REFERENCES geo_import.metadata (source_id) ON DELETE CASCADE,
    feature_key text NOT NULL,
    geom        geometry(Geometry, 4326) NOT NULL,
    geom_hash   text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    valid_from  timestamptz NOT NULL DEFAULT now(),
    valid_to    timestamptz
);
CREATE INDEX IF NOT EXISTS geometries_geom_gix ON geo_import.geometries USING gist (geom);
-- one current row per feature; history mode closes rows via valid_to
CREATE UNIQUE INDEX IF NOT EXISTS geometries_source_key_uix
    ON geo_import.geometries (source_id, feature_key) WHERE valid_to IS NULL;

CREATE TABLE IF NOT EXISTS geo_import.attributes (
    id          bigserial PRIMARY KEY,
    source_id   text NOT NULL REFERENCES geo_import.metadata (source_id) ON DELETE CASCADE,
    feature_key text NOT NULL,
    key         text NOT NULL,
    value_text  text,
    value_num   double precision,
    value_date  date,
    unit        text,
    valid_from  timestamptz NOT NULL DEFAULT now(),
    valid_to    timestamptz
);
CREATE INDEX IF NOT EXISTS attributes_source_key_ix ON geo_import.attributes (source_id, feature_key);
CREATE INDEX IF NOT EXISTS attributes_key_ix ON geo_import.attributes (key);

CREATE TABLE IF NOT EXISTS geo_import.import_runs (
    run_id     text PRIMARY KEY,
    started_at timestamptz NOT NULL,
    ended_at   timestamptz,
    status     text NOT NULL,
    report     jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Convenience view for tile/feature servers: current geometry + attributes as JSON.
CREATE OR REPLACE VIEW geo_import.features AS
SELECT g.source_id, g.feature_key, g.geom,
       COALESCE((SELECT jsonb_object_agg(a.key, COALESCE(a.value_num::text, a.value_date::text, a.value_text))
                 FROM geo_import.attributes a
                 WHERE a.source_id = g.source_id AND a.feature_key = g.feature_key
                   AND a.valid_to IS NULL), '{}'::jsonb) AS props
FROM geo_import.geometries g WHERE g.valid_to IS NULL;
