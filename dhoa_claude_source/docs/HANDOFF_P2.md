# HANDOFF P2: landing hero and navigation

## What changed
- `app/hero.py` (new, pure): `VIEW_MODES`, `DEFAULT_VIEW="overview"`, `hero_counts(frame)` (total, High, distinct non-blank districts), `hero_html(...)` (escaped).
- `app/streamlit_app.py`: `render_header` now = title, language pill, subtitle, **top navigation** (segmented control, collapsed label, same `_wkey/_seed/_commit` pattern) with Overview / Map / Near me / About. The old header metric row (incl. the "rule signals" count) is gone, so the numbers are no longer repeated on every view (P0 issue 3). New `render_overview` (hero + 2 buttons, `st.container(key="dhoa_action_row")` so they stay side by side on phones) and `render_about` (short; P7 owns the full panel). `main()` skips the sidebar for Overview/About. Stored view values keep the old names (`inspector`, `community`), plus `overview`, `about`. Default view is now **overview**.
- Hero buttons: "Explore the map" -> `inspector`; "Find kilns near me" -> `community` (via `on_click`, no reload).
- Hero numbers are real: total = rows, High = `priority_band == "High"`, districts = distinct non-blank `district`, date = parquet mtime (existing `_data_date_label`).
- `app/styles.py`: `.dhoa-hero*`, `.dhoa-about`; mobile title uses h2 size.
- Wording: no "violation/hazardous" text exists in either catalogue (only the old constant name `METRIC_RULE_VIOLATIONS`, left to avoid churn). Removed the duplicate "❔" from `HOW_TO_USE` in both languages (the popover already draws an icon; P0 issue 5).
- Tests: new `tests/test_hero_p2.py` (8 pure tests), 2 AppTests appended to `tests/test_views_m8.py` (hero + both CTAs, About), `tests/test_inspector_m4.py` now sets `dhoa_view_mode="inspector"` because the default changed.
- `scripts/shoot_p2_harness.py`, `docs/screens/p2/` (hero, normal and doubled-length text, bn/en, 360/768/1280, no horizontal overflow).

## New strings (both catalogues, no {fields})
NAV_OVERVIEW, NAV_MAP, NAV_NEAR_ME, NAV_ABOUT, HERO_MISSION, HERO_SUB, HERO_CTA_MAP, HERO_CTA_NEAR_ME, HERO_METRIC_DISTRICTS, ABOUT_TITLE, ABOUT_BODY. **All need native-speaker review**, especially the Bangla mission line. Reused: METRIC_TOTAL_CANDIDATES, METRIC_HIGH_PRIORITY_KILNS, METRIC_LAST_UPDATED, PRIORITY_NOTE.

## How to verify
`pytest -q tests/test_hero_p2.py tests/test_views_m8.py tests/test_inspector_m4.py tests/test_community_m5.py tests/test_strings_i18n.py`, then the full suite. Run the app: the first screen must be the hero; both buttons change the nav highlight and the view; Map and Near me still behave as before; Overview/About show no sidebar.

## Toggle bugs noticed
None seen (app not run). Risk to watch: the nav widget key is language-suffixed (`w_dhoa_view_mode@bn/@en`); the hero buttons set the canonical `dhoa_view_mode`, which `_seed` copies in on the next run.

## NOT verified
- **The app and every AppTest were not run** (no streamlit/geopandas/data/pytest here). 27 pure tests (P1 + P2) pass via a shim; `streamlit_app.py` is syntax-checked only. The two new AppTests and the edited ones are unrun.
- Screenshots use the real hero markup, CSS and fonts, but the nav and buttons are plain HTML mocks and the numbers are placeholders (2,135 / 430 / 5), not the parquet. Streamlit's segmented-control look and `st.button` are unproven.
- Benchmark not run (no data). Overview/About skip the sidebar and map, so they should be faster than before.
- `render_sidebar`/`dhoa_active_view` were not run for the new views; `dhoa_active_view` is only set when the sidebar renders (Map / Near me), as before.

## Owner must check by hand
1. Open the app fresh in bn and en at 360 px: hero visible without opening the sidebar; two buttons side by side.
2. Click both buttons; use the nav; switch language on each view (watch for nav label or highlight not following: log it for module L).
3. District count reads 5 and High count matches the old header.
4. Read the new Bangla/English copy.

## Decisions / limits
- Overview is the landing page for now (hero only). Charts and the district drill-down arrive in P3; About is minimal until P7.
- "Near me" CTA opens the community view; auto-locate is P5.

## First step for P3
Get the wheelhouse + `data/` in place, run pytest and the benchmark, then add the district charts below the hero buttons in `render_overview`, using the `PRIORITY` shapes/colours from `design_tokens.py` and a groupby unit test.
