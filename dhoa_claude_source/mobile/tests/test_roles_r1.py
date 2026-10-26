"""R1: role layer, passcode sign-in and demo switcher (pure logic, no browser)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from app import roles  # noqa: E402


def _secrets(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    monkeypatch.setattr(roles, "_secret", lambda name: values.get(name))


def test_default_role_is_public() -> None:
    state: dict = {}
    assert roles.get_role(state) == "public"
    assert not roles.is_staff(state)
    assert roles.require("public", state)
    assert not roles.require("inspector", state)


def test_unknown_role_value_falls_back_to_public() -> None:
    assert roles.get_role({roles.ROLE_KEY: "root"}) == "public"


def test_sign_in_disabled_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    _secrets(monkeypatch)
    state: dict = {}
    assert not roles.staff_sign_in_enabled()
    assert roles.sign_in("", "x", state) is None
    assert roles.sign_in("anything", "x", state) is None
    assert roles.get_role(state) == "public"


def test_inspector_and_admin_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    _secrets(monkeypatch, staff_passcode_inspector="ins-code", staff_passcode_admin="adm-code")
    state: dict = {}
    assert roles.sign_in("ins-code", "  Rina   Akter ", state) == "inspector"
    assert roles.staff_name(state) == "Rina Akter"
    assert roles.require("inspector", state) and not roles.require("admin", state)
    assert roles.sign_in("adm-code", "Admin", state) == "admin"
    assert roles.require("admin", state) and roles.require("inspector", state)


def test_wrong_passcode_rejected_and_locks_after_five(monkeypatch: pytest.MonkeyPatch) -> None:
    _secrets(monkeypatch, staff_passcode_inspector="ins-code")
    state: dict = {}
    for _ in range(roles.MAX_ATTEMPTS):
        assert roles.sign_in("nope", "", state) is None
    assert roles.attempts_left(state) == 0
    assert roles.sign_in("ins-code", "", state) is None  # locked, even with the right code
    assert roles.get_role(state) == "public"


def test_passcode_is_never_stored_in_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _secrets(monkeypatch, staff_passcode_inspector="ins-code")
    state: dict = {}
    roles.sign_in("ins-code", "Rina", state)
    assert "ins-code" not in repr(state)


def test_sign_out_returns_to_public(monkeypatch: pytest.MonkeyPatch) -> None:
    _secrets(monkeypatch, staff_passcode_inspector="ins-code")
    state: dict = {}
    roles.sign_in("ins-code", "Rina", state)
    roles.sign_out(state)
    assert roles.get_role(state) == "public" and roles.staff_name(state) == ""


def test_demo_switcher_only_with_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _secrets(monkeypatch)
    state: dict = {}
    assert roles.demo_as("admin", state) == "public"
    _secrets(monkeypatch, demo_mode="true")
    assert roles.demo_as("admin", state) == "admin"
    assert roles.demo_as("public", state) == "public"
    assert roles.demo_as("superuser", state) == "public"


def test_empty_passcode_secret_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DHOA_STAFF_PASSCODE_INSPECTOR", raising=False)
    monkeypatch.setenv("DHOA_STAFF_PASSCODE_ADMIN", "   ")
    assert roles._secret("staff_passcode_admin") is None


def test_environment_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHOA_STAFF_PASSCODE_INSPECTOR", "from-env")
    state: dict = {}
    assert roles.sign_in("from-env", "A", state) == "inspector"
