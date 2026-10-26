"""P4 tests: pure inspector helpers, wiring guards and string parity.

Input: tiny synthetic rows/rules. Output: assertions on distance state, markup
escaping, heat points and that the app uses the helpers without caching a map.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd

import app.inspector as ins

ROOT = Path(__file__).resolve().parent.parent
RULES = [
    {"id": "near_school", "feature": "schools", "buffer_m": 1000},
    {"id": "near_government_forest", "feature": "government_forest", "buffer_m": 2000},
    {"id": "near_wetland", "feature": "water", "buffer_m": 1000},
]
NEW = ("LEGEND_TITLE", "HEAT_TOGGLE", "HEAT_HELP", "DETAIL_DISTANCES_TITLE",
       "DETAIL_WITHIN_FMT", "DETAIL_BEYOND_FMT", "DETAIL_STATE_UNKNOWN")


def test_distance_rows_use_configured_thresholds() -> None:
    row = {"dist_schools_m": 999.0, "dist_government_forest_m": 2000.0, "dist_water_m": float("nan")}
    got = {e["feature"]: e for e in ins.distance_rows(row, RULES)}
    assert got["schools"]["state"] == "inside" and got["schools"]["buffer_m"] == 1000.0
    assert got["government_forest"]["state"] == "outside"  # equal to the buffer is not inside
    assert got["water"]["state"] == "unknown" and got["water"]["distance_m"] is None


def test_distance_rows_without_buffer_are_unknown() -> None:
    got = ins.distance_rows({"dist_schools_m": 5.0}, [{"feature": "schools"}])
    assert got[0]["state"] == "unknown" and got[0]["distance_m"] == 5.0


def test_grid_html_escapes_and_pairs_dot_with_text() -> None:
    entries = ins.distance_rows({"dist_schools_m": 10.0}, RULES[:1])
    out = ins.distance_grid_html(
        entries, {"schools": "<b>School</b>"}, {"schools": "10 m"},
        {"schools:inside": "Within 1 km", "unknown": "n/a"},
    )
    assert "<b>School</b>" not in out and "&lt;b&gt;School" in out
    assert ins.INSIDE_DOT in out and "Within 1 km" in out and "aria-hidden='true'" in out


def test_legend_has_glyph_for_every_band_and_optional_note() -> None:
    out = ins.legend_html("Key", {"High": "High", "Medium": "Medium", "Low": "Low"}, "")
    for glyph in ("▲", "◆", "●"):
        assert glyph in out
    assert "<p>" not in out
    assert "<p>note &amp; more</p>" in ins.legend_html("Key", {}, "note & more")


def test_heat_points_drop_missing_and_cap() -> None:
    frame = pd.DataFrame({"lat": [23.1, None, 23.3, 23.4], "lon": [90.1, 90.2, 90.3, 90.4]})
    assert ins.heat_points(frame) == [[23.1, 90.1], [23.3, 90.3], [23.4, 90.4]]
    assert len(ins.heat_points(frame, limit=2)) <= 2
    assert ins.heat_points(pd.DataFrame({"a": []})) == []


def test_new_strings_in_both_languages_with_matching_fields() -> None:
    def load(name: str) -> dict[str, str]:
        tree = ast.parse((ROOT / "app" / name).read_text(encoding="utf-8"))
        return {n.targets[0].id: n.value.value for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)}
    bn, en = load("strings_bn.py"), load("strings_en.py")
    for name in NEW:
        assert name in bn and name in en
        assert re.findall(r"\{[^}]*\}", bn[name]) == re.findall(r"\{[^}]*\}", en[name])


def test_app_wiring_no_folium_map_cached_and_view_not_forced() -> None:
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "ins.distance_grid_html" in source and "ins.legend_html" in source
    assert 'key="dhoa_heatmap"' in source and "HeatMap" in source
    assert 'returned_objects=["last_object_clicked"]' in source
    tree = ast.parse(source)
    for node in ast.walk(tree):  # a cached function must not be annotated to return a folium.Map
        if isinstance(node, ast.FunctionDef) and any("cache" in ast.unparse(d) for d in node.decorator_list):
            assert "folium.Map" not in ast.unparse(node.returns or ast.Constant(""))
