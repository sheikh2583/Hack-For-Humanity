# M4 — Inspector redesign: handoff

## CHANGELOG (M4)
- **Priority by shape + colour.** Map markers are now inline-SVG icons: triangle = High, diamond = Medium, circle = Low, square = unclassified (`_marker_callback_js`). The list, detail card, sidebar priority filter and popup badges use the same glyphs (`kiln_data.PRIORITY_GLYPHS`, `priority_badge`).
- **Summary strip** above the list and map: matching kilns, High, Medium, Low, new candidates (`_render_summary_strip`, `kiln_data.priority_summary`). It replaces the old trailing line under the map.
- **Relative-ranking note** under the strip (`strings.PRIORITY_NOTE`): bands are shares of the ranking (top 20% / next 40% / rest 40%), not absolute risk.
- **Filter rail**: the left sidebar keeps the Apply form and gains a one-line hint (`RAIL_HINT`); priority options show their shape.
- **Detail card**: bordered card (`dhoa_detail_card`) under the map with priority badge, type, area, detection status, forest distance, coordinates and Directions / Street View / Earth links. A placeholder hint shows until a kiln is chosen.
- **States**: unified empty state (message + hint + one-click reset), "map is loading" spinner, map error with retry button.
- Typo fixed: `STATUS_NEW` said 2025–22, now 2025–26.
- Tests: new `tests/test_inspector_m4.py` (7 tests incl. two AppTests); localization tests rewritten for Bangla-only; `test_dashboard_m2.py` updated for folium 0.20 (`.data`).

## Checks run
- 63 dashboard tests pass (`test_inspector_m4`, `test_map_stability`, `test_kiln_data`, `test_dashboard_m2`, `test_dashboard_localization`, `test_dashboard_filters`, `test_streamlit_data_selection`).
- Real data (2,135 rows): map HTML 0.08 MB, base map build 0.02 s, summary 1 ms.
- Counts on the real data: High 430, Medium 855, Low 850 (of 2,135 after dropping false positives).

## NOT verified / owner must check by hand
1. **Visual check in a browser** (no browser in my sandbox): triangle/diamond/circle markers legible on street and satellite tiles, at zoom 7 and ≥12 (clusters disappear at 12), on a 360 px phone.
2. Marker click still selects the kiln and opens the popup now that markers are `L.marker` divIcons (previously circle markers); also check pan/zoom still causes no rerun.
3. **Native-speaker review** of new Bangla copy: `PRIORITY_NOTE`, `RAIL_HINT`, `EMPTY_FILTER_HINT`, `LOADING_MAP`, `RETRY`, `DETAIL_HINT`, summary labels, updated marker caption.
4. The brief says High/Medium/Low are "thirds (430/860/860)". They are 20% / 40% / 40% shares, so the note says that. Confirm that wording is what you want.
5. Upazila names are still English in messages (e.g. "'Adabor' এলাকায় …") because the data stores them in English.
6. Still open from other modules: header metric labels ("আইন লঙ্ঘন", "পরিবেশ বিপজ্জনক ভাটা"), the law expander, "last updated" date and hotline 16131 (all M6); two failing tests in `tests/test_popup.py` and the `_area_label` import in `tests/test_dashboard_presentation.py` (M0 leftovers); `rasterio` missing for `test_inspect_raster.py` in my environment.
7. GitHub repo not touched; nothing pushed.
