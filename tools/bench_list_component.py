"""Time the priority-list iframe component in real Chromium (no Streamlit needed).

Usage: ``python tools/bench_list_component.py [--rows 2135] [--parquet PATH] [--repeat 5]``.
Input: ``app/components/priority_candidate_list/index.html`` plus rows built the way the app builds
them (``kiln_data.build_list_frame``): from a synthetic frame by default, or from the real
``data/processed/kilns_prioritised.parquet`` with ``--parquet`` (needs geopandas/pyarrow).
Output: a Markdown table of milliseconds for (a) the first render, (b) a repeat render with identical
arguments, (c) a render where only ``selected_id`` changed, each at 1x and 4x CPU throttle and at a
desktop (1280 px) and a phone (412 px) width, plus DOM node count and payload size.

Streamlit posts a ``streamlit:render`` message to the iframe on every rerun that emits the element, so
(b) and (c) are what every marker click, selection and filter rerun costs the browser. Timing covers
JS plus style/layout up to the next painted frame. CPU throttling is Chromium's CDP
``Emulation.setCPUThrottlingRate``; it is a rough proxy for a phone, not a measurement of one.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import app.kiln_data as kd  # noqa: E402

COMPONENT = ROOT / "app" / "components" / "priority_candidate_list" / "index.html"
RULES = [
    {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3},
    {"id": "near_hospital", "feature": "hospitals", "buffer_m": 1000, "severity": 3},
]


def _synthetic(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(5)
    frame = pd.DataFrame(
        {
            "kiln_id": [f"k{i}" for i in range(n)], "lat": 22.5 + rng.random(n) * 2, "lon": 88.5 + rng.random(n) * 3,
            "district": rng.choice(["Dhaka", "Gazipur", "Rajshahi", "Chittagong", "Chapainawabganj"], n),
            "upazila": rng.choice([f"U{i}" for i in range(58)], n), "class": rng.choice(["Zigzag", "FCBK"], n),
            "priority_band": rng.choice(["High", "Medium", "Low"], n, p=[0.2, 0.4, 0.4]), "priority": rng.random(n),
            "dist_schools_m": rng.choice([200.0, 3000.0], n), "dist_hospitals_m": rng.choice([800.0, np.nan], n),
        }
    )
    return kd.prepare_display_frame(frame, RULES, version="bench")


def _payload(frame: pd.DataFrame, rules: list[dict]) -> dict:
    listing = kd.build_list_frame(frame, rules)
    return {
        "columns": listing.columns.tolist(),
        "rows": listing.astype(str).values.tolist(),
        "kiln_ids": frame["kiln_id"].astype(str).tolist(),
        "select_label": "View kiln", "selected_label": "Selected", "aria_label": "Priority list",
        "aria_select_fmt": "{0}: {1}", "lang": "en", "height": 640, "selected_id": None,
    }


# Runs inside the page: post one render message, wait two animation frames, return elapsed ms.
_TIME_RENDER = """
async (args) => {
  const start = performance.now();
  window.postMessage({ type: 'streamlit:render', args }, '*');
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return performance.now() - start;
}
"""


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else float("nan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=2135)
    parser.add_argument("--parquet", default="")
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright

    if args.parquet:
        import app.streamlit_app as dashboard  # noqa: PLC0415 - heavy import, only for real data

        frame = dashboard.get_prepared_data(Path(args.parquet))
        rules = dashboard._siting_rules()
        source = f"real parquet, {len(frame):,} rows"
    else:
        frame, rules, source = _synthetic(args.rows), RULES, f"synthetic, {args.rows:,} rows"
    base = _payload(frame, rules)
    size_kb = len(json.dumps(base, ensure_ascii=False).encode("utf-8")) / 1024
    ids = base["kiln_ids"]
    selected = {**base, "selected_id": ids[len(ids) // 2]}
    print(f"data: {source}; render-message payload {size_kb:,.0f} KB\n")
    print("| width | CPU | first render ms | identical re-render ms | selection-only change ms | DOM nodes |")
    print("|---|---|---|---|---|---|")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1280, 412):
            for throttle in (1, 4):
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.goto(COMPONENT.as_uri())
                client = page.context.new_cdp_session(page)
                client.send("Emulation.setCPUThrottlingRate", {"rate": throttle})
                first = page.evaluate(_TIME_RENDER, base)
                same = [page.evaluate(_TIME_RENDER, base) for _ in range(args.repeat)]
                flips = []
                for index in range(args.repeat):
                    flips.append(page.evaluate(_TIME_RENDER, selected if index % 2 == 0 else base))
                nodes = page.evaluate("document.getElementsByTagName('*').length")
                print(f"| {width} | {throttle}x | {first:,.0f} | {_median(same):,.0f} | {_median(flips):,.0f} | {nodes:,} |")
                page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
