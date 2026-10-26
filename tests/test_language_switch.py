"""Language-switch regressions: nothing stored in session state may be translated text."""

from __future__ import annotations

import re
from pathlib import Path

import app.streamlit_app as dashboard
import strings as app_strings  # the module the app imports (same file as app.strings)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")


def test_notices_are_stored_as_codes_and_every_code_exists_in_both_languages() -> None:
    assert not re.search(r'session_state\["community_notice"\]\s*=\s*\(\s*"[a-z]+",\s*T\.', SOURCE)
    for code, name in dashboard._NOTICE_NAMES.items():
        for language in app_strings.LANGUAGES:
            assert isinstance(app_strings.text(name, language), str) and app_strings.text(name, language), (code, language)
    assert app_strings.text("C_GPS_OK", "bn") != app_strings.text("C_GPS_OK", "en")


def test_gps_origin_label_follows_the_active_language(monkeypatch) -> None:
    state = {"community_origin": {"name": "", "gps": True, "lat": 23.8, "lon": 90.4}}
    monkeypatch.setattr(dashboard.st, "session_state", state)
    labels = {}
    for language in ("bn", "en"):
        monkeypatch.setattr(app_strings, "get_language", lambda language=language: language)
        labels[language] = dashboard._community_place(None).name
    assert labels["bn"] == app_strings.text("MY_LOCATION", "bn")
    assert labels["en"] == app_strings.text("MY_LOCATION", "en")
    assert labels["bn"] != labels["en"]


def test_geocoded_origin_keeps_the_typed_name_in_any_language(monkeypatch) -> None:
    state = {"community_origin": {"name": "Mirpur", "gps": False, "lat": 23.8, "lon": 90.4}}
    monkeypatch.setattr(dashboard.st, "session_state", state)
    for language in ("bn", "en"):
        monkeypatch.setattr(app_strings, "get_language", lambda language=language: language)
        assert dashboard._community_place(None).name == "Mirpur"


def test_widget_selections_are_canonical_values_not_labels() -> None:
    # Filter and suggestion widget values stay canonical while labels are localized.
    assert 'key=_wkey("filter_priority")' in SOURCE and '_priority_opts = ["High", "Medium", "Low"]' in SOURCE
    assert 'key=_wkey("community_suggestion")' in SOURCE and "format_func=lambda key: places[key].label" in SOURCE


def test_widget_keys_change_with_language_so_option_text_remounts(monkeypatch) -> None:
    keys = {}
    for language in ("bn", "en"):
        monkeypatch.setattr(app_strings, "get_language", lambda language=language: language)
        keys[language] = dashboard._wkey("filter_priority")
    assert keys["bn"] != keys["en"] and keys["bn"].startswith("w_filter_priority@")


def test_priority_labels_in_any_language_map_to_the_same_filter() -> None:
    import app.kiln_data as kd

    bn = [app_strings.text(n, "bn") for n in ("HIGH", "MEDIUM")]
    en = [app_strings.text(n, "en") for n in ("HIGH", "MEDIUM")]
    expected = kd.make_filter_key(priorities=["High", "Medium"])
    assert kd.make_filter_key(priorities=bn) == expected
    assert kd.make_filter_key(priorities=en) == expected
    assert kd.make_filter_key(priorities=[bn[0], en[1]]) == expected
    assert kd.make_filter_key(priorities=["???"]).priorities == ("High", "Medium", "Low")  # unknown = all, never zero
