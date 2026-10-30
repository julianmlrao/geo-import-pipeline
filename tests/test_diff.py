from shapely.geometry import Point

from geo_import.load import compute_diff
from geo_import.transform import AttrValue, Feature, geom_digest


def feat(key, x, val):
    g = Point(x, 52)
    return Feature(key, g, {"w": AttrValue(num=val)}, geom_digest(g))


def test_diff_new_changed_deleted_unchanged():
    old = [feat("a", 13, 1), feat("b", 13, 2), feat("c", 13, 3)]
    stored = {f.key: (f.geom_hash, f.attr_hash) for f in old}
    new = [feat("a", 13, 1), feat("b", 13, 99), feat("d", 14, 4)]  # b changed, c gone, d new
    diff, write, gone = compute_diff(stored, new)
    assert (diff.new, diff.changed, diff.deleted, diff.unchanged, diff.total) == (1, 1, 1, 1, 3)
    assert write == {"b", "d"} and gone == {"c"}


def test_geometry_change_counts_as_changed():
    a = feat("a", 13, 1)
    diff, _, _ = compute_diff({"a": (a.geom_hash, a.attr_hash)}, [feat("a", 13.5, 1)])
    assert diff.changed == 1
