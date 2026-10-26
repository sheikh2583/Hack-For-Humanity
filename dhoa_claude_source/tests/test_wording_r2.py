"""R2: no public-facing "inspector" / "community" wording.

Input: both string catalogues, the PDF label tables, the voice fallback texts, the user-facing docs and the
download file names. Output: assertions. Key names (VIEW_INSPECTOR, HELP_COMMUNITY, ...) are internal
identifiers and are allowed; only their VALUES are read by people. ``ROLE_INSPECTOR`` is the chip shown
after a staff member signs in, so it is the one allowed exception.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BANNED = re.compile(r"inspector|community|\u09aa\u09b0\u09bf\u09a6\u09b0\u09cd\u09b6\u0995|\u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf", re.I)
ALLOWED_KEYS = {"ROLE_INSPECTOR"}


def _strings(lang: str) -> dict[str, str]:
    module = importlib.import_module(f"app.strings_{lang}")
    return {k: v for k, v in vars(module).items() if k.isupper() and isinstance(v, str)}


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_catalogue_values_have_no_role_wording(lang: str) -> None:
    bad = {k: v[:60] for k, v in _strings(lang).items() if k not in ALLOWED_KEYS and BANNED.search(v)}
    assert not bad, bad


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_renamed_labels(lang: str) -> None:
    s = _strings(lang)
    assert s["HELP_INSPECTOR"].strip().splitlines()[0] != s["HELP_COMMUNITY"].strip().splitlines()[0]
    if lang == "en":
        assert "**Using the Map**" in s["HELP_INSPECTOR"] and "**Using Near me**" in s["HELP_COMMUNITY"]
        assert s["VOICE_INSPECTOR_SCRIPT"].startswith("Welcome to the Map page.")


def test_pdf_labels_have_no_role_wording() -> None:
    from src.eval import pdf_kit

    for lang, table in pdf_kit.LABELS.items():
        bad = {k: v for k, v in table.items() if isinstance(v, str) and BANNED.search(v)}
        assert not bad, (lang, bad)


def test_voice_fallback_texts_match_catalogues() -> None:
    from app import voice_scripts

    for lang in ("bn", "en"):
        catalogue = _strings(lang)
        for name, text in voice_scripts.TEXTS[lang].items():
            if name in catalogue:
                assert catalogue[name] == text, (lang, name)
            assert not BANNED.search(text), (lang, name)


def test_docs_and_download_names_are_clean() -> None:
    for doc in ("README.md", "docs/DASHBOARD_GUIDE.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert not re.search(r"community (view|search|report|pdf)|inspector view|\*\*(Inspector|Community)\*\*", text, re.I), doc
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    assert not re.search(r"dhoa_community_(report|candidates)", source)
