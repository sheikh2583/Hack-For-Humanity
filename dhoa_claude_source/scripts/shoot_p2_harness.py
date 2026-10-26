"""P2 harness: render the real hero markup + new CSS with real fonts (no Streamlit needed).

Usage: python scripts/shoot_p2_harness.py <out_dir>. Mocks the nav and buttons with plain HTML,
so it proves layout/text-length behaviour of the hero, not Streamlit's widget DOM.
"""
from __future__ import annotations

import http.server
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app.hero as hero  # noqa: E402
import app.strings as T  # noqa: E402
import app.styles as styles  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SITE = Path(tempfile.mkdtemp(prefix="dhoa_p2_")); (SITE / "app").mkdir()
(SITE / "app" / "static").symlink_to(ROOT / "app" / "static", target_is_directory=True)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=str(SITE), **k)
    def log_message(self, *a): pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def page(lang: str, stress: bool) -> str:
    t = lambda n: T.text(n, lang)  # noqa: E731
    mission, sub = t("HERO_MISSION"), t("HERO_SUB")
    values = ["2,135", "430", "5", "2026-04-24"]
    if stress:  # long copy and long numbers must not break the layout
        mission, sub = mission + " " + mission, sub + " " + sub
        values = ["12,345,678", "1,234,567", "64", "2026-04-24"]
    metrics = list(zip(values, [t("METRIC_TOTAL_CANDIDATES"), t("METRIC_HIGH_PRIORITY_KILNS"), t("HERO_METRIC_DISTRICTS"), t("METRIC_LAST_UPDATED")]))
    nav = "".join(f"<div class='tab{' on' if i == 0 else ''}'>{t(n)}</div>" for i, n in enumerate(("NAV_OVERVIEW", "NAV_MAP", "NAV_NEAR_ME", "NAV_ABOUT")))
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    {styles.page_css(t('PAGE_LOADING'))}<style>
    body{{margin:0;padding:12px 20px;background:var(--dhoa-color-background);color:var(--dhoa-color-text);font-family:var(--dhoa-font);line-height:1.65}}
    .nav{{display:flex;gap:6px;margin:10px 0}}.tab{{flex:1;min-height:44px;display:flex;align-items:center;justify-content:center;text-align:center;border:1px solid var(--dhoa-color-border-strong);border-radius:10px;background:var(--dhoa-color-raised);font-weight:600;padding:0 6px}}
    .tab.on{{background:var(--dhoa-color-primary);border-color:var(--dhoa-color-primary)}}
    .acts{{display:flex;gap:8px}}.acts div{{flex:1;min-height:44px;display:flex;align-items:center;justify-content:center;text-align:center;border-radius:10px;font-weight:700;padding:4px 8px;border:1px solid var(--dhoa-color-border-strong);background:var(--dhoa-color-raised)}}
    .acts .p{{background:var(--dhoa-color-primary);border-color:var(--dhoa-color-primary)}}</style></head><body>
    <h1 class="dhoa-brand-title" style="margin:0">{T.text('APP_TITLE', lang) if hasattr(T,'APP_TITLE') else 'Dhoa'}</h1>
    <div class="nav">{nav}</div><hr>
    {hero.hero_html(mission, sub, metrics)}
    <div class="acts"><div class="p">{t('HERO_CTA_MAP')}</div><div>{t('HERO_CTA_NEAR_ME')}</div></div></body></html>"""


with sync_playwright() as p:
    b = p.chromium.launch()
    for stress in (False, True):
        for lang in ("bn", "en"):
            (SITE / "index.html").write_text(page(lang, stress), encoding="utf-8")
            for w in (360, 768, 1280):
                pg = b.new_page(viewport={"width": w, "height": 700})
                pg.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
                pg.evaluate("document.fonts.ready.then(() => 1)"); pg.wait_for_timeout(300)
                over = pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                tag = f"hero_{'long_' if stress else ''}{lang}_{w}"
                pg.screenshot(path=str(OUT / f"{tag}.png"), full_page=True)
                print(tag, "H-OVERFLOW" if over else "ok"); pg.close()
    b.close()
