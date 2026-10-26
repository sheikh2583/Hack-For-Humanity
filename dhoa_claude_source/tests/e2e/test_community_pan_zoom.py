"""Browser check: the Community map also keeps its view (no rerun, no snap-back).

Run manually: ``DHOA_E2E=1 pytest tests/e2e/test_community_pan_zoom.py -s``
(needs the real data, streamlit and Playwright Chromium).
"""

from __future__ import annotations

import os

import pytest

from tests.e2e.test_map_pan_zoom import ROOT, server  # noqa: F401  (reuse the fixture)

pytestmark = pytest.mark.skipif(os.environ.get("DHOA_E2E") != "1", reason="set DHOA_E2E=1 to run")


def test_community_map_pan_and_zoom_do_not_rerun(server: str) -> None:  # noqa: F811
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        received: list[int] = []
        page.on("websocket", lambda ws: ws.on("framereceived", lambda frame: received.append(len(frame))))
        page.goto(server)
        page.get_by_text("কমিউনিটি").first.click()
        page.get_by_placeholder("জায়গার নাম লিখে খুঁজুন").first.click()
        page.keyboard.type("Savar")
        page.keyboard.press("Enter")
        frame = page.frame_locator("iframe[title*='streamlit_folium']").first
        frame.locator(".leaflet-control-zoom-in").wait_for(timeout=60_000)
        page.wait_for_timeout(3_000)
        before = len(received)
        frame.locator(".leaflet-control-zoom-in").click()
        page.wait_for_timeout(1_000)
        scale = frame.locator(".leaflet-control-scale-line").first.inner_text()
        box = frame.locator(".leaflet-container").bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 120, box["y"] + box["height"] / 2 + 60, steps=10)
        page.mouse.up()
        page.wait_for_timeout(4_000)
        assert len(received) == before, "community pan/zoom triggered a rerun"
        assert frame.locator(".leaflet-control-scale-line").first.inner_text() == scale
        browser.close()
