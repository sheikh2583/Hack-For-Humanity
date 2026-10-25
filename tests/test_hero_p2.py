"""P2 hero, navigation and wording (pure: no Streamlit run needed)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import app.hero as hero
import app.strings as T
import app.styles as styles

ROOT = Path(__file__).resolve().parents[1]
BANNED = ("লঙ্ঘন", "বিপজ্জনক", "violation", "hazardous", "illegal", "non-compliant", "advisory")
NEW_NAMES = ("NAV_OVERVIEW", "NAV_MAP", "NAV_NEAR_ME", "NAV_ABOUT", "HERO_MISSION", "HERO_SUB",
             "HERO_CTA_MAP", "HERO_CTA_NEAR_ME", "HERO_METRIC_DISTRICTS", "ABOUT_TITLE", "ABOUT_BODY")


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "priority_band": ["High", "High", "Medium", "Low", "Low"],
        "district": ["Dhaka", "Dhaka", "Gazipur", " ", None],
    })


def test_hero_counts_match_pandas() -> None:
    frame = _frame()
    counts = hero.hero_counts(frame)
    assert counts == {"total": 5, "high": int((frame.priority_band == "High").sum()), "districts": 2}


def test_hero_counts_survive_missing_columns_and_empty_frames() -> None:
    assert hero.hero_counts(pd.DataFrame()) == {"total": 0, "high": 0, "districts": 0}
    assert hero.hero_counts(pd.DataFrame({"x": [1]})) == {"total": 1, "high": 0, "districts": 0}


def test_hero_html_escapes_text_and_keeps_four_tiles() -> None:
    markup = hero.hero_html("<b>x</b> & y", "sub", [("1", "a"), ("2", "<i>b</i>"), ("3", "c"), ("4", "d")])
    assert "<b>x</b>" not in markup and "&lt;b&gt;x&lt;/b&gt; &amp; y" in markup
    assert markup.count("class='dhoa-metric'") == 4 and "<i>" not in markup


def test_navigation_order_and_default() -> None:
    assert hero.VIEW_MODES == ("overview", "inspector", "community", "about")
    assert hero.DEFAULT_VIEW == "overview"


def test_new_strings_exist_in_both_languages_and_are_neutral() -> None:
    for name in NEW_NAMES:
        for language in T.LANGUAGES:
            text = T.text(name, language)
            assert text.strip() and not any(word in text.casefold() for word in BANNED), (name, language)
    assert T.text("NAV_MAP", "bn") != T.text("NAV_MAP", "en")


def test_how_to_use_has_no_duplicate_emoji_icon() -> None:
    for language in T.LANGUAGES:
        assert "❔" not in T.text("HOW_TO_USE", language)  # the popover already draws an icon


def test_app_wiring_has_nav_keys_and_no_header_metric_row() -> None:
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    for needle in ('key="dhoa_hero_map"', 'key="dhoa_hero_near"', "def render_overview", "def render_about",
                   'if mode == "overview"', "label_visibility=\"collapsed\""):
        assert needle in source, needle
    assert "METRIC_LABELS[\"rule_violations\"]" not in source


def test_hero_css_wraps_long_text_and_scales_on_phones() -> None:
    css = styles.page_css("x")
    assert ".dhoa-hero-title" in css and "overflow-wrap: anywhere" in css
    assert "--dhoa-type-h2" in css.split("@media (max-width: 768px)")[1]
