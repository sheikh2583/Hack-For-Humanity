# HANDOFF P3: overview and district comparison

## What changed
- `app/overview.py` (new, pure, no Streamlit import): `district_stats(frame)` (district,total,high,medium,low; ranked total desc, high desc, name), `upazila_stats(frame, limit=10)` (same upazila name in two districts stays two rows), `type_split(frame)` (Zigzag, FCBK, other; zeros dropped), `bar_width`, and escaped HTML builders `bars_legend_html`, `district_bar_html`, `type_split_html`.
- `app/streamlit_app.py`: `render_overview` now ends with `render_overview_charts(gdf)`; `_open_district` callback sets the canonical district filter, resets upazila and selection, and switches the view to the Map. Uses `_drop_widget_state` so the sidebar widgets re-seed (existing pattern; no language-dependent keys added).
- `app/styles.py`: "overview charts (P3)" block, tokens only. FCBK segment uses a striped pattern (non-colour cue).
- Charts are HTML/CSS bars, not a chart library: direct value labels, `role="img"` aria-labels, readable at 360 px, bilingual through `T`.

## How to verify
1. `pytest tests/test_overview_p3.py tests/test_strings_i18n.py`. The pure tests were run here with a stand-in runner and passed (9/9 pure). The AppTest skipped (no streamlit).
2. Run the app, open Overview: numbers per district must equal `df.groupby("district")` (the test does this on synthetic data).
3. Click a district: Map opens with that district selected, no page reload.

## Decisions
- No chart library (no JS, nothing to cache, accessible by default).
- The bars show totals and High only; medium/low are in `district_stats` but not drawn.

## New strings (both catalogues)
OV_DISTRICTS_TITLE, OV_DISTRICTS_HINT, OV_OPEN_DISTRICT_FMT {0}, OV_SERIES_TOTAL, OV_SERIES_HIGH, OV_UPAZILAS_TITLE, OV_COL_CANDIDATES, OV_COL_HIGH, OV_TYPES_TITLE, OV_TYPE_OTHER, OV_SHARE_FMT {0:.0f}%, OV_NO_DATA. **All need native-speaker review.**

## Toggle bugs noticed
- `_open_district` has to drop the sidebar widget keys so the sidebar re-seeds after a language switch; not touched further (Module L).

## NOT verified
- Nothing here ran under real Streamlit/folium/pandas-with-pyarrow: the build sandbox cannot reach PyPI. The AppTest and the wiring test (imports the app) are unrun.
- No browser screenshots of the new bars (needs Playwright against a running app).
- Benchmarks (`tools/benchmark_dashboard.py`) not run; the stats are groupbys over ~2k rows so no regression is expected, but unmeasured.

## Owner must check by hand
- Bars at 360 px in both languages; long district names.
- Clicking a district lands on the Map with the right filter.
- Bangla copy.

## First step for P4
Read `render_sidebar`, `_render_summary_strip`, `render_map_fragment` in `app/streamlit_app.py`, and `kd.marker_payload`.
