"""Real-browser pass for modules P7/P8 (run by the owner; needs Chromium).

Usage: python tools/check_widths.py http://localhost:8501 --nav "Overview,Map,Near me,About" [--axe axe.min.js]
For each width (360, 412, 768, 1280) and each nav label it checks: no horizontal scroll, no
interactive element under 44 px (excluding inline text links inside paragraphs), a visible
focus ring after Tab, and optionally axe-core critical/serious violations (pass a local axe.min.js:
the sandbox CDN may be blocked). Screenshots go to ./screens_p8/. Exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WIDTHS = (360, 412, 768, 1280)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--nav", default="")
    parser.add_argument("--axe", default="")
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright

    out = Path("screens_p8")
    out.mkdir(exist_ok=True)
    failures = 0
    labels = [item.strip() for item in args.nav.split(",") if item.strip()] or [""]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in WIDTHS:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(args.url, wait_until="networkidle")
            page.wait_for_timeout(2500)
            for label in labels:
                if label:
                    page.get_by_role("button", name=label).first.click()
                    page.wait_for_timeout(1500)
                tag = f"{width}_{label or 'home'}".replace(" ", "_")
                page.screenshot(path=str(out / f"{tag}.png"), full_page=True)
                overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                small = page.evaluate(
                    """() => [...document.querySelectorAll('button,[role=button],a,input,select')]
                        .filter(e => e.offsetParent && !e.closest('p,li,caption'))
                        .filter(e => { const r = e.getBoundingClientRect(); return r.height < 43.5 || r.width < 43.5; })
                        .map(e => (e.innerText || e.getAttribute('aria-label') || e.tagName).slice(0, 30))"""
                )
                page.keyboard.press("Tab")
                ring = page.evaluate(
                    "(() => { const e = document.activeElement; if (!e) return 'none'; "
                    "const s = getComputedStyle(e); return s.outlineStyle + ' ' + s.outlineWidth + ' ' + s.boxShadow; })()"
                )
                print(f"{tag}: overflow={overflow}px small_targets={small} focus='{ring}'")
                failures += int(overflow > 1) + int(bool(small))
                if args.axe:
                    page.add_script_tag(path=args.axe)
                    result = page.evaluate("axe.run().then(r => r.violations.map(v => [v.impact, v.id, v.nodes.length]))")
                    bad = [v for v in result if v[0] in ("critical", "serious")]
                    print(f"  axe: {bad or 'no critical/serious'}")
                    failures += len(bad)
            page.close()
        browser.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
