"""R3: one Map screen with the Near me place search built in.

Input: app source, ``hero`` and the AppTest harness with synthetic data. Output: assertions that
(1) the top navigation is Overview, Map, About; (2) an old stored ``community`` view opens the Map;
(3) the search bar is on the Map and a chosen place shows nearby results with a way back;
(4) filters survive a search. The source-level tests need no Streamlit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
PICKER = "w_community_place_key@bn"


def test_navigation_has_three_items() -> None:
    import app.hero as hero

    assert hero.VIEW_MODES == ("overview", "inspector", "about")
    nav = SOURCE[SOURCE.index("def _nav_label"):SOURCE.index("def _go_to_view")]
    assert "NAV_NEAR_ME" not in nav and "community" not in nav


def test_there_is_no_separate_near_me_view_any_more() -> None:
    assert "def render_community_view" not in SOURCE
    assert 'if mode == "community"' not in SOURCE
    assert "def render_map_screen" in SOURCE and "render_map_screen(gdf, filters, visible)" in SOURCE
    assert "_render_community_inputs" not in SOURCE


def test_search_bar_reuses_the_existing_widget_keys() -> None:
    bar = SOURCE[SOURCE.index("def _render_search_bar"):SOURCE.index("def _render_community_empty")]
    for needle in ('key="dhoa_search_bar"', '_wkey("community_place_key")', '_wkey("community_radius_m")',
                   'key="community_gps"', 'key="community_example"', '"community_geocode_form"'):
        assert needle in bar, needle


def test_overview_near_me_button_opens_the_map_with_focus() -> None:
    assert 'on_click=_go_to_search' in SOURCE
    body = SOURCE[SOURCE.index("def _go_to_search"):SOURCE.index("def render_header")]
    assert '"dhoa_view_mode"] = "inspector"' in body and '"dhoa_focus_search"] = True' in body


def test_new_strings_exist_in_both_languages() -> None:
    import importlib

    for lang in ("bn", "en"):
        module = importlib.import_module(f"app.strings_{lang}")
        for name in ("MAP_CLEAR_SEARCH", "MAP_SEARCH_FILTERS_NOTE"):
            assert getattr(module, name).strip(), (lang, name)


def _app(view: str):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_view_mode"] = view
    return at.run()


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from tests.synthetic import write_parquet

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    return tmp_path


def test_old_stored_community_view_opens_the_map(data_dir: Path) -> None:
    at = _app("community")
    assert not at.exception
    assert at.session_state["dhoa_view_mode"] == "inspector"
    assert at.selectbox(key=PICKER) is not None


def test_choosing_a_place_shows_results_and_clear_returns_to_the_map(data_dir: Path) -> None:
    at = _app("inspector")
    assert not at.exception and not any(b.key == "dhoa_clear_search" for b in at.button)
    picker = at.selectbox(key=PICKER)
    picker.select_index(next(i for i, label in enumerate(picker.options) if label)).run()
    assert not at.exception
    assert any(b.key == "dhoa_clear_search" for b in at.button)
    next(b for b in at.button if b.key == "dhoa_clear_search").click().run()
    assert not at.exception
    assert at.session_state["community_place_key"] is None
    assert not any(b.key == "dhoa_clear_search" for b in at.button)


def test_sidebar_filters_survive_a_search(data_dir: Path) -> None:
    at = _app("inspector")
    at.selectbox(key="w_filter_district@bn").select("Gazipur").run()
    picker = at.selectbox(key=PICKER)
    picker.select_index(next(i for i, label in enumerate(picker.options) if label)).run()
    assert not at.exception
    assert at.session_state["filter_district"] == "Gazipur"
