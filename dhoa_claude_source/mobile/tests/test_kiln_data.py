"""Tests for ``app/kiln_data.py`` (M2 data layer) using tiny synthetic data.

Input schema: synthetic kiln frames with the dashboard columns. Output: the
vectorised filter, list table, popup and distance helpers must agree with a
slow reference implementation of the behaviour they replaced.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

import app.kiln_data as kd
import app.strings as T

RULES = [
    {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3},
    {"id": "near_hospital", "feature": "hospitals", "buffer_m": 1000, "severity": 3},
    {"id": "near_settlement", "feature": "settlements", "buffer_m": 1000, "severity": 2},
    {"id": "near_railway", "feature": "railways", "buffer_m": 1000, "severity": 3},
    {"id": "near_wetland", "feature": "water", "buffer_m": 1000, "severity": 2},
    {"id": "near_government_forest", "feature": "government_forest", "buffer_m": 2000, "severity": 3},
]


def _frame(count: int = 60) -> pd.DataFrame:
    """Deterministic synthetic kilns covering ties, NaNs and missing bands."""
    rng = np.random.default_rng(7)
    districts = np.array(["Dhaka", "Gazipur", "Rajshahi"])[rng.integers(0, 3, count)]
    upazilas = np.array(["Savar", "Tongi", "Boalia", "Mirpur"])[rng.integers(0, 4, count)]
    bands = np.array(["High", "Medium", "Low"])[rng.integers(0, 3, count)]
    priority = rng.integers(0, 6, count).astype(float)  # many ties on purpose
    priority[::11] = np.nan
    frame = pd.DataFrame(
        {
            "kiln_id": [f"k{i}" for i in range(count)],
            "lat": 23.5 + rng.random(count),
            "lon": 90.0 + rng.random(count),
            "district": districts,
            "upazila": upazilas,
            "class": np.array(["Zigzag", "FCBK"])[rng.integers(0, 2, count)],
            "priority_band": bands,
            "priority": priority,
            "detection_status": np.array([kd.NEW_CANDIDATE_STATUS, kd.KNOWN_CANDIDATE_STATUS])[
                rng.integers(0, 2, count)
            ],
            "dist_schools_m": rng.choice([150.0, 900.0, 1500.0, 12000.0, np.nan], count),
            "dist_hospitals_m": rng.choice([300.0, 1200.0, np.nan], count),
            "dist_settlements_m": rng.choice([50.0, 5000.0], count),
            "dist_railways_m": rng.choice([999.0, 1000.0, 4000.0, np.nan], count),
            "dist_water_m": rng.choice([10.0, 3000.0], count),
            "dist_government_forest_m": rng.choice([1999.0, 2000.0, 9000.0, np.nan], count),
        }
    )
    frame["breached_rules"] = [
        ["near_school"] if i % 3 == 0 else ([] if i % 3 == 1 else ["near_hospital", "near_railway"])
        for i in range(count)
    ]
    return frame


def _reference_filter(
    frame: pd.DataFrame, district: str, upazila: str, kiln_type: str, priorities: list[str]
) -> list[str]:
    """Slow copy of the pre-M2 ``get_filtered_gdf`` inspector branch (ids only)."""
    result = frame.copy()
    if district != kd.ALL_DISTRICTS:
        result = result[result["district"].astype(str).eq(district)]
    if upazila != kd.ALL_AREAS:
        result = result[result["upazila"].astype(str).eq(upazila)]
    if kiln_type != kd.ALL_KILN_TYPES:
        result = result[result["class"].astype(str).eq(kiln_type)]
    known = result["priority_band"].astype(str).isin(kd.PRIORITY_ORDER)
    if known.any():
        result = result[result["priority_band"].astype(str).isin(priorities)]
    result = result.sort_values("priority", ascending=False, na_position="last", kind="stable")
    return result["kiln_id"].tolist()


def test_make_filter_key_normalises_labels_and_defaults() -> None:
    """Bangla and English priorities map to canonical ordered English values."""
    assert kd.make_filter_key().priorities == ("High", "Medium", "Low")
    assert kd.make_filter_key(priorities=[T.LOW, "High"]).priorities == ("High", "Low")
    assert kd.make_filter_key(priorities=[]).priorities == ("High", "Medium", "Low")
    assert kd.make_filter_key(priorities=["bogus"]).priorities == ("High", "Medium", "Low")
    key = kd.make_filter_key("Dhaka", "Savar", "FCBK", [T.MEDIUM])
    assert key == ("Dhaka", "Savar", "FCBK", ("Medium",))
    assert hash(key) == hash(kd.make_filter_key("Dhaka", "Savar", "FCBK", ["Medium"]))


def test_filter_positions_matches_reference_for_all_combinations() -> None:
    """The vectorised filter returns the same ids in the same order as the old one."""
    frame = _frame()
    districts = [kd.ALL_DISTRICTS, "Dhaka", "Gazipur", "Nowhere"]
    upazilas = [kd.ALL_AREAS, "Savar", "Mirpur"]
    types = [kd.ALL_KILN_TYPES, "FCBK", "Zigzag"]
    priority_sets = [["High"], ["Medium", "Low"], ["High", "Medium", "Low"]]
    for district, upazila, kiln_type, priorities in itertools.product(
        districts, upazilas, types, priority_sets
    ):
        key = kd.make_filter_key(district, upazila, kiln_type, priorities)
        got = kd.filter_candidates(frame, key)["kiln_id"].tolist()
        assert got == _reference_filter(frame, district, upazila, kiln_type, priorities)


def test_filter_skips_priority_when_no_known_band() -> None:
    """Rows with only unknown bands are not filtered to zero."""
    frame = _frame(6)
    frame["priority_band"] = kd.UNKNOWN_PRIORITY
    key = kd.make_filter_key(priorities=["High"])
    assert len(kd.filter_candidates(frame, key)) == 6


def test_filter_missing_columns_returns_no_rows() -> None:
    """A filter on a column the data lacks yields an empty result."""
    frame = _frame(5).drop(columns=["district", "upazila", "class"])
    for key in (
        kd.make_filter_key(district="Dhaka"),
        kd.make_filter_key(upazila="Savar"),
        kd.make_filter_key(kiln_type="FCBK"),
    ):
        assert kd.filter_candidates(frame, key).empty


def test_take_candidates_adds_unknown_band_and_returns_a_copy() -> None:
    """Without priority_band the column is added; the source is never modified."""
    frame = _frame(4).drop(columns=["priority_band"])
    result = kd.filter_candidates(frame, kd.make_filter_key())
    assert set(result["priority_band"]) == {kd.UNKNOWN_PRIORITY}
    assert "priority_band" not in frame.columns
    result.loc[result.index[0], "kiln_id"] = "changed"
    assert "changed" not in frame["kiln_id"].tolist()


def test_parse_signal_ids_accepts_lists_arrays_and_strings() -> None:
    """Every storage form of breached_rules decodes to the same id set."""
    expected = frozenset({"near_school", "near_hospital"})
    assert kd.parse_signal_ids(["near_school", "near_hospital"]) == expected
    assert kd.parse_signal_ids(np.array(["near_school", "near_hospital"])) == expected
    assert kd.parse_signal_ids('["near_school", "near_hospital"]') == expected
    assert kd.parse_signal_ids("near_school, near_hospital") == expected
    for empty in (None, float("nan"), "", [], ["", "nan", None]):
        assert kd.parse_signal_ids(empty) == frozenset()


def test_area_display_name_cases() -> None:
    """Area labels cover both parts, one part, and none."""
    assert kd.area_display_name("Savar", "Dhaka") == f"Savar, {T.DISTRICT_DHAKA}"
    assert kd.area_display_name(None, "Dhaka") == T.DISTRICT_DHAKA
    assert kd.area_display_name("Savar", None) == "Savar"
    assert kd.area_display_name(float("nan"), "  ") == T.UNKNOWN_AREA


def test_distance_cells_formats_and_marks_buffer() -> None:
    """Metres/kilometres, missing data and the in-buffer warning mark."""
    cells = kd.distance_cells(np.array([340.0, 1000.0, 2500.0, np.nan]), 1000.0)
    assert cells[0] == T.M_FMT.format(340.0) + " ⚠️"
    assert cells[1] == T.KM_FMT.format(1.0)  # exactly on the buffer is not inside it
    assert cells[2] == T.KM_FMT.format(2.5)
    assert cells[3] == T.NO_DATA
    assert kd.distance_cells(np.array([5.0]), math.nan) == [T.M_FMT.format(5.0)]


def test_build_list_frame_matches_row_by_row_reference() -> None:
    """The vectorised list table equals the former per-row construction."""
    frame = _frame(40)
    got = kd.build_list_frame(frame, RULES)

    icons = kd.PRIORITY_GLYPHS
    labels = {
        "schools": T.SCHOOL, "hospitals": T.HOSPITAL, "railways": T.RAILWAY,
        "settlements": T.SETTLEMENT, "government_forest": T.GOVERNMENT_FOREST, "water": T.WETLAND,
    }
    records = []
    for _, row in frame.iterrows():
        record = {
            T.VIEW_KILN: T.VIEW_KILN,
            T.AREA: f"📍 {kd.area_display_name(row['upazila'], row['district'])}",
            T.PRIORITY: f"{icons.get(row['priority_band'], '')} {kd.priority_label(row['priority_band'])}".strip(),
        }
        for rule in RULES:
            value = row.get(f"dist_{rule['feature']}_m")
            if pd.isna(value):
                cell = T.NO_DATA
            else:
                cell = T.KM_FMT.format(value / 1000) if value >= 1000 else T.M_FMT.format(value)
                if value < rule["buffer_m"]:
                    cell += " ⚠️"
            record[T.DISTANCE_FROM_FMT.format(labels[rule["feature"]])] = cell
        records.append(record)
    expected = pd.DataFrame(records)
    pd.testing.assert_frame_equal(got, expected, check_dtype=False)


def test_popup_traffic_light_levels_use_rule_thresholds() -> None:
    """Red/yellow/green/grey follow the configured buffer, not a constant."""
    row = {
        "kiln_id": "k", "lat": 23.7, "lon": 90.4, "class": "Zigzag", "priority_band": "High",
        "district": "Dhaka", "upazila": "Savar",
        "dist_schools_m": 500.0,      # inside 1000 -> red
        "dist_hospitals_m": 1400.0,   # within 1.5x -> yellow
        "dist_settlements_m": 9000.0,  # outside -> green
        "dist_railways_m": np.nan,    # no data -> grey
    }
    popup = kd.popup_html_list(pd.DataFrame([row]), RULES)[0]
    assert f"<span>🔴</span> {T.SCHOOL}: {T.M_DOT_FMT.format(500.0)}" in popup
    assert f"<span>🟡</span> {T.HOSPITAL}: {T.M_DOT_FMT.format(1400.0)}" in popup
    assert f"<span>🟢</span> {T.SETTLEMENT}: {T.OUTSIDE_THRESHOLD}" in popup
    assert f"<span>⚪</span> {T.RAILWAY}: {T.NO_DATA}" in popup

    tighter = [{**rule, "buffer_m": 100} for rule in RULES]
    popup_tight = kd.popup_html_list(pd.DataFrame([row]), tighter)[0]
    assert f"<span>🟢</span> {T.SCHOOL}: {T.OUTSIDE_THRESHOLD}" in popup_tight

    flagged = {**row, "dist_settlements_m": 9000.0, "breached_rules": ["near_settlement"]}
    popup_breach = kd.popup_html_list(pd.DataFrame([flagged]), RULES)[0]
    assert f"<span>🔴</span> {T.SETTLEMENT}: {T.M_DOT_FMT.format(9000.0)}" in popup_breach


def test_popup_html_escapes_untrusted_text_and_handles_missing_coordinates() -> None:
    """Hostile ids/areas are escaped; a missing coordinate gives '#' links."""
    row = {
        "kiln_id": "<script>alert(1)</script>", "lat": np.nan, "lon": np.nan,
        "class": "FCBK", "priority_band": "Low", "district": "<b>x</b>", "upazila": "a&b",
    }
    popup = kd.popup_html_list(pd.DataFrame([row]), RULES)[0]
    assert "<script>" not in popup and "<b>x</b>" not in popup
    assert "&lt;script&gt;" in popup and "a&amp;b" in popup
    assert "href='#'" in popup
    assert T.NO_DATA in popup
    assert T.FIXED_CHIMNEY_KILN in popup


def test_with_display_columns_is_idempotent_and_keeps_rows() -> None:
    """Display columns are added once, aligned to rows, and never recomputed."""
    frame = _frame(10)
    prepared = kd.with_display_columns(frame, RULES)
    assert all(column in prepared.columns for column in kd.DISPLAY_COLUMNS)
    assert prepared["kiln_id"].tolist() == frame["kiln_id"].tolist()
    assert not any(column in frame.columns for column in kd.DISPLAY_COLUMNS)
    assert kd.with_display_columns(prepared, RULES) is prepared
    empty = kd.with_display_columns(frame.iloc[0:0], RULES)
    assert empty.empty and all(column in empty.columns for column in kd.DISPLAY_COLUMNS)
    tooltip = prepared.loc[0, "ui_tooltip"]
    assert tooltip.count(" | ") == 2 and T.PRIORITY in tooltip


def test_prepare_display_frame_sets_version_and_default_status() -> None:
    """The prepared dataset carries its cache version and a default status."""
    frame = _frame(5).drop(columns=["detection_status"])
    prepared = kd.prepare_display_frame(frame, RULES, version="v1")
    assert prepared.attrs["dhoa_data_version"] == "v1"
    assert set(prepared["detection_status"]) == {"Known"}
    taken = kd.filter_candidates(prepared, kd.make_filter_key())
    assert all(column in taken.columns for column in kd.DISPLAY_COLUMNS)


def test_distances_from_point_m_matches_geodesic_reference() -> None:
    """Projected-CRS distances agree with WGS84 geodesics to well under 1 %."""
    from pyproj import Geod

    lats = np.array([24.0, 24.1, 24.0, 23.95])
    lons = np.array([90.0, 90.0, 90.1, 90.02])
    got = kd.distances_from_point_m(lats, lons, 24.0, 90.0)
    geod = Geod(ellps="WGS84")
    expected = np.array([geod.inv(90.0, 24.0, lon, lat)[2] for lat, lon in zip(lats, lons)])
    assert got[0] == 0
    np.testing.assert_allclose(got, expected, rtol=2e-3, atol=1.0)


def test_distances_non_finite_points_never_match() -> None:
    """NaN coordinates become inf so they fall outside every radius."""
    got = kd.distances_from_point_m([24.0, np.nan], [90.0, 90.0], 24.0, 90.0)
    assert got[0] == 0 and np.isinf(got[1])
    assert kd.nearest_position([np.nan], [np.nan], 24.0, 90.0) is None
    assert kd.nearest_position([], [], 24.0, 90.0) is None


def test_nearest_position_picks_closest_point() -> None:
    """The nearest marker is chosen with one vectorised distance call."""
    lats = [24.00, 24.50, 24.01]
    lons = [90.00, 90.50, 90.00]
    assert kd.nearest_position(lats, lons, 24.012, 90.0) == 2


def test_marker_payload_is_compact_escaped_and_drops_missing_coordinates() -> None:
    """The map payload is ~tens of bytes per kiln, HTML-safe, and skips NaN points."""
    import json

    frame = _frame(200)
    frame.loc[0, "lat"] = np.nan
    frame.loc[1, "upazila"] = "<img src=x onerror=alert(1)>"
    payload = kd.marker_payload(frame, RULES)
    assert len(payload["rows"]) == 199
    assert all(len(row) == 7 for row in payload["rows"])
    assert all(0 <= row[2] <= 3 for row in payload["rows"])
    assert len(payload["bands"]) == 4
    assert max(row[3] for row in payload["rows"]) < len(payload["types"])
    assert max(row[4] for row in payload["rows"]) < len(payload["areas"])
    assert "<" not in json.dumps(payload, ensure_ascii=False)
    assert len(json.dumps(payload["rows"])) / len(payload["rows"]) < 140  # bytes per kiln (incl. rule signals)


def test_marker_payload_band_index_and_empty_frame() -> None:
    """High/Medium/Low map to 0/1/2, anything else to 3; empty input is valid."""
    frame = _frame(3)
    frame["priority_band"] = ["High", "Medium", "weird"]
    assert [row[2] for row in kd.marker_payload(frame, RULES)["rows"]] == [0, 1, 3]
    empty = kd.marker_payload(frame.iloc[0:0], RULES)
    assert empty["rows"] == [] and empty["areas"] == []


def test_bounds_of_and_radius_bounds() -> None:
    """Bounds cover the finite points; the radius box is centred on the point."""
    frame = pd.DataFrame({"lat": [23.0, 24.0, np.nan], "lon": [90.0, 91.0, 95.0]})
    assert kd.bounds_of(frame) == [[23.0, 90.0], [24.0, 91.0]]
    assert kd.bounds_of(frame.iloc[2:]) is None
    (south, west), (north, east) = kd.radius_bounds(24.0, 90.0, 5000)
    assert math.isclose((south + north) / 2, 24.0) and math.isclose((west + east) / 2, 90.0)
    assert 0.08 < north - south < 0.10 and east - west > north - south  # ~5 km each way
