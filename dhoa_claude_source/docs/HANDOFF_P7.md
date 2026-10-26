# HANDOFF P7 - Delight, trust and states (DONE)

## What changed
- `app/trust.py` (new, pure): `contact_settings`, `contact_footer_html`, `steps_html`, `facts_html`, `state_html`, `skeleton_html`, `team_names`, `methodology_url`.
- `config/dashboard.yaml`: `contact.hotline_number/hotline_verified/website`, `about.team/methodology_url`.
- `app/streamlit_app.py`: favicon via `set_page_config(page_icon=...)`; `_contact()`; footer and sidebar contact line follow the flag; `render_about(gdf)` rebuilt; Overview "How it works" expander; skeleton placeholder in `main()` while data loads; error/empty cards with retry (`dhoa_retry_data_load`, `dhoa_retry_missing_data`, `dhoa_retry_map`, `dhoa_retry_render`); `community_alert_pdf` passes the verified hotline.
- `src/eval/pdf_kit.py` / `generate_community_report.py`: `do_1` now takes `{hotline}`; new `do_1_web` when unverified; `hotline=` kwarg.
- `app/styles.py`: panels, state cards, skeleton shimmer, fade-in (all token based).
- `app/static/favicon.png` (generated: kiln + smoke on dark tile).
- `app/strings_en.py` / `strings_bn.py`: 30 new strings (HOTLINE_LINE_FMT, DOE_WEB_LINE, FOOTER_WEB_LABEL, CONTACT_CALL/SMS, HOW_*, ABOUT_*, STATE_*, LIST_ARIA_*).

## Decisions (please confirm)
1. Unverified hotline = number hidden everywhere (UI + PDF), website only. This changes what users saw before (16131 was visible). To show it: set `hotline_verified: true` after you have called the number.
2. Team list is empty and the About page omits the row until you add real names (no invented names).
3. Sources named only as Sentinel-2 and OpenStreetMap (both named in docs/screening_provenance.md and the existing About text). Methodology link points to docs/screening_provenance.md on the repo main branch: confirm the URL is public.
4. Old string `DEPARTMENT_OF_ENVIRONMENT_HOTLINE_16131_` left in the catalogues, unused.

## Verify
`pytest tests/test_trust_p7.py tests/test_views_m8.py tests/test_pdf_p6.py tests/test_strings_i18n.py` (AppTests use synthetic data). Then run the app, open About in both languages, and throttle the network to see the skeleton.

## Toggle bugs noticed
None new.

## NOT verified
Real browser (no Chromium): skeleton appearance, fade-in, expander layout, favicon in the tab, screenshots. Real parquet. `tools/benchmark_dashboard.py` was not re-run (needs the real data): please run it before/after.

## Owner hand-checks
Bangla wording of the 30 new strings; the four decisions above; methodology URL.

## First step for next agent (P9)
Read HANDOFF_P7/P8, run `pytest`, `tools/check_widths.py` against a running app, then script the 3-minute demo path.
