"""M4 Inspector redesign: priority shapes, summary strip, note, detail card, states."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import app.kiln_data as kd
import app.strings as T
import app.streamlit_app as dashboard

ROOT = Path(__file__).resolve().parents[1]


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "kiln_id": list("abcde"),
            "lat": [23.7, 23.8, 23.9, 24.0, 24.1],
            "lon": [90.4] * 5,
            "class": ["FCBK", "Zigzag", "Zigzag", "FCBK", "Zigzag"],
            "priority_band": ["High", "High", "Medium", "Low", "weird"],
            "detection_status": [kd.NEW_CANDIDATE_STATUS, "Known (2023-24 survey)"] * 2 + [kd.NEW_CANDIDATE_STATUS],
            "district": ["Dhaka"] * 5,
            "upazila": ["Savar"] * 5,
        }
    )


def test_priority_summary_counts_bands_and_new_candidates() -> None:
    """The strip counts each band and new candidates column-wise; empty is all zeros."""
    counts = kd.priority_summary(_frame())
    assert counts == {"total": 5, "high": 2, "medium": 1, "low": 1, "new": 3}
    assert kd.priority_summary(_frame().iloc[0:0]) == {"total": 0, "high": 0, "medium": 0, "low": 0, "new": 0}
    assert kd.priority_summary(pd.DataFrame({"x": [1, 2]}))["high"] == 0


def test_priority_badges_use_distinct_shapes_not_colour_alone() -> None:
    """High/Medium/Low have three different shape glyphs plus a text label."""
    glyphs = kd.PRIORITY_GLYPHS
    assert len(set(glyphs.values())) == 3
    for band in ("High", "Medium", "Low"):
        badge = kd.priority_badge(band)
        assert badge.startswith(glyphs[band]) and kd.priority_label(band) in badge


def test_marker_js_draws_a_different_shape_per_priority_band() -> None:
    """Marker icons are shaped SVGs (triangle/diamond/circle/square), not only coloured dots."""
    js = dashboard._marker_callback_js(kd.marker_payload(_frame(), []))
    for shape in ("<polygon points='11,2 21,19 1,19'", "<polygon points='11,1 21,11 11,21 1,11'", "<circle", "<rect"):
        assert shape in js
    assert "L.marker(" in js and "L.divIcon(" in js and "circleMarker" not in js
    assert "bindPopup" not in js


def test_priority_note_states_relative_shares_matching_the_data() -> None:
    """The note says the bands are relative shares, and 20/40/40 matches the real band sizes."""
    assert "আপেক্ষিক" in T.PRIORITY_NOTE and "পরম" in T.PRIORITY_NOTE
    path = ROOT / "data" / "processed" / "kilns_prioritised.parquet"
    if not path.exists():
        pytest.skip("parquet not present")
    bands = pd.read_parquet(path, columns=["priority_band"])["priority_band"].astype(str).value_counts()
    total = int(bands.sum())
    assert [round(100 * int(bands[b]) / total) for b in ("High", "Medium", "Low")] == [20, 40, 40]


def test_new_strings_are_real_bangla_without_escapes() -> None:
    """New copy is stored as Bangla characters (no \\u escapes) and has no developer wording."""
    source = (ROOT / "app" / "strings.py").read_text(encoding="utf-8")
    assert "\\u0" not in source.replace("\\u200d", "")
    for text in (T.PRIORITY_NOTE, T.EMPTY_FILTER_HINT, T.LOADING_MAP, T.DETAIL_HINT, T.RAIL_HINT):
        assert any("\u0980" <= ch <= "\u09ff" for ch in text)


def test_inspector_apptest_renders_summary_strip_and_note() -> None:
    """AppTest: the Inspector loads without exceptions and shows the strip and the note."""
    if not (ROOT / "data" / "processed" / "kilns_prioritised.parquet").exists():
        pytest.skip("parquet not present")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.session_state["dhoa_view_mode"] = "inspector"  # P2: the default view is now the Overview
    at.session_state["dhoa_role"] = "inspector"; at.session_state["dhoa_staff_name"] = "Test"
    at.run()
    assert not at.exception
    markdown = " ".join(m.value for m in at.markdown)
    assert "dhoa-summary" in markdown
    assert any(T.PRIORITY_NOTE == c.value for c in at.caption)
    assert not any(e.value == T.COULD_NOT_RENDER_THE_DASHBOARD for e in at.error)


def test_inspector_apptest_empty_filter_shows_reset_state() -> None:
    """AppTest: a district/area/priority combination with no kilns shows the empty state."""
    path = ROOT / "data" / "processed" / "kilns_prioritised.parquet"
    if not path.exists():
        pytest.skip("parquet not present")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.session_state["dhoa_view_mode"] = "inspector"  # P2: the default view is now the Overview
    at.session_state["dhoa_role"] = "inspector"; at.session_state["dhoa_staff_name"] = "Test"
    at.run()
    # Adabor is a listed Dhaka area with no kilns in the data (empty result, not an error).
    at.selectbox(key="w_filter_district@bn").select("Dhaka").run()
    at.selectbox(key="w_filter_upazila@bn").select("Adabor")
    next(b for b in at.button if b.label == T.APPLY_FILTERS).click().run()
    assert not at.exception
    assert any(T.NO_KILNS_IN_AREA_FMT.format("Adabor") == i.value for i in at.info)
    assert any(b.key == "dhoa_empty_reset_filters" for b in at.button)
    next(b for b in at.button if b.key == "dhoa_empty_reset_filters").click().run()
    assert not at.exception
    assert not any(b.key == "dhoa_empty_reset_filters" for b in at.button)
