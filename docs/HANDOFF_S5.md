# Handoff — S5: Inspector visits and community report inbox

Date: 2026-10-26

## Changes

- Extended the local SQLite store with `visits(kiln_id,status,assignee,updated_by,updated_at)` and `notes(kiln_id,text,author,created_at)`. Visits keep the current state per kiln; notes are appended and read in insertion order. No records are seeded.
- Added canonical visit statuses: `not_visited`, `assigned`, `visited`, `confirmed_active`, and `not_a_kiln`. Report inbox statuses are `new`, `reviewed`, and `resolved`.
- Added Map detail controls for visit status, assignee, “assign to me,” and note history. Added the staff-only My visit list with status filter, priority or data-derived distance sort, map opening, and directions.
- Added a staff-only community report inbox with status actions, optional uploaded image display, and map navigation to the report location or related kiln. The Reports navigation shows the count of new and reviewed records.
- Added all new display labels in Bangla and English. Public-facing views continue to receive the public data frame; they do not call visit or inbox listing methods.

## Verification

- `python -m pytest tests/test_storage_s4.py -q` — 4 passed, including synthetic persistence of visits, notes, and report handling metadata.
- `python -m pytest tests/test_strings_i18n.py -q` — 4 passed.
- `python -m compileall -q app/storage.py app/streamlit_app.py` — passed.
- `git diff --check` — passed.
- No training, inference, benchmarks, smoke tests, or GPU workloads were run. No records were submitted to the app database.

## Not verified / owner hand-checks

- The staff-only Map, Work, and Reports screens were not exercised in a live browser session. Verify sign-in, assignment, note history, sorting, navigation, report handling, and the bell count with a temporary `DHOA_APP_DB` before deployment.
- SQLite on Streamlit Community Cloud remains ephemeral. Configure durable shared storage before relying on report or visit persistence across rebuilds or multiple app instances.
- “Distance” sorting requires choosing an origin from existing data-derived places because the plan does not define a default staff location. Confirm this interaction fits the inspection workflow.
- Directions open Google Maps using the stored WGS84 coordinates. Check that link behavior is suitable for inspectors’ devices.
- The S2 known failures recorded in `HANDOFF_S3.md` were not rechecked during S5.

## Files

- `app/storage.py`
- `app/streamlit_app.py`
- `app/strings_bn.py`
- `app/strings_en.py`
- `tests/test_storage_s4.py`
- `CHANGELOG.md`
- `docs/HANDOFF_S5.md`
