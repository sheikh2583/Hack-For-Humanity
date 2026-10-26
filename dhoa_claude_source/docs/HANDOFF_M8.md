# M8 — Tests and QA: handoff

## CHANGELOG (M8)
- **Hermetic app runs**: `DHOA_DATA_DIR` env var overrides the data folder (one line in `streamlit_app.py`), so AppTests can load a synthetic parquet instead of the real data. Default behaviour is unchanged.
- `tests/synthetic.py`: tiny made-up kiln data (+ a "Remote Bazar" place whose two kilns are ~11 km apart, for the empty state) and a GeoParquet writer.
- `tests/test_views_m8.py` (AppTest, both views, synthetic data): Inspector loads and filters; Community prompt -> result for an upazila, a district-level pick and a named place; empty state shows nearest distance and the widen button actually widens; a point outside coverage is explained.
- `tests/test_filters_m8.py`: filter results vs brute-force pandas for 4 districts x 3 priority sets; band counts add up; community distances vs `pyproj.Geod`; results nest as the radius grows; every listed whole-area place returns exactly its kiln count; empty-state helpers.
- `tests/test_perf_gate.py` (2,135 synthetic rows): filter < 1 s, list frame < 0.3 s, community search < 0.3 s, marker payload < 2 s and < 1 MB. `DHOA_PERF_FACTOR=3` relaxes it on slow machines. The existing `test_map_stability.py` already gates map HTML < 1 MB.
- `tests/e2e/test_community_pan_zoom.py`: Playwright check for the Community map (zero reruns, no snap-back), next to the existing Inspector one. Opt-in: `DHOA_E2E=1`.
- `tools/benchmark_dashboard.py`: timing table for the real data (or `--synthetic`). The "before" numbers from your M0 baseline were not in the zip I have, so the before/after table must be assembled on your side: run it on the M0 commit and now.
- `docs/QA_CHECKLIST.md`: manual checklist for 360 / 412 / 768 / 1280 px, both views.

## Checks run
- Syntax parse of every new file. The Community helper logic used by the new tests was exercised with a haversine stand-in for the distance function (empty state at 1 km, nearest 5.44 km, 2 kilns at 10 km, outside-coverage point -> None, Dhaka point -> Dhaka).
- NOT run: pytest, the AppTests, Playwright, the benchmark (no streamlit/pyproj/pytest/network in my sandbox).

## NOT verified / owner must check by hand
1. **Run the whole suite**: `pytest -q` then `DHOA_PERF_FACTOR=1 pytest tests/test_perf_gate.py`. Expect to fix a few things in the AppTests first; I could not execute them.
2. **Synthetic parquet schema**: it has no `dist_*_m` or `breached_rules` columns. If the loader or popups require them, add them in `tests/synthetic.py`.
3. AppTest details that may need adjusting to your Streamlit 1.66: setting the segmented control through `session_state["community_radius_m"]`, `select_index` on a selectbox with `index=None`, `at.warning`/`at.info` collections.
4. The perf gate uses synthetic data; the real-data numbers (and the before/after table) need `tools/benchmark_dashboard.py` on your machine. Timings depend on hardware, hence the factor.
5. The e2e tests need `playwright install chromium` and the real data; the Community one types "Savar" into the picker by placeholder text and may need a selector tweak.
6. Stale M0 leftovers still in the repo: `test_header_marks_metrics_for_mobile_grid` (old `@import`/h1 markup) in `test_dashboard_presentation.py`, and `rasterio`-dependent `test_inspect_raster.py`.
7. Nothing pushed to GitHub.
