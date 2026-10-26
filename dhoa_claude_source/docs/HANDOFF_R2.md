# HANDOFF R2 — Wording cleanup

## Changes
- Public-facing wording no longer says "Inspector view" / "Community view" / "পরিদর্শক ভিউ" / "কমিউনিটি ভিউ".
- `app/strings_en.py`, `app/strings_bn.py` (values only; key names unchanged, see Decisions):
  - `HELP_INSPECTOR` heading -> "Using the Map" / "মানচিত্র কীভাবে ব্যবহার করবেন".
  - `HELP_COMMUNITY` heading -> "Using Near me" / "“আমার কাছে” কীভাবে ব্যবহার করবেন".
  - `VIEW_INSPECTOR` / `VIEW_COMMUNITY` (not used by any code) -> "Map" / "Near me" (bn: মানচিত্র / আমার কাছে), matching `NAV_MAP` / `NAV_NEAR_ME`.
  - `VOICE_INSPECTOR_SCRIPT`: "Welcome to the Inspector view." -> "Welcome to the Map page." (bn: "মানচিত্র পাতায় আপনি সব ইটভাটার প্রার্থী…"). Rest of both scripts unchanged. `VOICE_COMMUNITY_SCRIPT` had no role word and is unchanged.
  - `REPORT_COMMUNITY_NOTE`: "community awareness" -> "general awareness" (bn: সাধারণ সচেতনতা).
  - `DOWNLOAD_COMMUNITY_CSV`: "Download community list" -> "Download list" (bn: তালিকা ডাউনলোড করুন).
  - Section comments in the catalogues renamed (no behaviour).
- `app/voice_scripts.py`: fallback copy of the Map script updated to the identical new text (a test now enforces parity).
- `src/eval/pdf_kit.py`: the downloaded Near me PDF said "Community Report" and "community awareness". Now "Near Me Report" / "আমার কাছে প্রতিবেদন" and "general awareness".
- `app/streamlit_app.py`: download file names `dhoa_community_report.pdf` -> `dhoa_near_me_report.pdf`, `dhoa_community_candidates.csv` -> `dhoa_near_me_candidates.csv` (people see these). Nothing else in that file changed.
- Voice audio: `guide_inspector_bn.mp3` and `guide_inspector_en.mp3` were rendered from the old script (they say "Inspector view" aloud). The app already refuses audio whose hash does not match, so they were never going to play; they are deleted and removed from `manifest.json`. The Map page guide now uses the browser "Read aloud" voice plus the written text until re-rendered. The community mp3s are still valid (script unchanged).
- `tests/test_voice_p10.py`: `test_committed_audio_if_any_matches_current_scripts` now skips a view/language whose mp3 is not on disk (it still fails if a file exists with a stale hash).
- Docs: `README.md` (dashboard paragraph: "Map" / "Near me"), `docs/DASHBOARD_GUIDE.md` ("Near me search and report" section).
- New `tests/test_wording_r2.py` (7 tests): no catalogue value (bn + en) contains inspector/community/পরিদর্শক/কমিউনিটি except `ROLE_INSPECTOR`; PDF labels clean; voice fallback == catalogue; README/guide clean; download names clean.

## How to verify
1. `pytest tests/test_wording_r2.py tests/test_voice_p10.py tests/test_strings_i18n.py`
2. Run the app in both languages. Open "How to use" on Map and on Near me: headings read "Using the Map" / "Using Near me". Download the Near me PDF: title "Near Me Report", note says "general awareness". File names start `dhoa_near_me_`.
3. Optional: `grep -ril "inspector\|community" app/strings_en.py` shows only key names and `ROLE_INSPECTOR` (the chip shown after staff sign-in, which is allowed).

## Decisions
- Kept key names (`HELP_INSPECTOR`, `VOICE_COMMUNITY_SCRIPT`, `view == "community"`, ...) because the brief says to keep internal view-mode values, `tools/*` and tests reference them, and R3 replaces the two views anyway. Only text people read changed.
- `ROLE_INSPECTOR` ("Inspector"/"পরিদর্শক") stays: it appears only after sign-in, where "staff" wording is allowed.
- Did not rename `generate_community_report.py` or the `community_title` PDF label keys (internal).

## New strings
None added. 8 values changed in each catalogue plus 2 PDF label values per language.

## Toggle bugs noticed
- None new in this module.

## NOT verified
- Full pytest suite and a real browser run (Playwright/Chromium, 1280/484/360 px screenshots): this sandbox has no pytest, Streamlit, fpdf or network. I ran the new tests, `test_strings_i18n` (3 tests) and the non-Streamlit voice tests through a small stand-in runner: they pass. Streamlit AppTest-based tests (rest of `test_voice_p10`, layout, views, etc.) were not run. The original code gives the same result under that runner, so it is the environment, not this change.
- PDF text was changed in the label table only; I did not generate a PDF to look at it.
- Bangla wording is new copy and needs native review (see below).

## Owner hand-checks
- Run `pytest` locally and click through both languages once.
- Read the new Bangla: "মানচিত্র কীভাবে ব্যবহার করবেন", "“আমার কাছে” কীভাবে ব্যবহার করবেন", "মানচিত্র পাতায় আপনি…", "সাধারণ সচেতনতার জন্য", "আমার কাছে প্রতিবেদন".
- Re-render the Map voice guide when convenient: `pip install edge-tts` then `python tools/generate_voice_guides.py` (restores the recorded voice for the Map page; not required for the app to work).
- Developer docs still mention the old names and were left alone (not user-facing): `docs/QA_CHECKLIST.md`, `docs/slide_outline.md`, `docs/screenshots_needed.md`, `docs/P0_AUDIT.md`, `docs/ARCHITECTURE.md`. Worth updating in R7 (slide_outline and screenshots_needed feed the pitch).

## First step for next module (R3)
Merge Map and Near me into one screen. State to reuse: `community_place_key`, `community_origin`, `community_radius_m`, `_render_community_inputs`, `_render_community_results`, `render_community_view`, and `hero.VIEW_MODES` (`overview, inspector, community, about`). Note `tools/patch_voice_guide.py` looks for the line `st.markdown(T.HELP_COMMUNITY ...)`; if R3 changes that line, that one-off patcher stops matching (the voice guide is already patched in, so it is not needed again).
