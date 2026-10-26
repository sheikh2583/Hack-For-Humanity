# Handoff — S3: Kilns near me

Date: 2026-10-26

## Changes

- Replaced the compact results dataframe with individual public candidate cards showing kiln type, nearest place, distance when the search has a radius, and a directions link.
- Rendered the map column before the result-list column so narrow layouts encounter the map first.
- Applied the same neutral colour to public marker clusters and kiln markers.
- Added the two card labels to both Bangla and English catalogues.
- Kept the existing public-frame route, location/geocoder/voice controls, radius chips, neutral marker payload, search point/radius overlay, and allowlisted community PDF input. The PDF allowlist and report layout contain no priority column.

## How to verify

- Focused tests: `tests/test_s3_near_me.py`, `tests/test_community_p5.py`, `tests/test_map_stability.py`, `tests/test_strings_i18n.py`, and `tests/test_pdf_p6.py` — 34 passed.
- Browser: Playwright + Chromium, live Streamlit app, Savar search in Bangla and English at 1280, 484, and 360 px. Directions appeared, priority wording was absent from rendered public text, and no horizontal overflow was detected.
- Screenshots: `docs/screenshots/s3/{bn,en}_{1280,484,360}.png` (captured at the result panel in the live app).
- Performance spot check: selecting Savar through all 143 cards took 0.498 s; rendered public map HTML was 11,899 bytes.

## Decisions

- Used Streamlit link buttons for directions to provide a full-width touch target.
- Kept distance hidden for whole-upazila/district results, where there is no radius search.
- The checkout has no earlier `docs/HANDOFF_*.md`; this handoff is the first module handoff found here.

## New strings

- `C_CARD_DISTANCE_FMT`
- `C_CARD_PLACE_FMT`

Both are present in `app/strings_bn.py` and `app/strings_en.py`.

## Toggle bugs noticed

- None while working on S3. Module L remains skipped as requested.

## Not verified

- Did not run the full pytest suite. The first combined attempt also exposed existing S2 public Overview test failures in `tests/test_public_split_s2.py` (generic high-band CSS string remains in the captured public render, and the district-view capture contains a priority label). These are outside this S3 change and should be rechecked by the owner.
- The 0.498 s latency and 11,899-byte payload are one Savar spot check, not a broad performance sweep. Did not run a real-browser pan/zoom rerun check; existing structural map-stability tests passed.
- Did not verify community PDF appearance in a PDF viewer; generation tests pass in both languages.
- Did not inspect voice playback or geolocation permission behavior.

## Owner hand-checks

- Review the six responsive screenshots, especially the map-before-cards order at 484 and 360 px and the touch size of the directions buttons.
- Review the two S2 failures before treating the public-source separation as fully verified.
- Confirm card copy and nearest-place choice with a Bangla reviewer.

## First step for S4

Flag the ephemeral-storage concern before implementing public reports. Agree on SQLite (`data/app.db`, git-ignored) as the initial storage adapter; start without seeded records.
