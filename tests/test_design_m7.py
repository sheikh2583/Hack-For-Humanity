"""M7/P1 design tokens, contrast, tap targets and mobile CSS (no Streamlit needed)."""

from __future__ import annotations

import re
from pathlib import Path

import app.design_tokens as tk
import app.styles as styles

ROOT = Path(__file__).resolve().parents[1]
CSS = styles.page_css("লোড হচ্ছে")


def test_contrast_ratio_matches_wcag_reference_values() -> None:
    assert round(tk.contrast_ratio("#000000", "#ffffff"), 1) == 21.0
    assert tk.contrast_ratio("#ffffff", "#ffffff") == 1.0


def test_text_colours_meet_aa_on_page_and_card() -> None:
    for name in ("text", "text_muted", "text_soft", "high_text", "new_text", "accent_text", "medium", "low", "unclassified"):
        for background in ("background", "card"):
            assert tk.contrast_ratio(tk.COLORS[name], tk.COLORS[background]) >= 4.5, (name, background)


def test_primary_button_and_marker_contrast() -> None:
    assert tk.contrast_ratio(tk.COLORS["on_primary"], tk.COLORS["primary"]) >= 4.5
    assert tk.contrast_ratio(tk.COLORS["on_primary"], tk.COLORS["primary_hover"]) >= 4.5
    for name in ("high", "medium", "low", "new", "primary", "border_strong"):
        assert tk.contrast_ratio(tk.COLORS[name], tk.COLORS["background"]) >= 3.0, name
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert f'primaryColor = "{tk.COLORS["primary"]}"' in config


def test_every_token_is_exposed_as_css_variable() -> None:
    root = tk.css_variables()
    for name in tk.COLORS:
        assert f"--dhoa-color-{name.replace('_', '-')}:" in root
    assert "--dhoa-tap: 44px" in root and tk.MIN_TAP_PX >= 44


def test_tap_target_rule_covers_buttons_links_controls() -> None:
    block = re.search(r"([^{}]*)\{ min-height: var\(--dhoa-tap\); \}", CSS)
    assert block is not None
    for selector in ("stButton", "stDownloadButton", "stFormSubmitButton", "stBaseLinkButton", "stSegmentedControl", "stExpander"):
        assert selector in block.group(1)


def test_mobile_keeps_action_row_side_by_side_but_stacks_other_columns() -> None:
    assert '[data-testid="stHorizontalBlock"] { flex-direction: column;' in CSS  # general stacking stays
    assert ".st-key-dhoa_action_row" in CSS and "flex-direction: row !important" in CSS
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    assert 'key="dhoa_action_row"' in source


def test_map_height_is_sensible_on_phones_and_fonts_are_self_hosted() -> None:
    assert "clamp(300px, 55dvh, 520px)" in CSS
    assert CSS.count("@font-face") == 8 and "fonts.googleapis" not in CSS and "@import" not in CSS
    assert "prefers-reduced-motion" in CSS and ":focus-visible" in CSS


def test_no_stray_hex_colours_outside_tokens_in_page_css() -> None:
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", styles._BODY_CSS)  # P1: tokens only, via var(--dhoa-*)
