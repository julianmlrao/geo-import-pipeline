import pytest
from pydantic import ValidationError

from geo_import.config import CsvSource, WfsSource, load_sources, parse_source
from tests.conftest import ROOT


def test_repo_configs_are_valid():
    sources = load_sources(ROOT / "config" / "sources")
    assert {s.source_id for s in sources} >= {"bb_gemeinden"}
    assert any(isinstance(s, CsvSource) and s.join for s in sources)


def test_wfs_requires_layer():
    with pytest.raises(ValidationError):
        parse_source(
            {"source_id": "x", "title": "t", "type": "wfs", "url": "http://x", "feature_key": "id"}
        )


def test_csv_needs_exactly_one_geometry_mode():
    base = {"source_id": "x", "title": "t", "type": "csv", "url": "a.csv", "feature_key": "id"}
    with pytest.raises(ValidationError):
        parse_source(base)
    with pytest.raises(ValidationError):
        parse_source({**base, "wkt_column": "w", "lon_column": "a", "lat_column": "b"})
    assert isinstance(parse_source({**base, "wkt_column": "w"}), CsvSource)


def test_unknown_field_rejected_and_bad_id():
    with pytest.raises(ValidationError):
        parse_source(
            {
                "source_id": "Bad Id",
                "title": "t",
                "type": "wfs",
                "url": "u",
                "layer": "l",
                "feature_key": "k",
            }
        )
    with pytest.raises(ValidationError):
        parse_source(
            {
                "source_id": "x",
                "title": "t",
                "type": "wfs",
                "url": "u",
                "layer": "l",
                "feature_key": "k",
                "bogus": 1,
            }
        )


def test_join_target_must_exist(tmp_path):
    (tmp_path / "a.yaml").write_text(
        "source_id: a\ntitle: t\ntype: csv\nurl: a.csv\nfeature_key: k\n"
        "join: {target_source: missing, on: k}\n"
    )
    with pytest.raises(ValueError, match="join target"):
        load_sources(tmp_path)


def test_wfs_defaults():
    s = parse_source(
        {
            "source_id": "x",
            "title": "t",
            "type": "wfs",
            "url": "u",
            "layer": "l",
            "feature_key": "k",
        }
    )
    assert isinstance(s, WfsSource) and s.mode == "replace" and s.version == "2.0.0"
