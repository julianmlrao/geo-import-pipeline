"""CSV adapter: URL or file, encoding and delimiter detection, WKT / lon-lat geometry."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from pathlib import Path

import requests
from shapely import wkt
from shapely.geometry import Point

from geo_import import http
from geo_import.adapters.base import FetchStats, RawFeature
from geo_import.config import CsvSource

DELIMITERS = ";,\t|"


def decode(raw: bytes, encoding: str | None) -> tuple[str, str]:
    """Decode bytes; without explicit encoding try UTF-8 (with BOM), then Windows-1252."""
    if encoding:
        return raw.decode(encoding), encoding
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


def detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample else ""
        return max(DELIMITERS, key=first.count)


class CsvAdapter:
    def __init__(
        self, cfg: CsvSource, session: requests.Session | None = None, base: Path | None = None
    ) -> None:
        self.cfg = cfg
        self.session = session
        self.base = base or Path(".")
        self.stats = FetchStats()
        self.encoding: str | None = None
        self.delimiter: str | None = None

    def _read(self) -> bytes:
        url = self.cfg.url
        if url.startswith(("http://", "https://")):
            return http.get(url, timeout=self.cfg.timeout, session=self.session).content
        path = Path(url.removeprefix("file://"))
        return (path if path.is_absolute() else self.base / path).read_bytes()

    def fetch(self) -> Iterator[RawFeature]:
        text, self.encoding = decode(self._read(), self.cfg.encoding)
        lines = text.splitlines()[self.cfg.skip_rows :]
        if not lines:
            return
        self.delimiter = self.cfg.delimiter or detect_delimiter("\n".join(lines[:20]))
        reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=self.delimiter)
        for i, row in enumerate(reader):
            props = {k.strip(): (v.strip() if v else None) for k, v in row.items() if k}
            yield RawFeature(props, self._geometry(props), str(i))

    def _geometry(self, props: dict[str, str | None]) -> Point | None:
        c = self.cfg
        if c.wkt_column:
            value = props.get(c.wkt_column)
            return wkt.loads(value) if value else None
        if c.lon_column and c.lat_column:
            lon, lat = props.get(c.lon_column), props.get(c.lat_column)
            if lon and lat:
                dec = c.decimal
                return Point(float(lon.replace(dec, ".")), float(lat.replace(dec, ".")))
        return None
