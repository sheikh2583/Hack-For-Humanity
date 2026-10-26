"""Regression tests for the Bangla-only dashboard labels (M1) and filtering."""

import geopandas as gpd
from shapely.geometry import Point

import app.streamlit_app as dashboard


def test_app_has_no_language_toggle_helpers() -> None:
    """The English toggle and its helpers are gone; the app is Bangla-only."""
    for name in ("_ui_text", "_english_ui", "_locale", "_set_locale_from_toggle"):
        assert not hasattr(dashboard, name)


def test_visible_labels_are_bangla() -> None:
    """District and area labels render in Bangla."""
    assert dashboard._district_label("Dhaka") == "ঢাকা"
    assert dashboard._area_display_name({"upazila": "Mirpur", "district": "Dhaka"}) != "Mirpur, Dhaka"


def test_district_and_area_filtering_selects_canonical_rows(monkeypatch) -> None:
    """Canonical district and area filters select the expected rows."""
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
    assert dashboard.get_filtered_gdf(frame)["kiln_id"].tolist() == ["mirpur"]
