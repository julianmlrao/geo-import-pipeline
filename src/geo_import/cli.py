"""Command line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import psycopg
import typer

from geo_import import config, load, pipeline, report
from geo_import import logging as glog

app = typer.Typer(help="Configurable WFS/CSV import pipeline for PostGIS.", no_args_is_help=True)
MIGRATIONS = Path(__import__("os").environ.get("GEO_IMPORT_MIGRATIONS", "db/migrations"))


def _load() -> list[config.WfsSource | config.CsvSource]:
    try:
        return config.load_sources(config.sources_dir())
    except ValueError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command()
def run(
    source: Annotated[list[str] | None, typer.Option("--source", "-s", help="Source id")] = None,
    all_: Annotated[bool, typer.Option("--all", help="Run all configured sources")] = False,
) -> None:
    """Run an import now (one or more sources, or all)."""
    glog.setup()
    sources = _load()
    if not all_ and not source:
        typer.echo("Pass --all or --source ID", err=True)
        raise typer.Exit(2)
    if source:
        unknown = set(source) - {s.source_id for s in sources}
        if unknown:
            typer.echo(f"Unknown source(s): {', '.join(sorted(unknown))}", err=True)
            raise typer.Exit(2)
        sources = [s for s in sources if s.source_id in source]
    migrate()
    rr = pipeline.run(sources)
    typer.echo(f"Run {rr.run_id}: {rr.status}")
    for s in rr.sources:
        typer.echo(
            f"  {s.source_id}: {s.status} new={s.new} changed={s.changed} "
            f"deleted={s.deleted}" + (f" ERROR {s.error}" if s.error else "")
        )
    typer.echo(f"Report: {config.reports_dir() / (rr.run_id + '.md')}")
    raise typer.Exit(0 if rr.status != "failed" else 1)


@app.command()
def migrate() -> None:
    """Apply database migrations."""
    with psycopg.connect(config.database_dsn(), autocommit=True, connect_timeout=15) as conn:
        load.migrate(conn, str(MIGRATIONS))


@app.command("validate-config")
def validate_config() -> None:
    """Validate all YAML files in the configuration directory."""
    sources = _load()
    typer.echo(f"OK: {len(sources)} sources valid")


@app.command("list-sources")
def list_sources() -> None:
    """List configured sources."""
    for s in _load():
        typer.echo(f"{s.source_id:24} {s.type:4} {s.schedule or '-':12} {s.title}")


@app.command("report")
def report_cmd(
    which: Annotated[str, typer.Argument()] = "latest",
    fmt: Annotated[str, typer.Option("--format")] = "md",
) -> None:
    """Print a stored report (default: latest)."""
    files = sorted(config.reports_dir().glob("*.json"))
    if not files:
        typer.echo("No reports yet", err=True)
        raise typer.Exit(1)
    path = files[-1] if which == "latest" else config.reports_dir() / f"{which}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    sys.stdout.write(json.dumps(data, indent=2) if fmt == "json" else report.to_markdown(data))


@app.command()
def schedule() -> None:
    """Start the scheduler (blocking), used by the importer container."""
    from geo_import.scheduler import serve

    glog.setup()
    serve()
