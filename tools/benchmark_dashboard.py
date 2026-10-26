"""Time the dashboard hot paths on the real dataset (or a synthetic one).

Usage: ``python tools/benchmark_dashboard.py [--synthetic] [--repeat 3]``.
Input: ``data/processed/kilns_prioritised.parquet`` (unless ``--synthetic``,
2,135 made-up rows). Output: a Markdown table of best-of-N seconds for load,
filter, list frame, community search, marker payload and the rendered base-map
HTML size. CPU only; no GPU, network or Streamlit session needed for these
paths except ``build_map`` which is timed through the app module.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import app.community as cm  # noqa: E402
import app.kiln_data as kd  # noqa: E402

RULES = [{"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3}]


def _synthetic(n: int = 2135) -> pd.DataFrame:
    rng = np.random.default_rng(5)
    frame = pd.DataFrame(
        {
            "kiln_id": [f"k{i}" for i in range(n)], "lat": 22.5 + rng.random(n) * 2, "lon": 88.5 + rng.random(n) * 3,
            "district": rng.choice(["Dhaka", "Gazipur", "Rajshahi", "Chittagong", "Chapainawabganj"], n),
            "upazila": rng.choice([f"U{i}" for i in range(58)], n), "class": rng.choice(["Zigzag", "FCBK"], n),
            "priority_band": rng.choice(["High", "Medium", "Low"], n, p=[0.2, 0.4, 0.4]),
            "priority": rng.random(n), "dist_schools_m": rng.choice([200.0, 3000.0], n),
        }
    )
    return kd.prepare_display_frame(frame, RULES, version="bench")


def _best(fn, repeat: int) -> float:
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return min(times)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    rows: list[tuple[str, str]] = []
    if args.synthetic:
        frame = _synthetic()
        rows.append(("data", "synthetic 2,135 rows"))
    else:
        import app.streamlit_app as dashboard

        start = time.perf_counter()
        frame = dashboard.get_prepared_data()
        rows.append(("load + prepare (first call)", f"{time.perf_counter() - start:.2f} s"))
        if frame is None:
            raise SystemExit("data/processed/kilns_prioritised.parquet not found")
    key = kd.make_filter_key("Dhaka", kd.ALL_AREAS, kd.ALL_KILN_TYPES, ("High", "Medium"))
    rules = RULES if args.synthetic else __import__("app.streamlit_app", fromlist=["x"])._siting_rules()
    rows += [
        ("filter (district+priority)", f"{_best(lambda: kd.take_candidates(frame, kd.filter_positions(frame, key)), args.repeat):.3f} s"),
        ("list frame", f"{_best(lambda: kd.build_list_frame(frame, rules), args.repeat):.3f} s"),
        ("marker payload", f"{_best(lambda: kd.marker_payload(frame, rules), args.repeat):.3f} s"),
        ("community search 10 km", f"{_best(lambda: cm.search(frame, cm.point_place('p', 23.8, 90.4), 10000), args.repeat):.3f} s"),
    ]
    print("| step | best of", args.repeat, "|\n|---|---|")
    for name, value in rows:
        print(f"| {name} | {value} |")


if __name__ == "__main__":
    main()
