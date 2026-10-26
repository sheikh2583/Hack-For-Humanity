# M7 — Visual polish and mobile: handoff

## CHANGELOG (M7)
- **Tokens in one place**: new `app/design_tokens.py` (colours, spacing, type scale, 44 px tap size, font stack, WCAG `contrast_ratio`, `css_variables()` -> `--dhoa-*` custom properties). `DESIGN_COLORS` in `streamlit_app.py` now reads from it.
- **CSS moved** out of `streamlit_app.py` into `app/styles.py` (`page_css`). Hard-coded greys now use the variables; the 8 `@font-face` rules are generated (self-hosted, no external font). Tests check no stray hex colours remain.
- **Contrast (WCAG AA)**: measured and fixed. White text on the old primary red `#e53e3e` was 4.1:1 (fail) -> primary is now `#c53030` (5.5:1), also in `.streamlit/config.toml`. Red/blue text on the card was 3.8/3.9:1 -> lighter `high_text` / `new_text` tokens exist for text use (≥ 4.5:1). Marker/shape colours stay (≥ 3:1 on the page background; priority is also shown by shape).
- **Mobile stacking**: the general ≤768 px "stack all columns" rule stays, but the 3 detail-card buttons (Directions / Street View / Earth) sit in `st.container(key="dhoa_action_row")` and stay side by side with smaller text.
- **Map height** on phones: `clamp(300px, 55dvh, 520px)` (old `52vh` kept as fallback).
- **Tap targets**: 44 px minimum extended to form-submit, link buttons, segmented control, popover and expander headers (the custom list and GPS buttons already had 44 px).
- **Focus and motion**: visible focus ring on all controls; `prefers-reduced-motion` respected.
- Tests: `tests/test_design_m7.py` (8 tests); the stale CSS assertion in `test_dashboard_presentation.py` updated to the current rules.

## Checks run
- All 8 token/contrast/CSS checks were run as a script here (pass). Not run: pytest, Streamlit, any browser (no network in my sandbox).

## NOT verified / owner must check by hand
1. **Look at it in a browser** at 360, 412, 768, 1280 px: the 3-button row on a 360 px phone (text may wrap/truncate), map height, summary strip grid, sidebar on mobile.
2. **Streamlit's own theme**: I changed only `primaryColor`. Please eyeball the primary buttons and sliders in the new red (it is a bit darker).
3. **`:has`-free selectors depend on Streamlit's test ids** (`stBaseLinkButton-secondary`, `stSegmentedControl`, `stColumn`, `st-key-*`). If a Streamlit upgrade renames them, the rules silently stop applying; check once after upgrading.
4. **Marker colours** on satellite tiles were not re-checked (colour alone is not relied on; shapes carry priority).
5. **Contrast of Streamlit-rendered widgets** (disabled controls, placeholders, dataframe) was not measured; only our own colours were.
6. `test_header_marks_metrics_for_mobile_grid` in `test_dashboard_presentation.py` still asserts an old `@import` font and an old `<h1 ... id=...>`; it was already stale before M7 (M0 leftover) and I did not touch it. The community PDF is still English (not in M7 scope).
7. Nothing pushed to GitHub.
