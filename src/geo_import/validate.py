"""Schema checks against the configuration; produces warnings, errors for fatal cases."""

from __future__ import annotations

from geo_import.adapters.base import RawFeature
from geo_import.config import CsvSource, WfsSource


class ValidationError(RuntimeError):
    """Source data is unusable; the existing data of this source stays untouched."""


def check_schema(cfg: WfsSource | CsvSource, raw: list[RawFeature]) -> list[str]:
    if not raw:
        raise ValidationError("source returned no records; existing data kept")
    seen: set[str] = set()
    for rf in raw:
        seen.update(rf.properties)
    warnings: list[str] = []
    expected = set(cfg.mapping) | {cfg.feature_key}
    if isinstance(cfg, CsvSource) and cfg.join:
        expected.add(cfg.join.on)
    missing = sorted(expected - seen)
    if cfg.feature_key not in seen:
        raise ValidationError(f"feature_key field {cfg.feature_key!r} not found in source")
    if missing:
        warnings.append(f"configured fields missing in source: {', '.join(missing)}")
    if not cfg.keep_unmapped:
        extra = sorted(seen - expected)
        if extra:
            shown = ", ".join(extra[:8]) + (" …" if len(extra) > 8 else "")
            warnings.append(f"{len(extra)} unmapped source fields ignored: {shown}")
    return warnings
