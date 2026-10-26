"""Render the voice guides.

    pip install edge-tts                             # best quality (neural voice), needs internet
    python tools/generate_voice_guides.py            # all four files
    python tools/generate_voice_guides.py --view community --lang bn

    # Offline alternative (robotic but always works): needs `espeak-ng` and `ffmpeg` on PATH
    python tools/generate_voice_guides.py --engine espeak

Reads the spoken scripts (VOICE_INSPECTOR_SCRIPT / VOICE_COMMUNITY_SCRIPT) from
app/strings_bn.py and app/strings_en.py, renders each with a neural voice and writes
app/static/audio/guide_<view>_<lang>.mp3 plus manifest.json (script hashes). Re-run after
ANY change to a script; a stale file is ignored by the app. Voices can be changed with
--voice-bn / --voice-en (list them with: edge-tts --list-voices).
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import voice  # noqa: E402

SCRIPT_NAME = {"inspector": "VOICE_INSPECTOR_SCRIPT", "community": "VOICE_COMMUNITY_SCRIPT"}


async def _render(text: str, voice_name: str, rate: str, target: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice_name, rate=rate).save(str(target))


def _render_espeak(text: str, lang: str, rate_wpm: int, target: Path) -> None:
    """Offline render: espeak-ng -> wav -> mp3 (ffmpeg). Fails loudly if a tool is missing."""
    for tool in ("espeak-ng", "ffmpeg"):
        if shutil.which(tool) is None:
            raise SystemExit(f"--engine espeak needs `{tool}` on PATH (e.g. apt install espeak-ng ffmpeg)")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "guide.wav"
        subprocess.run(
            ["espeak-ng", "-v", "bn" if lang == "bn" else "en-us", "-s", str(rate_wpm), "-g", "6", "-w", str(wav), text],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "24000", "-b:a", "64k", str(target)],
            check=True,
        )
    if not target.is_file() or target.stat().st_size < 2000:
        raise SystemExit(f"rendering produced an empty file: {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("edge", "espeak"), default="edge")
    parser.add_argument("--view", choices=voice.VIEWS)
    parser.add_argument("--lang", choices=voice.LANGUAGES)
    parser.add_argument("--voice-bn", default="bn-BD-NabanitaNeural")
    parser.add_argument("--voice-en", default="en-IN-NeerjaNeural")
    parser.add_argument("--rate", default="-5%", help="speaking speed, e.g. -10%% for slower")
    args = parser.parse_args()
    voice.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = voice.AUDIO_DIR / voice.MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    for lang in ([args.lang] if args.lang else voice.LANGUAGES):
        catalogue = importlib.import_module(f"strings_{lang}")
        for view in ([args.view] if args.view else voice.VIEWS):
            text = getattr(catalogue, SCRIPT_NAME[view])
            name = voice.audio_name(view, lang)
            if args.engine == "espeak":
                _render_espeak(text, lang, 135 if lang == "bn" else 150, voice.AUDIO_DIR / name)
            else:
                asyncio.run(_render(text, args.voice_bn if lang == "bn" else args.voice_en, args.rate, voice.AUDIO_DIR / name))
            manifest[name] = voice.script_hash(text)
            print("rendered", name)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
