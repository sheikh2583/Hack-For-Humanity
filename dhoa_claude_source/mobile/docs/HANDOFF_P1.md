# HANDOFF P1: design system

## What changed (files + why)
- `app/design_tokens.py` (rewritten): single source for colours, spacing, radii, shadows, type scale, line-heights, weights, tap size, `PRIORITY` (colour + shape + glyph per band). Adds WCAG contrast and colour-blind (protan/deutan/tritan, Machado) checks, and three generators: `css_variables()`, `component_root_block()`, `streamlit_theme()`.
- Palette: Okabe-Ito on a blue-grey surface. High = vermillion `#d55e00` (triangle), Medium = yellow `#f0e442` (diamond), Low = bluish green `#009e73` (circle), new = reddish purple `#cc79a7`, accent/primary = blue `#0072b2` (white text 5.2:1). Old red/orange/green and the gold "advisory" border colour are gone (`advisory` token renamed `unclassified`, a neutral grey).
- `app/styles.py`: CSS rebuilt from tokens only (no hex literals). New: tiles (`.dhoa-metric`), chips (`.dhoa-chip--high|medium|low|new`, helper `priority_chip_html`), cards (`.dhoa-card`), primary/secondary buttons, inputs, sidebar, segmented control, language pill (`.st-key-dhoa_lang_toggle`), body line-height 1.65, heading 1.5, brand 1.8 (Bangla conjuncts). Fonts were already self-hosted (8 `@font-face`, no `@import`): unchanged.
- `app/streamlit_app.py` (small edits): `DESIGN_COLORS` keys; text-safe priority colours in tables (`PRIORITY_TEXT_COLORS`); popup colours from tokens (the badge was dark text on a dark chip, now light chip); markers get a white halo + dark outline so yellow/vermillion read on any tile; summary strip uses tokens; language radio wrapped in `st.container(key="dhoa_lang_toggle")` (styling hook only, the widget and its key are untouched).
- `app/components/*/index.html`: hard-coded colours replaced by a generated `:root` block between `dhoa-tokens` markers; `tools/sync_component_tokens.py` rewrites it (`--check` verifies). Gold borders became neutral; selection is the accent blue. List line-height 1.45 -> 1.6.
- `.streamlit/config.toml`: theme colours now equal the tokens (a test enforces it).
- Tests: `tests/test_design_m7.py` updated; new `tests/test_design_p1.py` (10 tests: CVD separation >= 30 dE for all three bands under all vision types, shapes/glyphs unique, token coverage, no stray hex in CSS/app/components, component sync, theme sync).
- `scripts/shoot_p1_harness.py` + `docs/screens/p1/`: before/after screenshots (bn/en at 360/768/1280) of mock markup using the old and new CSS.

## How to verify
1. `pytest -q tests/test_design_m7.py tests/test_design_p1.py` then the full dashboard suite.
2. `python tools/sync_component_tokens.py --check` (exit 0).
3. Run the app, look at both views in both languages at 360/768/1280 (see "owner must check").
4. `python scripts/shoot_p1_harness.py <old_app_dir> docs/screens/p1` re-creates the screenshots.

## Decisions
- Dark theme only; accent is blue (not red) so red-orange stays reserved for "High".
- Medium is yellow, not orange: vermillion vs orange collapse for deuteranopes (Okabe-Ito advice). Shape + glyph always accompany colour.
- Language toggle was restyled only by CSS plus a container key; no i18n or state code touched.
- No new user-visible strings (no catalogue changes).

## Toggle bugs noticed
None seen (the app was not run, see below).

## NOT verified (important)
- **The Streamlit app was never run in this pass.** The sandbox has no streamlit/geopandas/folium/fpdf/pytest, no PyPI access, and the zip has no `data/` (parquet). I need a wheelhouse zip (and `data/processed/`) to run the app and the full test suite. Only the pure-Python tests (19: `test_design_m7` + `test_design_p1`) were run, with a small shim instead of pytest, and all passed. `streamlit_app.py` was only syntax-checked.
- Streamlit's own widget selectors (`stBaseButton-*`, `stBaseLinkButton-*`, segmented control active state, radio circle hidden via `label > div:first-child:not([data-testid])`) are written from memory of the 1.6x DOM and are unproven. If the language pill shows radio dots or the active tab is not blue, inspect the DOM and adjust `styles.py`.
- Screenshots are mock markup in real Chromium with the real fonts (Noto Sans Bengali loaded, no horizontal scroll at 360/768/1280), not the real app. The priority-list iframe component was only checked for token sync, not rendered.
- `tools/benchmark_dashboard.py` not run (no data). Changes are CSS plus a slightly longer marker SVG string; expect no change, but confirm.
- The candidate-list iframe cannot load `/app/static` fonts, so it still falls back to Nirmala/system for Bangla (pre-existing).

## Owner must check by hand
- Medium yellow marker and halo on real street and satellite tiles (sandbox blocks tiles).
- Popup: priority badge and the new-candidate badge are readable.
- The popup rule rows still use red/yellow/green emoji dots (🔴🟡🟢⚪). Left alone for P4 (threshold-dot grid).
- Pill toggle works and the PDF/other screens are unchanged.

## First step for the next module (P2)
Get the wheelhouse + data running first, run pytest and the benchmark, then build the hero and top navigation using `.dhoa-metric`, `.dhoa-chip`, primary/secondary buttons from P1 (no new colours: add tokens in `design_tokens.py` and run the sync tool if a component needs them).
