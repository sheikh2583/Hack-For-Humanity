"""Map-first layout: the map is the first thing on screen; sidebar fits without scrolling."""

from __future__ import annotations

import re
from pathlib import Path

import app.styles as styles

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
CSS = styles.page_css("x")


def test_map_comes_before_the_list_and_is_wider() -> None:
    assert "map_panel, list_panel = st.columns([3, 2]" in SOURCE
    assert "list_panel, map_panel" not in SOURCE


def test_header_is_one_row_and_tool_views_have_no_subtitle_or_divider() -> None:
    body = SOURCE[SOURCE.index("def render_header"):SOURCE.index("def render_overview")]
    assert 'st.container(key="dhoa_header_row")' in body and "st.columns(\n            [1.1, 7.2, 1.7, 1.8]" in body
    assert 'if selected_mode not in ("inspector", "community"):' in body
    assert body.index("st.divider()") > body.index('if selected_mode not in ("inspector", "community")')


def test_sidebar_is_compact_priority_is_pills_and_map_type_left_the_sidebar() -> None:
    sidebar = SOURCE[SOURCE.index("def render_sidebar"):SOURCE.index("def _metres_text")]
    assert "st.pills(" in sidebar and "st.multiselect(" not in sidebar
    assert "_render_map_type_filter()" not in sidebar and "st.download_button" not in sidebar
    assert "T.SEARCH_2" not in sidebar and "T.RAIL_HINT" not in sidebar
    assert sidebar.index("RESET_FILTERS") < sidebar.index("dhoa_sidebar_contact")


def test_map_toolbar_holds_legend_heat_toggle_and_map_type() -> None:
    render_map = SOURCE[SOURCE.index("def render_map("):SOURCE.index("render_map_fragment = ")]
    assert 'st.container(key="dhoa_map_toolbar")' in render_map
    assert render_map.index("dhoa_map_toolbar") < render_map.index("_render_map_type_filter()") < render_map.index("st_folium(")
    # the report button / hint now sits below the map, not above it
    assert render_map.index("st_folium(") < render_map.index("_render_report_download(")


def test_css_sizes_map_to_the_window_and_keeps_rows_on_phones() -> None:
    assert "clamp(420px, calc(100dvh - 300px), 860px)" in CSS
    assert "clamp(300px, 55dvh, 520px)" in CSS  # the phone rule is unchanged
    assert re.search(r"\.st-key-dhoa_header_row \[data-testid=\"stColumn\"\]:nth-child\(4\) \{ order: 2", CSS)
    assert ".dhoa-summary .dhoa-metric { padding" in CSS and CSS.count("{") == CSS.count("}")


def test_list_frame_height_follows_the_window_on_desktop() -> None:
    html = (ROOT / "app" / "components" / "priority_candidate_list" / "index.html").read_text(encoding="utf-8")
    assert "viewport.height - 250" in html and "args.height || 760" not in html
