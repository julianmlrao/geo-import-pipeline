"""Run report as JSON and Markdown."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SourceReport:
    source_id: str
    title: str
    type: str
    status: str = "pending"  # success | failed
    started_at: str = ""
    ended_at: str = ""
    duration_s: float = 0.0
    new: int = 0
    changed: int = 0
    deleted: int = 0
    unchanged: int = 0
    total: int = 0
    license: str | None = None
    attribution: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RunReport:
    run_id: str
    started_at: str
    ended_at: str = ""
    duration_s: float = 0.0
    status: str = "success"  # success | partial | failed
    sources: list[SourceReport] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def finish(self) -> None:
        ok = [s for s in self.sources if s.status == "success"]
        self.status = "success" if len(ok) == len(self.sources) else ("partial" if ok else "failed")


def to_markdown(r: dict[str, Any]) -> str:
    srcs = r["sources"]
    lines = [
        f"# Import-Bericht {r['run_id']}",
        "",
        f"- Status: **{r['status']}**",
        f"- Start: {r['started_at']}",
        f"- Ende: {r['ended_at']}",
        f"- Laufzeit: {r['duration_s']:.1f} s",
        f"- Quellen: {len(srcs)} ({sum(s['status'] == 'success' for s in srcs)} erfolgreich, "
        f"{sum(s['status'] != 'success' for s in srcs)} fehlgeschlagen)",
        "",
        "## Quellen",
        "",
        "| Quelle | Status | Zeitstempel | Neu | Geändert | Gelöscht | Unverändert | Gesamt |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for s in srcs:
        lines.append(
            f"| `{s['source_id']}` | {s['status']} | {s['ended_at']} | {s['new']} | "
            f"{s['changed']} | {s['deleted']} | {s['unchanged']} | {s['total']} |"
        )
    failed = [s for s in srcs if s["status"] != "success"]
    if failed:
        lines += ["", "## Fehlgeschlagene Quellen", ""]
        lines += [f"- `{s['source_id']}` ({s['title']}): {s['error']}" for s in failed]
    warned = [s for s in srcs if s["warnings"]]
    if warned:
        lines += ["", "## Warnungen", ""]
        for s in warned:
            lines += [f"- `{s['source_id']}`: {w}" for w in s["warnings"]]
    lic = [s for s in srcs if s.get("license")]
    if lic:
        lines += ["", "## Lizenzen", ""]
        lines += [
            f"- `{s['source_id']}`: {s['license']} – {s.get('attribution') or ''}" for s in lic
        ]
    return "\n".join(lines) + "\n"


def write_report(report: RunReport, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    data = report.to_dict()
    jpath = directory / f"{report.run_id}.json"
    mpath = directory / f"{report.run_id}.md"
    jpath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    mpath.write_text(to_markdown(data), encoding="utf-8")
    return jpath, mpath
