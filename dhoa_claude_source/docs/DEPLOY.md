# Deploy and demo hardening (M9)

## Before deploying (once)
1. In your verified environment: `pytest -q`, then `python tools/freeze_deploy_requirements.py` and commit `requirements.lock.txt` (exact versions for rebuilds). `requirements.txt` already pins Streamlit 1.66.x, streamlit-folium 0.27.4 and folium 0.20.x.
2. **Data must be in the repo or the app shows its "data missing" page.** `data/processed/kilns_prioritised.parquet` (~2,150 rows) must be committed (check `.gitignore` and the file size). The app never generates data.
3. `python tools/measure_memory.py` on the real data and compare with the memory limit in Streamlit Community Cloud's current docs; after deploying, watch the live figure under *Manage app*.
4. Python version: set 3.11 or 3.12 in the Cloud app's Advanced settings (the project supports both).
5. Secrets: none are required. Do not commit API keys.

## Cold start and sleeping apps
- Community Cloud puts idle apps to sleep; the first visitor then waits for a cold start. A plain ping does **not** keep the app awake.
- `.github/workflows/keep_warm.yml` + `tools/keep_warm.py` visit the app in headless Chromium every 8 h (secret `DHOA_APP_URL`). Run it manually (*Actions -> keep-warm -> Run workflow*) once to confirm it works. Whether this is enough depends on Cloud's current idle rule; confirm in its docs.
- **For the demo**: open the app yourself 30 minutes before, click through both views once (warms caches: data, places, geocoder), and keep that tab open.

## Demo-day risks and fallbacks
| Risk | Fallback |
|---|---|
| Venue Wi-Fi is slow/blocked | Phone hotspot; local `streamlit run app/streamlit_app.py` on the laptop; the backup video |
| Map tiles do not load | Switch tile layer (street/satellite) from the map control; markers still work |
| GPS denied or on http | Pick a place from the list (the app says so in Bangla) |
| Name search (geocoder) offline | Use the picker; the fallback is optional |
| Cloud app asleep | Open it early; local copy |

## Backup video (record yourself; I cannot record)
Screen-record the 3-minute script in `docs/DEMO_SCRIPT.md` at 1280x720 with voice-over, once on desktop and once phone-sized (DevTools 412 px). Save as MP4 on the laptop, a phone and a USB stick. Re-record after any UI change.
