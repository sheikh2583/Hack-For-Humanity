# M9 — Deploy and demo hardening: handoff

## CHANGELOG (M9)
- `requirements.txt`: UI stack pinned to the versions in your brief (streamlit 1.66.x, streamlit-folium 0.27.4, folium 0.20.x); no GPU packages. `tools/freeze_deploy_requirements.py` writes an exact `requirements.lock.txt` from the environment you verified.
- `tools/measure_memory.py`: RSS after import / data load / Community search.
- Keep-warm: `tools/keep_warm.py` (Playwright opens the app, clicks the wake button if asleep) + `.github/workflows/keep_warm.yml` (every 8 h, secret `DHOA_APP_URL`). A plain HTTP ping does not wake or keep an app awake.
- `docs/DEPLOY.md` (checklist, cold-start advice, demo-day fallbacks, how to record the backup video), `docs/DEMO_SCRIPT.md` (3 min, timed table + rehearsal checklist), `CHANGELOG.md` (one section per module), README: dashboard section rewritten and a dev-commands block added.
- `tests/test_deploy_m9.py` (5 tests: pins, no GPU deps, workflow file, demo timeline sums to 180 s, no secrets).

## Checks run
- Syntax parse of all new Python, YAML load of the workflow, demo timeline arithmetic (adds up to 3:00), and `freeze_deploy_requirements.py` ran in my sandbox (it only had 8 of the packages, so I deleted its output). Nothing else executed; no network.

## NOT verified / owner must check by hand
1. **Memory on Community Cloud**: I could not measure it. Run `tools/measure_memory.py` locally, then check *Manage app* after deploy against Cloud's current limit.
2. **Lock file**: generate `requirements.lock.txt` yourself in your tested venv (my sandbox has different versions, e.g. pandas 3.0.2 / numpy 2.4.4 here). Decide whether Cloud should use the lock file (rename it to `requirements.txt` for exact rebuilds).
3. **Is the data committed?** The Cloud app needs `data/processed/kilns_prioritised.parquet` in the repo; I could not see your repo, only the zip. Also `static/`/`app/static` fonts must be committed.
4. **Keep-warm**: not run. Confirm Cloud's current sleep rule, add the `DHOA_APP_URL` secret, run the workflow once manually, and check its logs. The button text "Yes, get this app back up" is from memory and may differ.
5. **Backup video**: not recorded (I can't). Record it from `docs/DEMO_SCRIPT.md`, desktop and phone size.
6. **Demo script**: the Bangla button names and the "named place with an empty 1 km result" need picking on the real data; time it on stage.
7. Python version: choose 3.11 or 3.12 in Cloud settings.
8. `CHANGELOG.md` has one-line entries for M0-M3 (from the brief, no detail); paste your earlier handoffs there if you want them complete.
9. Nothing pushed to GitHub.

## Final owner to-do across all modules
Run `pytest -q`; check the Bangla copy with a native speaker (M4-M6 blocks); decide the law expander and verify hotline 16131 (M6); check GPS on https (M5); browse at 360/412/768/1280 px (`docs/QA_CHECKLIST.md`); assemble the before/after benchmark table with `tools/benchmark_dashboard.py` on the M0 commit and now.
