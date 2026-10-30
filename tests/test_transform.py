from shapely.geometry import Point, Polygon

from geo_import.adapters.base import RawFeature
from geo_import.config import ColumnType, parse_source
from geo_import.transform import convert, geom_digest, to_wgs84, transform_features


def cfg(**kw):
    base = {
        "source_id": "x",
        "title": "t",
        "type": "wfs",
        "url": "u",
        "layer": "l",
        "feature_key": "id",
        "mapping": {"id": "id", "n": "wert"},
        "types": {"wert": {"type": "number", "unit": "m"}},
    }
    return parse_source({**base, **kw})


def test_crs_transform_utm33_to_wgs84():
    # Brandenburg an der Havel approx. (E 330000, N 5810000) in EPSG:25833
    g = to_wgs84(Point(330000, 5810000), "EPSG:25833")
    assert 12.4 < g.x < 12.7 and 52.3 < g.y < 52.5


def test_convert_numbers_with_decimal_comma_and_dates():
    assert convert("1.234,5", ColumnType(type="number"), ",").num == 1234.5
    assert convert("12.03.2026", ColumnType(type="date")).date.isoformat() == "2026-03-12"
    assert convert("", ColumnType(type="number")) is None


def test_mapping_dedup_invalid_geometry_and_missing_key():
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])
    raw = [
        RawFeature({"id": "a", "n": "1,5", "extra": "x"}, Point(330000, 5810000)),
        RawFeature({"id": "a", "n": "2"}, Point(305001, 5810000)),  # duplicate key
        RawFeature({"id": None, "n": "3"}, Point(330000, 5810000)),  # missing key
        RawFeature(
            {"id": "b", "n": "x"},
            Polygon([(330000, 5810000), (330010, 5810010), (330010, 5810000), (330000, 5810010)]),
        ),
        RawFeature({"id": "c", "n": "1"}, None),  # no geometry
    ]
    res = transform_features(cfg(), raw, needs_geometry=True)
    assert [f.key for f in res.features] == ["a", "b"]
    assert "extra" not in res.features[0].attrs
    joined = " ".join(res.warnings)
    assert "duplicate" in joined and "without feature_key" in joined
    assert "invalid geometries repaired" in joined and "without geometry" in joined
    assert bowtie is not None
    assert res.features[1].geom.is_valid


def test_digest_ignores_float_noise():
    a = Point(13.0000000001, 52.0)
    b = Point(13.0000000002, 52.0)
    assert geom_digest(a) == geom_digest(b)
    assert geom_digest(a) != geom_digest(Point(13.001, 52.0))
