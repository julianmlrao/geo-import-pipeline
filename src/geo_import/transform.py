"""Mapping, type conversion, CRS transformation and geometry repair."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Any

import shapely
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform

from geo_import.adapters.base import RawFeature
from geo_import.config import ColumnType, CsvSource, WfsSource


@dataclass
class AttrValue:
    text: str | None = None
    num: float | None = None
    date: date | None = None
    unit: str | None = None

    def canonical(self) -> list[Any]:
        return [self.text, self.num, self.date.isoformat() if self.date else None, self.unit]


@dataclass
class Feature:
    key: str
    geom: BaseGeometry | None
    attrs: dict[str, AttrValue] = field(default_factory=dict)
    geom_hash: str | None = None

    @property
    def attr_hash(self) -> str:
        data = {k: v.canonical() for k, v in sorted(self.attrs.items())}
        return hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest()


@lru_cache(maxsize=8)
def _transformer(src: str, dst: str = "EPSG:4326") -> Transformer:
    return Transformer.from_crs(src, dst, always_xy=True)


def to_wgs84(geom: BaseGeometry, crs_source: str) -> BaseGeometry:
    if crs_source.upper() in ("EPSG:4326", "OGC:CRS84"):
        return geom
    return shp_transform(_transformer(crs_source.upper()).transform, geom)


def geom_digest(geom: BaseGeometry) -> str:
    """Hash of the geometry rounded to ~1 cm so float noise does not count as a change."""
    rounded = shapely.set_precision(geom, 1e-7)
    return hashlib.sha1(shapely.to_wkb(rounded)).hexdigest()


def convert(value: str | None, ctype: ColumnType, decimal: str = ".") -> AttrValue | None:
    """Convert a raw string to a typed value; raises ValueError on bad input."""
    if value is None or value == "":
        return None
    if ctype.type == "number":
        s = value.strip().replace(" ", "")
        if decimal == ",":
            s = s.replace(".", "").replace(",", ".")
        return AttrValue(num=float(s), unit=ctype.unit)
    if ctype.type == "date":
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return AttrValue(date=datetime.strptime(value.strip(), fmt).date(), unit=ctype.unit)
            except ValueError:
                continue
        raise ValueError(f"not a date: {value!r}")
    return AttrValue(text=value, unit=ctype.unit)


@dataclass
class TransformResult:
    features: list[Feature]
    warnings: list[str]
    skipped: int = 0


def transform_features(
    cfg: WfsSource | CsvSource, raw: list[RawFeature], needs_geometry: bool
) -> TransformResult:
    """Apply mapping and type conversion; reproject and repair geometries."""
    warnings: list[str] = []
    out: dict[str, Feature] = {}
    dup = invalid = bad_values = skipped = no_geom = 0
    decimal = cfg.decimal if isinstance(cfg, CsvSource) else "."
    for rf in raw:
        key_raw = rf.properties.get(cfg.feature_key)
        if not key_raw:
            skipped += 1
            continue
        key = str(key_raw)
        geom = None
        if needs_geometry:
            if rf.geometry is None or rf.geometry.is_empty:
                no_geom += 1
                continue
            geom = to_wgs84(rf.geometry, cfg.crs_source)
            if not geom.is_valid:
                invalid += 1
                geom = shapely.make_valid(geom)
            geom = shapely.force_2d(geom)
        attrs: dict[str, AttrValue] = {}
        for src_field, value in rf.properties.items():
            target = cfg.mapping.get(src_field, src_field if cfg.keep_unmapped else None)
            if target is None:
                continue
            try:
                conv = convert(value, cfg.types.get(target, ColumnType()), decimal)
            except ValueError:
                bad_values += 1
                continue
            if conv is not None:
                attrs[target] = conv
        if key in out:
            dup += 1
            continue
        feat = Feature(key=key, geom=geom, attrs=attrs)
        if geom is not None:
            feat.geom_hash = geom_digest(geom)
        out[key] = feat
    for count, text in (
        (skipped, "records without feature_key skipped"),
        (no_geom, "records without geometry skipped"),
        (dup, "duplicate feature_key values dropped (first kept)"),
        (invalid, "invalid geometries repaired (make_valid)"),
        (bad_values, "values not convertible to configured type dropped"),
    ):
        if count:
            warnings.append(f"{count} {text}")
    return TransformResult(list(out.values()), warnings, skipped)
