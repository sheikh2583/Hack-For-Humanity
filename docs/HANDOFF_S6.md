# Handoff — S6: Inspector staff tools

Date: 2026-10-26

## Changes

- Added `saved_filters`, scoped by the signed-in display name and filter name. The snapshot stores the existing Inspector filter values (district, upazila, priority bands, and kiln type). Saved filters can be updated, applied to the Map, or deleted.
- Added an append-only `activity_log` with actor, action, target, details, and timestamp. Visit status/assignment updates, notes, visit photos, saved filter changes, and report status changes add entries; the Work section shows recent activity.
- Added optional JPEG, PNG, or WebP visit photo storage beside the SQLite database, with database-relative references and a staff-only display in Map detail.
- Added Google Maps multi-stop links for the current My visit list order. The first listed kiln is the first route origin; each link covers up to five stops and subsequent links reuse the prior segment’s last stop so no assigned point is dropped. Google Maps chooses road directions; the app does not calculate or optimize a route.
- Kept the existing filtered CSV and selected-kiln PDF controls on the Inspector Map path. Added new labels in Bangla and English.
- No fake records were added to the repository database. Browser verification used synthetic GeoParquet and a temporary SQLite database under `X:\temp\dhoa_s6_browser`.

## Verification

- Focused tests: storage, route helpers, translation parity, public split checks, and the S6 staff/public AppTest — 36 passed; two previously known S2 Overview tests were not rerun.
- AppTest created seven synthetic assignments and confirmed ordered multi-link routes. A public Inspector Portal session did not show saved filters, activity, visit-photo controls, CSV, or PDF exports.
- Real browser: opened the app on temporary synthetic data, used the temporary demo sign-in, switched to English, opened Work, saved a named filter, and applied it to return to Map.
- `python -m compileall -q app/storage.py app/staff_tools.py app/streamlit_app.py` and `git diff --check` passed.
- No training, inference, benchmark, or GPU workload was run.

## Decisions

- Filter snapshots store only current canonical UI filters and are private to the exact display-name string supplied at sign-in.
- Google Maps URL documentation allows up to three waypoints on mobile browsers and up to nine on other platforms. Five total kiln stops per link (origin, up to three waypoints, destination) work across those limits. Links preserve the displayed Work-list order and do not request stop optimization. Source: [Google Maps URLs documentation](https://developers.google.com/maps/documentation/urls/get-started).
- Activity details store status/assignment transitions as JSON; note contents are not copied into the activity log. The note itself remains in the existing notes table.

## New strings

Added S6 labels for saved filters, activity events, visit photos, and route links to both `app/strings_en.py` and `app/strings_bn.py`.

## Toggle bugs noticed

- None observed during S6. The previously skipped language-toggle bugs remain untouched.

## Not verified / owner hand-checks

- Did not exercise visit-photo upload and image display in the live browser; SQLite photo reference and bytes are covered with a synthetic storage test. Check the upload control on Map detail using a disposable JPEG/PNG/WebP.
- Did not test the Google Maps links on a mobile browser. Stop grouping follows the current official Maps URLs platform waypoint limits; test with the devices inspectors will use.
- Did not verify persistence on Streamlit Community Cloud. Local SQLite files and sibling photo directories are ephemeral there; configure durable shared storage before relying on cross-restart or multi-instance records.
- Did not run the full test suite or a performance benchmark. The two known S2 Overview tests documented in `HANDOFF_S3.md` were not rechecked.
- Confirm the saved-filter field set and exact display-name ownership fit the inspector workflow.

## Files

- `app/storage.py`
- `app/staff_tools.py`
- `app/streamlit_app.py`
- `app/strings_bn.py`
- `app/strings_en.py`
- `tests/test_storage_s4.py`
- `tests/test_staff_tools_s6.py`
- `tests/test_public_split_s2.py`
- `CHANGELOG.md`
- `docs/HANDOFF_S6.md`

## First step for S7

Use the existing public data date and report-storage behavior to add accurate Data as of and Methods text, then finish accessibility and the short demo path without inventing data coverage, legal thresholds, or example records.

## Suggested commit command

```powershell
git add -- CHANGELOG.md app/storage.py app/staff_tools.py app/streamlit_app.py app/strings_bn.py app/strings_en.py tests/test_storage_s4.py tests/test_staff_tools_s6.py tests/test_public_split_s2.py docs/HANDOFF_S6.md
git commit -m "Complete S6 inspector staff tools"
```
