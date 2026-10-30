"""Minimal GML 3 geometry parser (simple features) based on lxml elements."""

from __future__ import annotations

from typing import Any

from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

GML = "http://www.opengis.net/gml/3.2"
GML3 = "http://www.opengis.net/gml"


def local(el: Any) -> str:
    tag = str(el.tag)
    return tag.rsplit("}", 1)[-1]


def _coords(text: str, dim: int, swap: bool) -> list[tuple[float, ...]]:
    nums = [float(t) for t in text.split()]
    pts = [tuple(nums[i : i + dim]) for i in range(0, len(nums) - dim + 1, dim)]
    if swap:
        pts = [(p[1], p[0], *p[2:]) for p in pts]
    return pts


def _dim(el: Any, default: int = 2) -> int:
    return int(el.get("srsDimension", default))


def _ring(el: Any, swap: bool, dim: int) -> list[tuple[float, ...]]:
    for child in el.iter():
        if local(child) == "posList":
            return _coords(child.text or "", _dim(child, dim), swap)
        if local(child) == "pos":  # ring given as sequence of pos
            break
    return [c for p in el.iter() if local(p) == "pos" for c in _coords(p.text or "", dim, swap)]


def _polygon(el: Any, swap: bool, dim: int) -> Polygon:
    shell: list[tuple[float, ...]] = []
    holes: list[list[tuple[float, ...]]] = []
    for child in el:
        if local(child) == "exterior":
            shell = _ring(child, swap, dim)
        elif local(child) == "interior":
            holes.append(_ring(child, swap, dim))
    return Polygon(shell, holes)


def parse_geometry(el: Any, swap_xy: bool = False) -> BaseGeometry:
    """Parse a gml geometry element. swap_xy for lat/lon axis order (e.g. urn EPSG:4326)."""
    name = local(el)
    dim = _dim(el)
    if name == "Point":
        pos = next(c for c in el.iter() if local(c) == "pos")
        return Point(*_coords(pos.text or "", dim, swap_xy)[0])
    if name in ("LineString", "Curve"):
        return LineString(_ring(el, swap_xy, dim))
    if name == "Polygon":
        return _polygon(el, swap_xy, dim)
    if name in ("MultiSurface", "MultiPolygon"):
        polys = [_polygon(p, swap_xy, dim) for p in el.iter() if local(p) == "Polygon"]
        return MultiPolygon(polys)
    if name in ("MultiCurve", "MultiLineString"):
        lines = [
            LineString(_ring(p, swap_xy, dim))
            for p in el.iter()
            if local(p) in ("LineString", "Curve")
        ]
        return MultiLineString(lines)
    if name == "MultiPoint":
        pts = [parse_geometry(p, swap_xy) for p in el.iter() if local(p) == "Point"]
        return MultiPoint(pts)
    raise ValueError(f"unsupported GML geometry: {name}")
