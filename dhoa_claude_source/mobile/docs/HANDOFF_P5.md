# HANDOFF P5: community "Near me"

## What changed
Most of the P5 brief already existed from M5, so this module adds one feature and records the audit.
- Already present, unchanged: the three steps (`C_STEP1/2/3`), radius 1/2/5/10 km with default 5 (`cm.RADIUS_CHOICES_M`), whole-area (district/upazila) choices that list every kiln and disable the radius, "Use my location" via the `dhoa_geolocate` component (no reload), cached Bangladesh-restricted geocoding (`_cached_geocode`, `cm.geocode_bangladesh`), empty state naming the nearest kiln with the one-click "Show within N km" button (`_render_community_empty`), help text on the place, GPS, name search and distance inputs.
- New: `cm.example_origin(places)` (pure): Savar in Dhaka if the data has it, else the upazila with most kilns; returned as a point at that upazila's kiln centre (data-derived, no typed coordinates).
- New: `_apply_community_example(gdf)` callback plus a "Try an example" button in step 1 (`key="community_example"`). It sets the origin and the 5 km radius through the canonical keys; the existing `_seed` pattern copies them into the widgets. No `st.rerun`.

## How to verify
1. `pytest tests/test_community_p5.py tests/test_community_m5.py tests/test_strings_i18n.py`. The 5 tests in `test_community_p5.py` passed here with a stand-in runner; the others were not run.
2. Open Near me, press "Try an example": the summary reads "N kilns within 5 km of Savar, Dhaka", the list and map appear, no reload.

## Decisions
- The example is a point (not the Savar upazila choice) because an upazila choice ignores the radius and the brief says "5 km".
- The origin name is stored as plain data text ("Savar, Dhaka"), the same as a geocoded name, so it does not re-translate on a language switch. (Toggle bug, see below.)

## New strings (both catalogues, no fields)
C_EXAMPLE_BUTTON, C_EXAMPLE_HELP. **Need native-speaker review.**

## Toggle bugs noticed
- The example origin name stays English after switching to Bangla (stored text, like geocoded names). Not fixed (Module L).

## NOT verified
- Nothing ran under real Streamlit. Button placement (above the GPS button) and whether the callback's state is picked up before the widgets render are untested.
- The brief's "empty state suggests the nearest kiln" was audited by reading, not by running.
- No screenshots; no benchmark (no data-layer change).

## Owner must check by hand
- Example button with the real data (is Savar in Dhaka present? what does the summary say?).
- That a language switch after the example does not clear the result.
- Bangla copy.

## First step for P6
Read `app/presentation.py`, `community_alert_pdf`, `_report_from_json` and the report generator it calls; find the Bangla font used by fpdf2.
