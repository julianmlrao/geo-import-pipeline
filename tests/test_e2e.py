"""End-to-end: WFS + CSV into PostGIS, report matches DB, second run shows diff."""

from __future__ import annotations

import json
import os

import pytest
import responses

from geo_import import pipeline
from geo_import.config import parse_source
from tests.helpers import CSV_V1, gml_collection

pytestmark = pytest.mark.db
URL = "https://example.test/wfs"


def sources(tmp_path):
    (tmp_path / "v1.csv").write_text(CSV_V1, encoding="utf-8")
    wfs = parse_source(
        {
            "source_id": "gem",
            "title": "Gemeinden",
            "type": "wfs",
            "url": URL,
            "layer": "app:gem",
            "feature_key": "ags",
            "page_size": 100,
            "license": "dl-de/by-2-0",
            "mapping": {"ags": "ags", "gem_name": "name"},
        }
    )
    csv = parse_source(
        {
            "source_id": "bev",
            "title": "Bevölkerung",
            "type": "csv",
            "url": "v1.csv",
            "feature_key": "AGS",
            "join": {"target_source": "gem", "on": "AGS"},
            "decimal": ",",
            "mapping": {"Einwohner": "einwohner", "Flaeche": "flaeche"},
            "types": {
                "einwohner": {"type": "number", "unit": "Personen"},
                "flaeche": {"type": "number", "unit": "km2"},
            },
        }
    )
    bad = parse_source(
        {
            "source_id": "kaputt",
            "title": "Kaputt",
            "type": "wfs",
            "url": "https://bad.test/wfs",
            "layer": "x",
            "feature_key": "id",
        }
    )
    return [wfs, csv, bad]


ITEMS_V1 = [
    ("g1", "12051000", "Brandenburg", (330000, 5810000)),
    ("g2", "12052000", "Cottbus", (450000, 5750000)),
    ("g3", "12053000", "Frankfurt", (480000, 5800000)),
]


@responses.activate
def test_two_runs(conn, tmp_path, monkeypatch):
    monkeypatch.setattr("geo_import.http.time.sleep", lambda s: None)
    responses.add(responses.GET, URL, body=gml_collection(ITEMS_V1))
    responses.add(responses.GET, "https://bad.test/wfs", status=500)
    reports = tmp_path / "reports"
    r1 = pipeline.run(
        sources(tmp_path), dsn=os.environ["GEO_IMPORT_TEST_DSN"], reports=reports, base=tmp_path
    )

    by = {s.source_id: s for s in r1.sources}
    assert r1.status == "partial"
    assert by["kaputt"].status == "failed" and "HTTP 500" in (by["kaputt"].error or "")
    assert (by["gem"].new, by["gem"].total) == (3, 3)
    assert (by["bev"].new, by["bev"].total) == (2, 2)
    assert any("ohne passende Geometrie" in w for w in by["bev"].warnings) is False

    # report numbers agree with the database
    assert (
        conn.execute("SELECT count(*) FROM geo_import.geometries WHERE source_id='gem'").fetchone()[
            0
        ]
        == 3
    )
    assert conn.execute("SELECT count(*) FROM geo_import.metadata").fetchone()[0] == 2
    x, y = conn.execute(
        "SELECT ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom)) "
        "FROM geo_import.geometries WHERE feature_key='12051000'"
    ).fetchone()
    assert 12.4 < x < 12.8 and 52.3 < y < 52.6  # EPSG:4326
    assert (
        conn.execute("SELECT ST_SRID(geom) FROM geo_import.geometries LIMIT 1").fetchone()[0]
        == 4326
    )
    n, unit = conn.execute(
        "SELECT value_num, unit FROM geo_import.attributes "
        "WHERE source_id='bev' AND feature_key='12052000' AND key='einwohner'"
    ).fetchone()
    assert (n, unit) == (95123.0, "Personen")
    assert conn.execute("SELECT count(*) FROM geo_import.import_runs").fetchone()[0] == 1
    data = json.loads((reports / f"{r1.run_id}.json").read_text())
    assert data["sources"][0]["source_id"] == "gem"
    assert "kaputt" in (reports / f"{r1.run_id}.md").read_text()

    # second run: g1 changed (moved), g2 unchanged, g3 deleted, g4 new
    items = [
        ("g1", "12051000", "Brandenburg", (330500, 5810000)),
        ITEMS_V1[1],
        ("g4", "12054000", "Potsdam", (360000, 5805000)),
    ]
    responses.replace(responses.GET, URL, body=gml_collection(items))
    srcs = sources(tmp_path)
    (tmp_path / "v1.csv").write_text(CSV_V1.replace("74113", "74999"), encoding="utf-8")
    r2 = pipeline.run(srcs, dsn=os.environ["GEO_IMPORT_TEST_DSN"], reports=reports, base=tmp_path)
    g = {s.source_id: s for s in r2.sources}["gem"]
    assert (g.new, g.changed, g.deleted, g.unchanged) == (1, 1, 1, 1)
    b = {s.source_id: s for s in r2.sources}["bev"]
    assert (b.new, b.changed, b.deleted, b.unchanged) == (0, 1, 0, 1)
    assert (
        conn.execute("SELECT count(*) FROM geo_import.geometries WHERE source_id='gem'").fetchone()[
            0
        ]
        == 3
    )
    assert (
        conn.execute(
            "SELECT record_count FROM geo_import.metadata WHERE source_id='gem'"
        ).fetchone()[0]
        == 3
    )


@responses.activate
def test_failed_source_keeps_existing_data(conn, tmp_path):
    responses.add(responses.GET, URL, body=gml_collection(ITEMS_V1))
    wfs = sources(tmp_path)[0]
    pipeline.run([wfs], dsn=os.environ["GEO_IMPORT_TEST_DSN"], reports=tmp_path / "r")
    responses.replace(responses.GET, URL, body=gml_collection([]))  # empty answer
    r = pipeline.run([wfs], dsn=os.environ["GEO_IMPORT_TEST_DSN"], reports=tmp_path / "r")
    assert r.sources[0].status == "failed"
    assert conn.execute("SELECT count(*) FROM geo_import.geometries").fetchone()[0] == 3


@responses.activate
def test_history_mode_keeps_old_rows(conn, tmp_path):
    responses.add(responses.GET, URL, body=gml_collection(ITEMS_V1))
    wfs = sources(tmp_path)[0].model_copy(update={"mode": "history"})
    pipeline.run([wfs], dsn=os.environ["GEO_IMPORT_TEST_DSN"], reports=tmp_path / "r")
    responses.replace(responses.GET, URL, body=gml_collection(ITEMS_V1[:2]))
    r = pipeline.run([wfs], dsn=os.environ["GEO_IMPORT_TEST_DSN"], reports=tmp_path / "r")
    assert r.sources[0].deleted == 1
    cur, closed = conn.execute(
        "SELECT count(*) FILTER (WHERE valid_to IS NULL), count(*) FILTER (WHERE valid_to IS NOT NULL)"
        " FROM geo_import.geometries"
    ).fetchone()
    assert (cur, closed) == (2, 1)
