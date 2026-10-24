"""Design tokens for the Dhoa dashboard (module M7): the one place for colours,
spacing, type scale and tap-target size.

Input schema: none (constants). Output schema: ``COLORS`` / ``SPACE`` /
``TYPE_SCALE`` dicts, ``MIN_TAP_PX``, ``contrast_ratio`` (WCAG 2.x) and
``css_variables`` (a ``:root{...}`` block of ``--dhoa-*`` custom properties).

Contrast rules checked by tests: text >= 4.5:1 on the page and card
backgrounds, meaningful non-text marks >= 3:1, white text on the primary
button >= 4.5:1. ``*_text`` colours are lighter variants of the marker colours
for use as text, because the marker reds/blues are below 4.5:1 on the card.
"""

from __future__ import annotations

COLORS: dict[str, str] = {
    "background": "#0e1117",
    "card": "#1e2329",
    "text": "#fafafa",
    "text_muted": "#aab4c0",
    "text_soft": "#cbd5e1",
    "border": "#475569",
    "primary": "#c53030",       # white-on-primary 5.5:1 (was #e53e3e, 4.1:1)
    "on_primary": "#ffffff",
    "high": "#e53e3e",
    "medium": "#dd6b20",
    "low": "#38a169",
    "new": "#3182ce",
    "advisory": "#d69e2e",
    "high_text": "#f56565",
    "new_text": "#63b3ed",
    "focus": "#d69e2e",
}
SPACE: dict[str, str] = {"xs": "0.25rem", "sm": "0.5rem", "md": "0.75rem", "lg": "1rem", "xl": "1.5rem"}
TYPE_SCALE: dict[str, str] = {
    "caption": "0.82rem", "body": "1rem", "metric": "1.15rem",
    "h3": "1.15rem", "h2": "1.35rem", "title": "1.9rem",
}
MIN_TAP_PX = 44
FONT_STACK = '"Noto Sans Bengali", "Nirmala UI", "Vrinda", system-ui, sans-serif'


def _linear(channel: int) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    """Relative luminance of ``#rrggbb`` (WCAG 2.x)."""
    text = hex_colour.lstrip("#")
    red, green, blue = (int(text[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two ``#rrggbb`` colours (1.0 to 21.0)."""
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def css_variables() -> str:
    """Return a ``:root`` block exposing every token as a ``--dhoa-*`` property."""
    lines = [f"  --dhoa-color-{name.replace('_', '-')}: {value};" for name, value in COLORS.items()]
    lines += [f"  --dhoa-space-{name}: {value};" for name, value in SPACE.items()]
    lines += [f"  --dhoa-type-{name}: {value};" for name, value in TYPE_SCALE.items()]
    lines.append(f"  --dhoa-tap: {MIN_TAP_PX}px;")
    lines.append(f"  --dhoa-font: {FONT_STACK};")
    return ":root {\n" + "\n".join(lines) + "\n}\n"
