"""S2: public/staff data split, the public Overview and the staff-only Dashboard.

Input: synthetic kiln frames that carry sentinel staff values (a band, a score, a distance, a
provenance string). Output: assertions that no staff-only column name or sentinel value can be
found in any public payload, table, map script, PDF input or public text. The AppTest cases need
streamlit; the rest are pure pandas.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import app.community as cm
import app.kiln_data as kd
import app.overview as ov
import app.strings as T

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
SENTINEL_DISTANCE = 424242.5
SENTINEL_TEXT = "SECRET_PROVENANCE_TEXT"


def _staff_frame() -> pd.DataFrame:
    """Raw pipeline-shaped frame: public columns plus every documented staff-only column."""
    count = 6
    return pd.DataFrame({
        "kiln_id": [f"k{i}" for i in range(count)],
        "lat": [23.80 + 0.01 * i for i in range(count)],
        "lon": [90.30 + 0.01 * i for i in range(count)],
        "district": ["Dhaka"] * 4 + ["Gazipur"] * 2,
        "upazila": ["Savar"] * 3 + ["Dhamrai", "Tongi", "Tongi"],
        "class": ["Zigzag", "FCBK"] * 3,
        "nearest_place": [None] * count,
        "priority": np.linspace(0.1, 0.9, count),
        "priority_rank": range(1, count + 1),
        "priority_band": ["High", "High", "Medium", "Medium", "Low", "Low"],
        "exposure": [0.5] * count,
        "breach_severity_score": [3.0] * count,
        "breach_count": [1] * count,
        "breach_score": [3.0] * count,
        "breached_rules": [["near_school"]] * count,
        "rule_signals_count": [1] * count,
        "rule_data_notes": [SENTINEL_TEXT] * count,
        "rules_version": ["v-secret"] * count,
        "rules_verified": [False] * count,
        "signal_provenance_json": [SENTINEL_TEXT] * count,
        "technology_flagged": [True] * count,
        "n_schools": [4] * count, "n_hospitals": [2] * count, "settlement_area": [0.7] * count,
        "n_schools_normalized": [0.4] * count,
        "dist_schools_m": [SENTINEL_DISTANCE] * count,
        "dist_hospitals_m": [SENTINEL_DISTANCE] * count,
        "dist_settlements_m": [SENTINEL_DISTANCE] * count,
        "dist_government_forest_m": [SENTINEL_DISTANCE] * count,
        "dist_new_feature_m": [SENTINEL_DISTANCE] * count,  # unknown future dist_ column: prefix guard
        "confidence": [0.93] * count,
    })


def _public() -> pd.DataFrame:
    return kd.prepare_public_frame(_staff_frame(), "v1")


def test_every_documented_staff_column_is_staff_only_and_public_columns_are_kept() -> None:
    staff = _staff_frame()
    public = kd.public_view(staff)
    assert kd.leaked_columns(public) == []
    assert list(public.columns) == ["kiln_id", "lat", "lon", "district", "upazila", "class", "nearest_place"]
    for name in kd.STAFF_ONLY_COLUMNS:
        assert kd.is_staff_only_column(name), name
    for name in kd.PUBLIC_DISPLAY_COLUMNS + ("kiln_id", "lat", "lon", "district", "upazila", "class", "geometry",
                                             "detection_status", "nearest_place", "verified"):
        assert not kd.is_staff_only_column(name), name
    assert "priority_band" in staff.columns  # the input frame is never changed


def test_public_frame_carries_no_staff_column_or_value() -> None:
    public = _public()
    assert kd.leaked_columns(public) == []
    assert set(kd.PUBLIC_DISPLAY_COLUMNS) <= set(public.columns)
    assert public.attrs["dhoa_data_version"] == "v1-public"
    flat = public.astype(str).to_csv()
    for needle in (SENTINEL_TEXT, str(SENTINEL_DISTANCE), "near_school", "High", "Medium"):
        assert needle not in flat, needle


def test_public_marker_payload_has_no_band_signal_or_distance() -> None:
    payload = kd.public_marker_payload(_public())
    assert set(payload) == {"rows", "types", "areas"}
    assert all(len(row) == 4 for row in payload["rows"]) and len(payload["rows"]) == 6
    text = json.dumps(payload, ensure_ascii=False)
    for needle in (SENTINEL_TEXT, str(SENTINEL_DISTANCE), "priority", "band", "High", "near_school"):
        assert needle not in text, needle
    staff_text = json.dumps(kd.marker_payload(kd.with_display_columns(_staff_frame().assign(priority_band="High"), [])))
    assert "bands" in staff_text  # the staff payload still has them: the split is by function, not by accident


def test_public_map_script_is_neutral() -> None:
    tree = ast.parse(SOURCE)
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_public_marker_callback_js")
    namespace = {
        "json": json, "html": __import__("html"), "T": T, "Mapping": dict, "Any": object,
        "DESIGN_COLORS": {"unclassified": "#9aa7b4", "marker_outline": "#0b0f14", "marker_halo": "#ffffff"},
    }
    exec(compile(ast.Module([func], []), "public_js", "exec"), namespace)  # noqa: S102 - our own source
    script = namespace["_public_marker_callback_js"](kd.public_marker_payload(_public()), 7)
    for needle in ("priority", "band", "signal", "rule", "High", "Medium", "Low", "colors"):
        assert needle not in script, needle
    assert script.count("D.color") == 1  # one neutral fill, no per-band colour list


def test_community_search_on_the_public_frame_only_counts() -> None:
    frame = _public()
    places = cm.build_places(frame)
    original = kd.distances_from_point_m
    kd.distances_from_point_m = lambda lat, lon, a, b: np.zeros(len(lat))  # pyproj is not needed here
    try:
        result = cm.search(frame, places[0], None)
    finally:
        kd.distances_from_point_m = original
    assert result.summary == {"total": len(result.rows)}
    assert kd.leaked_columns(result.rows.drop(columns=["distance_m"])) == []


def test_public_district_counts_have_no_high_series() -> None:
    counts = ov.public_district_counts(_public())
    assert list(counts.columns) == ["district", "total"]
    assert counts.set_index("district")["total"].to_dict() == {"Dhaka": 4, "Gazipur": 2}
    assert ov.public_district_counts(pd.DataFrame({"x": [1]})).empty
    markup = ov.public_district_bar_html(4, 4, "All <b>")
    assert "▲" not in markup and "dhoa-bar-high" not in markup and "&lt;b&gt;" in markup


def test_community_pdf_has_no_priority_column() -> None:
    from src.eval import generate_community_report as gcr

    assert len(gcr._COLUMN_WIDTHS) == 5 and abs(sum(gcr._COLUMN_WIDTHS) - 180.0) < 1e-9
    source = (ROOT / "src" / "eval" / "generate_community_report.py").read_text(encoding="utf-8")
    assert "priority_band" not in source.replace("no priority", "") and "col_priority" not in source
    assert "priority_band" not in SOURCE[SOURCE.index("_PDF_COLUMNS ="):SOURCE.index("def _cached_community_pdf")]


def _function_source(name: str, *, docstring: bool = True) -> str:
    tree = ast.parse(SOURCE)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    if not docstring and func.body and isinstance(func.body[0], ast.Expr) and isinstance(
        getattr(func.body[0], "value", None), ast.Constant
    ) and isinstance(func.body[0].value.value, str):
        func.body = func.body[1:] or [ast.Pass()]  # the docstring may say "no priority"; the code may not use it
        return ast.unparse(func)
    return ast.get_source_segment(SOURCE, func) or ""


@pytest.mark.parametrize("name", [
    "render_overview", "render_public_districts", "_open_district_near_me", "render_community_view",
    "_render_community_inputs", "_render_community_results", "_render_community_summary",
    "_render_community_table", "_render_community_map", "_render_public_candidate",
    "_public_marker_callback_js", "_cached_public_marker_payload", "render_about",
])
def test_public_render_functions_never_touch_staff_data(name: str) -> None:
    body = _function_source(name, docstring=False)
    assert body, name
    for needle in ("priority", "ui_popup_html", "marker_payload(frame, _siting", "breach", "dist_", "signal_provenance",
                   "DOWNLOAD_COMMUNITY_CSV", "PRIORITY_NOTE"):
        assert needle not in body.replace("_cached_public_marker_payload", "").replace("public_marker_payload", ""), (name, needle)


def test_main_hands_only_the_public_frame_to_public_views() -> None:
    body = _function_source("main")
    for call in ("render_overview(public_gdf)", "render_about(public_gdf)", "render_community_view(public_gdf)"):
        assert call in body, call
    for call in ("render_overview(gdf)", "render_about(gdf)", "render_community_view(gdf)"):
        assert call not in body, call
    assert "render_overview_charts(" not in body and "render_portal_dashboard(gdf)" in body


def test_staff_charts_refuse_to_render_for_the_public() -> None:
    body = _function_source("render_overview_charts")
    assert body.index("roles.is_staff()") < body.index("ov.district_stats(gdf)")


def test_public_text_is_neutral_in_both_languages() -> None:
    names = ("PUB_HERO_MISSION", "PUB_HERO_SUB", "PUB_OV_DISTRICTS_HINT", "PUB_OV_OPEN_DISTRICT_FMT",
             "PUB_HOW_3_HEAD", "PUB_HOW_3_BODY", "HELP_COMMUNITY")
    banned = ("priority", "অগ্রাধিকার", "rank", "illegal", "violation", "breach", "inspector", "পরিদর্শক", "csv", "list")
    for name in names:
        for language in T.LANGUAGES:
            text = T.text(name, language)
            assert text.strip(), (name, language)
            if name != "HELP_COMMUNITY":  # help text may say "list" (the place list), never the staff words
                banned_here = banned
            else:
                banned_here = banned[:-2]
            assert not any(word in text.casefold() for word in banned_here), (name, language)
    assert T.text("PUB_OV_OPEN_DISTRICT_FMT", "en").format("Dhaka") == "See kiln candidates in Dhaka"
    for language in T.LANGUAGES:
        assert "{0}" in T.text("PUB_OV_OPEN_DISTRICT_FMT", language)


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pytest.importorskip("streamlit")
    pytest.importorskip("geopandas")
    pytest.importorskip("pyarrow")
    from tests.synthetic import write_parquet

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    return tmp_path


def _page_text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [b.label for b in at.button]
    parts += [i.value for i in at.info] + [h.value for h in at.subheader]
    return " ".join(str(part) for part in parts)


def test_public_overview_apptest_has_three_numbers_a_button_and_no_priority(data_dir: Path) -> None:
    """Not run in the authoring sandbox (no streamlit)."""
    from streamlit.testing.v1 import AppTest

    for language in T.LANGUAGES:
        at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
        at.session_state["dhoa_lang"] = language
        at.run()
        assert not at.exception
        text = _page_text(at)
        assert T.text("PUB_HERO_MISSION", language) in text
        assert text.count("dhoa-metric'") == 3  # kiln candidates, districts covered, data date
        for banned in (T.text("OV_SERIES_HIGH", language), T.text("OV_TYPES_TITLE", language),
                       T.text("METRIC_HIGH_PRIORITY_KILNS", language), T.text("PRIORITY_NOTE", language),
                       "dhoa-bar-high", "dhoa-split", "▲"):
            assert banned not in text, banned
        assert any(b.key == "dhoa_hero_near" for b in at.button)
        assert not any(b.key == "dhoa_hero_map" for b in at.button)
        assert [b for b in at.button if b.key and b.key.startswith("dhoa_ov_open_")]


def test_public_district_button_opens_near_me_for_that_district(data_dir: Path) -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120).run()
    button = next(b for b in at.button if b.key and b.key.startswith("dhoa_ov_open_"))
    district = button.key.removeprefix("dhoa_ov_open_")
    button.click().run()
    assert not at.exception
    assert at.session_state["dhoa_view_mode"] == "community"
    assert at.session_state["community_place_key"] == cm.place_key(cm.KIND_DISTRICT, district)
    assert at.session_state["dhoa_role"] if "dhoa_role" in at.session_state else True
    text = _page_text(at)
    assert T.text("C_SUMMARY_HIGH_FMT", "bn").split("{")[0].strip() not in text  # no "of them high priority"
    assert not any(w in text for w in (T.text("PRIORITY", "bn"), T.text("SUMMARY_HIGH", "bn")))
    assert not any(b.key == "community_candidates_csv_download" for b in at.get("download_button"))


def test_staff_dashboard_keeps_the_high_series_and_type_split(data_dir: Path) -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_role"] = "inspector"
    at.session_state["dhoa_staff_name"] = "Test"
    at.session_state["dhoa_view_mode"] = "inspector"
    at.session_state["dhoa_portal_tab"] = "dashboard"
    at.run()
    assert not at.exception
    text = _page_text(at)
    assert "dhoa-bar-high" in text and "dhoa-split" in text
    assert any(T.text("METRIC_HIGH_PRIORITY_KILNS", "bn") in str(m.label) for m in at.metric)
