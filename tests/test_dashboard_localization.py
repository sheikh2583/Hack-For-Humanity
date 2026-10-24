"""Regression tests for the dashboard's app-wide locale and display labels."""

import geopandas as gpd
from shapely.geometry import Point

import app.streamlit_app as dashboard


def test_locale_toggle_updates_the_app_locale(monkeypatch) -> None:
    """The language control updates one shared locale state."""
    state: dict[str, object] = {"dhoa_language_toggle": True}
    monkeypatch.setattr(dashboard.st, "session_state", state)

    dashboard._set_locale_from_toggle()

    assert dashboard._locale() == "en"
    state["dhoa_language_toggle"] = False
    dashboard._set_locale_from_toggle()
    assert dashboard._locale() == "bn"


def test_visible_labels_follow_the_active_locale(monkeypatch) -> None:
    """Several user-facing labels change while canonical place names remain stable."""
    state: dict[str, object] = {"dhoa_locale": "bn"}
    monkeypatch.setattr(dashboard.st, "session_state", state)
    bangla = (
        dashboard._ui_text("ফিল্টার", "Filters"),
        dashboard._district_label("Dhaka"),
        dashboard._area_display_name({"upazila": "Mirpur", "district": "Dhaka"}),
    )

    state["dhoa_locale"] = "en"
    english = (
        dashboard._ui_text("ফিল্টার", "Filters"),
        dashboard._district_label("Dhaka"),
        dashboard._area_display_name({"upazila": "Mirpur", "district": "Dhaka"}),
    )

    assert bangla != english
    assert bangla[1] == "ঢাকা"
    assert english[1] == "Dhaka"
    assert english[2] == "Mirpur, Dhaka"


def test_district_and_area_filtering_is_locale_independent(monkeypatch) -> None:
    """Canonical district and area filters select the same rows in both locales."""
    frame = gpd.GeoDataFrame(
        {
            "kiln_id": ["mirpur", "savar", "other"],
            "district": ["Dhaka", "Dhaka", "Gazipur"],
            "upazila": ["Mirpur", "Savar", "Gazipur Sadar"],
            "class": ["Zigzag", "FCBK", "Zigzag"],
            "priority_band": ["High", "Medium", "Low"],
            "lat": [23.81, 23.85, 24.1],
            "lon": [90.36, 90.27, 90.2],
        },
        geometry=[Point(90.36, 23.81), Point(90.27, 23.85), Point(90.2, 24.1)],
        crs="EPSG:4326",
    )
    state: dict[str, object] = {
        "dhoa_active_view": "inspector",
        "filter_district": "Dhaka",
        "filter_upazila": "Mirpur",
        "filter_priority": ["উচ্চ", "মাঝারি", "নিম্ন"],
        "filter_kiln_type": dashboard.ALL_KILN_TYPES,
    }
    monkeypatch.setattr(dashboard.st, "session_state", state)

    results: list[list[str]] = []
    for locale in ("bn", "en"):
        state["dhoa_locale"] = locale
        results.append(dashboard.get_filtered_gdf(frame)["kiln_id"].tolist())

    assert results == [["mirpur"], ["mirpur"]]
