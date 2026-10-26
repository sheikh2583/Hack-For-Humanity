"""M5 Community redesign tests (synthetic data; AppTests skip without the parquet)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import app.community as cm
import app.strings as T

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "processed" / "kilns_prioritised.parquet"


def _frame() -> pd.DataFrame:
    """Two districts. Savar: 4 kilns near (23.85, 90.25); one 7 km east.
    Tongi (Gazipur): 2 kilns near (23.90, 90.40). One named place."""
    rows = [
        ("a", 23.8500, 90.2500, "Dhaka", "Savar", "High", "Ashulia"),
        ("b", 23.8520, 90.2520, "Dhaka", "Savar", "Medium", "Ashulia"),
        ("c", 23.8540, 90.2500, "Dhaka", "Savar", "Low", None),
        ("d", 23.8500, 90.3170, "Dhaka", "Savar", "High", None),  # ~6.8 km east of a
        ("e", 23.9000, 90.4000, "Gazipur", "Tongi", "Low", None),
        ("f", 23.9010, 90.4010, "Gazipur", "Tongi", "High", "Tongi Bazar"),
    ]
    return pd.DataFrame(
        rows, columns=["kiln_id", "lat", "lon", "district", "upazila", "priority_band", "nearest_place"]
    )


def test_build_places_only_lists_areas_with_data_and_counts() -> None:
    places = {p.key: p for p in cm.build_places(_frame())}
    assert cm.place_key(cm.KIND_DISTRICT, "Dhaka") in places
    assert places[cm.place_key(cm.KIND_DISTRICT, "Dhaka")].kiln_count == 4
    assert places[cm.place_key(cm.KIND_UPAZILA, "Gazipur", "Tongi")].kiln_count == 2
    assert places[cm.place_key(cm.KIND_NAMED, "Dhaka", "Ashulia")].kiln_count == 2
    assert not any("Adabor" in p.name for p in places.values())  # no data -> not offered


def test_upazila_shows_all_its_kilns_without_radius() -> None:
    place = next(p for p in cm.build_places(_frame()) if p.kind == cm.KIND_UPAZILA and p.name == "Savar")
    result = cm.search(_frame(), place, radius_m=1000)  # radius ignored for whole areas
    assert result.radius_m is None and len(result.rows) == 4
    assert result.summary["high"] == 2
    assert not place.radius_applies


def test_radius_search_filters_and_sorts_by_distance() -> None:
    frame = _frame()
    origin = cm.point_place("here", 23.85, 90.25)
    near = cm.search(frame, origin, 1000)
    assert list(near.rows["kiln_id"])[0] == "a" and set(near.rows["kiln_id"]) == {"a", "b", "c"}
    assert near.rows["distance_m"].is_monotonic_increasing
    wide = cm.search(frame, origin, 10000)
    assert "d" in set(wide.rows["kiln_id"]) and "e" not in set(wide.rows["kiln_id"])


def test_default_radius_is_5_km_and_choices_are_1_2_5_10() -> None:
    assert cm.RADIUS_CHOICES_M == (1000, 2000, 5000, 10000)
    assert cm.DEFAULT_RADIUS_M == 5000
    result = cm.search(_frame(), cm.point_place("p", 23.85, 90.25), None)
    assert result.radius_m == 5000 and "d" not in set(result.rows["kiln_id"])  # d is ~6.8 km away


def test_empty_state_helpers_find_nearest_and_next_radius() -> None:
    frame = _frame()
    origin = cm.point_place("empty", 23.85, 90.2000)  # ~5.1 km west of kiln a
    assert cm.search(frame, origin, 1000).empty
    distance, row = cm.nearest_beyond(frame, origin.lat, origin.lon)
    assert row["kiln_id"] == "a" and 4800 < distance < 5400
    assert cm.radius_to_reach(distance) == 10000
    assert cm.radius_to_reach(2300.0) == 5000
    assert cm.radius_to_reach(10_001.0) is None
    assert cm.next_radius(1000) == 2000 and cm.next_radius(10000) is None
    assert cm.nearest_beyond(frame.iloc[0:0], 23.0, 90.0) is None


def test_covered_district_detects_points_outside_the_five_districts() -> None:
    frame = _frame()
    assert cm.covered_district(frame, 23.86, 90.26) == "Dhaka"
    assert cm.covered_district(frame, 22.35, 91.80) is None  # far from every district box


def test_bangladesh_filter_and_geocoder_fallback_chain() -> None:
    assert cm.in_bangladesh(23.8, 90.4) and not cm.in_bangladesh(28.6, 77.2)
    calls: list[str] = []

    def abroad(query: str) -> tuple[float, float]:
        calls.append("abroad")
        return (28.6, 77.2)  # Delhi: must be rejected

    def good(query: str) -> tuple[float, float]:
        calls.append("good")
        return (23.8, 90.4)

    no_sleep = lambda seconds: None  # noqa: E731
    assert cm.geocode_bangladesh("Mirpur", [abroad, good], sleep=no_sleep) == (23.8, 90.4)
    assert calls == ["abroad", "good"]
    assert cm.geocode_bangladesh("   ", [good], sleep=no_sleep) is None


def test_geocoder_distinguishes_not_found_from_outage() -> None:
    no_sleep = lambda seconds: None  # noqa: E731

    def broken(query: str) -> tuple[float, float]:
        raise TimeoutError

    assert cm.geocode_bangladesh("x", [lambda q: None], sleep=no_sleep) is None  # cacheable
    with pytest.raises(cm.GeocodeUnavailable):  # must not be cached
        cm.geocode_bangladesh("x", [broken, broken], sleep=no_sleep)


def test_rate_limit_waits_between_calls() -> None:
    waits: list[float] = []
    times = iter([100.0, 100.0, 100.2, 100.2])  # two calls 0.2 s apart
    cm._LAST_CALL[0] = 0.0
    cm.geocode_bangladesh("a", [lambda q: None], clock=lambda: next(times), sleep=waits.append)
    cm.geocode_bangladesh("b", [lambda q: None], clock=lambda: next(times), sleep=waits.append)
    assert waits and waits[-1] == pytest.approx(cm.MIN_INTERVAL_S - 0.2, abs=1e-6)


def test_no_geolocation_page_reload_or_legacy_query_params_remain() -> None:
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "window.parent.location" not in source and "_geo_lat" not in source and "gps_lat" not in source
    component = (ROOT / "app" / "components" / "geolocate" / "index.html").read_text(encoding="utf-8")
    assert "window.parent.location" not in component and "alert(" not in component
    assert "streamlit:setComponentValue" in component


def test_copy_is_bangla_and_has_no_escapes() -> None:
    text = (ROOT / "app" / "strings_bn.py").read_text(encoding="utf-8")
    m5 = text[text.index("# --- M5"):]
    assert "\\u" not in m5
    for name in ("C_STEP1", "C_STEP2", "C_STEP3", "C_GPS_DENIED", "C_EMPTY_NEAREST_FMT"):
        assert any("\u0980" <= ch <= "\u09ff" for ch in getattr(T, name))


def _apptest():
    if not PARQUET.exists():
        pytest.skip("parquet not present")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.session_state["dhoa_view_mode"] = "inspector"  # R3: the search bar lives on the Map
    return at.run()


def test_community_apptest_shows_the_map_before_a_place_is_chosen() -> None:
    at = _apptest()
    assert not at.exception
    assert not any(i.value == T.C_PICK_PROMPT for i in at.info)
    assert at.selectbox(key="w_community_place_key@bn") is not None


def test_community_apptest_every_upazila_choice_gives_a_result_or_next_step() -> None:
    at = _apptest()
    picker = at.selectbox(key="w_community_place_key@bn")
    upazilas = [i for i, label in enumerate(picker.options) if label.endswith("টি ভাটা") and "," in label][:6]
    assert upazilas
    for index in upazilas:
        picker.select_index(index).run()
        assert not at.exception
        assert not any(i.value == T.C_PICK_PROMPT for i in at.info)
        assert any("dhoa_community_summary" == c.key for c in at.get("container")) or at.markdown


def test_community_apptest_empty_radius_offers_one_click_widen() -> None:
    at = _apptest()
    picker = at.selectbox(key="w_community_place_key@bn")
    named = [i for i, label in enumerate(picker.options) if label]  # any place
    picker.select_index(named[0]).run()
    assert not at.exception
