# HANDOFF P4: inspector redesign

## What changed
- `app/inspector.py` (new, pure): `distance_rows(row, rules)` (state inside / outside / unknown from `buffer_m` in `config/rules.yaml`; equal to the buffer counts as outside), `distance_grid_html`, `legend_html`, `heat_points(frame, limit=5000)` (unweighted, so the layer shows density, not risk).
- `app/streamlit_app.py`:
  - `_render_distance_grid(row)` inside the selected-kiln card: icon, feature label, distance, dot (●/○/–) plus text ("Within 1 km" / "Beyond 1 km"). Dot shape and text carry the state, not colour alone.
  - Map panel now starts with the marker key (▲ ◆ ● with colours) and a `st.toggle` (`key="dhoa_heatmap"`, language-neutral) for the heatmap.
  - `_selected_feature_group(lat, lon, heat)` now returns one overlay group (highlight ring and/or HeatMap) passed to `feature_group_to_add`, so toggling it or selecting a kiln does not remount the map. The community map call still works (it passes lat/lon only).
  - Map panel wrapped in `st.container(key="dhoa_map_sticky")`.
- `app/styles.py`: legend, `.dhoa-dist*` grid, sticky rule (desktop >= 769 px). Tokens only.
- Kept from earlier modules (not rebuilt): Apply-filters form, summary strip, `PRIORITY_NOTE` ("relative, not absolute"), street/satellite selector, directions/street view/Earth links, PDF download, coordinates.

## How to verify
1. `pytest tests/test_inspector_p4.py tests/test_map_stability.py tests/test_inspector_m4.py tests/test_strings_i18n.py`. The pure tests in `test_inspector_p4.py` passed here (6 of 7 listed pure + wiring); nothing else was run.
2. Open Map: legend visible; toggle heatmap: the view must not move; click a list row: card shows the icon grid in < 1 s and the map keeps its zoom.
3. `python tools/benchmark_dashboard.py` (map payload < 1 MB; the heatmap adds ~2k points of two numbers when on).

## Decisions
- Heatmap has no weights (no invented risk scale).
- The legend carries no note of its own: the summary strip caption directly above already shows `PRIORITY_NOTE` (an existing test expects it there); avoids saying it twice.
- Detail card stays under the map in the right column.

## New strings (both catalogues)
LEGEND_TITLE, HEAT_TOGGLE, HEAT_HELP, DETAIL_DISTANCES_TITLE, DETAIL_WITHIN_FMT {0}, DETAIL_BEYOND_FMT {0}, DETAIL_STATE_UNKNOWN. **All need native-speaker review** (Bangla "-এর মধ্যে/-এর বাইরে" phrasing especially).

## Toggle bugs noticed
- The heatmap toggle uses a fixed key, so it survives a language switch; the sidebar/map-type widgets keep the existing `_wkey` pattern. Nothing new found; no changes to the toggle.

## NOT verified
- Nothing ran under real Streamlit/folium/streamlit-folium (not installable in the build sandbox). In particular: HeatMap inside `feature_group_to_add`, the sticky CSS and the < 1 s selection are untested.
- Sticky map: the right column is normally taller than the list (list height is fixed at 640 px), so sticky may have no visible effect. Check by hand; if wanted, the fix is a taller/auto list height.
- Not done: the sidebar is still the filter rail (the brief's "rail" is satisfied by it); the street/satellite selector remains in the sidebar, not in the map panel.
- Distance column names follow the list (`dist_<feature>_m`); a feature with another column name shows "No data".

## Owner must check by hand
Heatmap look and readability in both basemaps; the grid at 360 px; Bangla copy; that the "inside" border colour is distinguishable (also has the ○/● shape and text).

## First step for P5
Read `_render_community_inputs`, `_render_community_empty`, `_render_community_results`, `_set_community_origin`, `_submit_community_geocode` and `app/community.py`.
