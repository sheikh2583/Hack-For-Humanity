"""S1: roles, the Inspector Portal sign-in gate, the four fixed sections and the sub-tabs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT))

import hero  # noqa: E402
import roles  # noqa: E402
import strings as T  # noqa: E402


def test_default_is_public_and_sign_in_needs_the_passcode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHOA_STAFF_PASSCODE", "s3cret")
    state: dict = {}
    assert roles.get_role(state) == "public" and not roles.is_staff(state)
    assert not roles.sign_in("wrong", "Rina", state) and roles.get_role(state) == "public"
    assert not roles.sign_in("", "Rina", state)
    assert roles.sign_in("s3cret", "  Rina   Akter ", state)
    assert roles.is_staff(state) and roles.staff_name(state) == "Rina Akter"
    roles.sign_out(state)
    assert roles.get_role(state) == "public" and roles.staff_name(state) == ""


def test_without_a_configured_passcode_nobody_can_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DHOA_STAFF_PASSCODE", raising=False)
    monkeypatch.setenv("DHOA_DEMO_MODE", "1")
    state: dict = {}
    assert not roles.signin_available()
    assert not roles.sign_in("", "x", state) and not roles.sign_in("anything", "x", state)
    assert roles.demo_enabled() and roles.get_role(state) == "public"


def test_demo_mode_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHOA_STAFF_PASSCODE", "public-demo-passcode")
    monkeypatch.setenv("DHOA_DEMO_MODE", "1")
    state: dict = {}
    assert roles.demo_enabled() and roles.signin_available()
    assert roles.sign_in("public-demo-passcode", roles.DEMO_NAME, state)
    assert roles.staff_name(state) == roles.DEMO_NAME


def test_blank_name_and_long_name_are_cleaned() -> None:
    assert roles.clean_name("   ") == "Staff" and roles.clean_name(None) == "Staff"
    assert len(roles.clean_name("x" * 200)) == 60


def test_four_fixed_sections_in_order_with_labels_in_both_languages() -> None:
    assert hero.VIEW_MODES == ("overview", "community", "inspector", "about")
    for lang in T.LANGUAGES:
        names = [T.text(k, lang) for k in ("NAV_OVERVIEW", "NAV_NEAR_ME", "NAV_INSPECTOR", "NAV_ABOUT")]
        assert all(names) and len(set(names)) == 4
    assert T.text("NAV_INSPECTOR", "en").startswith("🔒") and T.text("NAV_INSPECTOR", "bn").startswith("🔒")


def test_portal_strings_exist_in_both_languages_and_have_no_legal_wording() -> None:
    names = [n for n in dir(__import__("strings_en")) if n.startswith("PORTAL_")]
    assert names
    for name in names:
        for lang in T.LANGUAGES:
            value = T.text(name, lang)
            assert value and not any(w in value.lower() for w in ("illegal", "violation", "breach"))


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pytest.importorskip("streamlit")
    pytest.importorskip("geopandas")
    pytest.importorskip("pyarrow")
    from tests.synthetic import write_parquet

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    return tmp_path


def _app(**state):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    for key, value in state.items():
        at.session_state[key] = value
    return at


def test_public_sees_the_sign_in_instead_of_the_staff_map(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHOA_STAFF_PASSCODE", "s3cret")
    at = _app(dhoa_view_mode="inspector").run()
    assert not at.exception
    assert any(i.key == "dhoa_signin_passcode" for i in at.text_input)
    markdown = " ".join(m.value for m in at.markdown if not m.value.lstrip().startswith("<style"))
    assert "dhoa-summary" not in markdown and not any(b.key == "dhoa_portal_signout" for b in at.button)
    assert not any(s.key and s.key.startswith("w_filter_district") for s in at.selectbox)


def test_demo_button_fills_dummy_credentials_without_signing_in(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DHOA_STAFF_PASSCODE", "public-demo-passcode")
    monkeypatch.setenv("DHOA_DEMO_MODE", "1")
    at = _app(dhoa_view_mode="inspector").run()
    assert not at.exception and at.button(key="dhoa_fill_demo_credentials")
    at.button(key="dhoa_fill_demo_credentials").click().run()
    assert at.text_input(key="dhoa_signin_passcode").value == "public-demo-passcode"
    assert at.text_input(key="dhoa_signin_name").value == roles.DEMO_NAME
    assert "dhoa_role" not in at.session_state
    at.button(key="dhoa_signin_submit").click().run()
    assert not at.exception and roles.staff_name(at.session_state) == roles.DEMO_NAME


def test_wrong_passcode_is_rejected_and_the_right_one_opens_the_portal(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DHOA_STAFF_PASSCODE", "s3cret")
    at = _app(dhoa_view_mode="inspector").run()
    at.text_input(key="dhoa_signin_passcode").set_value("nope")
    at.text_input(key="dhoa_signin_name").set_value("Rina")
    at.button[0].click().run()
    assert at.error and "dhoa_role" not in at.session_state
    at.text_input(key="dhoa_signin_passcode").set_value("s3cret")
    at.button[0].click().run()
    assert not at.exception and at.session_state["dhoa_role"] == "inspector"
    assert any(b.key == "dhoa_portal_signout" for b in at.button)
    assert at.session_state["dhoa_portal_tab"] == "map"


def test_staff_sub_tabs_route_and_sign_out_returns_to_the_overview(data_dir: Path) -> None:
    at = _app(dhoa_view_mode="inspector", dhoa_role="inspector", dhoa_staff_name="Rina").run()
    assert not at.exception
    for tab in ("dashboard", "work", "reports"):
        at.session_state["dhoa_portal_tab"] = tab
        at.run()
        assert not at.exception
    at.button(key="dhoa_portal_signout").click().run()
    assert not at.exception
    assert at.session_state["dhoa_view_mode"] == "overview"
    assert not any(b.key == "dhoa_portal_signout" for b in at.button)


def test_public_district_link_never_opens_the_staff_map(data_dir: Path) -> None:
    at = _app().run()
    buttons = [b for b in at.button if b.key and b.key.startswith("dhoa_ov_open_")]
    assert buttons
    buttons[0].click().run()
    assert not at.exception and at.session_state["dhoa_view_mode"] == "community"
