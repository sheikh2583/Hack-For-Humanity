"""M3 tests: map payload size, no zoom/bounds persistence, no popups, stable keys.

Input schema: the app source plus synthetic kiln frames. Output: the structural
guarantees behind "pan and zoom cause zero reruns" that can be checked without
a browser. The browser check is ``tests/e2e/test_map_pan_zoom.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

import app.kiln_data as kd
import app.streamlit_app as dashboard

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
RULES = [{"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3}]


def _st_folium_calls() -> list[ast.Call]:
    return [
        node for node in ast.walk(TREE)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "st_folium"
    ]


def test_every_st_folium_call_returns_only_the_last_click() -> None:
    """Pan/zoom/bounds are never returned to Python, so they cannot rerun the script."""
    calls = _st_folium_calls()
    assert len(calls) == 2  # Inspector + Community
    for call in calls:
        keyword = next(item for item in call.keywords if item.arg == "returned_objects")
        assert ast.literal_eval(keyword.value) == ["last_object_clicked"]


def test_map_tile_selectbox_does_not_duplicate_its_seeded_default(monkeypatch) -> None:
    """The widget reads the session-state seed without also applying index 0."""
    state = {"map_tile": "street"}
    captured: dict[str, object] = {}

    def selectbox(*args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return "street"

    monkeypatch.setattr(dashboard.st, "session_state", state)
    monkeypatch.setattr(dashboard.st, "selectbox", selectbox)
    assert dashboard._render_map_type_filter() == "street"
    assert captured.get("index") is None


def test_zoom_and_bounds_are_not_persisted() -> None:
    """The snap-back state (map_center/map_zoom/bounds) is gone from the app."""
    strings = {node.value for node in ast.walk(TREE) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert not strings & {"map_center", "map_zoom", "bounds"}


def test_map_has_no_layer_control_and_no_embedded_popups() -> None:
    """No LayerControl (past remount crash) and no per-marker popups in the payload."""
    names = {node.attr for node in ast.walk(TREE) if isinstance(node, ast.Attribute)}
    names |= {node.id for node in ast.walk(TREE) if isinstance(node, ast.Name)}
    assert "Popup" not in names
    layer_control_calls = [
        node for node in ast.walk(TREE)
        if isinstance(node, ast.Attribute) and node.attr == "LayerControl"
    ]
    # Only the opt-in branch of _add_map_base_layers may mention it; both callers pass False.
    assert len(layer_control_calls) == 1


def test_map_has_stable_zoom_limits_and_resizes_after_layout_changes() -> None:
    """Leaflet keeps one world view and recalculates tiles after responsive resize."""
    map_view = dashboard._new_map("street", None)
    options = map_view.options
    assert options["minZoom"] == dashboard.DEFAULT_ZOOM - 1
    assert options["maxZoom"] == dashboard.SELECTED_ZOOM + 3
    assert options.get("worldCopyJump", options.get("world_copy_jump")) is False
    rendered = map_view.get_root().render()
    assert "invalidateSize" in rendered
    assert "noWrap: true" in rendered or '"noWrap": true' in rendered  # folium 0.20 renders JSON
    assert "minZoom" in rendered and "maxZoom" in rendered  # must reach the browser, not only the dict


def test_selected_marker_and_radius_use_feature_group_not_the_base_map() -> None:
    """Both st_folium calls pass feature_group_to_add (highlight / radius overlay)."""
    for call in _st_folium_calls():
        assert any(item.arg == "feature_group_to_add" for item in call.keywords)


def test_inspector_map_key_depends_on_filters_and_tile_only() -> None:
    """The key (remount trigger) changes with filters/tile, never with selection."""
    first = dashboard._map_key("dhoa_map", ("Dhaka", "a", "b", ("High",)), "street")
    assert first == dashboard._map_key("dhoa_map", ("Dhaka", "a", "b", ("High",)), "street")
    assert first != dashboard._map_key("dhoa_map", ("Dhaka", "a", "b", ("High",)), "satellite")
    assert first != dashboard._map_key("dhoa_map", ("Gazipur", "a", "b", ("High",)), "street")


def test_rendered_map_for_2135_kilns_is_under_one_megabyte(monkeypatch) -> None:
    """The full-dataset map HTML is < 1 MB (was 5-6 MB with embedded popups)."""
    monkeypatch.setattr(dashboard.st, "session_state", {"map_tile": "street"})
    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": RULES}})
    rng = np.random.default_rng(1)
    count = 2135
    frame = pd.DataFrame(
        {
            "kiln_id": [f"k{i}" for i in range(count)],
            "lat": 23.0 + rng.random(count) * 2,
            "lon": 89.0 + rng.random(count) * 2,
            "district": rng.choice(["Dhaka", "Gazipur", "Rajshahi"], count),
            "upazila": rng.choice([f"উপজেলা{i}" for i in range(58)], count),
            "class": rng.choice(["Zigzag", "FCBK"], count),
            "priority_band": rng.choice(["High", "Medium", "Low"], count),
        }
    )
    prepared = kd.prepare_display_frame(frame, RULES, version="size-test")
    html_text = dashboard.build_map(prepared, {}, prepared).get_root().render()
    assert len(html_text.encode("utf-8")) < 1_000_000
    assert "bindPopup" not in html_text


def test_marker_callback_embeds_only_escaped_lookup_text() -> None:
    """Tooltip lookups are JSON with HTML-escaped labels (Leaflet renders them as HTML)."""
    frame = pd.DataFrame(
        {"kiln_id": ["a"], "lat": [23.7], "lon": [90.4], "class": ["FCBK"],
         "priority_band": ["High"], "district": ["Dhaka"], "upazila": ["<b>x</b>"]}
    )
    js = dashboard._marker_callback_js(kd.marker_payload(frame, RULES))
    assert "<b>" not in js and "&lt;b&gt;" in js
    assert js.startswith("(function(){") and js.endswith("})()")


def test_marker_click_opens_directions_popup_without_embedding_popups() -> None:
    """Clicking a marker opens a details popup with a Google Maps directions link.

    The popup is built in the browser from the row's coordinates, so the page
    still carries no per-marker ``bindPopup`` content.
    """
    frame = pd.DataFrame(
        {"kiln_id": ["a"], "lat": [23.7], "lon": [90.4], "class": ["FCBK"],
         "priority_band": ["High"], "district": ["Dhaka"], "upazila": ["Savar"]}
    )
    js = dashboard._marker_callback_js(kd.marker_payload(frame, RULES))
    assert "m.on('click'" in js and "openOn(mp)" in js
    assert "google.com/maps" in js and "/dir/?api=1&destination=" in js
    assert "bindPopup" not in js


def test_popup_lists_rule_signal_distances_from_config_thresholds() -> None:
    """The popup shows distance to school, hospital etc. with a traffic-light state.

    States come from ``kiln_data.popup_signal_codes`` (thresholds read from the
    rules, not hardcoded); the page still embeds no per-marker popup HTML.
    """
    frame = pd.DataFrame(
        {"kiln_id": ["a", "b"], "lat": [23.7, 23.8], "lon": [90.4, 90.5], "class": ["FCBK", "Zigzag"],
         "priority_band": ["High", "Low"], "district": ["Dhaka"] * 2, "upazila": ["Savar"] * 2,
         "dist_schools_m": [120.0, 9000.0], "dist_hospitals_m": [None, 50.0]}
    )
    payload = kd.marker_payload(frame, RULES)
    states, metres = kd.popup_signal_codes(frame, RULES)
    assert len(states[0]) == len(payload["rules"]) == 6
    assert states[0][1] == "3" and metres[0][1] == -1  # missing hospital distance -> grey
    assert metres[0][0] == 120 and metres[1][0] == 9000
    assert payload["rows"][0][5] == states[0] and payload["rows"][0][6] == metres[0]
    js = dashboard._marker_callback_js(payload)
    assert "rule-signal-row" in js and "bindPopup" not in js
