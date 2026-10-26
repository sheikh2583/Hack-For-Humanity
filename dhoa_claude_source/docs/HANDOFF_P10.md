# HANDOFF P10 - Voice guide (DONE in code; mp3 files still to render)

## What changed
- `app/voice.py` (new, pure): `script_hash`, `audio_name`, `current_audio` (mp3 used only if `app/static/audio/manifest.json` has the hash of the CURRENT script), `speech_html` (browser read-aloud button).
- `app/components/voice_guide/index.html` (new): one-way custom component (same protocol as `geolocate`) with the browser "Read aloud" button. Replaced an earlier `components.html`/`st.iframe` version that rendered blank for the owner.
- `app/streamlit_app.py`: `render_voice_guide(view, where, transcript=False)`; shown ONLY inside the "How to use" popover of BOTH views, under the written guide (owner preference: not directly on the page). If `app/components/voice_guide/` is missing it shows a text message instead of a blank box. Never raises. `?debug=1` shows tracebacks in the error card.
- `app/strings_en.py` / `strings_bn.py`: `VOICE_INSPECTOR_SCRIPT`, `VOICE_COMMUNITY_SCRIPT`, `VOICE_READ_ALOUD`, `VOICE_STOP`, `VOICE_NO_VOICE`, `VOICE_TRANSCRIPT`.
- `tools/generate_voice_guides.py` (new): renders 4 mp3 with edge-tts neural voices (bn-BD-NabanitaNeural, en-IN-NeerjaNeural) and writes the manifest.
- `tests/test_voice_p10.py` (new).

## Why both views
Community = citizens, possibly low literacy or on phones: audio helps most. Inspector = officials/judges: a ~1 minute spoken tour helps first-time users and the demo. Different scripts, same player, same place (How to use). Not added to Overview/About (no task to explain).

## Owner steps
1. `pip install edge-tts`, then `python tools/generate_voice_guides.py` (internet needed). Listen to all four files (Bangla pronunciation of ধোঁয়া, ফিল্টার, হিটম্যাপ).
2. Commit `app/static/audio/*.mp3` and `manifest.json`.
3. Native-speaker review of both Bangla scripts. If you edit any script, re-run the generator; stale audio is ignored automatically (fallback button shows instead).
4. Until the mp3 files exist, the guide shows a browser "Read aloud" button; many desktop browsers have no Bangla voice, then it shows a short message.

## NOT verified
Real browser playback, Bangla voices, popover layout on 360 px, iframe height (96 px), file size on Streamlit Cloud. No mp3 rendered here (TTS endpoints unreachable from the build sandbox).

## Toggle bugs noticed
Audio follows the active language at render time; not tested across live toggles.


## UPDATE (after owner testing)
- The browser read-aloud component rendered blank in the owner's environment and is no longer used by the UI (`app/components/voice_guide/` is left in the repo, unused).
- The voice section now appears ONLY when a pre-rendered mp3 matching the current script exists; otherwise nothing is shown. So the voice feature is invisible until `python tools/generate_voice_guides.py` has been run and `app/static/audio/*.mp3` + `manifest.json` are committed.
- Work in progress (not delivered): rendering the four mp3 files inside the build sandbox with an offline Bangla VITS model (Coqui, Apache-2.0). Not finished; the generator script remains the supported path.
