"""Adapter interface and the common feature record."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from shapely.geometry.base import BaseGeometry


@dataclass
class RawFeature:
    """Feature as read from a source, geometry still in the source CRS."""

    properties: dict[str, Any]
    geometry: BaseGeometry | None = None
    fid: str | None = None


@dataclass
class FetchStats:
    warnings: list[str] = field(default_factory=list)


class Adapter(Protocol):
    stats: FetchStats

    def fetch(self) -> Iterator[RawFeature]: ...
