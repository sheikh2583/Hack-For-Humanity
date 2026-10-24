"""Page CSS for the Dhoa dashboard (module M7): tokens, fonts, layout, mobile rules.

Input schema: the "page loading" string. Output schema: one ``<style>`` block.
No Streamlit import, so it is unit-testable. Colours come from ``design_tokens``.
"""

from __future__ import annotations

try:  # imported as ``app.styles`` (tests) or ``styles`` (Streamlit)
    from app import design_tokens as tokens
except ImportError:  # pragma: no cover
    import design_tokens as tokens  # type: ignore[no-redef]

_BENGALI_RANGE = (
    "U+0951-0952,U+0964-0965,U+0980-09FE,U+1CD0,U+1CD2,U+1CD5-1CD6,U+1CD8,U+1CE1,"
    "U+1CEA,U+1CED,U+1CF2,U+1CF5-1CF7,U+200C-200D,U+20B9,U+25CC,U+A8F1"
)
_LATIN_RANGE = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,"
    "U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
)


def font_face_css() -> str:
    """Self-hosted Noto Sans Bengali @font-face rules (files in app/static/fonts)."""
    rules = []
    for weight in (400, 500, 600, 700):
        for subset, unicode_range in (("bengali", _BENGALI_RANGE), ("latin", _LATIN_RANGE)):
            rules.append(
                '@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; '
                f"font-weight: {weight};\n  src: url(\"/app/static/fonts/noto-sans-bengali-{subset}-{weight}-normal.woff2\") "
                f'format("woff2");\n  unicode-range: {unicode_range}; }}'
            )
    return "\n".join(rules)


_BODY_CSS = """html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100%; padding: 0.75rem 1.25rem 1.5rem;
}
[data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding-top: 0.75rem !important;
}
/* Hide heading permalinks only; keep map, navigation, and export links usable. */
[data-testid="stHeaderActionElements"],
h1 a, h2 a, h3 a, h4 a,
[role="heading"] a, [role="heading"] button,
h1 [data-testid="stHeaderActionElements"],
h2 [data-testid="stHeaderActionElements"],
h3 [data-testid="stHeaderActionElements"],
h4 [data-testid="stHeaderActionElements"],
[role="heading"] [data-testid="stHeaderActionElements"] { display: none !important; }
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] { margin-top: 0.2rem; }
[data-testid="stMetric"] { min-width: 0; }
/* Replace Streamlit's developer-oriented status icon with a Bengali loading cue. */
[data-testid="stStatusWidget"],
[data-testid^="stStatusWidget"],
[data-testid="stStatusWidgetRunningIcon"] {
    width: auto !important;
    height: auto !important;
    min-width: 0;
    margin-right: 0.4rem !important;
    overflow: visible !important;
}
[data-testid="stStatusWidget"] > *,
[data-testid^="stStatusWidget"] > *,
[data-testid="stStatusWidgetRunningIcon"] svg,
[data-testid="stStatusWidgetRunningIcon"] img { display: none !important; }
[data-testid="stStatusWidget"]::after,
[data-testid^="stStatusWidget"]::after,
[data-testid="stStatusWidgetRunningIcon"]::after {
    content: "__PAGE_LOADING__";
    display: block;
    max-width: 220px;
    color: var(--dhoa-color-text-soft);
    font-family: "Noto Sans Bengali", "Nirmala UI", "Vrinda", sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.35;
    white-space: nowrap;
}
.dhoa-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: clamp(0.5rem, 1.2vw, 1rem);
    width: 100%;
    margin: 0.5rem 0 1rem;
}
.dhoa-metrics.dhoa-summary { grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 0.25rem 0 0.5rem; }
.dhoa-pin { background: none; border: 0; }
.dhoa-pin svg { display: block; filter: drop-shadow(0 0 1px rgba(0,0,0,.7)); }
.dhoa-metric { min-width: 0; padding: 0.35rem 0.65rem; border-left: 2px solid var(--dhoa-color-border); }
.dhoa-metric strong { display: block; font-size: 1.15rem; line-height: 1.3; }
.dhoa-metric span { display: block; color: var(--dhoa-color-text-muted); font-size: 0.82rem; line-height: 1.35; }
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button,
[data-testid="stBaseLinkButton-secondary"],
[data-testid="stBaseLinkButton-primary"],
[data-testid="stSegmentedControl"] button,
[data-testid="stPopover"] button,
[data-testid="stExpander"] summary,
[data-baseweb="select"] > div,
[data-testid="stSlider"] [role="slider"] { min-height: var(--dhoa-tap); }
.dhoa-mobile-map-hint {
    display: none;
    margin: 0.25rem 0 0.65rem;
    color: var(--dhoa-color-text-soft);
    font-size: 0.9rem;
}
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding: 0.65rem 0.75rem 1.5rem;
    }
    [data-testid="stMainBlockContainer"] { padding-top: 1.35rem !important; }
    [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.75rem; }
    [data-testid="stMetricContainer"] { min-width: 0; }
    [data-testid="stStatusWidgetRunningIcon"]::after {
        max-width: 115px;
        font-size: 0.7rem;
        line-height: 1.3;
        white-space: normal;
        text-align: right;
    }
    [data-testid="stIFrame"] iframe {
        width: 100% !important; height: 52vh !important;
        height: clamp(300px, 55dvh, 520px) !important;
        min-height: 280px !important; max-height: 500px !important;
    }
    .st-key-dhoa_map_frame iframe {
        width: 100% !important;
        height: 52vh !important;
        min-height: 300px !important;
        max-height: 500px !important;
    }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    .dhoa-metrics { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem !important; }
    .dhoa-mobile-map-hint { display: block !important; }
}
/* Keep action buttons side by side on phones (only inside keyed rows). */
@media (max-width: 768px) {
    .st-key-dhoa_action_row [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; gap: 0.5rem !important;
    }
    .st-key-dhoa_action_row [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; }
    .st-key-dhoa_action_row a, .st-key-dhoa_action_row button { font-size: 0.85rem; padding-left: 0.4rem; padding-right: 0.4rem; }
}
@media (max-width: 480px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.5rem; padding-right: 0.5rem;
    }
    body, p, label, [data-testid="stCaptionContainer"] { font-size: 14px; }
}
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
    display: block !important;
    box-sizing: border-box !important;
    width: 100% !important;
    padding: 0.38em 0 0.12em !important;
    margin-top: 0.35rem !important;
    line-height: 1.8 !important;
    overflow: visible !important;
    font-family: "Noto Sans Bengali", sans-serif !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
}
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title span {
    font-family: "Noto Sans Bengali", sans-serif !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
    line-height: inherit !important;
    overflow: visible !important;
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
        font-size: 1.9rem !important;
        line-height: 1.8 !important;
        padding-top: 0.38em !important;
        padding-bottom: 0.12em !important;
    }
}


:focus-visible { outline: 3px solid var(--dhoa-color-focus); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
"""


def page_css(page_loading: str) -> str:
    """Return the full ``<style>`` block for the dashboard."""
    body = _BODY_CSS.replace("__PAGE_LOADING__", page_loading)
    return f"<style>\n{tokens.css_variables()}{font_face_css()}\n{body}</style>"
