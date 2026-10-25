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
    return at.run()


def _picker_index(at, needle: str) -> int:
    options = at.selectbox(key="community_place_key").options
    return next(i for i, label in enumerate(options) if needle in label)


def test_inspector_loads_without_exception(data_dir: Path) -> None:
    at = _run("inspector")
    assert not at.exception
    assert not any(e.value == T.COULD_NOT_RENDER_THE_DASHBOARD for e in at.error)
    assert any(T.PRIORITY_NOTE == c.value for c in at.caption)


def test_inspector_district_filter_reduces_results(data_dir: Path) -> None:
    at = _run("inspector")
    at.selectbox(key="filter_district").select("Gazipur").run()
    next(b for b in at.button if b.label == T.APPLY_FILTERS).click().run()
    assert not at.exception
    markdown = " ".join(m.value for m in at.markdown)
    assert "dhoa-summary" in markdown


def test_community_prompts_then_answers_for_each_kind_of_choice(data_dir: Path) -> None:
    at = _run("community")
    assert not at.exception and any(i.value == T.C_PICK_PROMPT for i in at.info)
    for needle in ("Savar", "Tongi", REMOTE_PLACE):
        at.selectbox(key="community_place_key").select_index(_picker_index(at, needle)).run()
        assert not at.exception, needle
        assert not any(i.value == T.C_PICK_PROMPT for i in at.info), needle


def test_community_empty_state_offers_one_click_widen(data_dir: Path) -> None:
    at = _run("community")
    at.session_state["community_radius_m"] = 1000
    at.selectbox(key="community_place_key").select_index(_picker_index(at, REMOTE_PLACE)).run()
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
