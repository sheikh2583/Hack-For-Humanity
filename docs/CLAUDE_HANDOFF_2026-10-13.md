# Claude handoff - updated 2026-10-18

Use this note with `kilnwatch_bd_share.zip` when continuing Dhoa dashboard and hosting work.

## Current status

The Streamlit Community Cloud logs identify the deployed app as:

- URL: `https://hack-for-humanity-dhtqzvofebzbjrsyunlnmz.streamlit.app/`
- Repository slug: `hack-for-humanity`
- Branch: `main`
- Entrypoint: `app/streamlit_app.py`

The logs show Python 3.14.8 and Streamlit 1.66.0. A `KeyError: 'dashboard_filters'` appeared once during an earlier update/import; later log entries say the app updated. The repeated current crash is `AttributeError: 'NoneType' object has no attribute 'info'` at the loading placeholder line, caused by using `with st.empty() as loading_msg` (the context manager does not bind the placeholder). The local code now uses `loading_msg = st.empty()` and then `loading_msg.info(...)`; it clears the placeholder after each view renders and on error paths.

The local code change is uncommitted. Python syntax parsing and `git diff --check` passed after the fix. No tests or browser verification have been run. The corrected code has not been pushed or confirmed on the hosted app.

Other recent UI work already present in the repo includes an adjustable community radius, a marker legend, a more prominent community report download, updated help text, legal reference expander, revised KPI labels, and coordinate input examples. Keep those changes intact.

## Repository state

- Workspace: `X:\AIUB Hackathon` (Windows PowerShell).
- Branch: `main`, tracking `origin/main`.
- HEAD and `origin/main` were aligned at inspection: `9dab633af70a48f423fcb3b4930a60454d7d8cc0` (`anything goes`, 2026-10-18).
- Current local modifications: `app/streamlit_app.py` (loading placeholder fix) and this handoff note.
- `data/processed/kilns_prioritised.parquet` is tracked. The 118.96 MB `data/raw/boundaries/geoBoundaries_BGD_ADM3.geojson` is ignored and untracked to avoid GitHub's 100 MB file limit.

## Hosting diagnosis

The log confirms Streamlit Community Cloud is running the repository slug `hack-for-humanity`, branch `main`, with entrypoint `app/streamlit_app.py`. The log does not expose the deployed commit SHA, so compare the deployment revision in the Cloud app settings with GitHub `main` before claiming a deployment is current. The app reads `data/processed/kilns_prioritised.parquet`.

After the local loading placeholder fix is reviewed, push it only if the user asks. Then confirm that Streamlit Cloud rebuilds and the hosted URL loads without the `NoneType.info` error. The one-off `dashboard_filters` KeyError is not explained by the excerpt; if it recurs, inspect the full traceback and deployment file tree. The log also notes nonfatal warnings about a missing `app/static` folder and multiple dependency manifests (`requirements.txt` and `pyproject.toml`); Streamlit used `requirements.txt`.

## Project instructions

Read `AGENTS.md` before editing. Key requirements:

- Never invent schemas, legal thresholds, or coordinates; legal values are sourced from `config/rules.yaml`.
- Keep geometries in EPSG:4326 and do distance/area calculations in EPSG:9680 with the configured UTM fallback.
- Keep GPU workloads user-managed. Do not run training, inference, benchmarks, smoke tests, or other GPU work unless the user specifically requests it.
- Never display developer-facing advisory, verification, preprocessing, or legal-status wording in the UI. Keep it in docs/logs.
- At task end, report what could not be verified and what the user should check by hand.
- Do not add or run tests unless the user asks.

## Next actions

1. Review the loading placeholder fix in `app/streamlit_app.py`; the hosted logs show it was the repeated crash.
2. Run syntax parsing and `git diff --check`; do not run tests unless requested.
3. The hosted URL and target are now known, but the deployed commit SHA remains unverified. Do not push or redeploy unless the user asks.
4. After a later authorized push, confirm the Cloud rebuild and manually check the hosted UI, including both views and the community report download.

The share ZIP omits credentials, model weights, datasets, rasters, and GeoParquet files. Deployment account settings and runtime logs may require the user's access.
