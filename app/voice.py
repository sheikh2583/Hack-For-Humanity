"""Voice guide helpers (module P10): pre-rendered AI voice files with a browser fallback.

Input schema: view name ("inspector" or "community"), language ("bn" or "en") and the spoken
script from the string catalogue. Output schema: the path of a pre-rendered mp3 that matches
the CURRENT script, or ``None``; and the speech language tag for the "Read aloud" component
(``app/components/voice_guide``) that uses the browser's own voice. No Streamlit import, so it is unit-testable.

An mp3 is only used when ``app/static/audio/manifest.json`` records the hash of the script it
was rendered from. If someone edits the script and forgets to re-render, the stale audio is
ignored (never played) and the fallback button is shown.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent / "static" / "audio"
MANIFEST = "manifest.json"
VIEWS = ("inspector", "community")
LANGUAGES = ("bn", "en")
_SPEECH_LANG = {"bn": "bn-BD", "en": "en-US"}


def script_hash(text: str) -> str:
    """Short stable hash of a spoken script."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def audio_name(view: str, lang: str) -> str:
    """File name of the rendered guide, e.g. ``guide_community_bn.mp3``."""
    return f"guide_{view}_{lang}.mp3"


def current_audio(view: str, lang: str, script: str, audio_dir: Path = AUDIO_DIR) -> Path | None:
    """Return the mp3 path when it exists AND its recorded hash matches ``script``, else None."""
    name = audio_name(view, lang)
    path = audio_dir / name
    try:
        manifest = json.loads((audio_dir / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not path.is_file() or manifest.get(name) != script_hash(script):
        return None
    return path


def speech_lang(lang: str) -> str:
    """BCP-47 tag the browser voice is matched against (the component compares the first two letters)."""
    return _SPEECH_LANG.get(lang, "en-US")
