"""Run orchestration: every source is isolated (own try block, own transaction)."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import requests
from psycopg.types.json import Jsonb

from geo_import import config, load, report, transform, validate
from geo_import.adapters.base import Adapter
from geo_import.adapters.csv import CsvAdapter
from geo_import.adapters.wfs import WfsAdapter
from geo_import.config import CsvSource, WfsSource

log = logging.getLogger(__name__)
SourceCfg = WfsSource | CsvSource


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(2)


def make_adapter(cfg: SourceCfg, session: requests.Session | None, base: Path) -> Adapter:
    if isinstance(cfg, WfsSource):
        return WfsAdapter(cfg, session)
    return CsvAdapter(cfg, session, base)


def order_sources(sources: list[SourceCfg]) -> list[SourceCfg]:
    """Join sources run after the sources they attach to."""
    return sorted(sources, key=lambda s: isinstance(s, CsvSource) and s.join is not None)


def run_source(
    conn: psycopg.Connection[Any],
    cfg: SourceCfg,
    run_id: str,
    session: requests.Session | None = None,
    base: Path = Path("."),
) -> report.SourceReport:
    sr = report.SourceReport(
        cfg.source_id,
        cfg.title,
        cfg.type,
        license=cfg.license,
        attribution=cfg.attribution,
        started_at=_now(),
    )
    t0 = time.monotonic()
    try:
        adapter = make_adapter(cfg, session, base)
        raw = list(adapter.fetch())
        sr.warnings += adapter.stats.warnings
        sr.warnings += validate.check_schema(cfg, raw)
        needs_geom = not (isinstance(cfg, CsvSource) and cfg.join)
        result = transform.transform_features(cfg, raw, needs_geom)
        sr.warnings += result.warnings
        if not result.features:
            raise validate.ValidationError("no usable records after transformation; data kept")
        detected = getattr(adapter, "detected_crs", None)
        if detected and cfg.crs_source.split(":")[-1] not in detected:
            sr.warnings.append(
                f"server reports CRS {detected}, configuration says {cfg.crs_source}"
            )
        diff = load.load_source(conn, cfg, result.features, run_id, cfg.crs_source, sr.warnings)
        sr.new, sr.changed, sr.deleted = diff.new, diff.changed, diff.deleted
        sr.unchanged, sr.total = diff.unchanged, diff.total
        sr.status = "success"
    except Exception as exc:  # isolation: error goes into the report, not the run
        log.exception("source %s failed", cfg.source_id)
        sr.status = "failed"
        sr.error = f"{type(exc).__name__}: {exc}"[:500]
    sr.ended_at = _now()
    sr.duration_s = round(time.monotonic() - t0, 2)
    return sr


def run(
    sources: list[SourceCfg],
    *,
    dsn: str | None = None,
    reports: Path | None = None,
    session: requests.Session | None = None,
    base: Path = Path("."),
    on_start: Callable[[str], None] | None = None,
) -> report.RunReport:
    run_id = new_run_id()
    if on_start:
        on_start(run_id)
    rr = report.RunReport(run_id=run_id, started_at=_now())
    t0 = time.monotonic()
    try:
        conn = psycopg.connect(dsn or config.database_dsn(), autocommit=True, connect_timeout=15)
    except psycopg.Error as exc:
        for cfg in order_sources(sources):
            rr.sources.append(
                report.SourceReport(
                    cfg.source_id,
                    cfg.title,
                    cfg.type,
                    status="failed",
                    started_at=_now(),
                    ended_at=_now(),
                    error=f"database unavailable: {exc}"[:300],
                )
            )
    else:
        with conn:
            for cfg in order_sources(sources):
                log.info("source %s: start", cfg.source_id)
                rr.sources.append(run_source(conn, cfg, run_id, session, base))
            rr.ended_at = _now()
            rr.duration_s = round(time.monotonic() - t0, 2)
            rr.finish()
            conn.execute(
                "INSERT INTO geo_import.import_runs (run_id, started_at, ended_at, status, report)"
                " VALUES (%s,%s,%s,%s,%s)",
                (rr.run_id, rr.started_at, rr.ended_at, rr.status, Jsonb(rr.to_dict())),
            )
    rr.ended_at = rr.ended_at or _now()
    rr.duration_s = round(time.monotonic() - t0, 2)
    rr.finish()
    report.write_report(rr, reports or config.reports_dir())
    return rr
