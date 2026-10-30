"""APScheduler with cron expressions from the source configuration."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from geo_import import config, load, pipeline

log = logging.getLogger(__name__)
DEFAULT_CRON = os.environ.get("GEO_IMPORT_DEFAULT_CRON", "")


def _migrate() -> None:
    import psycopg

    migrations = os.environ.get("GEO_IMPORT_MIGRATIONS", "db/migrations")
    with psycopg.connect(config.database_dsn(), autocommit=True) as conn:
        load.migrate(conn, migrations)


def _run(source_ids: list[str]) -> None:
    sources = [s for s in config.load_sources(config.sources_dir()) if s.source_id in source_ids]
    rr = pipeline.run(sources)
    log.info("scheduled run %s finished: %s", rr.run_id, rr.status)


def serve() -> None:
    """Block and run sources on their cron schedule; optionally one run at startup."""
    _migrate()
    sources = config.load_sources(config.sources_dir())
    sched = BlockingScheduler(timezone=os.environ.get("TZ", "UTC"))
    groups: dict[str, list[str]] = {}
    for s in sources:
        if cron := (s.schedule or DEFAULT_CRON):
            groups.setdefault(cron, []).append(s.source_id)
    for cron, ids in groups.items():
        sched.add_job(
            _run,
            CronTrigger.from_crontab(cron),
            args=[ids],
            id=f"cron:{cron}",
            max_instances=1,
            coalesce=True,
        )
        log.info("scheduled %s: %s", cron, ", ".join(ids))
    if os.environ.get("GEO_IMPORT_RUN_ON_START", "0") == "1":
        from datetime import datetime, timedelta

        import psycopg

        with psycopg.connect(config.database_dsn()) as conn:
            have = conn.execute("SELECT count(*) FROM geo_import.metadata").fetchone()
        if have and have[0] == 0:  # first start only: empty database
            sched.add_job(
                _run,
                "date",
                args=[[s.source_id for s in sources]],
                run_date=datetime.now() + timedelta(seconds=5),
            )
    if not groups:
        log.warning("no schedules configured; scheduler idle")
    sched.start()
