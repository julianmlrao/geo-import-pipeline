"""Atomic per-source load: diff against stored state, replace (or version) in one transaction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
import shapely

from geo_import.config import CsvSource, WfsSource
from geo_import.transform import AttrValue, Feature


@dataclass
class Diff:
    new: int = 0
    changed: int = 0
    deleted: int = 0
    unchanged: int = 0
    total: int = 0
    unmatched_join_keys: int = 0


def migrate(conn: psycopg.Connection[Any], migrations_dir: str) -> None:
    """Apply db/migrations/*.sql in order (all statements are idempotent)."""
    from pathlib import Path

    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(727001)")
        for path in sorted(Path(migrations_dir).glob("*.sql")):
            conn.execute(path.read_text(encoding="utf-8"))


def _stored_state(
    conn: psycopg.Connection[Any], source_id: str, with_geom: bool
) -> dict[str, tuple[str | None, str]]:
    """key -> (geom_hash, attr_hash) of the current rows."""
    geoms: dict[str, str] = {}
    if with_geom:
        for key, h in conn.execute(
            "SELECT feature_key, geom_hash FROM geo_import.geometries "
            "WHERE source_id = %s AND valid_to IS NULL",
            (source_id,),
        ):
            geoms[key] = h
    attrs: dict[str, dict[str, list[Any]]] = {}
    for key, k, t, n, d, u in conn.execute(
        "SELECT feature_key, key, value_text, value_num, value_date, unit "
        "FROM geo_import.attributes WHERE source_id = %s AND valid_to IS NULL",
        (source_id,),
    ):
        attrs.setdefault(key, {})[k] = [t, n, d.isoformat() if d else None, u]
    keys = set(geoms) | set(attrs)
    return {
        k: (
            geoms.get(k),
            hashlib.sha1(json.dumps(attrs.get(k, {}), sort_keys=True).encode()).hexdigest(),
        )
        for k in keys
    }


def compute_diff(
    stored: dict[str, tuple[str | None, str]], features: list[Feature]
) -> tuple[Diff, set[str], set[str]]:
    """Return diff counters plus the keys to (re)write and the keys to remove."""
    diff = Diff(total=len(features))
    write: set[str] = set()
    current = {f.key for f in features}
    for f in features:
        old = stored.get(f.key)
        if old is None:
            diff.new += 1
            write.add(f.key)
        elif old != (f.geom_hash, f.attr_hash):
            diff.changed += 1
            write.add(f.key)
        else:
            diff.unchanged += 1
    gone = set(stored) - current
    diff.deleted = len(gone)
    return diff, write, gone


def load_source(
    conn: psycopg.Connection[Any],
    cfg: WfsSource | CsvSource,
    features: list[Feature],
    run_id: str,
    crs_source: str,
    warnings: list[str],
) -> Diff:
    """Replace the data of one source atomically. Any exception rolls back this source only."""
    with_geom = not (isinstance(cfg, CsvSource) and cfg.join)
    now = datetime.now(UTC)
    with conn.transaction():
        stored = _stored_state(conn, cfg.source_id, with_geom)
        diff, write, gone = compute_diff(stored, features)
        if isinstance(cfg, CsvSource) and cfg.join:
            target = {
                r[0]
                for r in conn.execute(
                    "SELECT feature_key FROM geo_import.geometries "
                    "WHERE source_id = %s AND valid_to IS NULL",
                    (cfg.join.target_source,),
                )
            }
            diff.unmatched_join_keys = sum(1 for f in features if f.key not in target)
            if diff.unmatched_join_keys:
                warnings.append(
                    f"{diff.unmatched_join_keys} Datensätze ohne passende Geometrie in "
                    f"{cfg.join.target_source}"
                )
        details = dict(cfg.details)
        if isinstance(cfg, CsvSource) and cfg.join:
            details["join_target"] = cfg.join.target_source
        conn.execute(
            """
            INSERT INTO geo_import.metadata (source_id, title, source_type, url, layer, license,
                attribution, crs_source, last_import_at, last_run_id, record_count, details)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (source_id) DO UPDATE SET title=EXCLUDED.title,
                source_type=EXCLUDED.source_type, url=EXCLUDED.url, layer=EXCLUDED.layer,
                license=EXCLUDED.license, attribution=EXCLUDED.attribution,
                crs_source=EXCLUDED.crs_source, last_import_at=EXCLUDED.last_import_at,
                last_run_id=EXCLUDED.last_run_id, record_count=EXCLUDED.record_count,
                details=EXCLUDED.details
            """,
            (
                cfg.source_id,
                cfg.title,
                cfg.type,
                cfg.url,
                getattr(cfg, "layer", None),
                cfg.license,
                cfg.attribution,
                crs_source,
                now,
                run_id,
                diff.total,
                json.dumps(details),
            ),
        )
        if cfg.mode == "replace":
            for table in ("attributes", "geometries"):
                conn.execute(
                    f"DELETE FROM geo_import.{table} WHERE source_id = %s",
                    (cfg.source_id,),
                )
            to_write = features
        else:  # history: close superseded rows, keep unchanged ones
            close = write | gone
            for table in ("attributes", "geometries"):
                conn.execute(
                    f"UPDATE geo_import.{table} SET valid_to = %s "
                    "WHERE source_id = %s AND valid_to IS NULL AND feature_key = ANY(%s)",
                    (now, cfg.source_id, list(close)),
                )
            to_write = [f for f in features if f.key in write]
        _insert(conn, cfg.source_id, to_write, now, with_geom)
    return diff


def _insert(
    conn: psycopg.Connection[Any],
    source_id: str,
    feats: list[Feature],
    now: datetime,
    with_geom: bool,
) -> None:
    with conn.cursor() as cur:
        if with_geom:
            with cur.copy(
                "COPY geo_import.geometries (source_id, feature_key, geom, geom_hash, imported_at,"
                " valid_from) FROM STDIN"
            ) as cp:
                for f in feats:
                    assert f.geom is not None and f.geom_hash is not None
                    cp.write_row(
                        (
                            source_id,
                            f.key,
                            shapely.to_wkb(
                                shapely.set_srid(f.geom, 4326), hex=True, include_srid=True
                            ),
                            f.geom_hash,
                            now,
                            now,
                        )
                    )
        with cur.copy(
            "COPY geo_import.attributes (source_id, feature_key, key, value_text, value_num,"
            " value_date, unit, valid_from) FROM STDIN"
        ) as cp:
            for f in feats:
                for k, v in f.attrs.items():
                    assert isinstance(v, AttrValue)
                    cp.write_row((source_id, f.key, k, v.text, v.num, v.date, v.unit, now))
