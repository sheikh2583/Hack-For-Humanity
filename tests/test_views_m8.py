"""M8 AppTests for both views on hermetic synthetic data (DHOA_DATA_DIR)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("geopandas")
pytest.importorskip("pyarrow")

import app.community as cm  # noqa: E402
import app.strings as T  # noqa: E402
from tests.synthetic import REMOTE_PLACE, write_parquet  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    return tmp_path


def _run(view: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_view_mode"] = view
    if view == "inspector":
        at.session_state["dhoa_role"] = "inspector"
        at.session_state["dhoa_staff_name"] = "Test"
    return at.run()


def _picker_index(at, needle: str) -> int:
    options = at.selectbox(key="w_community_suggestion@bn").options
    return next(i for i, label in enumerate(options) if needle in label)


def test_inspector_loads_without_exception(data_dir: Path) -> None:
    at = _run("inspector")
    assert not at.exception
    assert not any(e.value == T.COULD_NOT_RENDER_THE_DASHBOARD for e in at.error)
    assert any(T.PRIORITY_NOTE == c.value for c in at.caption)


def test_inspector_district_filter_reduces_results(data_dir: Path) -> None:
    at = _run("inspector")
    at.selectbox(key="w_filter_district@bn").select("Gazipur").run()
    next(b for b in at.button if b.label == T.APPLY_FILTERS).click().run()
    assert not at.exception
    markdown = " ".join(m.value for m in at.markdown)
    assert "dhoa-summary" in markdown


def test_community_prompts_then_answers_for_each_kind_of_choice(data_dir: Path) -> None:
    at = _run("community")
    assert not at.exception and any(i.value == T.C_PICK_PROMPT for i in at.info)
    for needle in ("Savar", "Tongi", REMOTE_PLACE):
        index = _picker_index(at, needle)
        at.selectbox(key="w_community_suggestion@bn").select_index(index).run()
        assert not at.exception, needle
        assert not any(i.value == T.C_PICK_PROMPT for i in at.info), needle


def test_community_empty_state_offers_one_click_widen(data_dir: Path) -> None:
    at = _run("community")
    at.session_state["community_radius_m"] = 1000
    index = _picker_index(at, REMOTE_PLACE)
    at.selectbox(key="w_community_suggestion@bn").select_index(index).run()
    assert not at.exception
    assert any("কিমি" in i.value and "কোনো ভাটা পাওয়া যায়নি" in i.value for i in at.info)
    widen = [b for b in at.button if b.key == "community_widen"]
    assert widen, "no widen button"
    widen[0].click().run()
    assert not at.exception
    assert at.session_state["community_radius_m"] in cm.RADIUS_CHOICES_M
    assert at.session_state["community_radius_m"] > 1000
    assert not any(b.key == "community_widen" for b in at.button)


def test_community_point_outside_coverage_is_explained(data_dir: Path) -> None:
    at = _run("community")
    at.session_state["community_origin"] = {"name": "far", "lat": 22.35, "lon": 91.80}
    at.run()
    assert not at.exception
    assert any("আওতাভুক্ত" in w.value for w in at.warning)


def test_language_switch_keeps_filters_and_gives_same_results(data_dir: Path) -> None:
    """Switching bn -> en remounts the sidebar widgets with English option text, same filter, same rows."""
    at = _run("inspector")
    at.selectbox(key="w_filter_district@bn").select("Gazipur").run()
    next(b for b in at.button if b.label == T.APPLY_FILTERS).click().run()
    assert at.session_state["filter_district"] == "Gazipur"
    at.radio(key="dhoa_lang").set_value("en").run()
    assert not at.exception
    assert at.session_state["filter_district"] == "Gazipur"
    assert at.session_state["filter_priority"] == ["High", "Medium", "Low"]
    assert not any("w_filter_district@bn" == w.key for w in at.selectbox)
    english_district = at.selectbox(key="w_filter_district@en")
    assert english_district.value == "Gazipur"
    # priority is a pills control now (not exposed by AppTest): the seeded value must be canonical English keys
    assert at.session_state["w_filter_priority@en"] == ["High", "Medium", "Low"]
    assert not any(i.value == T.text("NO_CANDIDATES_MATCH_THESE_FILTERS", "en") for i in at.info)


def test_overview_is_the_default_and_hero_buttons_switch_views(data_dir: Path) -> None:
    """P2 (not run in the authoring sandbox): landing hero, real counts, and both CTAs."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120).run()
    assert not at.exception
    markdown = " ".join(m.value for m in at.markdown if not m.value.lstrip().startswith("<style"))
    assert "dhoa-hero" in markdown and T.PUB_HERO_MISSION in markdown
    assert "dhoa-summary" not in markdown  # the map summary strip is not on the landing page
    assert not any(b.key == "dhoa_hero_map" for b in at.button)  # the public never gets the staff-map button
    staff = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    staff.session_state["dhoa_role"] = "inspector"
    staff.session_state["dhoa_staff_name"] = "Test"
    staff.run()
    staff.button(key="dhoa_hero_map").click().run()
    assert staff.session_state["dhoa_view_mode"] == "inspector" and not staff.exception
    assert any(T.PRIORITY_NOTE == c.value for c in staff.caption)
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120).run()
    at.button(key="dhoa_hero_near").click().run()
    assert at.session_state["dhoa_view_mode"] == "community" and not at.exception


def test_about_view_renders(data_dir: Path) -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_view_mode"] = "about"
    at.run()
    assert not at.exception and T.ABOUT_BODY in " ".join(m.value for m in at.markdown)
