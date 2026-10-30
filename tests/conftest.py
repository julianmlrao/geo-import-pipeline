from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from geo_import import load

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    dsn = os.environ.get("GEO_IMPORT_TEST_DSN")
    if not dsn:
        pytest.skip("GEO_IMPORT_TEST_DSN not set (needs PostGIS)")
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS geo_import CASCADE")
        load.migrate(c, str(ROOT / "db" / "migrations"))
        yield c
