# HANDOFF R3 — One Map screen with built-in place search

**Not run in a browser or with Streamlit.** The authoring sandbox had no Streamlit, pytest or network, so every change below was checked by reading code, compiling, and running the source-level tests through a stand-in runner. The AppTest tests and all visual/performance checks are still to be run (see NOT verified).

## Changes
- `app/hero.py`: `VIEW_MODES = ("overview", "inspector", "about")`. Navigation is Overview · Map · About. Internal value `inspector` still means the Map.
- `app/streamlit_app.py`:
  - New `_render_search_bar` replaces `_render_community_inputs`: one bordered bar (`key="dhoa_search_bar"`) with place picker + distance on the first row, "Use my location" / example / typed place below. Same widget keys, callbacks, notices and geocoder as before, so the old flows (GPS, typed place, example, whole district/upazila, widen-radius) are unchanged.
  - New `render_map_screen(gdf, filters, visible)` replaces `render_community_view` and is what `main()` calls for the Map. No place chosen -> exactly the previous Map (summary strip + map + list). Place chosen -> "Clear search" button, a one-line note, then the old results block (summary, list, radius circle map, PDF, CSV).
  - `_render_community_results(..., heading=True)`: the "Step 3" heading can be switched off (the Map screen does).
  - `_clear_search` callback; `_go_to_search` callback for the Overview "Find kilns near me" button (opens the Map and asks for focus); `_focus_search_input` focuses the place picker after that (best effort, wrapped in try/except).
  - `render_header`: a stored `dhoa_view_mode == "community"` is mapped to the Map; one help popover for the Map (uses `HELP_INSPECTOR`, which now covers search + filters); subtitle/divider logic uses `!= "inspector"`.
  - The `get_filtered_gdf` "community" branch and the `("community", ...)` marker-cache key are untouched (still used by the search map).
- Strings (both catalogues): `HELP_INSPECTOR` rewritten ("Using the Map": look near you / browse everything / details); `VOICE_INSPECTOR_SCRIPT` mentions the search (fallback copy in `voice_scripts.py` kept identical); new `MAP_CLEAR_SEARCH`, `MAP_SEARCH_FILTERS_NOTE`. Bangla is new copy and needs native review.
- Docs: README dashboard paragraph and `docs/DASHBOARD_GUIDE.md` heading/intro.
- **Fix to my R2 delivery:** R2 wrote the changed catalogue values with `\u` escapes, but the catalogues use literal Bangla/emoji (and `test_copy_is_bangla_and_has_no_escapes` requires it). Converted back to literal; values are identical (checked programmatically). The only remaining `\u` is the original `\u200d` in `PRIORITY_NOTE`. This zip therefore includes the R2 files again, in their corrected form.
- **Second R2 miss, fixed:** `test_committed_audio_files_play_in_the_popover` still expected the Map mp3 that R2 deleted. It now skips until the Map voice guide is re-rendered.

## Tests updated (obsolete assumptions)
- `tests/test_hero_p2.py` (3 nav items), `tests/test_layout_m11.py` (header condition), `tests/test_views_m8.py` and `tests/test_community_m5.py` (Near me tests now run on the Map; "pick a place" prompt is gone when nothing is chosen; Overview CTA lands on the Map), `tests/test_voice_p10.py` (only the Map view has a guide; audio test skips until re-rendered), `tests/test_trust_p7.py` (view list).
- New `tests/test_map_screen_r3.py`: 5 source-level tests (run here, pass) + 3 AppTests (old `community` value opens the Map; choose place -> results -> Clear returns to the map; sidebar filters survive a search).
- Run here via stand-in runner: `test_map_screen_r3` (5), `test_wording_r2` (7), `test_hero_p2` (8), `test_layout_m11` (6), `test_strings_i18n` all pass. Not run: every AppTest.

## How to verify
1. `pytest` (expect the 15 failures that existed before R1 and nothing new; the AppTests above are the ones to watch).
2. `streamlit run app/streamlit_app.py`, both languages:
   - Header shows Overview · Map · About only.
   - Overview -> "Find kilns near me": Map opens and the cursor is in the place picker.
   - Map with nothing chosen looks and behaves as before. Pan/zoom must not reset the map; selecting a kiln must not blank it.
   - Pick Savar (or any place), then 1/2/5/10 km; pick an upazila/district (distance disabled, "whole area"); "Use my location"; typed place; example button. Results, circle, PDF (`dhoa_near_me_report.pdf`) and CSV work. "Clear search" returns to the full map and keeps sidebar filters.
   - Old link/session with view `community` opens the Map.
   - Screenshots at 1280, 484 and 360 px; filter change < 1 s, payload < 1 MB, selection < 1 s.

## Decisions / deviations from the R3 brief
- Filters stay in the sidebar (district / area / kiln type / priority / "More filters" are already there as the form). The top bar holds place search, GPS, distance. Whole-district/upazila search is done through the place picker (as before) rather than separate filter boxes. Moving the filters into the top bar is a bigger change that I did not make blind; say if you want it.
- Search results ignore the sidebar filters (a note on screen says so). Making them apply needs the community result computed on the filtered frame; left for later.
- Kept dead strings (`HELP_COMMUNITY`, `VOICE_COMMUNITY_SCRIPT`, `NAV_NEAR_ME`, `C_STEP*`) because tests/tools pin them; safe to delete in R7 tidy.
- `tools/patch_voice_guide.py` (one-off) looks for `render_community_view` / `HELP_COMMUNITY` and would no longer match; the voice guide is already patched in.

## New strings
`MAP_CLEAR_SEARCH`, `MAP_SEARCH_FILTERS_NOTE` (bn + en). Changed: `HELP_INSPECTOR`, `VOICE_INSPECTOR_SCRIPT`.

## Toggle bugs noticed
None (not looked for; Module L skipped).

## NOT verified
- Everything that needs Streamlit or a browser (see above), including: the custom GPS component (`_geolocate`) in a narrow column, the search bar at 360 px, the focus script (`components.html` iframe reaching `window.parent`), and fragment behaviour of the search map when it now sits under the new bar.
- Streamlit version quirks: `st.button(icon=...)` and `st.columns(vertical_alignment=...)` are used and assumed available in the pinned 1.66.

## Owner hand-checks
- Click through both languages as above; read the new Bangla help/voice text.
- Re-render the Map voice guide when convenient (`pip install edge-tts`, `python tools/generate_voice_guides.py`).

## First step for next module (R4)
Build `STAFF_ONLY_COLUMNS` from the real parquet columns and `kiln_data.public_view(df)`; the public paths to strip are now: `_cached_marker_payload` callers (`render_map`, `_render_community_map`), `_popup_content`, `_render_selected_candidate` (rule distances), `_render_community_table` (priority column), `_render_summary_strip`, `_render_priority_list`/list payload, `community_alert_pdf`, and the CSV buttons. Both map modes now live on the one Map screen, so one public/staff switch covers them.
