"""Page CSS for the Dhoa dashboard (modules M7, P1): tokens, fonts, components, layout, mobile rules.

Input schema: the "page loading" string. Output schema: one ``<style>`` block.
No Streamlit import, so it is unit-testable. Every colour, size, radius and shadow
comes from ``design_tokens`` through ``var(--dhoa-*)``: the CSS below contains no hex literals.
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


_BODY_CSS = """/* ---- base: surface, type, rhythm ---------------------------------------- */
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
.stApp, .stApp button, .stApp input, .stApp textarea, .stApp select,
[data-baseweb="select"], [data-baseweb="popover"], [data-testid="stMarkdownContainer"] {
    font-family: var(--dhoa-font);
}
.stApp { background: var(--dhoa-color-background); color: var(--dhoa-color-text); }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, label, .dhoa-metric span {
    line-height: var(--dhoa-lh-body);
}
h1, h2, h3, h4 { font-family: var(--dhoa-font); font-weight: var(--dhoa-weight-bold); line-height: var(--dhoa-lh-heading); letter-spacing: 0; }
h2 { font-size: var(--dhoa-type-h2); }
h3 { font-size: var(--dhoa-type-h3); }
a { color: var(--dhoa-color-accent-text); }
hr { border-color: var(--dhoa-color-border) !important; }
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100%; padding: 0.75rem 1.25rem 1.5rem;
}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="stMain"] { flex: 1 1 100% !important; width: 100% !important; min-width: 0; }
[data-testid="stMainBlockContainer"] {
    box-sizing: border-box; width: 100% !important; max-width: none !important;
    /* Streamlit's fixed top bar is 60px tall and paints over the first row (it hid the
       language switch); keep the page content clear of it. */
    padding: 4.25rem clamp(1rem, 3vw, 3rem) 1.5rem !important;
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
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color: var(--dhoa-color-text-muted); font-size: var(--dhoa-type-caption); line-height: var(--dhoa-lh-body);
}
[data-testid="stMetric"] { min-width: 0; }
/* Replace Streamlit's developer-oriented status icon with a loading cue. */
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
    font-family: var(--dhoa-font);
    font-size: var(--dhoa-type-caption);
    font-weight: var(--dhoa-weight-medium);
    line-height: var(--dhoa-lh-body);
    white-space: nowrap;
}

/* ---- metric tiles ---------------------------------------------------------- */
.dhoa-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: clamp(0.5rem, 1.2vw, 1rem);
    width: 100%;
    margin: 0.5rem 0 1rem;
}
.dhoa-metrics.dhoa-summary { grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 0.25rem 0 0.5rem; }
.dhoa-metric {
    min-width: 0;
    padding: var(--dhoa-space-md) var(--dhoa-space-lg);
    background: var(--dhoa-color-card);
    border: 1px solid var(--dhoa-color-border);
    border-left: 4px solid var(--dhoa-color-border-strong);
    border-radius: var(--dhoa-radius-md);
    box-shadow: var(--dhoa-shadow-card);
}
.dhoa-metric strong {
    display: block; font-size: var(--dhoa-type-h2); font-weight: var(--dhoa-weight-bold);
    line-height: var(--dhoa-lh-heading); overflow-wrap: anywhere;
}
.dhoa-metric span { display: block; color: var(--dhoa-color-text-muted); font-size: var(--dhoa-type-caption); }


/* ---- landing hero (P2) ------------------------------------------------------ */
.dhoa-hero { margin: var(--dhoa-space-lg) 0 var(--dhoa-space-md); }
.dhoa-hero-title {
    max-width: 34ch; font-size: var(--dhoa-type-display); font-weight: var(--dhoa-weight-bold);
    line-height: var(--dhoa-lh-heading); overflow-wrap: anywhere;
}
.dhoa-hero-sub {
    max-width: 62ch; margin: var(--dhoa-space-sm) 0 var(--dhoa-space-lg);
    color: var(--dhoa-color-text-soft); font-size: var(--dhoa-type-metric); line-height: var(--dhoa-lh-body);
}
.dhoa-hero-metrics { margin-bottom: var(--dhoa-space-lg); }
/* ---- overview charts (P3): HTML bars with direct value labels ------------------- */
.dhoa-section-title { font-size: var(--dhoa-type-h3); font-weight: var(--dhoa-weight-bold); margin: var(--dhoa-space-xl) 0 var(--dhoa-space-xs); }
.dhoa-bar-legend { display: flex; flex-wrap: wrap; gap: var(--dhoa-space-md); color: var(--dhoa-color-text-soft); font-size: var(--dhoa-type-caption); margin: var(--dhoa-space-xs) 0 var(--dhoa-space-sm); }
.dhoa-key { display: inline-block; width: 1.1em; margin-inline-end: var(--dhoa-space-xs); font-style: normal; text-align: center; }
.dhoa-key-total { height: 0.7em; background: var(--dhoa-color-primary); border-radius: var(--dhoa-radius-sm); }
.dhoa-key-high { color: var(--dhoa-color-high-text); }
.dhoa-bar-block { display: grid; gap: var(--dhoa-space-xs); padding: var(--dhoa-space-sm) 0; min-height: var(--dhoa-tap); align-content: center; }
.dhoa-bar-line { display: flex; align-items: center; gap: var(--dhoa-space-sm); min-height: 1.25rem; }
.dhoa-bar { display: block; min-width: 2px; height: 0.9rem; border-radius: var(--dhoa-radius-sm); }
.dhoa-bar-total { background: var(--dhoa-color-primary); }
.dhoa-bar-high { background: var(--dhoa-color-high); }
.dhoa-bar-value { font-weight: var(--dhoa-weight-semibold); white-space: nowrap; }
.dhoa-bar-value-high { color: var(--dhoa-color-high-text); }
.dhoa-split-bar { display: flex; height: 1.1rem; overflow: hidden; border-radius: var(--dhoa-radius-sm); border: 1px solid var(--dhoa-color-border-strong); }
.dhoa-split-seg { display: block; height: 100%; }
.dhoa-split-zigzag { background: var(--dhoa-color-primary); }
.dhoa-split-fcbk { background: repeating-linear-gradient(45deg, var(--dhoa-color-accent-text) 0 6px, var(--dhoa-color-raised) 6px 12px); }
.dhoa-split-other { background: var(--dhoa-color-unclassified); }
.dhoa-split-legend { list-style: none; display: flex; flex-wrap: wrap; gap: var(--dhoa-space-sm) var(--dhoa-space-lg); padding: 0; margin: var(--dhoa-space-sm) 0 0; }
.dhoa-split-key { display: inline-block; width: 1.1em; height: 0.9em; margin-inline-end: var(--dhoa-space-xs); vertical-align: middle; border-radius: var(--dhoa-radius-sm); }
.dhoa-split-share { color: var(--dhoa-color-text-muted); }
.dhoa-legend { display: flex; flex-wrap: wrap; align-items: center; gap: var(--dhoa-space-xs) var(--dhoa-space-lg); font-size: var(--dhoa-type-caption); color: var(--dhoa-color-text-soft); margin-bottom: var(--dhoa-space-xs); }
.dhoa-legend ul { list-style: none; display: flex; flex-wrap: wrap; gap: var(--dhoa-space-md); padding: 0; margin: 0; }
.dhoa-legend-key { font-style: normal; margin-inline-end: var(--dhoa-space-xs); }
.dhoa-legend-high { color: var(--dhoa-color-high-text); }
.dhoa-legend-medium { color: var(--dhoa-color-medium); text-shadow: 0 0 1px var(--dhoa-color-text); }
.dhoa-legend-low { color: var(--dhoa-color-low); }
.dhoa-dist-grid { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr)); gap: var(--dhoa-space-sm); padding: 0; margin: 0 0 var(--dhoa-space-md); }
.dhoa-dist { display: grid; grid-template-columns: auto 1fr; column-gap: var(--dhoa-space-sm); padding: var(--dhoa-space-sm); border: 1px solid var(--dhoa-color-border); border-radius: var(--dhoa-radius-md); background: var(--dhoa-color-card); }
.dhoa-dist-icon { grid-row: 1 / span 3; font-size: 1.4rem; }
.dhoa-dist-name, .dhoa-dist-state { color: var(--dhoa-color-text-soft); font-size: var(--dhoa-type-caption); }
.dhoa-dist-inside { border-color: var(--dhoa-color-high); }
.dhoa-dist-inside .dhoa-dot { color: var(--dhoa-color-high-text); }
.dhoa-dot { font-style: normal; }
@media (min-width: 769px) { .st-key-dhoa_map_sticky { position: sticky; top: var(--dhoa-space-md); align-self: flex-start; } }
.dhoa-about { max-width: 70ch; }
.dhoa-about p { color: var(--dhoa-color-text-soft); font-size: var(--dhoa-type-metric); }

/* ---- cards and chips ------------------------------------------------------- */
.dhoa-card, [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > .dhoa-card-marker) {
    background: var(--dhoa-color-card);
    border: 1px solid var(--dhoa-color-border);
    border-radius: var(--dhoa-radius-lg);
    box-shadow: var(--dhoa-shadow-card);
    padding: var(--dhoa-space-lg);
}
.dhoa-chip {
    display: inline-flex; align-items: center; gap: var(--dhoa-space-xs);
    padding: var(--dhoa-space-xxs) var(--dhoa-space-md);
    border: 1px solid var(--dhoa-color-border-strong); border-radius: var(--dhoa-radius-pill);
    background: var(--dhoa-color-raised); color: var(--dhoa-color-text);
    font-size: var(--dhoa-type-caption); font-weight: var(--dhoa-weight-semibold); line-height: var(--dhoa-lh-body);
}
.dhoa-chip--high { border-color: var(--dhoa-color-high); color: var(--dhoa-color-high-text); }
.dhoa-chip--medium { border-color: var(--dhoa-color-medium); color: var(--dhoa-color-medium); }
.dhoa-chip--low { border-color: var(--dhoa-color-low); color: var(--dhoa-color-low); }
.dhoa-chip--new { border-color: var(--dhoa-color-new); color: var(--dhoa-color-new-text); }
.dhoa-pin { background: none; border: 0; }
.dhoa-pin svg { display: block; }

/* ---- buttons, inputs, navigation ------------------------------------------ */
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button,
[data-testid^="stBaseLinkButton"],
[data-testid="stSegmentedControl"] button,
[data-testid="stPopover"] button,
[data-testid="stExpander"] summary,
[data-baseweb="select"] > div,
.st-key-dhoa_lang_toggle [role="radiogroup"] label,
[data-testid="stSlider"] [role="slider"] { min-height: var(--dhoa-tap); }
[data-testid^="stBaseButton-secondary"], [data-testid^="stBaseLinkButton-secondary"] {
    background: var(--dhoa-color-raised); color: var(--dhoa-color-text);
    border: 1px solid var(--dhoa-color-border-strong); border-radius: var(--dhoa-radius-md);
    font-weight: var(--dhoa-weight-semibold); line-height: var(--dhoa-lh-body);
    transition: background-color 0.12s ease, border-color 0.12s ease;
}
[data-testid^="stBaseButton-secondary"]:hover, [data-testid^="stBaseLinkButton-secondary"]:hover {
    background: var(--dhoa-color-card); border-color: var(--dhoa-color-accent-text); color: var(--dhoa-color-text);
}
[data-testid^="stBaseButton-primary"], [data-testid^="stBaseLinkButton-primary"] {
    background: var(--dhoa-color-primary); color: var(--dhoa-color-on-primary);
    border: 1px solid var(--dhoa-color-primary); border-radius: var(--dhoa-radius-md);
    font-weight: var(--dhoa-weight-bold); line-height: var(--dhoa-lh-body);
    transition: background-color 0.12s ease;
}
[data-testid^="stBaseButton-primary"]:hover, [data-testid^="stBaseLinkButton-primary"]:hover {
    background: var(--dhoa-color-primary-hover); border-color: var(--dhoa-color-primary-hover); color: var(--dhoa-color-on-primary);
}
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="textarea"] {
    background: var(--dhoa-color-raised) !important;
    border-color: var(--dhoa-color-border-strong) !important;
    border-radius: var(--dhoa-radius-md) !important;
}
[data-testid="stSidebar"] { background: var(--dhoa-color-card); border-right: 1px solid var(--dhoa-color-border); }
[data-testid="stSegmentedControl"] button { border-radius: var(--dhoa-radius-md); font-weight: var(--dhoa-weight-semibold); }
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] {
    background: var(--dhoa-color-primary); color: var(--dhoa-color-on-primary); border-color: var(--dhoa-color-primary);
}
[data-testid="stExpander"], [data-testid="stPopover"] button {
    border-color: var(--dhoa-color-border); border-radius: var(--dhoa-radius-md);
}
[data-testid="stAlert"] { border-radius: var(--dhoa-radius-md); }

/* ---- language toggle: a two-option pill, same family as the buttons -------- */
.st-key-dhoa_lang_toggle [role="radiogroup"] {
    display: inline-flex; gap: 0; padding: 2px;
    background: var(--dhoa-color-raised); border: 1px solid var(--dhoa-color-border-strong);
    border-radius: var(--dhoa-radius-pill);
}
.st-key-dhoa_lang_toggle [role="radiogroup"] label {
    display: flex; align-items: center; justify-content: center; margin: 0;
    padding: 0 var(--dhoa-space-lg); min-width: var(--dhoa-tap);
    border-radius: var(--dhoa-radius-pill); cursor: pointer;
    font-weight: var(--dhoa-weight-semibold); color: var(--dhoa-color-text-soft);
}
.st-key-dhoa_lang_toggle [role="radiogroup"] label > div:first-child:not([data-testid]) { display: none; }
.st-key-dhoa_lang_toggle [role="radiogroup"] label:has(input:checked) {
    background: var(--dhoa-color-primary); color: var(--dhoa-color-on-primary);
}
.st-key-dhoa_lang_toggle [role="radiogroup"] label p { margin: 0; line-height: var(--dhoa-lh-tight); }

.dhoa-mobile-map-hint {
    display: none;
    margin: 0.25rem 0 0.65rem;
    color: var(--dhoa-color-text-soft);
    font-size: var(--dhoa-type-caption);
}
.dhoa-footer { color: var(--dhoa-color-text-muted); font-size: var(--dhoa-type-caption); padding: var(--dhoa-space-lg) 0; }

/* ---- phones and tablets ---------------------------------------------------- */
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding: 0.65rem 0.75rem 1.5rem;
    }
    [data-testid="stMainBlockContainer"] { padding-top: 4.25rem !important; }
    [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.75rem; }
    [data-testid="stMetricContainer"] { min-width: 0; }
    [data-testid="stStatusWidgetRunningIcon"]::after {
        max-width: 115px;
        font-size: 0.75rem;
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
    h2 { font-size: var(--dhoa-type-h3) !important; }
    h3 { font-size: var(--dhoa-type-metric) !important; }
    [data-testid="stMetricValue"] { font-size: var(--dhoa-type-h3); }
    .dhoa-metrics { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem !important; }
    .dhoa-metric { padding: var(--dhoa-space-sm) var(--dhoa-space-md); }
    .dhoa-metric strong { font-size: var(--dhoa-type-h3); }
    .dhoa-mobile-map-hint { display: block !important; }
    .dhoa-hero-title { font-size: var(--dhoa-type-h2); }
    .dhoa-hero-sub { font-size: var(--dhoa-type-body); }
}
/* Keep action buttons side by side on phones (only inside keyed rows). */
@media (max-width: 768px) {
    .st-key-dhoa_action_row [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; gap: 0.5rem !important;
    }
    .st-key-dhoa_action_row [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; }
    .st-key-dhoa_action_row a, .st-key-dhoa_action_row button { font-size: 0.85rem; padding-left: 0.4rem; padding-right: 0.4rem; }
    /* The language toggle stays on one line next to the title. */
    .st-key-dhoa_lang_toggle [role="radiogroup"] { display: flex; width: 100%; }
    .st-key-dhoa_lang_toggle [role="radiogroup"] label { flex: 1 1 0; padding: 0 var(--dhoa-space-sm); }
}
@media (max-width: 480px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.5rem; padding-right: 0.5rem;
    }
    body, p, label, [data-testid="stCaptionContainer"] { font-size: 0.9rem; }
}

/* ---- brand title (Bangla conjuncts need the tall line box) ---------------- */
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
    display: block !important;
    box-sizing: border-box !important;
    width: 100% !important;
    padding: 0.38em 0 0.12em !important;
    margin-top: 0.35rem !important;
    font-size: var(--dhoa-type-title);
    line-height: var(--dhoa-lh-brand) !important;
    overflow: visible !important;
    font-family: var(--dhoa-font) !important;
    color: var(--dhoa-color-text);
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
}
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title span {
    font-family: var(--dhoa-font) !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
    line-height: inherit !important;
    overflow: visible !important;
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
        font-size: var(--dhoa-type-title) !important;
        line-height: var(--dhoa-lh-brand) !important;
        padding-top: 0.38em !important;
        padding-bottom: 0.12em !important;
    }
}

/* ---- P7: panels, states, skeleton -------------------------------------------- */
.dhoa-panel { background: var(--dhoa-color-card); border: 1px solid var(--dhoa-color-border); border-radius: var(--dhoa-radius-md, 12px); padding: var(--dhoa-space-md); margin: var(--dhoa-space-md) 0; animation: dhoa-fade 180ms ease-out; }
.dhoa-panel-title { font-weight: var(--dhoa-weight-bold, 700); margin-bottom: var(--dhoa-space-sm); }
.dhoa-steps { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--dhoa-space-sm); grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); }
.dhoa-step { display: flex; gap: var(--dhoa-space-sm); align-items: flex-start; min-width: 0; }
.dhoa-step-no { flex: none; width: 2rem; height: 2rem; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; background: var(--dhoa-color-primary); color: var(--dhoa-color-on-primary); font-weight: 700; }
.dhoa-step strong, .dhoa-step span { display: block; overflow-wrap: anywhere; }
.dhoa-step span { color: var(--dhoa-color-text-soft); }
.dhoa-facts { margin: 0; display: grid; gap: var(--dhoa-space-sm); }
.dhoa-facts dt { color: var(--dhoa-color-text-muted); font-size: var(--dhoa-type-caption); }
.dhoa-facts dd { margin: 0; overflow-wrap: anywhere; }
.dhoa-state { display: flex; gap: var(--dhoa-space-sm); align-items: flex-start; padding: var(--dhoa-space-md); margin: var(--dhoa-space-md) 0; border-radius: var(--dhoa-radius-md, 12px); background: var(--dhoa-color-raised); border: 1px solid var(--dhoa-color-border-strong); animation: dhoa-fade 180ms ease-out; }
.dhoa-state strong, .dhoa-state span { display: block; overflow-wrap: anywhere; }
.dhoa-state span:not(.dhoa-state-glyph) { color: var(--dhoa-color-text-soft); }
.dhoa-state-glyph { flex: none; width: 1.75rem; height: 1.75rem; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; border: 2px solid var(--dhoa-color-accent-text); color: var(--dhoa-color-accent-text); }
.dhoa-state--error .dhoa-state-glyph { border-color: var(--dhoa-color-high-text); color: var(--dhoa-color-high-text); }
.dhoa-skeleton { margin: var(--dhoa-space-lg) 0; }
.dhoa-skel-tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--dhoa-space-sm); margin-bottom: var(--dhoa-space-md); }
.dhoa-skel-tile, .dhoa-skel-bar { background: linear-gradient(90deg, var(--dhoa-color-card) 25%, var(--dhoa-color-raised) 50%, var(--dhoa-color-card) 75%); background-size: 200% 100%; animation: dhoa-shimmer 1.4s linear infinite; border-radius: var(--dhoa-radius-md, 12px); }
.dhoa-skel-tile { height: 4.5rem; }
.dhoa-skel-bar { height: 1.25rem; margin-bottom: var(--dhoa-space-sm); }
.dhoa-skel-text { color: var(--dhoa-color-text-muted); font-size: var(--dhoa-type-caption); }
@keyframes dhoa-fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
@keyframes dhoa-shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* ---- P8: small-screen safety and link targets --------------------------------- */
.dhoa-footer a { display: inline-block; min-height: var(--dhoa-tap, 44px); line-height: var(--dhoa-tap, 44px); padding: 0 var(--dhoa-space-xs, 4px); color: var(--dhoa-color-accent-text); }
.dhoa-metric strong, .dhoa-hero-title, .dhoa-about p { overflow-wrap: anywhere; }
[data-testid="stMarkdownContainer"] table { display: block; max-width: 100%; overflow-x: auto; }
img, svg, iframe { max-width: 100%; }
@media (max-width: 480px) { .dhoa-skel-tiles { grid-template-columns: 1fr; } }

/* ---- focus and motion ------------------------------------------------------ */
:focus-visible { outline: 3px solid var(--dhoa-color-focus); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
    .dhoa-skel-tile, .dhoa-skel-bar { animation: none !important; }
    *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
/* ---- map-first layout (M11): the map is on screen without scrolling ------------------ */
[data-testid="stMainBlockContainer"] .st-key-dhoa_header_row h1.dhoa-brand-title {
    font-size: 1.8rem !important; padding: 0.1em 0 !important; margin: 0 !important; line-height: 1.5 !important;
}
.st-key-dhoa_header_row [data-testid="stHorizontalBlock"] { align-items: center; margin-bottom: 0.25rem; }
.st-key-dhoa_header_row h1.dhoa-brand-title { white-space: nowrap; }
/* Inspector Portal second-level navigation: visibly smaller and quieter than the top bar */
.st-key-dhoa_portal_bar {
    background: var(--dhoa-color-card); border: 1px solid var(--dhoa-color-border);
    border-radius: var(--dhoa-radius-md, 10px); padding: 0.3rem 0.6rem; margin: 0 0 0.6rem;
}
.st-key-dhoa_portal_bar [data-testid="stHorizontalBlock"] { align-items: center; gap: 0.5rem; }
.st-key-dhoa_portal_bar [data-testid="stSegmentedControl"] { overflow-x: auto; }
.st-key-dhoa_portal_bar button { font-size: 0.85rem !important; min-height: 2rem !important; }
.st-key-dhoa_portal_bar [data-testid="stCaptionContainer"] { margin-top: 0 !important; text-align: right; }
/* The sign-in card sits in normal document flow, centered by flexbox, instead of being
   transform-positioned against the preview's containing block: Streamlit can wrap a keyed
   container in an extra layout element, which previously left `position: absolute` anchored
   to the wrong ancestor. Only the decorative, non-interactive preview is taken out of flow. */
.st-key-dhoa_signin_stage {
    position: relative; isolation: isolate; min-height: min(78vh, 850px); margin-top: 0.75rem;
    display: flex; align-items: center; justify-content: center; padding: 1rem 0;
}
.st-key-dhoa_signin_preview {
    position: absolute; inset: 0; z-index: 0;
    max-height: min(78vh, 850px); overflow: hidden; filter: blur(5px); opacity: 0.48;
    pointer-events: none; user-select: none;
}
.st-key-dhoa_signin_panel {
    position: relative; z-index: 10; margin: 0 auto;
    width: min(27rem, calc(100% - 2rem)); max-height: 100%; overflow-y: auto;
    box-sizing: border-box; padding: 1.25rem;
    border: 1px solid var(--dhoa-color-border-strong); border-radius: var(--dhoa-radius-md, 12px);
    background: var(--dhoa-color-card); box-shadow: var(--dhoa-shadow-card);
}
.st-key-dhoa_signin_panel .dhoa-section-title { margin-top: 0; }
@media (max-width: 768px) {
    .st-key-dhoa_signin_stage { min-height: 76vh; }
    .st-key-dhoa_signin_preview { max-height: 76vh; }
    .st-key-dhoa_signin_panel { padding: 1rem; }
}
.st-key-dhoa_community_list {
    max-height: clamp(400px, 60dvh, 680px);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 4px;
}
@media (max-width: 768px) {
    .st-key-dhoa_portal_bar [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: wrap !important; gap: 0.4rem !important;
    }
    .st-key-dhoa_portal_bar [data-testid="stColumn"] { min-width: 0 !important; }
    .st-key-dhoa_portal_bar [data-testid="stColumn"]:nth-child(1) { flex: 1 1 100% !important; }
    /* Keep the report notice and account controls readable at phone widths. */
    .st-key-dhoa_portal_bar [data-testid="stColumn"]:nth-child(2) { flex: 1 1 42% !important; min-width: 0 !important; }
    .st-key-dhoa_portal_bar [data-testid="stColumn"]:nth-child(3) { flex: 1 1 38% !important; min-width: 0 !important; }
    .st-key-dhoa_portal_bar [data-testid="stColumn"]:nth-child(4) { flex: 0 0 auto !important; min-width: 7.5rem !important; }
    .st-key-dhoa_portal_bar [data-testid="stCaptionContainer"] { text-align: left; overflow-wrap: anywhere; }
    .st-key-dhoa_portal_bar [data-testid="stColumn"]:nth-child(4) button { white-space: nowrap; }
    .st-key-dhoa_portal_bar [data-testid="stSegmentedControl"],
    .st-key-dhoa_header_row [data-testid="stSegmentedControl"] { max-width: 100%; overflow-x: auto !important; }
    /* Keep all navigation options in one compact, horizontally scrollable row. */
    .st-key-dhoa_portal_bar [data-testid="stButtonGroup"] > div,
    .st-key-dhoa_header_row [data-testid="stButtonGroup"] > div { flex-wrap: nowrap !important; overflow-x: auto !important; }
}
/* slim one-line summary strip: value and label side by side */
.dhoa-metrics.dhoa-summary { gap: 0.4rem; margin: 0 0 0.25rem; }
.dhoa-summary .dhoa-metric {
    display: flex; align-items: baseline; gap: 0.45rem; flex-wrap: wrap;
    padding: 0.3rem 0.6rem; box-shadow: none;
}
.dhoa-summary .dhoa-metric strong { display: inline; font-size: var(--dhoa-type-body); }
.dhoa-summary .dhoa-metric span { display: inline; }
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] { margin-top: -0.35rem; }
.st-key-dhoa_map_toolbar [data-testid="stHorizontalBlock"] { gap: 0.5rem; }
.st-key-dhoa_map_toolbar [data-testid="stElementContainer"] { margin: 0; }
.st-key-dhoa_map_toolbar .dhoa-legend { margin: 0; }
@media (min-width: 769px) {
    /* map height follows the window: header + summary + toolbar stay above it, no page scroll to see it */
    .st-key-dhoa_map_frame iframe {
        height: clamp(420px, calc(100dvh - 300px), 860px) !important;
        min-height: 420px !important;
    }
}
/* Inspector filters are part of the full-width page, not a separate sidebar rail. */
.st-key-dhoa_filter_panel { margin: 0 0 0.75rem; }
.st-key-dhoa_filter_panel h4 { margin: 0 0 0.25rem; }
.st-key-dhoa_filter_panel [data-testid="stForm"] { padding: 0; }
.st-key-dhoa_filter_panel [data-testid="stWidgetLabel"] { margin-bottom: 0.1rem; min-height: 0; }
/* header, toolbar and filter rows keep their columns on phones (wrap instead of one tall stack) */
@media (max-width: 768px) {
    .st-key-dhoa_header_row [data-testid="stHorizontalBlock"],
    .st-key-dhoa_map_toolbar [data-testid="stHorizontalBlock"],
    .st-key-dhoa_filter_panel [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: wrap !important; gap: 0.4rem !important;
    }
    .st-key-dhoa_header_row [data-testid="stColumn"]:nth-child(1) { order: 1; flex: 1 1 50% !important; }
    .st-key-dhoa_header_row [data-testid="stColumn"]:nth-child(4) { order: 2; flex: 1 1 40% !important; }
    .st-key-dhoa_header_row [data-testid="stColumn"]:nth-child(2) { order: 3; flex: 1 1 100% !important; }
    .st-key-dhoa_header_row [data-testid="stColumn"]:nth-child(3) { order: 4; flex: 1 1 100% !important; }
    .st-key-dhoa_map_toolbar [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 45% !important; }
    .st-key-dhoa_filter_panel [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 45% !important; }
    .st-key-dhoa_filter_panel [data-testid="stForm"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:nth-child(2) { flex: 1 1 100% !important; }
    .st-key-dhoa_filter_panel [data-testid="stPills"],
    .st-key-dhoa_filter_panel [data-testid="stPills"] [role="group"] { max-width: 100%; flex-wrap: wrap !important; }
    .dhoa-summary .dhoa-metric { padding: 0.25rem 0.5rem; }
    .dhoa-metrics.dhoa-summary { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
}
/* The local Help chatbot floats above page content and never restores the sidebar. */
.st-key-dhoa_chatbot {
    position: fixed !important; right: 1.25rem; bottom: 1.25rem; z-index: 10000;
    width: max-content !important; max-width: calc(100vw - 2rem);
}
.st-key-dhoa_chatbot [data-testid="stPopover"] > button {
    display: flex; align-items: center; justify-content: center;
    width: 3.75rem; height: 3.75rem; min-width: 3.75rem; min-height: 3.75rem !important;
    padding: 0 !important; border: 2px solid var(--dhoa-color-border-strong) !important;
    border-radius: 50% !important; background: var(--dhoa-color-primary) !important;
    color: var(--dhoa-color-on-primary) !important; font-size: 1.65rem !important;
    box-shadow: var(--dhoa-shadow-card); transition: transform 140ms ease, box-shadow 140ms ease;
}
.st-key-dhoa_chatbot [data-testid="stPopover"] > button:hover {
    transform: translateY(-2px); box-shadow: var(--dhoa-shadow-card);
}
.st-key-dhoa_chatbot [data-testid="stPopoverBody"] {
    width: min(23rem, calc(100vw - 2rem)) !important;
    max-height: min(75dvh, 42rem) !important; overflow-y: auto !important;
    border: 1px solid var(--dhoa-color-border-strong);
    border-radius: var(--dhoa-radius-md, 12px); box-shadow: var(--dhoa-shadow-card);
}
.st-key-dhoa_chat_history_view { overflow-y: auto; }
@media (max-width: 768px) {
    .st-key-dhoa_chatbot {
        right: 0.75rem; bottom: calc(3.5rem + env(safe-area-inset-bottom));
    }
    .st-key-dhoa_chatbot [data-testid="stPopover"] > button {
        width: 3.35rem; height: 3.35rem; min-width: 3.35rem; min-height: 3.35rem !important;
    }
    .st-key-dhoa_chatbot [data-testid="stPopoverBody"] {
        width: calc(100vw - 1.5rem) !important; max-width: 23rem !important;
    }
}
"""


def priority_chip_html(band: str, label: str) -> str:
    """Return a ``.dhoa-chip`` for a priority band: glyph (shape) plus text, never colour alone.

    Input: band key (``High``/``Medium``/``Low``) and an already-translated, already-escaped
    label. Output: an HTML string; an unknown band gives a neutral chip without glyph.
    """
    spec = tokens.PRIORITY.get(band)
    if spec is None:
        return f"<span class='dhoa-chip'>{label}</span>"
    return f"<span class='dhoa-chip dhoa-chip--{band.lower()}'><span aria-hidden='true'>{spec['glyph']}</span>{label}</span>"


def page_css(page_loading: str) -> str:
    """Return the full ``<style>`` block for the dashboard.
"""
    body = _BODY_CSS.replace("__PAGE_LOADING__", page_loading)
    return f"<style>\n{tokens.css_variables()}{font_face_css()}\n{body}</style>"
