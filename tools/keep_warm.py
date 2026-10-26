"""Open the deployed app in a real browser so it does not go to sleep.

Usage: ``DHOA_APP_URL=https://<your-app>.streamlit.app python tools/keep_warm.py``.
A plain HTTP request does not count as activity (and does not wake a sleeping
app), so this drives headless Chromium via Playwright: it opens the page, clicks
the "get this app back up" button if the sleep screen is shown, waits for the
app to render, stays ~20 s on the page, and exits 0. Exit 1 on failure.
Needs ``pip install playwright && playwright install chromium``.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    url = os.environ.get("DHOA_APP_URL", "").strip()
    if not url.startswith("https://"):
        print("Set DHOA_APP_URL to the https URL of the deployed app.")
        return 1
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, timeout=120_000)
        wake = page.get_by_role("button", name="Yes, get this app back up")
        if wake.count():
            wake.first.click()
            print("app was asleep; wake button clicked")
        try:
            page.locator("[data-testid='stApp']").wait_for(timeout=180_000)
            page.get_by_text("ধোঁয়া").first.wait_for(timeout=180_000)
        except Exception as error:  # noqa: BLE001
            print(f"app did not render: {error}")
            browser.close()
            return 1
        page.wait_for_timeout(20_000)
        browser.close()
    print("app is warm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
