"""P3 overview statistics, markup and drill-down (pure tests plus one hermetic AppTest)."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

import app.overview as ov
import app.strings as T

ROOT = Path(__file__).resolve().parents[1]
NEW_NAMES = (
    "OV_DISTRICTS_TITLE", "OV_DISTRICTS_HINT", "OV_OPEN_DISTRICT_FMT", "OV_SERIES_TOTAL",
    "OV_SERIES_HIGH", "OV_UPAZILAS_TITLE", "OV_COL_CANDIDATES", "OV_COL_HIGH", "OV_TYPES_TITLE",
    "OV_TYPE_OTHER", "OV_SHARE_FMT", "OV_NO_DATA",
)
BANNED = ("লঙ্ঘন", "বিপজ্জনক", "violation", "hazardous", "illegal", "advisory")


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "district": ["Dhaka", "Dhaka", "Dhaka", "Gazipur", "Gazipur", "Rajshahi", " ", None],
        "upazila": ["Savar", "Savar", "Keraniganj", "Tongi", "Tongi", "Boalia", "X", None],
        "priority_band": ["High", "Low", "High", "Medium", "High", "Low", "High", "Low"],
        "class": ["Zigzag", "FCBK", "Zigzag", "Zigzag", None, "FCBK", "Other", "Zigzag"],
    })


def test_district_stats_match_an_independent_groupby() -> None:
    frame = _frame()
    stats = ov.district_stats(frame).set_index("district")
    valid = frame[frame["district"].fillna("").str.strip().ne("")]
    assert stats["total"].to_dict() == valid.groupby("district").size().to_dict()
    for band in ("High", "Medium", "Low"):
        expected = valid[valid["priority_band"] == band].groupby("district").size()
        got = stats[band.lower()]
        for district in stats.index:
            assert got[district] == int(expected.get(district, 0)), (district, band)
    assert list(ov.district_stats(frame)["district"]) == ["Dhaka", "Gazipur", "Rajshahi"]  # ranked


def test_district_stats_sum_to_rows_with_a_district_and_handle_missing_columns() -> None:
    frame = _frame()
    assert int(ov.district_stats(frame)["total"].sum()) == 6
    assert ov.district_stats(pd.DataFrame()).empty
    assert ov.district_stats(frame.drop(columns=["priority_band"]))["high"].sum() == 0


def test_upazila_stats_rank_and_keep_same_name_in_two_districts_apart() -> None:
    frame = pd.concat([_frame(), pd.DataFrame({"district": ["Gazipur"], "upazila": ["Savar"],
                                               "priority_band": ["High"], "class": ["Zigzag"]})])
    top = ov.upazila_stats(frame, limit=3)
    assert top.iloc[0].to_dict() == {"upazila": "Savar", "district": "Dhaka", "total": 2, "high": 1}
    savar = ov.upazila_stats(frame, limit=50).query("upazila == 'Savar'")
    assert sorted(savar["district"]) == ["Dhaka", "Gazipur"]
    assert int(ov.upazila_stats(frame, limit=50)["total"].sum()) == int(frame["upazila"].notna().sum())
    assert len(ov.upazila_stats(frame, limit=2)) == 2 and ov.upazila_stats(frame, limit=0).empty


def test_type_split_counts_add_up() -> None:
    frame = _frame()
    parts = dict(ov.type_split(frame))
    assert parts == {"Zigzag": int((frame["class"] == "Zigzag").sum()),
                     "FCBK": int((frame["class"] == "FCBK").sum()),
                     "other": 2}
    assert sum(parts.values()) == len(frame)
    assert ov.type_split(pd.DataFrame({"x": [1, 2]})) == [("other", 2)]
    assert ov.type_split(pd.DataFrame()) == []


def test_bar_width_scales_to_the_maximum() -> None:
    assert ov.bar_width(50, 200) == 25.0 and ov.bar_width(200, 200) == 100.0
    assert ov.bar_width(0, 200) == 0.0 and ov.bar_width(5, 0) == 0.0


def test_bar_markup_prints_values_pairs_high_with_glyph_and_escapes() -> None:
    row = {"district": "Dhaka", "total": 1234, "high": 56}
    markup = ov.district_bar_html(row, 1234, "All <b>", "High & co")
    assert "1,234" in markup and "▲ 56" in markup and "width:100.0%" in markup
    assert "<b>" not in markup and "&lt;b&gt;" in markup and "&amp; co" in markup
    legend = ov.bars_legend_html("A", "B")
    assert "▲" in legend and "dhoa-key-total" in legend


def test_split_markup_names_every_segment_with_count_and_share() -> None:
    markup = ov.type_split_html([("Zigzag", 3), ("FCBK", 1)], {"Zigzag": "Z", "FCBK": "F<"}, "{0:.0f}%")
    assert "<strong>3</strong>" in markup and "75%" in markup and "25%" in markup
    assert "F<" not in markup and "F&lt;" in markup
    assert "dhoa-split-zigzag" in markup and "dhoa-split-fcbk" in markup
    assert ov.type_split_html([], {}, "{0}") == ""


def test_new_strings_in_both_languages_with_matching_fields() -> None:
    for name in NEW_NAMES:
        for language in T.LANGUAGES:
            text = T.text(name, language)
            assert text.strip() and not any(w in text.casefold() for w in BANNED), (name, language)
    assert T.text("OV_DISTRICTS_TITLE", "bn") != T.text("OV_DISTRICTS_TITLE", "en")
    assert T.text("OV_OPEN_DISTRICT_FMT", "en").format("Dhaka") == "Open Dhaka on the map"


def test_app_wiring_district_buttons_open_the_map_filtered() -> None:
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_open_district")
    body = ast.get_source_segment(source, func)
    assert '"dhoa_view_mode"] = "inspector"' in body and '"filter_district"] = district' in body
    assert "on_click=_open_district" in source and "dhoa_ov_open_" in source
    assert "render_overview_charts(gdf)" in source


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pytest.importorskip("streamlit")
    pytest.importorskip("geopandas")
    pytest.importorskip("pyarrow")
    from tests.synthetic import write_parquet

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    return tmp_path


def test_overview_charts_render_and_a_district_button_opens_the_filtered_map(data_dir: Path) -> None:
    """Not run in the authoring sandbox (no streamlit): bars render; the button filters the map."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120).run()
    assert not at.exception
    markdown = " ".join(m.value for m in at.markdown)
    assert "dhoa-bar-block" in markdown and "dhoa-split" in markdown
    district_buttons = [b for b in at.button if b.key and b.key.startswith("dhoa_ov_open_")]
    assert district_buttons
    target = district_buttons[0].key.removeprefix("dhoa_ov_open_")
    district_buttons[0].click().run()
    assert not at.exception
    assert at.session_state["dhoa_view_mode"] == "inspector"
    assert at.session_state["filter_district"] == target
