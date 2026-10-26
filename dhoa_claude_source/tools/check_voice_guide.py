"""Find out exactly why the voice guide is (not) showing. Run from the repo root:

    python tools/check_voice_guide.py

Checks, in order: which app file is used and whether it has the voice code; the four mp3 files and
whether each matches the CURRENT script text (a one-word edit makes the audio "stale" and the old
code then hides the guide silently); the component folder; and finally it runs the real app headlessly
(Streamlit AppTest) for both views and both languages and reports what the popover really contains.
Paste the whole output when asking for help.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(APP))
MARKER = "DHOA-VOICE-GUIDE v3"
problems: list[str] = []


def line(status: str, text: str) -> None:
    print(f"  [{status:^7}] {text}")


def bad(text: str, fix: str) -> None:
    problems.append(f"{text}\n      -> {fix}")
    line("PROBLEM", text)


print(f"Repo: {ROOT}\nPython: {sys.version.split()[0]}")
try:
    import streamlit

    print(f"Streamlit: {streamlit.__version__}")
except Exception as exc:  # noqa: BLE001
    print(f"Streamlit: NOT IMPORTABLE ({exc})")

# 1. the app file ---------------------------------------------------------------------------------
print("\n1. App file")
app_file = APP / "streamlit_app.py"
source = app_file.read_text(encoding="utf-8", errors="replace") if app_file.is_file() else ""
if not source:
    bad(f"{app_file} not found", "run this from the repository root")
else:
    line("info", f"{app_file.relative_to(ROOT)}  {len(source.encode('utf-8')):,} bytes")
    if MARKER in source:
        line("OK", "has the fixed voice guide (always shows heading + transcript, shows problems)")
    else:
        bad(
            "streamlit_app.py does NOT have the fixed voice guide: with the old code, stale or missing audio hides the guide completely",
            "python tools/patch_voice_guide.py   (edits only the voice function; keeps your other changes)",
        )
    for needle, label in (("import voice", "import voice"), ("_voice_player = components.declare_component", "voice component declared"), ("render_voice_guide(selected_mode", "guide called under the help text")):
        if needle in source:
            line("OK", label)
        else:
            bad(f"missing in streamlit_app.py: {label}", "python tools/patch_voice_guide.py")

# 2. scripts + audio -------------------------------------------------------------------------------
print("\n2. Audio files vs the CURRENT script text")
try:
    voice = importlib.import_module("voice")
    audio_dir = voice.AUDIO_DIR
except Exception as exc:  # noqa: BLE001
    voice = None
    bad(f"app/voice.py cannot be imported: {exc}", "restore app/voice.py from the repository")
if voice is not None:
    line("info", f"audio folder: {audio_dir}  (exists: {audio_dir.is_dir()})")
    if not (audio_dir / voice.MANIFEST).is_file():
        bad("manifest.json is missing", "copy app/static/audio/ from the fix, or run tools/generate_voice_guides.py")
    stale_any = False
    for lang in voice.LANGUAGES:
        catalogue = importlib.import_module(f"strings_{lang}")
        for view, name in (("inspector", "VOICE_INSPECTOR_SCRIPT"), ("community", "VOICE_COMMUNITY_SCRIPT")):
            script = getattr(catalogue, name, None)
            mp3 = audio_dir / voice.audio_name(view, lang)
            tag = f"{view}/{lang}"
            if script is None:
                bad(f"{tag}: strings_{lang}.py has no {name}", "restore the VOICE_* texts in app/strings_*.py")
            elif not mp3.is_file():
                bad(f"{tag}: {mp3.name} is missing", "copy the mp3 files into app/static/audio/")
            elif voice.current_audio(view, lang, script) is None:
                stale_any = True
                bad(f"{tag}: {mp3.name} exists but was made from DIFFERENT text than the script now in strings_{lang}.py (stale)", "see the fix below")
            else:
                line("OK", f"{tag}: {mp3.name} {mp3.stat().st_size:,} bytes, matches the script")
    if stale_any:
        problems.append(
            "FIX for stale audio: re-render from the current text. Easiest (internet needed, neural voice):\n"
            "         pip install edge-tts\n"
            "         python tools/generate_voice_guides.py\n"
            "      then restart Streamlit. Repeat this after every edit of a VOICE_*_SCRIPT."
        )
    component = (voice.COMPONENT_DIR / "index.html")
    line("OK" if component.is_file() else "PROBLEM", f"browser read-aloud component: {component.relative_to(ROOT) if component.is_file() else 'MISSING'}")

# 3. the real app, headless -------------------------------------------------------------------------
print("\n3. What the real app shows in the 'How to use' popover (headless run)")
try:
    from streamlit.testing.v1 import AppTest

    data_dir = os.environ.get("DHOA_DATA_DIR")
    note = "your data"
    if not data_dir and not (ROOT / "data" / "processed" / "kilns_prioritised.parquet").is_file():
        import tempfile

        from tests.synthetic import write_parquet

        tmp = Path(tempfile.mkdtemp())
        write_parquet(tmp)
        os.environ["DHOA_DATA_DIR"] = str(tmp)
        note = "synthetic test data (your data file was not found)"
    line("info", f"using {note}")
    for lang in ("bn", "en"):
        catalogue = importlib.import_module(f"strings_{lang}")
        for view in ("inspector", "community"):
            at = AppTest.from_file(str(app_file), default_timeout=180)
            at.session_state["dhoa_view_mode"] = view
            at.session_state["dhoa_lang"] = lang
            at.run()
            heading = any(m.value == f"**{catalogue.LISTEN_TO_THE_GUIDE}**" for m in at.markdown)
            players = len(at.get("audio"))
            unavailable = [c.value for c in at.caption if "Voice guide unavailable" in c.value]
            errors = [e.value for e in at.exception]
            tag = f"{view}/{lang}"
            if errors:
                bad(f"{tag}: the app raised: {errors[0][:200]}", "send this output")
            elif unavailable:
                bad(f"{tag}: the guide hit an error: {unavailable[0]}", "open the app with ?debug=1 for the message, and send it")
            elif not heading:
                bad(f"{tag}: the popover has NO voice section", "python tools/patch_voice_guide.py, then restart Streamlit")
            elif players:
                line("OK", f"{tag}: heading + audio player + transcript")
            else:
                line("WARN", f"{tag}: heading + browser read-aloud + transcript, but no mp3 player (audio missing or stale, see step 2)")
except Exception as exc:  # noqa: BLE001
    line("SKIPPED", f"headless run not possible here: {type(exc).__name__}: {exc}")

print("\n" + "=" * 70)
if problems:
    print(f"{len([p for p in problems if not p.startswith('FIX')])} problem(s) found:\n")
    for item in problems:
        print(" *", item)
    sys.exit(1)
print("Everything is in place. After restarting Streamlit, open  How to use  in the Map or Near me view.")
