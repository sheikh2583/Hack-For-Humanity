"""P1 design system: palette is colour-blind safe, one source of truth, no stray colours."""

from __future__ import annotations

import itertools
import re
import subprocess
import sys
from pathlib import Path

import app.design_tokens as tk
import app.styles as styles

ROOT = Path(__file__).resolve().parents[1]
BANDS = ("high", "medium", "low")


def test_priority_bands_stay_distinct_for_every_colour_vision_type() -> None:
    for kind in (None, *tk.CVD_KINDS):
        for a, b in itertools.combinations(BANDS, 2):
            assert tk.delta_e(tk.COLORS[a], tk.COLORS[b], kind) >= 30, (a, b, kind)


def test_every_priority_band_has_its_own_shape_and_glyph() -> None:
    assert set(tk.PRIORITY) == {"High", "Medium", "Low"}
    assert len({spec["shape"] for spec in tk.PRIORITY.values()}) == 3
    assert len({spec["glyph"] for spec in tk.PRIORITY.values()}) == 3
    for spec in tk.PRIORITY.values():  # the text colour of each band is readable on the card
        assert tk.contrast_ratio(tk.COLORS[spec["text_color"]], tk.COLORS["card"]) >= 4.5


def test_marker_outline_and_halo_work_on_dark_and_light_tiles() -> None:
    assert tk.contrast_ratio(tk.COLORS["marker_outline"], "#ffffff") >= 7
    assert tk.contrast_ratio(tk.COLORS["marker_halo"], "#000000") >= 7


def test_popup_text_is_readable_on_its_light_surface() -> None:
    assert tk.contrast_ratio(tk.COLORS["popup_text"], "#ffffff") >= 4.5
    assert tk.contrast_ratio(tk.COLORS["popup_text"], tk.COLORS["popup_badge"]) >= 4.5


def test_all_token_groups_reach_the_page_css() -> None:
    root = tk.css_variables()
    for prefix, group in (("space", tk.SPACE), ("radius", tk.RADII), ("shadow", tk.SHADOWS),
                          ("type", tk.TYPE_SCALE), ("lh", tk.LINE_HEIGHT), ("weight", tk.WEIGHTS)):
        for name in group:
            assert f"--dhoa-{prefix}-{name}:" in root


def test_bangla_line_height_is_generous() -> None:
    assert float(tk.LINE_HEIGHT["body"]) >= 1.6 and float(tk.LINE_HEIGHT["heading"]) >= 1.4
    assert float(tk.LINE_HEIGHT["brand"]) >= 1.7


def test_css_only_uses_defined_tokens() -> None:
    css = styles.page_css("x")
    defined = set(re.findall(r"(--dhoa-[a-z0-9-]+):", tk.css_variables()))
    used = set(re.findall(r"var\((--dhoa-[a-z0-9-]+)\)", css))
    assert not used - defined, used - defined


def test_component_token_blocks_are_in_sync() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "sync_component_tokens.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, "run: python tools/sync_component_tokens.py"


def test_components_and_app_code_have_no_stray_hex_colours() -> None:
    allowed = {value.lower() for value in tk.COLORS.values()} | {"#fff", "#ffffff", "#000000"}
    for path in [*ROOT.glob("app/components/*/index.html"), ROOT / "app" / "streamlit_app.py"]:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"/\* dhoa-tokens:start.*?dhoa-tokens:end \*/", "", text, flags=re.S)
        stray = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b", text)} - allowed
        assert not stray, (path.name, stray)


def test_theme_config_matches_tokens() -> None:
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    for key, value in tk.streamlit_theme().items():
        assert f'{key} = "{value}"' in config


def test_priority_chip_pairs_glyph_with_text() -> None:
    chip = styles.priority_chip_html("High", "উচ্চ")
    assert "dhoa-chip--high" in chip and tk.PRIORITY["High"]["glyph"] in chip and "উচ্চ" in chip
    assert "dhoa-chip--" not in styles.priority_chip_html("Unknown", "x")
