# Claude handoff - updated 2026-10-18

Use this note with `kilnwatch_bd_share.zip` when continuing Dhoa dashboard and hosting work.

## Current status

The user reported that the map UI was difficult to read, the markers and radius were unclear, and the community report was not easy to find. The local Community View has since been updated:

- A user-adjustable search radius is available from 250 m to 5,000 m in 250 m steps, defaulting to 1,000 m.
- Candidate count, result table, map circle, and community PDF use the selected radius.
- The map shows a blue search pin and a blue radius outline. Red, orange, and green candidate markers indicate high, medium, and low priority. The help popover now describes these markers and radius behavior.
- The community report download is shown with the results above the table. The sidebar's duplicate disabled report button was removed.
- Place-name search takes precedence over coordinate inputs; the form now explains this.
- PDF generation errors are written to the application log.
- `docs/DASHBOARD_GUIDE.md` documents the adjustable radius and community report contents.

The UI and documentation changes are local and uncommitted. Python syntax parsing and `git diff --check` passed. No pytest suite or browser verification was run. Do not claim the report download or rendered UI has been confirmed until manually checked in the app.

## Repository state

- Workspace: `X:\AIUB Hackathon` (Windows PowerShell).
- Branch: `main`, tracking `origin/main`.
- HEAD and `origin/main` were aligned at inspection: `4da36dca5492cd4d5799d636ce14d0f6a6b67532` (`finally`, 2026-10-18).
- Current modified files: `app/streamlit_app.py`, `docs/DASHBOARD_GUIDE.md`.
- The project has a configured Git remote. Confirm the current remote before any push or deployment work.
- `data/processed/kilns_prioritised.parquet` is tracked. The 118.96 MB `data/raw/boundaries/geoBoundaries_BGD_ADM3.geojson` is ignored and untracked to avoid GitHub's 100 MB file limit.

## Hosting diagnosis

The hosted URL and actual hosting provider have not been supplied. `docs/DEPLOYMENT.md` documents Streamlit Community Cloud as the recommended route and names `app/streamlit_app.py` as the entrypoint, but this does not prove which host, repository, branch, or commit the user's deployed app uses.

Before diagnosing hosted staleness, obtain or inspect the deployed URL and identify its provider. Compare its repository, branch, entrypoint, deployed commit, build/runtime logs, and data source with the local project. Do not claim the host is fixed without checking the deployed URL and revision. Do not modify or redeploy an external app until the target is known. For Streamlit Community Cloud, check the app settings and latest deployment logs; expected entrypoint is `app/streamlit_app.py`, with the repository root as working directory. The app reads `data/processed/kilns_prioritised.parquet`.

## Project instructions

Read `AGENTS.md` before editing. Key requirements:

- Never invent schemas, legal thresholds, or coordinates; legal values are sourced from `config/rules.yaml`.
- Keep geometries in EPSG:4326 and do distance/area calculations in EPSG:9680 with the configured UTM fallback.
- Keep GPU workloads user-managed. Do not run training, inference, benchmarks, smoke tests, or other GPU work unless the user specifically requests it.
- Never display developer-facing advisory, verification, preprocessing, or legal-status wording in the UI. Keep it in docs/logs.
- At task end, report what could not be verified and what the user should check by hand.
- Do not add or run tests unless the user asks.

## Next actions

1. Ask the user to check the Community View help popover, radius slider, map legend, and community report download in the browser.
2. If the report still fails, inspect the application log entry added at the PDF generation boundary and fix the concrete failure.
3. Continue the hosting diagnosis only after the hosted URL/provider is known. Verify deployment revision before reporting status.
4. Preserve the current local changes unless the user asks to commit or discard them. No commit, push, or redeploy has been requested.

The share ZIP omits credentials, model weights, datasets, rasters, and GeoParquet files. Deployment account settings and runtime logs may require the user's access.
