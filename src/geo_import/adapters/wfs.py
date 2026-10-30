"""WFS adapter: paged GetFeature (GML or GeoJSON) with CRS detection."""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator
from typing import Any

import requests
from lxml import etree
from shapely.geometry import shape

from geo_import import http
from geo_import.adapters.base import FetchStats, RawFeature
from geo_import.adapters.gml import local, parse_geometry
from geo_import.config import WfsSource

log = logging.getLogger(__name__)
GML_NS = {"http://www.opengis.net/gml/3.2", "http://www.opengis.net/gml"}


def _is_latlon_urn(srs: str | None) -> bool:
    """urn:ogc:def:crs:EPSG::4326 (and 'epsg/0/4326') use lat/lon axis order."""
    if not srs:
        return False
    s = srs.lower()
    return s.startswith(("urn:", "http://www.opengis.net/def")) and s.endswith(("4326", "4258"))


class WfsAdapter:
    def __init__(self, cfg: WfsSource, session: requests.Session | None = None) -> None:
        self.cfg = cfg
        self.session = session
        self.stats = FetchStats()
        self.detected_crs: str | None = None

    def _params(self, start: int, count: int) -> dict[str, Any]:
        v2 = self.cfg.version.startswith("2")
        p: dict[str, Any] = {
            "SERVICE": "WFS",
            "VERSION": self.cfg.version,
            "REQUEST": "GetFeature",
            "TYPENAMES" if v2 else "TYPENAME": self.cfg.layer,
            "STARTINDEX": start,
            "COUNT" if v2 else "MAXFEATURES": count,
        }
        if self.cfg.filter:
            p["FILTER"] = self.cfg.filter
        if self.cfg.output_format == "geojson":
            p["OUTPUTFORMAT"] = "application/json"
        return p

    def fetch(self) -> Iterator[RawFeature]:
        start = 0
        seen: set[str] = set()
        limit = self.cfg.max_features
        while limit is None or start < limit:
            count = self.cfg.page_size if limit is None else min(self.cfg.page_size, limit - start)
            resp = http.get(
                self.cfg.url,
                self._params(start, count),
                timeout=self.cfg.timeout,
                session=self.session,
            )
            page = (
                list(self._parse_geojson(resp.content))
                if self.cfg.output_format == "geojson"
                else list(self._parse_gml(resp.content))
            )
            new = [f for f in page if f.fid is None or f.fid not in seen]
            if page and not new:
                self.stats.warnings.append(
                    "server ignored STARTINDEX (repeated features); stopped paging"
                )
                return
            seen.update(f.fid for f in new if f.fid)
            yield from new
            start += len(page)
            if len(page) < count:
                return

    def _parse_geojson(self, content: bytes) -> Iterator[RawFeature]:
        import json

        data = json.loads(content)
        if data.get("type") != "FeatureCollection":
            raise http.FetchError(f"unexpected GeoJSON response: {str(data)[:200]}")
        for i, f in enumerate(data["features"]):
            geom = shape(f["geometry"]) if f.get("geometry") else None
            yield RawFeature(f.get("properties") or {}, geom, str(f.get("id", i)))

    def _parse_gml(self, content: bytes) -> Iterator[RawFeature]:
        if b"ExceptionReport" in content[:2000] or b"ServiceException" in content[:2000]:
            text = etree.fromstring(content)
            parts = [
                " ".join("".join(e.itertext()).split())
                for e in text.iter()
                if local(e) in ("ExceptionText", "ServiceException")
            ]
            msg = " ".join(parts)
            raise http.FetchError(f"WFS exception: {msg[:300]}")
        for _ev, member in etree.iterparse(io.BytesIO(content), tag="{*}member"):
            feature = next(iter(member), None)
            if feature is None:
                continue
            yield self._feature(feature)
            member.clear()

    def _feature(self, feature: Any) -> RawFeature:
        props: dict[str, Any] = {}
        geom = None
        fid = feature.get("{http://www.opengis.net/gml/3.2}id") or feature.get(
            "{http://www.opengis.net/gml}id"
        )
        for child in feature:
            if not isinstance(child.tag, str):  # comments, processing instructions
                continue
            name = local(child)
            if name == "boundedBy":
                continue
            gml_child = next(
                (g for g in child if isinstance(g.tag, str) and etree.QName(g).namespace in GML_NS),
                None,
            )
            if name == self.cfg.geometry_field and gml_child is not None:
                srs = gml_child.get("srsName")
                if srs and self.detected_crs is None:
                    self.detected_crs = srs
                geom = parse_geometry(gml_child, swap_xy=_is_latlon_urn(srs))
            elif len(child) == 0:
                props[name] = (child.text or "").strip() or None
        return RawFeature(props, geom, fid)
