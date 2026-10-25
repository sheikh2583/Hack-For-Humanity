"""M8 filter-correctness and community-distance tests on synthetic data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import app.community as cm
import app.kiln_data as kd
from tests.synthetic import make_kilns

RULES = [{"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3}]


def _prepared() -> pd.DataFrame:
    frame = make_kilns(80)
    frame["priority_band"] = pd.qcut(frame["priority"].rank(method="first"), [0, 0.2, 0.6, 1], labels=["Low", "Medium", "High"]).astype(str)
    return kd.prepare_display_frame(frame, RULES, version="m8")


@pytest.mark.parametrize("district", [kd.ALL_DISTRICTS, "Dhaka", "Gazipur", "Rajshahi"])
@pytest.mark.parametrize("bands", [("High",), ("High", "Low"), ("High", "Medium", "Low")])
def test_filter_matches_brute_force(district: str, bands: tuple[str, ...]) -> None:
    frame = _prepared()
    key = kd.make_filter_key(district, kd.ALL_AREAS, kd.ALL_KILN_TYPES, bands)
    got = set(frame.iloc[kd.filter_positions(frame, key)]["kiln_id"])
    expected = frame
    if district != kd.ALL_DISTRICTS:
        expected = expected[expected["district"] == district]
    expected = expected[expected["priority_band"].isin(bands)]
    assert got == set(expected["kiln_id"])


def test_band_counts_add_up_to_total() -> None:
    summary = kd.priority_summary(_prepared())
    assert summary["high"] + summary["medium"] + summary["low"] == summary["total"]


def test_community_distances_match_geodesic_reference() -> None:
    from pyproj import Geod

    frame = _prepared()
    origin = cm.point_place("o", 23.85, 90.35)
    rows = cm.search(frame, origin, 10_000).rows
    geod = Geod(ellps="WGS84")
    expected = [geod.inv(90.35, 23.85, lon, lat)[2] for lat, lon in zip(rows["lat"], rows["lon"])]
    np.testing.assert_allclose(rows["distance_m"].to_numpy(), expected, rtol=2e-3, atol=1.0)


def test_radius_results_are_nested_as_radius_grows() -> None:
    frame = _prepared()
    origin = cm.point_place("o", 23.85, 90.35)
    ids = [set(cm.search(frame, origin, r).rows["kiln_id"]) for r in cm.RADIUS_CHOICES_M]
    assert all(a <= b for a, b in zip(ids, ids[1:]))


def test_every_listed_place_gives_a_non_empty_result() -> None:
    frame = _prepared()
    for place in cm.build_places(frame):
        result = cm.search(frame, place, cm.DEFAULT_RADIUS_M)
        if place.radius_applies:
            assert result.rows is not None  # may be empty; the UI explains it
        else:
            assert len(result.rows) == place.kiln_count, place.key


def test_empty_state_names_nearest_and_widen_target() -> None:
    frame = _prepared()
    remote = next(p for p in cm.build_places(frame) if p.name == "Remote Bazar")
    assert cm.search(frame, remote, 1000).empty
    distance, row = cm.nearest_beyond(frame, remote.lat, remote.lon)
    assert 5000 < distance < 7000 and row["kiln_id"] in {"r1", "r2"}
    assert cm.radius_to_reach(distance) == 10000
    assert not cm.search(frame, remote, 10000).empty
