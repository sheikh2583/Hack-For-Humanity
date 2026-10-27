"""M2 dashboard tests: cached filtering, vectorised helpers, filter form.

Input schema: tiny synthetic kiln frames (no real data) except the single
AppTest smoke test, which is skipped when the parquet is absent.
Output: the Streamlit-facing functions must agree with ``app/kiln_data.py`` and
no per-row config reads, radius slider or per-row geometry work may remain.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

import app.kiln_data as kd
import app.streamlit_app as dashboard

ROOT = Path(__file__).resolve().parent.parent
RULES = [
    {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3},
    {"id": "near_hospital", "feature": "hospitals", "buffer_m": 1000, "severity": 3},
]


def _prepared(count: int = 30) -> pd.DataFrame:
    """Return a prepared synthetic dataset (display columns + version token)."""
    rng = np.random.default_rng(3)
    frame = pd.DataFrame(
        {
            "kiln_id": [f"k{i}" for i in range(count)],
            "lat": 23.6 + rng.random(count) * 0.2,
            "lon": 90.3 + rng.random(count) * 0.2,
            "district": np.array(["Dhaka", "Gazipur"])[rng.integers(0, 2, count)],
            "upazila": np.array(["Savar", "Tongi"])[rng.integers(0, 2, count)],
            "class": np.array(["Zigzag", "FCBK"])[rng.integers(0, 2, count)],
            "priority_band": np.array(["High", "Medium", "Low"])[rng.integers(0, 3, count)],
            "priority": rng.random(count),
            "dist_schools_m": rng.choice([200.0, 3000.0], count),
            "dist_hospitals_m": rng.choice([800.0, np.nan], count),
            "breached_rules": [["near_school"]] * count,
        }
    )
    # The version token keys the app caches, so it must identify the exact content.
    return kd.prepare_display_frame(frame, RULES, version=f"test-{count}")


@pytest.fixture()
def inspector_state(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace Streamlit's session state with a plain dict for one test."""
    state: dict[str, Any] = {
        "dhoa_active_view": "inspector",
        "filter_district": dashboard.ALL_DISTRICTS,
        "filter_upazila": dashboard.ALL_AREAS,
        "filter_kiln_type": dashboard.ALL_KILN_TYPES,
        "filter_priority": [dashboard.T.HIGH, dashboard.T.MEDIUM, dashboard.T.LOW],
    }
    monkeypatch.setattr(dashboard.st, "session_state", state)
    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": RULES}})
    return state


def test_inspector_radius_slider_is_gone() -> None:
    """The unused inspector radius slider and its session key no longer exist."""
    tree = ast.parse((ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8"))
    strings = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)}
    assert "filter_radius_m" not in strings


def test_reset_inspector_filters_restores_defaults_without_radius(
    inspector_state: dict[str, Any],
) -> None:
    """Reset writes only the four live filter keys."""
    inspector_state.update(filter_district="Dhaka", filter_upazila="Savar", filter_priority=[dashboard.T.LOW])
    dashboard._reset_inspector_filters()
    assert inspector_state["filter_district"] == dashboard.ALL_DISTRICTS
    assert inspector_state["filter_upazila"] == dashboard.ALL_AREAS
    assert inspector_state["filter_kiln_type"] == dashboard.ALL_KILN_TYPES
    assert len(inspector_state["filter_priority"]) == 3
    assert "filter_radius_m" not in inspector_state


def test_get_filtered_gdf_matches_pure_filter(inspector_state: dict[str, Any]) -> None:
    """The session-state wrapper returns exactly the pure filter's rows and order."""
    data = _prepared()
    inspector_state.update(filter_district="Dhaka", filter_priority=[dashboard.T.HIGH, dashboard.T.LOW])
    got = dashboard.get_filtered_gdf(data)
    expected = kd.filter_candidates(data, kd.make_filter_key("Dhaka", priorities=["High", "Low"]))
    assert got["kiln_id"].tolist() == expected["kiln_id"].tolist()
    assert set(got["district"]) <= {"Dhaka"}
    # A second call (cache hit) is identical and independent of the first object.
    again = dashboard.get_filtered_gdf(data)
    assert again["kiln_id"].tolist() == got["kiln_id"].tolist()
    again.loc[again.index[0], "kiln_id"] = "mutated"
    assert "mutated" not in data["kiln_id"].tolist()


def test_get_filtered_gdf_without_version_still_filters(inspector_state: dict[str, Any]) -> None:
    """A frame with no version token skips the cache and gives the same answer."""
    data = _prepared()
    plain = data.copy()
    plain.attrs.clear()
    inspector_state.update(filter_upazila="Tongi")
    assert (
        dashboard.get_filtered_gdf(plain)["kiln_id"].tolist()
        == dashboard.get_filtered_gdf(data)["kiln_id"].tolist()
    )


def test_build_map_uses_one_compact_marker_layer_without_per_row_config_reads(
    inspector_state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One FastMarkerCluster carries every kiln; config is not read per kiln."""
    from folium.plugins import FastMarkerCluster

    data = _prepared(40)
    calls = {"count": 0}

    def counting_config() -> dict[str, Any]:
        calls["count"] += 1
        return {"rules": {"siting_rules": RULES}}

    monkeypatch.setattr(dashboard, "load_config", counting_config)
    visible = dashboard.get_filtered_gdf(data)
    result = dashboard.build_map(data, {}, visible)
    layers = [item for item in result._children.values() if isinstance(item, FastMarkerCluster)]
    assert len(layers) == 1
    assert len(layers[0].data) == len(visible) == 40
    assert calls["count"] <= 2


def test_build_map_skips_kilns_without_coordinates(inspector_state: dict[str, Any]) -> None:
    """A NaN coordinate is skipped instead of failing the whole map."""
    from folium.plugins import FastMarkerCluster

    data = _prepared(5)
    broken = data.copy()
    broken.loc[broken.index[0], "lat"] = np.nan
    broken.attrs.clear()  # no version token -> built directly, not from the cache
    result = dashboard.build_map(broken, {}, broken)
    layer = next(item for item in result._children.values() if isinstance(item, FastMarkerCluster))
    assert len(layer.data) == 4


def test_popup_html_reuses_precomputed_column_and_falls_back(
    inspector_state: dict[str, Any],
) -> None:
    """A row with ui_popup_html returns it verbatim; a bare row is computed."""
    data = _prepared(3)
    row = data.iloc[0]
    assert dashboard._popup_html(row) == row["ui_popup_html"]
    bare = row.drop(labels=list(kd.DISPLAY_COLUMNS))
    assert dashboard._popup_html(bare) == row["ui_popup_html"]


def test_kiln_list_frame_has_one_distance_column_per_configured_rule(
    inspector_state: dict[str, Any],
) -> None:
    """The list adds one distance column per rule in rules.yaml (none hard-coded)."""
    frame = dashboard._kiln_list_frame(_prepared(6))
    assert frame.shape == (6, 3 + len(RULES))
    assert frame.columns[3] == kd.rule_column_label(RULES[0])


def test_list_payload_cached_and_direct_paths_agree(inspector_state: dict[str, Any]) -> None:
    """The cached payload equals the directly built one for the same filter."""
    data = _prepared(12)
    visible = dashboard.get_filtered_gdf(data)
    direct = dashboard._build_list_payload(visible)
    cached = dashboard._list_payload(visible, data)
    assert cached == direct
    assert dashboard._list_payload(visible, data) == direct  # cache hit
    columns, rows, ids = direct
    assert len(rows) == len(ids) == len(visible) and len(columns) == 3 + len(RULES)


def test_inspector_csv_bytes_match_uncached_export(inspector_state: dict[str, Any]) -> None:
    """The cached CSV is byte-identical to a fresh export of the same rows."""
    data = _prepared(8)
    visible = dashboard.get_filtered_gdf(data)
    assert dashboard._inspector_csv_bytes(visible, data) == dashboard.make_download_csv(
        visible, dashboard.INSPECTOR_CSV_COLUMNS
    )


def test_community_distances_are_vectorised_metres() -> None:
    """Distances from a point agree with WGS84 geodesics (projected-CRS maths)."""
    from pyproj import Geod

    frame = pd.DataFrame({"lat": [24.0, 24.05, 23.9], "lon": [90.0, 90.0, 90.07]})
    got = dashboard.community_distances(frame, 24.0, 90.0)
    geod = Geod(ellps="WGS84")
    expected = [geod.inv(90.0, 24.0, lon, lat)[2] for lat, lon in zip(frame["lat"], frame["lon"])]
    assert got.index.equals(frame.index)
    np.testing.assert_allclose(got.to_numpy(), expected, rtol=2e-3, atol=1.0)


def test_community_filter_applies_radius_and_orders_by_distance(
    inspector_state: dict[str, Any],
) -> None:
    """Community mode keeps kilns within the radius of the origin, nearest first."""
    data = _prepared(20)
    inspector_state.update(
        dhoa_active_view="community",
        community_origin={
            "name": "here", "lat": float(data["lat"].iloc[0]), "lon": float(data["lon"].iloc[0]),
        },
        community_radius_m=5000,
    )
    near = dashboard.get_filtered_gdf(data)
    assert near["distance_m"].is_monotonic_increasing
    assert near["distance_m"].le(5000).all()
    assert near.iloc[0]["kiln_id"] == data.iloc[0]["kiln_id"]
    inspector_state["community_radius_m"] = 1000
    assert len(dashboard.get_filtered_gdf(data)) >= 1  # the kiln at the search point itself
    inspector_state["community_origin"] = None  # nothing chosen -> empty, never an error
    assert dashboard.get_filtered_gdf(data).empty


def test_community_pdf_is_cached_per_result_set(
    inspector_state: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same results produce the PDF once; changed results rebuild it."""
    calls = {"count": 0}

    def fake_pdf(location: str, rows: pd.DataFrame, radius_m: int) -> bytes:
        calls["count"] += 1
        return f"{location}|{len(rows)}|{radius_m}".encode()

    monkeypatch.setattr(dashboard, "community_alert_pdf", fake_pdf)
    dashboard._cached_community_pdf.clear()
    rows = pd.DataFrame(
        {"distance_m": [10.0, 20.0], "class": ["Zigzag", "FCBK"],
         "priority_band": ["High", "Low"], "lat": [23.7, 23.8], "lon": [90.4, 90.5]}
    )
    first = dashboard._community_report("Savar", rows, 2000)
    assert dashboard._community_report("Savar", rows, 2000) == first
    assert calls["count"] == 1
    dashboard._community_report("Savar", rows.iloc[:1], 2000)
    assert calls["count"] == 2


@pytest.mark.skipif(
    not (ROOT / "data" / "processed" / "kilns_prioritised.parquet").is_file(),
    reason="real dataset not present",
)
def test_inspector_renders_apply_button_and_no_radius_slider() -> None:
    """AppTest: the app loads, the filter form has its apply button, no radius slider."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120).run()
    assert not at.exception
    assert dashboard.T.APPLY_FILTERS in [button.label for button in at.button]
    assert "filter_radius_m" not in [slider.key for slider in at.slider]
