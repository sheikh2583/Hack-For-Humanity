# HANDOFF S2 — Public data split, simple public Overview, staff Dashboard

IMPORTANT: written WITHOUT being able to run anything. PyPI was blocked in the authoring session, so Streamlit, pytest, geopandas, pyproj, fpdf2 and the browser were unavailable. The pure-pandas logic and the generated map script were run (see "How verified"); no app run, no AppTest, no PDF, no browser. Treat everything under "NOT verified" as untested.

## Changes
- app/kiln_data.py: `STAFF_ONLY_COLUMNS` (one place; explicit names taken from the documented outputs of src/rules/engine.py and src/score/priority.py, plus the `dist_*` alias spellings the popup accepts), `STAFF_ONLY_PREFIXES` (`priority`, `breach`, `rule`, `dist_`, `signal_`, and any `*_normalized`) as a safety net for columns not listed, `STAFF_ONLY_DISPLAY_COLUMNS` (`ui_priority`, `ui_tooltip`, `ui_popup_html`). New `is_staff_only_column`, `public_view(df)`, `leaked_columns(df)`, `with_public_display_columns`, `prepare_public_frame(df, version)` (public frame + `ui_area`/`ui_type`; version token ends `-public`) and `public_marker_payload(df)` (`[lat, lon, type, area]` rows only).
- app/streamlit_app.py:
  - `get_public_data()` (cached per file version and language; derived from the cached staff-prepared frame, so no second file load) and `main()` hands ONLY the public frame to Overview, About and Kilns near me. Staff frame is unchanged and used by the portal.
  - Public Overview (`render_overview`): mission line, three numbers (kiln candidates, districts covered, data date), "Kilns near me" button (staff also keep the portal-map shortcut), "How it works" expander (3 steps: no rule check, no ranking), and a district list with counts (`render_public_districts`). Each district name opens Kilns near me with that district chosen (`_open_district_near_me`). No High count, High series, kiln-type split or priority note.
  - Kilns near me cleaned of all priority/rule content: summary is a plain count; table has no priority column; community CSV download removed; map uses `_public_marker_callback_js` (one neutral grey circle, tooltip type | area, popup with type/area/coordinates/links) and `_cached_public_marker_payload` (key carries "public"); clicked-kiln card is `_render_public_candidate` (no priority, forest distance, distance grid, report PDF); the community PDF input no longer has `priority_band`.
  - About: public frame, public 3-step how-it-works, priority note removed.
  - Inspector > Dashboard: now four numbers (adds data date) plus `render_overview_charts` (district bars with High, top upazilas, kiln-type split, click-through to Inspector > Map filtered). `render_overview_charts` now returns immediately for a non-staff session.
- app/overview.py: `public_district_counts`, `public_district_bar_html` (no High series).
- app/community.py: `search()` summary is `{"total": n}` when the frame has no `priority_band`.
- src/eval/generate_community_report.py: community PDF has no priority column (five columns; the area column took the width).
- app/strings_en.py / strings_bn.py: 6 new `PUB_*` strings in both; `HELP_COMMUNITY` step 3 no longer mentions downloading "the list" (the CSV is gone).
- tests: new tests/test_public_split_s2.py; tests/test_overview_p3.py (staff chart test now opens Inspector > Dashboard); tests/test_views_m8.py (`PUB_HERO_MISSION`).

## How verified
Run with a small stand-in runner on pandas only (pytest unavailable): 23 cases of tests/test_public_split_s2.py pass, including: no staff column name or sentinel value (band, score, 424242.5 m distance, provenance text) in the public frame, marker payload or map script; unknown `dist_*`/`rule_*` columns dropped by the prefix guard; public search summary has no band counts; public district counts have no High series; source checks that the public render functions never mention priority, rule columns, the community CSV or the priority note, and that `main()` passes only `public_gdf` to the three public views. The generated public map script passed `node --check`. For the existing suites that could be imported, results were identical before and after my edits (the failures there come from missing pyproj/fpdf2 and S1 wording tests, not from S2).

## How to verify (needs your environment)
1. `pytest tests/test_public_split_s2.py tests/test_overview_p3.py tests/test_views_m8.py tests/test_roles_s1.py tests/test_community_m5.py tests/test_pdf_p6.py`
2. Compare my staff-only list with the real parquet: `python -c "import geopandas as gpd; from app import kiln_data as kd; df=gpd.read_parquet('data/processed/kilns_prioritised.parquet'); print(sorted(c for c in df.columns if kd.is_staff_only_column(c))); print(kd.public_view(df).columns.tolist())"`. Anything in the second list that is a model, priority or rule value must be added to `STAFF_ONLY_COLUMNS`.
3. Browser, public: Overview shows three numbers and no High/priority/type split; View Source (or `curl` the websocket payload) has no `priority_band`, `breached_rules`, `dist_`, `signal_provenance`; Kilns near me map markers are all one grey circle, tooltip "type | area", popup without priority/signals; no CSV button; PDF opens with five columns.
4. Browser, staff: Inspector > Dashboard matches the old Overview (High count, district bars with High, upazilas, type split); a district button opens Inspector > Map filtered.

## Decisions
- The public/staff split is by FRAME (server side), not by hiding widgets: public views never receive the staff frame.
- `confidence` (detector score) is in the staff-only list. It is not in your list, but only the priority formula and the staff card use it. Remove it from `STAFF_ONLY_COLUMNS` if you want it public.
- The community CSV export was removed for everyone (it is a public path); staff keep the portal Map CSV and per-kiln PDF.
- The community PDF's priority column was removed now (needed for "no priority in public"); the rest of the PDF redesign stays in S3.
- Staff use the same public Overview/About/Kilns near me as everyone; staff-only content is only inside the portal.
- Public "How it works" drops the rule-check and ranking steps and uses a new neutral third step.
- Cache separation: public data version ends `-public`; public payload key contains `"public"`; the staff payload cache is untouched.

## New strings (both languages)
PUB_HERO_MISSION, PUB_HERO_SUB, PUB_OV_DISTRICTS_HINT, PUB_OV_OPEN_DISTRICT_FMT, PUB_HOW_3_HEAD, PUB_HOW_3_BODY. Edited: HELP_COMMUNITY (step 3, both).

## Toggle bugs noticed
None (not tested).

## NOT verified
Everything that needs Streamlit/a browser: the app start, the AppTest cases (written, not run), Overview/Near-me rendering, the district-button navigation (sets `community_place_key` to `district|<name>|`; relies on the widget being re-seeded from it), map script behaviour in Leaflet, PDF generation after removing the column, the staff Dashboard, performance budget, screenshots. The Bangla text of the new strings.

## Owner hand-checks
- Bangla wording of the PUB_* strings and of HELP_COMMUNITY step 3.
- Static page assets still contain priority CSS class names and colour variables (design tokens, `.priority-badge`, chips). They are not data and carry no values, but a literal "page source has no word priority" check will find them. Splitting the CSS by role is a separate change.
- Voice: VOICE_COMMUNITY_SCRIPT (and its transcript in the Near-me help popover) still says "Priority colours ..." and "download ... the list". The audio is pre-recorded and yours, so I left it. Re-record/re-write before judges listen.
- The Bangla top-bar label for About is "সম্পর্কে" (S1); your plan says "পরিচিতি".
- docs/DASHBOARD_GUIDE.md and README still use "Inspector/Community view" wording (planned for the S7 wording pass).

## First step for next module (S3)
Redesign Kilns near me on the public frame (search card, result cards with Directions, radius chips, neutral markers already in place, empty/error states). Re-run the S2 leakage tests after every change; the new public JS is `_public_marker_callback_js` and the public card is `_render_public_candidate`.
