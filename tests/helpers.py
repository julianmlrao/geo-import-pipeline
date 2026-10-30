"""Builders for WFS/CSV test payloads."""

from __future__ import annotations

NS = (
    'xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" '
    'xmlns:app="http://www.deegree.org/app"'
)


def gml_collection(items: list[tuple[str, str, str, tuple[float, float]]]) -> bytes:
    """items: (gml_id, ags, name, (easting, northing)) -> squares of 1 km in EPSG:25833."""
    members = []
    for gid, ags, name, (e, n) in items:
        ring = f"{e} {n} {e + 1000} {n} {e + 1000} {n + 1000} {e} {n + 1000} {e} {n}"
        members.append(
            f'<wfs:member><app:gem gml:id="{gid}"><app:ags>{ags}</app:ags>'
            f"<app:gem_name>{name}</app:gem_name><app:gem_art>Gemeinde</app:gem_art>"
            f'<app:geom><!--Inlined geometry--><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::25833">'
            f"<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>"
            f"<gml:posList>{ring}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>"
            f"</gml:surfaceMember></gml:MultiSurface></app:geom></app:gem></wfs:member>"
        )
    body = "".join(members)
    return (
        f'<?xml version="1.0"?><wfs:FeatureCollection {NS}>{body}</wfs:FeatureCollection>'.encode()
    )


CSV_V1 = "AGS;Gemeinde;Einwohner;Flaeche\n12051000;Brandenburg;74113;229,73\n12052000;Cottbus;95123;165,61\n"
