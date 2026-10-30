"""Create landing-page screenshots from the static demo served at SHOT_URL (headless)."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("SHOT_URL", "http://localhost:8099").rstrip("/")
OUT = Path("site/assets")


def poll(page, expr: str) -> None:
    for _ in range(200):
        if page.evaluate(expr):
            return
        page.wait_for_timeout(300)
    raise SystemExit(f"timeout: {expr}")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1200, "height": 630}, locale="de-DE")
    page.goto(f"{URL}/demo/#karte")
    poll(page, "!!(window.__map && window.__map.loaded())")
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT / "step1.png"))
    page.screenshot(path=str(OUT / "og.png"))
    page.evaluate("window.__map.jumpTo({center:[13.0645,52.3989],zoom:10})")
    poll(page, "window.__map.areTilesLoaded()")
    page.wait_for_timeout(1500)
    pt = page.evaluate("(()=>{const p=window.__map.project([13.0645,52.3989]);return [p.x,p.y]})()")
    box = page.locator("#map").bounding_box()
    page.mouse.click(box["x"] + pt[0], box["y"] + pt[1])
    page.wait_for_selector("#info table")
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "step2.png"))
    page.goto(f"{URL}/demo/#berichte")
    page.wait_for_selector("#repview pre")
    page.screenshot(path=str(OUT / "step3.png"))
    b.close()
