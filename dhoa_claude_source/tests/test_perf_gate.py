"""M8 performance gate on 2,135 synthetic rows (targets from the brief).

Targets: filter change < 1 s, list frame < 0.3 s, build_map < 2 s, map HTML
< 1 MB, community search < 0.3 s. Set ``DHOA_PERF_FACTOR`` (e.g. 3) on slow CI.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd
import pytest

import app.community as cm
import app.kiln_data as kd

FACTOR = float(os.environ.get("DHOA_PERF_FACTOR", "1"))
RULES = [
    {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3},
    {"id": "near_hospital", "feature": "hospitals", "buffer_m": 1000, "severity": 3},
]


@pytest.fixture(scope="module")
def prepared() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    n = 2135
    frame = pd.DataFrame(
        {
            "kiln_id": [f"k{i}" for i in range(n)],
            "lat": 22.5 + rng.random(n) * 2.0, "lon": 88.5 + rng.random(n) * 3.0,
            "district": rng.choice(["Dhaka", "Gazipur", "Rajshahi", "Chittagong", "Chapainawabganj"], n),
            "upazila": rng.choice([f"U{i}" for i in range(58)], n),
            "class": rng.choice(["Zigzag", "FCBK"], n),
            "priority_band": rng.choice(["High", "Medium", "Low"], n, p=[0.2, 0.4, 0.4]),
            "priority": rng.random(n),
            "dist_schools_m": rng.choice([200.0, 3000.0], n),
            "dist_hospitals_m": rng.choice([800.0, np.nan], n),
            "breached_rules": [["near_school"]] * n,
        }
    )
    return kd.prepare_display_frame(frame, RULES, version="perf")


def _timed(fn, repeat: int = 3) -> float:
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


def test_filter_under_one_second(prepared: pd.DataFrame) -> None:
    key = kd.make_filter_key("Dhaka", kd.ALL_AREAS, kd.ALL_KILN_TYPES, ("High", "Medium"))
    assert _timed(lambda: kd.take_candidates(prepared, kd.filter_positions(prepared, key))) < 1.0 * FACTOR


def test_list_frame_under_300_ms(prepared: pd.DataFrame) -> None:
    assert _timed(lambda: kd.build_list_frame(prepared, RULES)) < 0.3 * FACTOR


def test_community_search_under_300_ms(prepared: pd.DataFrame) -> None:
    place = cm.point_place("p", 23.5, 90.0)
    assert _timed(lambda: cm.search(prepared, place, 10_000)) < 0.3 * FACTOR


def test_marker_payload_is_fast_and_small(prepared: pd.DataFrame) -> None:
    import json

    seconds = _timed(lambda: kd.marker_payload(prepared, RULES))
    assert seconds < 2.0 * FACTOR
    assert len(json.dumps(kd.marker_payload(prepared, RULES))) < 1_000_000
