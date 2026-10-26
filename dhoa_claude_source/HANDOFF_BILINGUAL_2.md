# Bilingual follow-up: fixes and what is still open

## Fixed in this pass (found by reading the code; nothing could be executed here)
1. **Stale-language notices (Community).** GPS/geocoder messages were saved in session state as translated text, so after switching language they stayed in the old one. They are now saved as codes (`_set_community_notice`, `_NOTICE_NAMES`) and translated when drawn.
2. **Stale "my location" label.** A GPS origin stored the translated label; it now stores `gps=True` and the label is looked up in the active language (`_community_place`).
3. `tests/test_dashboard_presentation.py`: the remaining stale test (`test_folium_marker_click_selects_candidate_for_report`) is skipped with a reason (flow replaced; covered by `test_map_stability.py`, `test_views_m8.py`); `test_dashboard_does_not_render_the_developer_banner` now patches the data/language/UI calls it needs; stale docstring fixed. All other skipped tests were already skipped with reasons by the previous agent.
4. `tests/test_header_m6.py` now checks the advisory wording in **both** languages (the English catalogue is clean: no violation/hazardous/illegal words).
5. New `tests/test_language_switch.py` (4 tests) guards the two bugs above and the canonical-value widgets.
6. `docs/QA_CHECKLIST.md`: language-toggle section replaced by the browser steps from your list.

## Verified statically
- `strings_bn` and `strings_en` have identical names (no missing/extra) and identical `{format}` fields for every string.
- The only import-time uses of `T.` in `streamlit_app.py` are `APP_TITLE`, `CHANDRABINDU` and the `LazyMapping/LazySequence` wrappers; no cached function builds text without the language in its key (`_prepared_data` has `lang`; every version-keyed cache inherits it through the data version; `_cached_community_pdf` has `lang`).

## NOT done / you must do
1. **Run `pytest -q` on your machine** (install `typer rich` first). My sandbox has no network, so pytest, typer, rich, streamlit, geopandas could not be installed; none of the tests ran.
2. **Browser check** (no browser here): follow the new QA section. One thing I could not settle by reading: the map's `st_folium` key does not include the language, so after a switch the component receives new map HTML under the same key. If the map ever goes blank after a switch, add the language to the `_map_key(...)` fingerprint (forces a clean remount, which is also what re-fits the view).
3. **Restore missing files from GitHub** (no network here). From the repo root:
   `git checkout origin/main -- src/eval/fonts/NotoSansBengali-Regular.ttf static` (or download them from github.com/sheikh2583/Hack-For-Humanity and copy). Then confirm `app/static/fonts/*.woff2` and `.streamlit/config.toml`'s font path resolve in the browser Network tab. `src/eval/fonts/` currently only has `OFL.txt`; the per-kiln PDF needs the TTF.
4. **English copy** needs a native-speaker review; the per-kiln PDF (`src/eval/generate_report.py`) is still not translated.
5. Nothing pushed to GitHub.

## Update: sidebar did not switch language, filters gave zero results
Cause (from your screenshot): the sidebar widgets (district, priority, kiln type, map type, community picker/radius, view switch) kept the same widget key across languages, so Streamlit reused the old widget and kept showing the previous language's option text (Bangla tags next to an English list), and the displayed selection and the stored one could disagree.
Fix: every widget with translated option text now has a **language-specific key** (`w_<name>@bn` / `@en`, see `_wkey`), so it is rebuilt when you switch. The real value lives under the language-neutral name (`filter_priority = ["High", ...]`, `filter_district = "Gazipur"`, ...). It is copied into the new widget before it is drawn (`_seed`) and copied back when you change it (`_commit`). Legacy Bangla/English labels in the stored priority are mapped to the canonical keys on every run, and an unknown value means "all", never zero rows.
Tests: AppTest keys changed to `w_filter_district@bn` etc. (test_inspector_m4, test_community_m5, test_views_m8); new `test_language_switch_keeps_filters_and_gives_same_results` (AppTest) plus pure tests that `_wkey` differs per language and that Bangla and English priority labels give the identical filter key.
Not run (no streamlit/pytest here). Side effect to expect: un-applied edits inside the filter form are dropped when you switch language.
