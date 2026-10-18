# Dhoa Claude handoff — 2026-10-18

Use this note with `claude_minimal_share.zip` for a focused dashboard review.

## Repository state

- Workspace: `X:\AIUB Hackathon`.
- Branch: `main`; inspected HEAD: `0571e01`.
- Local edits: `app/streamlit_app.py` is modified; untracked `uv.lock` is present.
- The ZIP includes the current `app/streamlit_app.py` and `uv.lock`; it does not include datasets, trained weights, rasters, generated run artifacts, credentials, or the virtual environment.

## Current map work

The working-tree changes address Folium rendering stability in the Inspector map. The map is simplified to one `MarkerCluster`; the Inspector map omits its Folium layer control, feature groups, heatmap, and injected map CSS. The sidebar still controls the basemap. The map component uses `width="100%"` and a key derived from the selected district and upazila. The Community map also uses `width="100%"`.

Filtering now preserves candidates when source data lacks priority bands or all bands are unknown, instead of returning an empty set. Review these behavior changes before replacing them with a different map strategy.

## Verification status

- The map call sites and current source were inspected while preparing this handoff.
- No automated tests, GPU workloads, running-app checks, browser checks, or hosted deployment checks were run for this package task.
- Treat hosted behavior and map interaction as unverified. Check Inspector and Community views in the browser, including marker popups, tile selection, and filter changes.

## Project constraints

Read `AGENTS.md` before editing. In particular:

- Do not invent schemas, legal thresholds, or coordinates. Read legal thresholds from `config/rules.yaml`.
- Keep geometry in EPSG:4326 and use the configured projected CRS for distance and area work.
- GPU workloads remain user-managed unless specifically requested.
- Keep developer-facing verification and advisory wording out of the UI.
- Do not run tests unless the user requests them. Report what remains unverified and what needs a manual check.

## Included review files

The ZIP contains the dashboard entry point and its direct helper modules, relevant configuration and rule/CRS/report modules, selected dashboard tests, project instructions, setup guidance, screening provenance, dashboard guide, and `uv.lock`. It is a source-review package; data files needed to run the dashboard are intentionally absent.
