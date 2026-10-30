-- Read-only access for web UI, pg_tileserv and pg_featureserv, plus a per-source tile function.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geo_reader') THEN
        GRANT USAGE ON SCHEMA geo_import TO geo_reader;
        GRANT SELECT ON ALL TABLES IN SCHEMA geo_import TO geo_reader;
    END IF;
END $$;

-- Vector tiles of one source: /geo_import.source_tile/{z}/{x}/{y}.pbf?src=<source_id>
CREATE OR REPLACE FUNCTION geo_import.source_tile(z integer, x integer, y integer, src text)
RETURNS bytea LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT COALESCE(ST_AsMVT(t, 'source', 4096, 'geom'), ''::bytea)
    FROM (
        SELECT g.feature_key,
               ST_AsMVTGeom(ST_Transform(g.geom, 3857), ST_TileEnvelope(z, x, y), 4096, 64, true)
                   AS geom
        FROM geo_import.geometries g
        WHERE g.source_id = src AND g.valid_to IS NULL
          AND g.geom && ST_Transform(ST_TileEnvelope(z, x, y, margin => 0.03125), 4326)
    ) t
$$;
COMMENT ON FUNCTION geo_import.source_tile IS 'Vector tiles of a single source (parameter src)';

-- Feature server layer: current geometries with their attributes as columns of JSON.
COMMENT ON VIEW geo_import.features IS 'Current geometries with attributes as JSON (props)';
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geo_reader') THEN
        GRANT EXECUTE ON FUNCTION geo_import.source_tile(integer, integer, integer, text)
            TO geo_reader;
    END IF;
END $$;
