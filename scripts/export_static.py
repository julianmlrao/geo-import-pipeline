"""Export the imported data and reports as static files for the GitHub Pages demo."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import psycopg
import shapely
from psycopg.rows import dict_row
from shapely.geometry import mapping

from geo_import import config, report

OUT = Path("site/demo/data")
TOLERANCE = {"polygon": 0.0004, "line": 0.0001, "point": 0.0}  # degrees (~30 m for polygons)


def kind_of(geom: shapely.Geometry) -> str:
    t = geom.geom_type
    return "point" if "Point" in t else "line" if "Line" in t else "polygon"


def main() -> None:
    dsn = config.database_dsn()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "reports").mkdir(parents=True)
    (OUT / "config").mkdir()
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        meta = conn.execute("SELECT * FROM geo_import.metadata ORDER BY source_id").fetchall()
        attrs: dict[tuple[str, str], dict[str, object]] = {}
        join_target = {m["source_id"]: m["details"].get("join_target") for m in meta}
        for a in conn.execute(
            "SELECT source_id, feature_key, key, value_text, value_num, value_date, unit "
            "FROM geo_import.attributes WHERE valid_to IS NULL"
        ):
            val = (
                a["value_num"]
                if a["value_num"] is not None
                else (str(a["value_date"]) if a["value_date"] else a["value_text"])
            )
            label = a["key"] + (f" ({a['unit']})" if a["unit"] else "")
            target = join_target.get(a["source_id"]) or a["source_id"]
            attrs.setdefault((target, a["feature_key"]), {})[label] = val
        layers = []
        for m in meta:
            if join_target.get(m["source_id"]):
                continue
            feats, kind = [], "polygon"
            rows = conn.execute(
                "SELECT feature_key, ST_AsBinary(geom) AS wkb FROM geo_import.geometries "
                "WHERE source_id = %s AND valid_to IS NULL ORDER BY feature_key",
                (m["source_id"],),
            ).fetchall()
            for r in rows:
                g = shapely.from_wkb(bytes(r["wkb"]))
                kind = kind_of(g)
                if TOLERANCE[kind]:
                    g = g.simplify(TOLERANCE[kind], preserve_topology=True)
                g = shapely.set_precision(g, 1e-5)
                props = {
                    "feature_key": r["feature_key"],
                    **attrs.get((m["source_id"], r["feature_key"]), {}),
                }
                feats.append({"type": "Feature", "geometry": mapping(g), "properties": props})
            (OUT / f"{m['source_id']}.geojson").write_text(
                json.dumps(
                    {"type": "FeatureCollection", "features": feats},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            layers.append(
                {
                    "source_id": m["source_id"],
                    "title": m["title"],
                    "kind": kind,
                    "attribution": m["attribution"],
                    "count": len(feats),
                }
            )
        runs = conn.execute(
            "SELECT run_id, started_at, status, report FROM geo_import.import_runs "
            "ORDER BY started_at DESC"
        ).fetchall()
    for r in runs:
        (OUT / "reports" / f"{r['run_id']}.json").write_text(
            json.dumps(r["report"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (OUT / "reports" / f"{r['run_id']}.md").write_text(
            report.to_markdown(r["report"]), encoding="utf-8"
        )
    files = sorted(p.name for p in config.sources_dir().glob("*.y*ml"))
    for name in files:
        shutil.copy(config.sources_dir() / name, OUT / "config" / name)
    index = {
        "layers": layers,
        "sources": [
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in m.items()}
            for m in meta
        ],
        "reports": [
            {
                "run_id": r["run_id"],
                "started_at": r["started_at"].isoformat(),
                "status": r["status"],
            }
            for r in runs
        ],
        "config": files,
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"exported {len(layers)} layers, {len(runs)} reports", file=sys.stderr)


if __name__ == "__main__":
    main()
