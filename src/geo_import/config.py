"""Pydantic models for source configuration files (config/sources/*.yaml)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


class JoinConfig(BaseModel):
    """Attach CSV attributes to geometries of another source."""

    model_config = ConfigDict(extra="forbid")
    target_source: str
    on: str  # CSV column that holds the target's feature_key

    @model_validator(mode="before")
    @classmethod
    def _yaml_on_is_true(cls, data: Any) -> Any:
        """YAML 1.1 parses an unquoted `on:` key as boolean True."""
        if isinstance(data, dict) and True in data:
            data = {("on" if k is True else k): v for k, v in data.items()}
        return data


class ColumnType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text", "number", "date"] = "text"
    unit: str | None = None


class BaseSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    url: str
    license: str | None = None
    attribution: str | None = None
    schedule: str | None = None  # cron expression, optional
    mode: Literal["replace", "history"] = "replace"
    timeout: float = 120.0
    details: dict[str, Any] = Field(default_factory=dict)  # DCAT-AP-like extras
    mapping: dict[str, str] = Field(default_factory=dict)  # source field -> target attribute
    keep_unmapped: bool = False
    feature_key: str  # source field used as stable key


class WfsSource(BaseSource):
    type: Literal["wfs"]
    layer: str
    version: str = "2.0.0"
    crs_source: str = "EPSG:25833"
    page_size: int = Field(default=1000, ge=1)
    max_features: int | None = None
    geometry_field: str = "geom"
    filter: str | None = None  # raw OGC FES filter XML
    output_format: Literal["gml", "geojson"] = "gml"
    types: dict[str, ColumnType] = Field(default_factory=dict)  # per target attribute


class CsvSource(BaseSource):
    type: Literal["csv"]
    layer: str | None = None
    delimiter: str | None = None  # auto-detected if omitted
    encoding: str | None = None  # auto-detected if omitted
    decimal: str = ","
    skip_rows: int = 0
    crs_source: str = "EPSG:4326"
    wkt_column: str | None = None
    lon_column: str | None = None
    lat_column: str | None = None
    join: JoinConfig | None = None
    types: dict[str, ColumnType] = Field(default_factory=dict)  # per target attribute

    @model_validator(mode="after")
    def _geometry_mode(self) -> CsvSource:
        if self.join and self.feature_key != self.join.on:
            raise ValueError("with join, feature_key must equal join.on")
        modes = [bool(self.wkt_column), bool(self.lon_column and self.lat_column), bool(self.join)]
        if sum(modes) != 1:
            raise ValueError("exactly one of wkt_column, lon_column+lat_column, join is required")
        return self


SourceConfig = Annotated[WfsSource | CsvSource, Field(discriminator="type")]
_adapter: TypeAdapter[WfsSource | CsvSource] = TypeAdapter(SourceConfig)


def parse_source(data: dict[str, Any]) -> WfsSource | CsvSource:
    return _adapter.validate_python(data)


def load_sources(directory: Path) -> list[WfsSource | CsvSource]:
    """Load and validate all YAML files; duplicate source_ids and bad joins are errors."""
    sources: list[WfsSource | CsvSource] = []
    for path in sorted(directory.glob("*.y*ml")):
        try:
            sources.append(parse_source(yaml.safe_load(path.read_text(encoding="utf-8"))))
        except Exception as exc:  # report the file name, keep the cause
            raise ValueError(f"{path.name}: {exc}") from exc
    ids = [s.source_id for s in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source_id in configuration")
    for s in sources:
        if isinstance(s, CsvSource) and s.join and s.join.target_source not in ids:
            raise ValueError(f"{s.source_id}: join target {s.join.target_source!r} not configured")
    return sources


def sources_dir() -> Path:
    return Path(os.environ.get("GEO_IMPORT_CONFIG_DIR", "config/sources"))


def reports_dir() -> Path:
    return Path(os.environ.get("GEO_IMPORT_REPORTS_DIR", "reports"))


def database_dsn() -> str:
    if dsn := os.environ.get("GEO_IMPORT_DSN"):
        return dsn
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'geo')} "
        f"user={os.environ.get('POSTGRES_USER', 'geo_import')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', '')}"
    )
