# HANDOFF R3 FIX — "Something went wrong" on the Map after choosing a place

## Symptom
Map screen drew the search bar, then the red "Something went wrong" card. Nothing was drawn after the bar (no "Clear search" button), and it only happened once a place was chosen.

## Most likely cause (not reproduced in a browser)
The first thing drawn after the bar when a place is chosen is the "Clear search" button, which reads two strings that R3 added (`MAP_CLEAR_SEARCH`, `MAP_SEARCH_FILTERS_NOTE`). A running Streamlit server keeps the old string catalogue in memory until it is restarted, so those two names were missing, `T.<name>` raised `AttributeError`, and `main()` showed the generic error card. With no place chosen, no new string is read, which is why the plain map still worked.
I could not run Streamlit here. In a stand-in harness (stub Streamlit, fake kiln frame) the Map screen renders without error for: no place, district, upazila, named place, GPS fix, typed point outside coverage, stale picker key, and the Overview focus flag. That rules out an ordinary Python bug in those paths; it does not prove the cause above.

## Changes (app/streamlit_app.py)
- `_R3_FALLBACK_TEXT` + `_r3_text(name)`: the two R3 strings fall back to built-in copies (bn + en) if the catalogue lacks them.
- `render_map_screen`: the results block is wrapped, so a failure there shows the error card under the search bar and the sidebar, instead of replacing the page. (`?debug=1` shows the real error.)
- New `tests/test_r3_fallback.py` (fallback copies equal both catalogues; no direct `T.MAP_*` reads left).

## How to verify
1. Stop Streamlit completely and start it again (Ctrl+C, `streamlit run app/streamlit_app.py`), then hard-refresh.
2. Map -> pick "Dhaka" -> list, circle map, PDF, CSV and "Clear search" appear. Repeat in Bangla.
3. If the red card still appears, open the app with `?debug=1` at the end of the URL and send the error text.

## NOT verified
Anything in a real browser or with real Streamlit 1.66.

## Toggle bugs noticed
None.
