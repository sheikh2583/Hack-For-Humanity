# Handoff — S4: SQLite storage and public reports

Date: 2026-10-26

## Changes

- Added `app/storage.py` with a replaceable `ReportStore` protocol and a SQLite implementation using the reports fields specified in the plan.
- The SQLite store creates its schema on first use and inserts no seed records. Optional JPEG, PNG, or WebP uploads are stored as files beside the database and referenced by a relative `photo_ref`.
- Added `.gitignore` entries for `data/app.db`, its SQLite sidecars, and `data/reports/`.
- Added a candidate-card correction form and a page-level missing-kiln form. Both accept an optional contact field; the missing-kiln form accepts optional coordinates and a photo.
- Coordinate validation derives the accepted extent from the existing public frame. The form has no hard-coded country bounds or default coordinates.
- Added a hidden honeypot, a per-Streamlit-session limit of three successful reports per hour, and a privacy line in Bangla and English.
- Added `DHOA_APP_DB` as a path override so browser verification can use a temporary database.
- Fixed the map selector’s duplicate default/state initialization from the attached Cloud log (`index=None`). Added a script-mode import fallback for `app.storage`.

## How to verify

- Focused tests: `tests/test_storage_s4.py`, `tests/test_s3_near_me.py`, `tests/test_community_m5.py`, `tests/test_community_p5.py`, `tests/test_map_stability.py`, and `tests/test_strings_i18n.py` — 39 passed.
- Playwright + Chromium: opened the candidate correction form, confirmed the honeypot container is not visible, submitted one synthetic report, and read it back after stopping and restarting Streamlit. The database was under the system temporary directory; no record was written to `data/app.db`.
- Playwright confirmed the missing-kiln form exposes latitude, longitude, and photo fields; that form was not submitted in the browser.

## Decisions

- SQLite is the local adapter at `data/app.db`. Streamlit Community Cloud local files are ephemeral, so this adapter alone does not provide durable Cloud storage across rebuilds. Use an external database or service before relying on submitted reports in production.
- The per-session cap is three successful submissions within one hour. It is an application abuse-control setting, not a legal threshold.
- The missing-kiln form accepts typed coordinates. It does not add a separate map-click coordinate picker.
- Photo content types are limited to JPEG, PNG, and WebP; the upload bytes are kept unchanged.

## New strings

`C_REPORT_EXISTING_TITLE`, `C_REPORT_CARD_ACTION`, `C_REPORT_EXISTING_REASON`, `C_REPORT_REASON_LOCATION`, `C_REPORT_REASON_NOT_KILN`, `C_REPORT_REASON_OTHER`, `C_REPORT_NEW_TITLE`, `C_REPORT_LAT`, `C_REPORT_LON`, `C_REPORT_NOTE`, `C_REPORT_CONTACT`, `C_REPORT_PHOTO`, `C_REPORT_SUBMIT`, `C_REPORT_SENT`, `C_REPORT_INVALID_COORDS`, `C_REPORT_COORDS_HELP`, `C_REPORT_NO_EXTENT`, `C_REPORT_RATE_LIMIT`, `C_REPORT_FAILED`, `C_REPORT_PRIVACY`, and `C_REPORT_HONEYPOT` were added in both language catalogues.

## Attached Streamlit log

- The latest fatal message in the supplied log is `ImportError: cannot import name 'storage' from 'app'`. This checkout now contains `app/storage.py` and uses a fallback import for Streamlit script execution. The Cloud app must deploy the revision containing both the import and the new module.
- The logged missing names (`RAIL_HINT`, `C_GPS_DENIED`, `STATE_LOADING`, voice and portal labels, and public-view helpers) exist in this checkout. The logged `community_filter_district` assignment is absent from the current source. Those traces indicate a stale or mixed deployed revision; they were not reproduced locally.
- The deprecation warning for `st.components.v1.html` has no matching call in the current Python source. The missing `app/static` warning also does not match this checkout, which contains that directory.
- The map selector’s default/state warning was relevant to current code and is fixed here.

## Toggle bugs noticed

- None while working on S4. Module L remains skipped as requested.

## Not verified

- Did not run the full test suite. Two existing S2 public Overview tests still fail on high-band CSS and a priority label in captured output, as documented in `HANDOFF_S3.md`.
- Did not submit the missing-kiln form from a browser, upload a real image, or exercise the rate limit interactively. Storage, photo byte handling, and synthetic extent validation have unit coverage.
- Did not verify persistence on Streamlit Community Cloud; its local filesystem is ephemeral.
- Did not verify a map-click origin; coordinate entry is the implemented path.

## Owner hand-checks

- Confirm that SQLite is acceptable for local judging and choose a durable backend before relying on Cloud submissions.
- Review Bangla form wording, the privacy line, and photo upload handling.
- Ensure the Cloud deployment includes `app/storage.py`, `app/strings.py`, both language catalogues, and the updated `streamlit_app.py` from one revision.

## First step for S5

Use `ReportStore.list_reports()` for the inspector inbox and open-report badge, then add the planned visits and notes tables without exposing them to public frames.
