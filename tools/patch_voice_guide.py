"""Patch the voice guide into YOUR app/streamlit_app.py without replacing the file.

    python tools/patch_voice_guide.py                # patches app/streamlit_app.py
    python tools/patch_voice_guide.py path/to/streamlit_app.py

It edits only three small places (and nothing else, so your other changes are kept):
  1. makes sure ``import voice`` is present;
  2. makes sure the ``_voice_player`` component is declared next to ``_geolocate``;
  3. replaces the body of ``render_voice_guide`` (adds the call under the help text if missing).

A backup is written next to the file (``streamlit_app.py.bak-voice``) the first time. Running it
twice is harmless. If the file does not look like this dashboard it stops WITHOUT changing it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER = "DHOA-VOICE-GUIDE v3"

NEW_FUNCTION = '''def render_voice_guide(view: str, where: str = "popover", transcript: bool = False) -> None:
    """Spoken "how to use" guide for ``view`` ({marker}).

    Always shows the heading and the written script. Audio: the pre-rendered mp3 when it matches the
    current script (``app/static/audio``); otherwise the browser "Read aloud" button. A problem is shown
    as a short visible note (details with ``?debug=1``), never silently hidden and never raised.
    """
    import logging as _logging

    try:
        lang = T.get_language()
        script = T.VOICE_COMMUNITY_SCRIPT if view == "community" else T.VOICE_INSPECTOR_SCRIPT
        audio = voice.current_audio(view, lang, script)
        st.markdown(f"**{{T.LISTEN_TO_THE_GUIDE}}**")
        if audio is not None:
            st.audio(str(audio), format="audio/mpeg")
        elif voice.component_available():
            _voice_player(
                text=script,
                lang=voice.speech_lang(lang),
                read=T.VOICE_READ_ALOUD,
                stop=T.VOICE_STOP,
                none=T.VOICE_NO_VOICE,
                key=f"dhoa_voice_{{where}}_{{view}}_{{lang}}",
                default=None,
            )
        with st.expander(T.VOICE_TRANSCRIPT):
            st.markdown(script)
        if str(st.query_params.get("debug", "")) == "1" and audio is None:
            stale = (voice.AUDIO_DIR / voice.audio_name(view, lang)).is_file()
            st.caption(
                "debug: the mp3 is out of date for the current script - re-run tools/generate_voice_guides.py"
                if stale
                else "debug: no mp3 found in app/static/audio for this view and language"
            )
    except Exception as exc:  # noqa: BLE001 - must never break the page
        _logging.getLogger(__name__).exception("Voice guide failed")
        try:
            debug = str(st.query_params.get("debug", "")) == "1"
            st.caption(f"Voice guide unavailable ({{type(exc).__name__}}" + (f": {{exc}})" if debug else ")"))
        except Exception:  # noqa: BLE001
            pass
'''.format(marker=MARKER)

VOICE_DECLARATION = '''_voice_player = components.declare_component(
    "dhoa_voice_guide",
    path=str(_ROOT / "app" / "components" / "voice_guide"),
)
'''


def fail(message: str) -> int:
    print(f"NOT PATCHED: {message}\nThe file was left unchanged.")
    return 1


def find_top_level_block(lines: list[str], start: int) -> int:
    """Index of the first line after the top-level definition that starts at ``start``."""
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() and not line.startswith((" ", "\t", ")", "]", "}")):
            return i
        i += 1
    return len(lines)


def patch(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    lines = text.split("\n")

    # 1) import voice
    if not re.search(r"^import voice\b", text, re.M):
        anchor = next((i for i, l in enumerate(lines) if re.match(r"^import (trust|hero|community as cm|design_tokens as tokens)\b", l)), None)
        if anchor is None:
            raise ValueError("cannot find the `import hero` / `import trust` lines to add `import voice` after")
        lines.insert(anchor + 1, "import voice")
        notes.append("added `import voice`")

    # 2) _voice_player declaration
    text2 = "\n".join(lines)
    if not re.search(r"^_voice_player\s*=\s*components\.declare_component", text2, re.M):
        anchor = next((i for i, l in enumerate(lines) if re.match(r"^_geolocate\s*=\s*components\.declare_component\(", l)), None)
        if anchor is None:
            anchor = next((i for i, l in enumerate(lines) if "components.declare_component(" in l and l.startswith("_")), None)
        if anchor is None:
            raise ValueError("cannot find an existing `components.declare_component(...)` to put `_voice_player` after")
        end = find_top_level_block(lines, anchor)
        lines[end:end] = VOICE_DECLARATION.rstrip("\n").split("\n")
        notes.append("declared the `_voice_player` component")

    # 3) render_voice_guide function
    start = next((i for i, l in enumerate(lines) if re.match(r"^def render_voice_guide\(", l)), None)
    new_lines = NEW_FUNCTION.rstrip("\n").split("\n")
    if start is not None:
        end = find_top_level_block(lines, start)
        while end > start and not lines[end - 1].strip():
            end -= 1
        lines[start:end] = new_lines
        notes.append("replaced `render_voice_guide`")
    else:
        anchor = next((i for i, l in enumerate(lines) if re.match(r"^def render_community_view\(", l)), None)
        if anchor is None:
            raise ValueError("cannot find `def render_community_view(` to put `render_voice_guide` before")
        lines[anchor:anchor] = new_lines + ["", ""]
        notes.append("added `render_voice_guide`")

    # 4) the call under the help text
    text3 = "\n".join(lines)
    calls = [m for m in re.finditer(r"^\s+render_voice_guide\(", text3, re.M)]
    if not calls:
        idx = next((i for i, l in enumerate(lines) if "HELP_COMMUNITY" in l and "st.markdown" in l), None)
        if idx is None:
            raise ValueError("cannot find the line that shows the help text (`st.markdown(T.HELP_COMMUNITY ...)`) to add the call under")
        indent = re.match(r"\s*", lines[idx]).group(0)
        lines.insert(idx + 1, f'{indent}render_voice_guide(selected_mode, "popover")')
        notes.append("added the `render_voice_guide(...)` call under the help text")
    return "\n".join(lines), notes


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    if not path.is_file():
        return fail(f"{path} does not exist")
    raw = path.read_bytes()
    original = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in original else "\n"
    text = original.replace("\r\n", "\n")
    if "def render_community_view(" not in text or "import streamlit" not in text:
        return fail(f"{path} does not look like the Dhoa dashboard (no render_community_view)")
    if MARKER in text:
        print(f"Already patched ({MARKER}): {path}")
        return 0
    try:
        patched, notes = patch(text)
        compile(patched, str(path), "exec")
    except (ValueError, SyntaxError) as exc:
        return fail(str(exc))
    backup = path.with_name(path.name + ".bak-voice")
    if not backup.exists():
        backup.write_bytes(raw)
    path.write_bytes(patched.replace("\n", newline).encode("utf-8"))
    print(f"Patched {path}")
    for note in notes:
        print(f"  - {note}")
    print(f"Backup: {backup}\nNow restart Streamlit and hard-refresh the browser (Ctrl+Shift+R).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
