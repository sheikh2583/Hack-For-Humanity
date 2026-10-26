VOICE GUIDE FIX  (does NOT replace app/streamlit_app.py - it patches your own file in place)

Run these from the repository root (the folder that contains app/ and tools/):

  1. Unzip this package over the repo (it only adds/replaces the files listed below).
  2. python tools/patch_voice_guide.py      <- edits only the voice function in YOUR streamlit_app.py
  3. python tools/check_voice_guide.py      <- tells you exactly what is still wrong, if anything
  4. Restart Streamlit, then hard-refresh the browser (Ctrl+Shift+R).
  5. Open "How to use" in the Map or Near me view.

If step 3 says an mp3 is STALE, the Bangla/English script text in app/strings_*.py differs from the text the
audio was made from. Re-render from your current text:
     pip install edge-tts
     python tools/generate_voice_guides.py
(Repeat after every edit of a VOICE_*_SCRIPT. Until then the guide still shows: heading, browser
 "Read aloud" button, and the written text.)

Files in this package:
  app/components/voice_guide/index.html   browser read-aloud (hardened)
  app/static/audio/*.mp3, manifest.json   pre-rendered guides (offline robotic voice; replace with edge-tts for a natural voice)
  tools/patch_voice_guide.py              in-place patcher        tools/check_voice_guide.py   diagnostic
  tools/generate_voice_guides.py          now also supports --engine espeak
  tests/test_voice_p10.py                 updated tests
