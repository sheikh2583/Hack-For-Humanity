# Dhoa hosted-app fixes: Claude handoff

This bundle contains the Streamlit app source, the runtime assets/configuration/data it needs, and focused regression tests. It excludes model weights, training datasets, intermediate pipeline outputs, caches, local databases, credentials, and Git history.

## Hosted app

https://hack-for-humanity-dhtqzvofebzbjrsyunlnmz.streamlit.app/?lang=en

## Browser findings (2026-10-27)

I rechecked the live app in a fresh browser session. Overview and About render. Overview reports 2,135 candidates across five districts (data as of 2026-10-26).

### P0: Nearby search page fails on entry

1. From Overview, click **Kilns near me**.
2. The view displays “Something went wrong. This part of the page could not be shown. Your filters are kept. Please try again.” before the place search or location controls render.
3. Click **Try again**; the same error remains.

This was reproducible in a fresh session. Clicking a district (Dhaka, 613 candidates) also navigated into this failed view, so district-to-results navigation is currently unusable. Browser developer console showed no errors; inspect the latest Streamlit Cloud server logs for the exception.

In the previous browser pass, when the page initially rendered, typing “Sav” showed no suggestions; pressing Enter then produced the same generic error. Retest autocomplete after restoring the view. The “Use my location” control previously produced no visible feedback; location permission was not granted, so test success/denied/timeout paths in a controlled browser.

### P1: Inspector Portal unavailable

Opening **Inspector Portal** displays “Staff sign-in is not available right now.” Authentication and staff writes cannot be tested until the hosted sign-in configuration is restored. Do not add public demo credentials or weaken the write-access gate as a workaround.

### Report/export controls to verify after restoring results

The failed view prevents access to the result list, map, and its reporting/download controls. In an earlier pass, clicking the first kiln’s **Report this kiln** control did not reveal a visible form. The missing-kiln form did expand and showed latitude, longitude, note, optional contact, optional photo upload, and submit controls. The report download control was visible, but I could not confirm a file was downloaded. Do not submit test reports to production; use a disposable local/test database for persistence checks.

### Working in the latest pass

- Overview and About loaded.
- District counts were visible.
- Inspector tab opened, but sign-in was unavailable.
- Browser console had no visible error/warning entries; this does not rule out a server-side exception.

## Fix request

1. Inspect current Streamlit Cloud logs and fix the exception that prevents the nearby view from rendering. Ensure both the navigation tab and district shortcuts reach the results page.
2. Restore typed-place suggestions and robust no-match/error handling. Search errors must not blank the results area or break other tabs.
3. Make geolocation success, denied permission, timeout, and unsupported-browser outcomes visible and usable.
4. Verify each kiln report action opens a form associated with the selected kiln. Validate report form behavior using a test database; never create a live production report for testing.
5. Verify report export actually downloads a readable file.
6. Keep Inspector access gated by configured staff authentication. Verify only after Cloud secrets/configuration are available.
7. Add/update regression tests for navigation into the nearby view, search suggestions/selection and unmatched input, geolocation outcomes, kiln-report form opening, and export generation.
8. Confirm the Streamlit Cloud entry point and dependency resolution work from this bundle’s repository root. Do not run training or inference as part of these fixes.

## Local setup

Use Python 3.11 and install the app dependencies from `requirements.txt`. Run the focused tests with `python -m pytest tests/test_s3_near_me.py tests/test_community_p5.py tests/test_community_m5.py tests/test_public_split_s2.py tests/test_deploy_m9.py tests/test_app_startup.py tests/test_dashboard_apptest.py tests/test_storage_s4.py tests/test_strings_i18n.py`.

Start the dashboard from the bundle root with `streamlit run app/streamlit_app.py`. The included `data/processed/kilns_prioritised.parquet` is the app’s required public candidate dataset; the app database is deliberately excluded and is created locally when needed.

## Manual checks still needed

- Current Cloud traceback and whether Cloud has finished rebuilding the newest repository revision.
- Location behavior with browser permission explicitly allowed and denied.
- Actual report persistence and export file contents in a disposable test environment.
- Inspector authentication and write flows after valid Cloud secrets are configured.
- Responsive map/results layout on intended desktop and mobile widths.
