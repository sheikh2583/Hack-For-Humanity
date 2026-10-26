"""Voice guide helpers (module P10): pre-rendered AI voice files with a browser fallback.

Input schema: view name ("inspector" or "community"), language ("bn" or "en") and the spoken
script from the string catalogue. Output schema: the path of a pre-rendered mp3 that matches
the CURRENT script, or ``None``; and the HTML of a small "Read aloud" button that uses the
browser's own speech voice. No Streamlit import, so it is unit-testable.

An mp3 is only used when ``app/static/audio/manifest.json`` records the hash of the script it
was rendered from. If someone edits the script and forgets to re-render, the stale audio is
ignored (never played) and the fallback button is shown.
"""

from __future__ import annotations

import hashlib
import html
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


def speech_html(text: str, lang: str, read_label: str, stop_label: str, no_voice: str) -> str:
    """Self-contained iframe body: a button that reads ``text`` with the browser's voice.

    If the browser has no voice for the language the button is replaced by ``no_voice``.
    All values are embedded as JSON / escaped, so nothing in them can break out of the page.
    """
    payload = json.dumps(
        {"text": text, "lang": _SPEECH_LANG.get(lang, "en-US"), "read": read_label, "stop": stop_label, "none": no_voice},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    return f"""<!doctype html><html lang="{html.escape(lang, quote=True)}"><head><meta charset="utf-8"><style>
body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans Bengali",sans-serif;color:#e6edf3}}
button{{min-height:44px;padding:0 16px;border-radius:10px;border:1px solid #3d4b5c;background:#162029;color:#e6edf3;font-size:15px;cursor:pointer}}
button:focus-visible{{outline:3px solid #fff;outline-offset:2px}}
p{{margin:8px 0 0;font-size:14px;color:#a3b0bd}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style></head><body><button id="b" type="button" aria-pressed="false" hidden></button><p id="m" role="status"></p>
<script>(function(){{var D={payload},b=document.getElementById("b"),m=document.getElementById("m"),s=window.speechSynthesis;
function has(){{var v=s?s.getVoices():[],p=D.lang.slice(0,2);for(var i=0;i<v.length;i++){{if(v[i].lang.toLowerCase().indexOf(p)===0)return v[i];}}return null;}}
function stop(){{if(s)s.cancel();b.textContent=D.read;b.setAttribute("aria-pressed","false");}}
function ready(){{var v=has();if(!v){{b.hidden=true;m.textContent=D.none;return;}}m.textContent="";b.hidden=false;b.textContent=D.read;
b.onclick=function(){{if(s.speaking){{stop();return;}}var u=new SpeechSynthesisUtterance(D.text);u.lang=D.lang;u.voice=v;u.rate=0.95;
u.onend=u.onerror=stop;s.speak(u);b.textContent=D.stop;b.setAttribute("aria-pressed","true");}};}}
if(!s||typeof SpeechSynthesisUtterance==="undefined"){{m.textContent=D.none;}}else{{ready();s.onvoiceschanged=ready;setTimeout(ready,400);}}
window.addEventListener("pagehide",function(){{if(s)s.cancel();}});}})();</script></body></html>"""
