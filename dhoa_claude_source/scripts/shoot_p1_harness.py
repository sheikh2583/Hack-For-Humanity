"""P1 before/after harness: apply the OLD and NEW page CSS to mock Dhoa markup and screenshot it.

Usage: python scripts/shoot_p1_harness.py <old_app_dir> <out_dir>
No Streamlit needed. It shows tokens, type, tiles, chips, buttons, the language pill and the
candidate-list component. It does NOT prove Streamlit's own widget selectors (see HANDOFF_P1).
"""
from __future__ import annotations

import http.server
import importlib.util
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OLD = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


def load(app_dir: Path, name: str):
    sys.path.insert(0, str(app_dir))
    for mod in ("design_tokens", "styles"):
        sys.modules.pop(mod, None)
        sys.modules.pop(f"app.{mod}", None)
    spec = importlib.util.spec_from_file_location(name, app_dir / "styles.py")
    # styles.py imports ``from app import design_tokens``; fall back to the sibling module
    import types
    pkg = types.ModuleType("app"); pkg.__path__ = [str(app_dir)]; sys.modules["app"] = pkg
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    sys.path.pop(0)
    return mod


TEXT = {
    "bn": dict(title="ধোঁয়া", sub="বাংলাদেশের ইটভাটা পর্যবেক্ষণ ড্যাশবোর্ড", loading="লোড হচ্ছে",
               tiles=[("২,১৩৫", "মোট ইটভাটা"), ("৪৩০", "উচ্চ অগ্রাধিকার"), ("৫", "জেলা"), ("২০২৬-০৪", "তথ্যের তারিখ")],
               chips=[("High", "উচ্চ"), ("Medium", "মাঝারি"), ("Low", "নিম্ন")],
               btn1="মানচিত্র দেখুন", btn2="আমার কাছের ভাটা", lang=("বাংলা", "English"),
               rows=[("ফজলুল হক, সাভার", "জিগজ্যাগ", "২৫০ মি."), ("চাঁপাইনবাবগঞ্জ সদর", "স্থায়ী চিমনি", "১,২০০ মি.")],
               head=("এলাকা", "ধরন", "স্কুল থেকে দূরত্ব")),
    "en": dict(title="Dhoa", sub="Bangladesh brick kiln monitoring dashboard", loading="Loading",
               tiles=[("2,135", "Total kilns"), ("430", "High priority"), ("5", "Districts"), ("2026-04", "Data date")],
               chips=[("High", "High"), ("Medium", "Medium"), ("Low", "Low")],
               btn1="Explore the map", btn2="Find kilns near me", lang=("বাংলা", "English"),
               rows=[("Fazlul Haque, Savar", "Zigzag", "250 m"), ("Chapainawabganj Sadar", "Fixed chimney", "1,200 m")],
               head=("Area", "Type", "Distance to school")),
}
GLYPH = {"High": "▲", "Medium": "◆", "Low": "●"}


def page(css: str, lang: str, new: bool) -> str:
    t = TEXT[lang]
    tiles = "".join(f"<div class='dhoa-metric'><strong>{v}</strong><span>{l}</span></div>" for v, l in t["tiles"])
    chips = "".join((f"<span class='dhoa-chip dhoa-chip--{b.lower()}'><span>{GLYPH[b]}</span>{l}</span>" if new
                     else f"<span style='margin-right:8px'>{GLYPH[b]} {l}</span>") for b, l in t["chips"])
    pill = "".join(f"<label class='{'on' if i == (0 if lang == 'bn' else 1) else ''}'>{x}</label>" for i, x in enumerate(t["lang"]))
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in t["rows"])
    head = "".join(f"<th>{h}</th>" for h in t["head"])
    pill_css = """
    .pill{display:inline-flex;padding:2px;border-radius:999px;border:1px solid var(--dhoa-color-border-strong);background:var(--dhoa-color-raised)}
    .pill label{min-height:40px;display:flex;align-items:center;padding:0 16px;border-radius:999px;font-weight:600;color:var(--dhoa-color-text-soft)}
    .pill label.on{background:var(--dhoa-color-primary);color:#fff}""" if new else """
    .pill label{padding:4px 10px}.pill label.on{color:#e53e3e}"""
    btn = ("<button class='b2'>%s</button><button class='b1'>%s</button>" % (t["btn2"], t["btn1"]))
    btn_css = ("""button{min-height:44px;padding:0 16px;font:inherit;font-weight:600;border-radius:10px;cursor:pointer}
    .b1{background:var(--dhoa-color-primary);color:#fff;border:1px solid var(--dhoa-color-primary)}
    .b2{background:var(--dhoa-color-raised);color:var(--dhoa-color-text);border:1px solid var(--dhoa-color-border-strong)}"""
               if new else """button{min-height:44px;padding:0 16px;font:inherit;border-radius:8px;border:1px solid #475569;background:#1e2329;color:#fafafa}
    .b1{background:#c53030;border-color:#c53030}""")
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    {css}<style>body{{margin:0;padding:12px 20px;background:var(--dhoa-color-background,#0e1117);color:var(--dhoa-color-text,#fafafa);font-family:var(--dhoa-font);line-height:1.5}}
    {pill_css}{btn_css}.row{{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}}
    .actions{{display:flex;gap:10px;margin:14px 0;flex-wrap:wrap}}.actions button{{flex:1 1 140px}}
    table{{border-collapse:collapse;width:100%;margin-top:12px}}th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid {'var(--dhoa-color-border)' if new else '#d69e2e'}}}
    th{{background:{'var(--dhoa-color-card)' if new else '#1e2329'}}}.sel td{{background:{'var(--dhoa-color-selected)' if new else '#3182ce'}}}
    .cap{{color:var(--dhoa-color-text-muted,#aab4c0);font-size:.85rem;margin:6px 0}}</style></head><body>
    <div class="row"><h1 class="dhoa-brand-title" style="margin:0">{t['title']}</h1><div class="pill">{pill}</div></div>
    <div class="cap">{t['sub']}</div>
    <div class="dhoa-metrics">{tiles}</div>
    <div style="margin:8px 0">{chips}</div>
    <div class="actions">{btn}</div>
    <table><tr>{head}</tr><tr class="sel">{rows.split('</tr>')[0].replace('<tr>','')}</tr>{rows.split('</tr>',1)[1]}</table>
    </body></html>"""


SITE = Path(tempfile.mkdtemp(prefix="dhoa_p1_"))
(SITE / "app").mkdir()
(SITE / "app" / "static").symlink_to(ROOT / "app" / "static", target_is_directory=True)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def log_message(self, *a):  # keep the console clean
        pass


_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Quiet)
PORT = _server.server_address[1]
threading.Thread(target=_server.serve_forever, daemon=True).start()


def main() -> None:
    old_styles = load(OLD, "old_styles")
    new_styles = load(ROOT / "app", "new_styles")
    fonts = ROOT / "app" / "static"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, styles, new in (("before", old_styles, False), ("after", new_styles, True)):
            for lang in ("bn", "en"):
                html = page(styles.page_css(TEXT[lang]["loading"]), lang, new)
                for width in (360, 768, 1280):
                    ctx = browser.new_context(viewport={"width": width, "height": 640})
                    pg = ctx.new_page()
                    (SITE / "index.html").write_text(html, encoding="utf-8")
                    pg.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
                    pg.evaluate("document.fonts.ready.then(() => document.fonts.size)")
                    pg.wait_for_timeout(300)
                    pg.screenshot(path=str(OUT / f"{label}_{lang}_{width}.png"), full_page=True)
                    overflow = pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                    loaded = pg.evaluate("[...document.fonts].filter(f => f.status === 'loaded').length")
                    print(label, lang, width, "h-overflow" if overflow else "ok", "fonts loaded:", loaded)
                    ctx.close()
        browser.close()


main()
