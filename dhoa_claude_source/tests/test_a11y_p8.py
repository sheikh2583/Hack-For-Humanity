"""P8: static accessibility and small-screen checks (the real-browser pass is tools/check_widths.py)."""

from __future__ import annotations

from pathlib import Path

import app.styles as styles

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = (ROOT / "app" / "components" / "priority_candidate_list" / "index.html").read_text(encoding="utf-8")


def test_candidate_list_has_accessible_names_and_keyboard_scroll() -> None:
    assert 'role="region"' in COMPONENT and 'tabindex="0"' in COMPONENT
    assert 'th.scope = "col"' in COMPONENT
    assert "aria-label" in COMPONENT and "aria_select_fmt" in COMPONENT
    assert "document.documentElement.lang" in COMPONENT
    assert 'aria-hidden="true"' in COMPONENT  # duplicate top scrollbar is hidden from AT
    assert "Select ${values" not in COMPONENT  # no hard-coded English row label


def test_candidate_list_keeps_focus_rings_and_reduced_motion() -> None:
    assert ":focus-visible" in COMPONENT and "prefers-reduced-motion" in COMPONENT
    assert "min-height: 44px" in COMPONENT


def test_page_css_has_focus_reduced_motion_and_no_sideways_scroll() -> None:
    css = styles.page_css("x")
    assert ":focus-visible" in css and "prefers-reduced-motion" in css
    assert "overflow-x: hidden" in css and "overflow-wrap: anywhere" in css
    assert "dhoa-skel-bar { animation: none" in css  # shimmer off for reduced motion


def test_footer_links_are_tap_sized() -> None:
    css = styles.page_css("x")
    assert ".dhoa-footer a" in css and "var(--dhoa-tap" in css
