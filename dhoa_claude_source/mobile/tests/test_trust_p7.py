"""P7: contact flag, trust panels, state cards (pure; no Streamlit run needed)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

import app.strings as T
import app.trust as trust
from src.eval.generate_community_report import generate_community_report

ROOT = Path(__file__).resolve().parents[1]
NEW = (
    "HOTLINE_LINE_FMT", "DOE_WEB_LINE", "FOOTER_WEB_LABEL", "CONTACT_CALL", "CONTACT_SMS", "HOW_TITLE",
    "HOW_1_HEAD", "HOW_1_BODY", "HOW_2_HEAD", "HOW_2_BODY", "HOW_3_HEAD", "HOW_3_BODY", "HOW_4_HEAD",
    "HOW_4_BODY", "ABOUT_DATA_TITLE", "ABOUT_DATA_DATE", "ABOUT_SOURCES", "ABOUT_SOURCES_VALUE",
    "ABOUT_COVERAGE", "ABOUT_COVERAGE_FMT", "ABOUT_TEAM", "ABOUT_METHODOLOGY", "STATE_RETRY",
    "STATE_ERROR_TITLE", "STATE_ERROR_BODY", "STATE_DATA_TITLE", "STATE_DATA_BODY", "STATE_LOADING",
    "LIST_ARIA_LABEL", "LIST_ARIA_SELECT_FMT",
)


def _cfg(**contact: object) -> dict:
    return {"contact": {"hotline_number": "16131", "website": "https://doe.gov.bd", **contact}}


def test_committed_config_keeps_hotline_hidden_until_verified() -> None:
    config = yaml.safe_load((ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))
    assert config["contact"]["hotline_verified"] is False
    assert trust.contact_settings(config)["number"] is None


def test_hotline_needs_explicit_true_and_valid_number() -> None:
    assert trust.contact_settings(_cfg(hotline_verified="yes"))["number"] is None
    assert trust.contact_settings(_cfg(hotline_verified=True, hotline_number="<x>"))["number"] is None
    assert trust.contact_settings(_cfg(hotline_verified=True))["number"] == "16131"
    assert trust.contact_settings(None)["number"] is None


def test_footer_unverified_has_no_number_or_phone_links() -> None:
    markup = trust.contact_footer_html(trust.contact_settings(_cfg(hotline_verified=False)), "L", "Web", "Call", "SMS")
    assert "16131" not in markup and "tel:" not in markup and "sms:" not in markup and "doe.gov.bd" in markup


def test_footer_verified_has_call_sms_and_bangla_digits() -> None:
    settings = trust.contact_settings(_cfg(hotline_verified=True))
    markup = trust.contact_footer_html(settings, "L", "Web", "Call", "SMS", "bn")
    assert "href='tel:16131'" in markup and "href='sms:16131'" in markup and "১৬১৩১" in markup


def test_panels_escape_text_and_skip_empty_values() -> None:
    assert "<b>" not in trust.steps_html("<b>t</b>", [("<i>h</i>", "b & c")])
    facts = trust.facts_html("T", [("a", "1"), ("b", "")])
    assert "<dt>a</dt>" in facts and "<dt>b</dt>" not in facts


def test_state_cards_announce_errors_and_methodology_url_is_validated() -> None:
    assert "role='alert'" in trust.state_html("error", "t", "b")
    assert "role='status'" in trust.state_html("empty", "t", "b")
    assert trust.methodology_url({"about": {"methodology_url": "javascript:alert(1)"}}) is None
    assert trust.methodology_url({"about": {"methodology_url": "https://example.org/x"}})
    assert trust.team_names({"about": {"team": [" A ", ""]}}) == ["A"]


def test_skeleton_is_labelled() -> None:
    assert "aria-label='Loading'" in trust.skeleton_html("Loading")


def test_new_strings_exist_in_both_languages_and_are_neutral() -> None:
    for name in NEW:
        for lang in ("bn", "en"):
            T.set_language(lang)
            assert getattr(T, name), (name, lang)
    banned = ("violation", "hazardous", "illegal", "advisory", "লঙ্ঘন", "বিপজ্জনক")
    T.set_language("en")
    assert not any(word in getattr(T, name).lower() for name in NEW for word in banned)


def test_community_pdf_hotline_line_follows_flag() -> None:
    rows = pd.DataFrame({"distance_m": [1.0], "class": ["FCBK"], "priority_band": ["High"], "lat": [23.7], "lon": [90.4]})
    assert generate_community_report("Savar", rows, 1000, "en", hotline=None).startswith(b"%PDF")
    assert generate_community_report("Savar", rows, 1000, "bn", hotline="16131").startswith(b"%PDF")


def test_favicon_exists() -> None:
    assert (ROOT / "app" / "static" / "favicon.png").stat().st_size > 200


# ---- AppTests on hermetic synthetic data (skipped when streamlit/pyarrow are missing) ----
import pytest  # noqa: E402

pytest.importorskip("streamlit")
pytest.importorskip("geopandas")
pytest.importorskip("pyarrow")
from tests.synthetic import write_parquet  # noqa: E402


def _app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str, lang: str = "bn"):
    from streamlit.testing.v1 import AppTest

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_view_mode"] = view
    at.session_state["dhoa_lang"] = lang
    return at.run()


def _body(at) -> str:
    return " ".join(m.value for m in at.markdown if not m.value.lstrip().startswith("<style"))


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_about_page_has_how_it_works_data_and_no_unverified_hotline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lang: str
) -> None:
    at = _app(tmp_path, monkeypatch, "about", lang)
    assert not at.exception
    body = _body(at)
    assert "dhoa-steps" in body and "dhoa-facts" in body
    assert "16131" not in body and "১৬১৩১" not in body and "tel:" not in body
    assert "doe.gov.bd" in body


@pytest.mark.parametrize("view", ["overview", "inspector"])
def test_every_view_runs_and_shows_website_only_footer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str
) -> None:
    at = _app(tmp_path, monkeypatch, view)
    assert not at.exception
    assert "doe.gov.bd" in _body(at) and "tel:" not in _body(at)
