"""Browser test against a running demo (headless). Run:

LIVE_URL=http://localhost:8080 DEMO_USER=demo DEMO_PASSWORD=... uv run pytest tests/e2e_live -q
"""

from __future__ import annotations

import os
import time

import pytest

pw = pytest.importorskip("playwright.sync_api")
URL = os.environ.get("LIVE_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(not URL, reason="LIVE_URL not set")
USER = os.environ.get("DEMO_USER", "demo")
PASSWORD = os.environ.get("DEMO_PASSWORD", "")


@pytest.fixture(scope="module")
def page():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")
        pg = ctx.new_page()
        yield pg
        browser.close()


def until(page, expr: str, timeout: float = 60.0) -> None:
    """Poll a JS expression via evaluate (wait_for_function would need unsafe-eval under our CSP)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if page.evaluate(expr):
            return
        page.wait_for_timeout(300)
    raise AssertionError(f"timeout waiting for {expr}")


def login(page, password: str) -> None:
    page.goto(f"{URL}/demo/login")
    page.fill("input[name=username]", USER)
    page.fill("input[name=password]", password)
    page.click("button[type=submit]")


def test_wrong_password_rejected(page):
    login(page, "falsch-" + PASSWORD)
    assert "falsch" in page.inner_text("body")
    assert "/sources" not in page.url


def test_full_flow(page):
    page.goto(URL + "/")
    page.click("text=Live-Demo öffnen")
    page.wait_for_url("**/demo/login")
    page.fill("input[name=username]", USER)
    page.fill("input[name=password]", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url("**/demo/sources")
    assert page.locator("tbody tr").count() >= 3

    page.click("nav >> text=Karte")
    page.wait_for_selector("#layers input[type=checkbox]")
    assert page.locator("#layers input[type=checkbox]").count() >= 2
    until(page, "!!(window.__map && window.__map.loaded())")
    page.evaluate("window.__map.jumpTo({center: [13.0645, 52.3989], zoom: 10})")
    until(page, "window.__map.areTilesLoaded()")
    pt = page.evaluate(
        "(() => { const p = window.__map.project([13.0645, 52.3989]); return [p.x, p.y]; })()"
    )
    box = page.locator("#map").bounding_box()
    page.mouse.click(box["x"] + pt[0], box["y"] + pt[1])
    page.wait_for_selector("#info table")
    text = page.inner_text("#info")
    assert "einwohner" in text and "Potsdam" in text

    page.click("nav >> text=Berichte")
    assert page.locator("tbody tr a").count() >= 1
    page.locator("tbody tr a").first.click()
    assert "Import-Bericht" in page.inner_text("article")

    page.click("nav >> text=Import")
    page.click("button:has-text('Import jetzt starten')")
    until(
        page,
        "/gestartet|Gedrosselt|läuft|Letzter/.test(document.getElementById('status').textContent)",
    )


def test_api_returns_geojson(page):
    r = page.request.get(f"{URL}/api/collections/geo_import.features/items.json?limit=1")
    assert r.ok and r.json()["type"] == "FeatureCollection"
