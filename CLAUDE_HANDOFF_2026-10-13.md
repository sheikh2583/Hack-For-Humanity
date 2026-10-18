# Claude handoff — 2026-10-13

Copy this note and upload `kilnwatch_bd_share.zip` to Claude to continue the
Dhoa dashboard and hosting work.

## Current request

The user reports that the hosted link does not reflect the latest local
changes. Diagnose the deployment source and build once the hosted URL and
hosting platform are available. Do not assume the host, repository, branch, or
entrypoint. The user has not supplied the hosted URL yet.

## Repository state

- Workspace: `X:\AIUB Hackathon` (Windows PowerShell).
- Git remote: `github.com:sheikh2583/Hack-For-Humanity.git`.
- Branch: `main`.
- Latest pushed commit: `9dc8139514429290f75f2561808f4f3536f44955`
  (`user facing`). At handoff creation the working tree is clean.
- The latest commit includes the updated Streamlit dashboard, startup changes,
  priority parquet update, OSM place enrichment, and presentation tests.
- `data/processed/kilns_prioritised.parquet` is tracked in Git and is part of
  the latest commit. The local 118.96 MB
  `data/raw/boundaries/geoBoundaries_BGD_ADM3.geojson` remains on disk but is
  ignored and untracked to avoid GitHub's 100 MB file limit.
- The previous push was rejected because ADM3 GeoJSON exceeded that limit. It
  was removed from the commit and the corrected commit was pushed successfully.

## Hosting diagnosis

`docs/DEPLOYMENT.md` documents Streamlit Community Cloud as the recommended
public hosting route and gives `app/streamlit_app.py` as the entrypoint, but
the repo itself does not identify the user's actual deployed app, host, or
selected deployment branch. GitHub `main` is current; this alone does not prove
the hosted app is connected to it or has rebuilt successfully.

Ask for or inspect the hosted URL and identify its provider. Then compare the
deployment's repository, branch, entrypoint, and deployed commit with the
commit above. Inspect build/runtime logs and the data source if needed. Do not
change or redeploy an external app until its target is known. If this is
Streamlit Community Cloud, check its app settings and latest deployment logs;
the expected entrypoint is `app/streamlit_app.py` and the repo root must be the
working directory. The app reads the committed prioritized parquet at
`data/processed/kilns_prioritised.parquet`.

## Project instructions

Read `AGENTS.md` before editing. Key requirements:

- Never invent schemas, legal thresholds, or coordinates; legal values are
  sourced from `config/rules.yaml`.
- Keep geometries in EPSG:4326 and do distance/area calculations in EPSG:9680
  with the configured UTM fallback.
- Keep GPU workloads user-managed. Do not run training, inference, benchmarks,
  smoke tests, or other GPU work unless the user specifically requests it.
- Never display developer-facing advisory, verification, preprocessing, or
  legal-status wording in the UI. Keep it in docs/logs.
- At task end, report what could not be verified and what the user should check
  by hand.

## Review scope

Review the source and current dashboard behavior in the ZIP. For the hosted
staleness issue, determine what evidence is needed to distinguish a wrong
deployment target from a failed or delayed build, stale runtime data, browser
cache, or another cause. Clearly separate verified facts from hypotheses.
Do not claim the host is fixed without checking the hosted URL and deployment
revision. Do not run GPU workloads.

The ZIP excludes credentials, model weights, datasets, rasters, and GeoParquet
files. Source review is possible, but deployment account settings and runtime
logs may require access from the user.
