"""Browser check that pan/zoom neither rerun the script nor snap the view back.

Run manually (needs the real data, streamlit and a Playwright Chromium):

    DHOA_E2E=1 pytest tests/e2e/test_map_pan_zoom.py -s

How it works: start ``streamlit run app/streamlit_app.py``; open it; zoom the
Leaflet map inside the st_folium iframe with its zoom buttons and drag it; then
assert (1) the Streamlit websocket received no script-run messages after the
interaction (zero reruns) and (2) the scale bar / zoom level after waiting is the
same as right after the gesture (no snap-back). The same check is the manual
procedure in HANDOFF_M3.md for the Community view.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(os.environ.get("DHOA_E2E") != "1", reason="set DHOA_E2E=1 to run")
PORT = 8599


@pytest.fixture(scope="module")
def server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py", "--server.port", str(PORT),
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(8)
    yield f"http://localhost:{PORT}"
    proc.terminate()


def test_pan_and_zoom_do_not_rerun_or_snap_back(server: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        received: list[int] = []
        page.on("websocket", lambda ws: ws.on("framereceived", lambda frame: received.append(len(frame))))
        page.goto(server)
        frame = page.frame_locator("iframe[title*='streamlit_folium']").first
        frame.locator(".leaflet-control-zoom-in").wait_for(timeout=60_000)
        page.wait_for_timeout(3_000)

        frames_before = len(received)
        frame.locator(".leaflet-control-zoom-in").click()
        frame.locator(".leaflet-control-zoom-in").click()
        page.wait_for_timeout(1_000)
        scale_after_zoom = frame.locator(".leaflet-control-scale-line").first.inner_text()
        box = frame.locator(".leaflet-container").bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 150, box["y"] + box["height"] / 2 + 80, steps=10)
        page.mouse.up()
        page.wait_for_timeout(4_000)  # long enough for a rerun to snap the view back

        assert len(received) == frames_before, "pan/zoom triggered a script rerun"
        assert frame.locator(".leaflet-control-scale-line").first.inner_text() == scale_after_zoom
        browser.close()
