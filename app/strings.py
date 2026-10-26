"""Language-aware text catalogue for the Dhoa dashboard (single entry point).

Input schema: ``T.NAME`` attribute reads, where ``NAME`` is defined in ``strings_bn`` and
``strings_en`` (the same names and ``str.format`` fields in both). Output schema: the
``str`` for the *active language*, read from ``st.session_state["dhoa_lang"]`` on every
access (``"bn"`` when there is no Streamlit session or no valid value), so one text
lookup is always correct for the current run and nothing language-dependent needs to be
computed at import time. Helpers: ``get_language``, ``set_language``, ``variants`` (a
name's text in every language, for matching either spelling), ``LazyMapping`` and
``LazySequence`` (module-level constants whose contents depend on the language).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any

try:  # imported as ``strings`` (app dir on sys.path) or as ``app.strings``
    from . import strings_bn, strings_en  # type: ignore[attr-defined]
except ImportError:
    import strings_bn
    import strings_en

LANGUAGES: tuple[str, ...] = ("bn", "en")
DEFAULT_LANGUAGE = "bn"
LANGUAGE_KEY = "dhoa_lang"
LANGUAGE_NAMES = {"bn": "বাংলা", "en": "English"}
_CATALOGUES = {"bn": strings_bn, "en": strings_en}
_COMPATIBILITY_TEXT = {
    "NAV_INSPECTOR": {"bn": "🔒 পরিদর্শক পোর্টাল", "en": "🔒 Inspector Portal"},
    "C_PLACE_SUGGESTIONS": {"bn": "মিল থাকা এলাকা", "en": "Matching areas"},
    "C_PLACE_SUGGESTION_PLACEHOLDER": {
        "bn": "মিল থাকা এলাকা বেছে নিন", "en": "Choose a matching area",
    },
    "C_GEO_SUGGESTION_FMT": {
        "bn": "বাংলাদেশে “{0}” খুঁজুন", "en": "Search Bangladesh for “{0}”",
    },
    "PUB_HERO_MISSION": {
        "bn": "স্যাটেলাইট ছবি থেকে শনাক্ত করা ইটভাটার প্রার্থী, মানচিত্রে দেখানো।",
        "en": "Brick kiln candidates found in satellite images and shown on a map.",
    },
    "PUB_HERO_SUB": {
        "bn": "আপনার বাড়ি বা গ্রামের কাছের ইটভাটার প্রার্থীগুলো খুঁজে নিন।",
        "en": "Find the kiln candidates near your home or village.",
    },
    "PUB_OV_DISTRICTS_HINT": {
        "bn": "জেলার নামে চাপলে সেই জেলার ইটভাটার প্রার্থী দেখা যাবে।",
        "en": "Select a district name to see its kiln candidates.",
    },
    "PUB_OV_OPEN_DISTRICT_FMT": {
        "bn": "{0}-এর ইটভাটার প্রার্থী দেখুন",
        "en": "See kiln candidates in {0}",
    },
    "PUB_HOW_3_HEAD": {"bn": "কাছের ভাটা খোঁজা", "en": "Find near you"},
    "PUB_HOW_3_BODY": {
        "bn": "প্রার্থীদের মানচিত্রে দেখানো হয়, যাতে কোনো এলাকার কাছের ভাটাগুলো খুঁজে নেওয়া যায়।",
        "en": "Candidates are shown on a map, so you can look up the ones near a place.",
    },
}


def get_language() -> str:
    """Return the active language code (``"bn"`` or ``"en"``)."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx(suppress_warning=True) is None:
            return DEFAULT_LANGUAGE
        value = st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    except Exception:  # noqa: BLE001 - no Streamlit runtime / session (tests, scripts)
        return DEFAULT_LANGUAGE
    return value if value in _CATALOGUES else DEFAULT_LANGUAGE


def set_language(language: str) -> None:
    """Make ``language`` active for the current session (ignored when invalid)."""
    if language not in _CATALOGUES:
        return
    import streamlit as st

    st.session_state[LANGUAGE_KEY] = language


def text(name: str, language: str | None = None) -> str:
    """Return ``name`` in ``language`` (default: active), falling back to Bangla."""
    code = language if language in _CATALOGUES else get_language()
    catalogue = _CATALOGUES[code]
    if hasattr(catalogue, name):
        return getattr(catalogue, name)
    if name in _COMPATIBILITY_TEXT:
        return _COMPATIBILITY_TEXT[name][code]
    return getattr(strings_bn, name)


def variants(name: str) -> tuple[str, ...]:
    """Return the distinct texts of ``name`` across all languages."""
    seen: list[str] = []
    for code in LANGUAGES:
        value = text(name, code)
        if value not in seen:
            seen.append(value)
    return tuple(seen)


def __getattr__(name: str) -> str:
    """Module attribute hook: ``strings.NAME`` is the active-language text."""
    if name.startswith("_") or not name.isupper():
        raise AttributeError(name)
    if not hasattr(strings_bn, name) and name not in _COMPATIBILITY_TEXT:
        raise AttributeError(f"module 'strings' has no attribute {name!r}")
    return text(name)


class LazyMapping(Mapping):
    """Read-only mapping rebuilt from ``factory`` on every access (language-aware)."""

    def __init__(self, factory: Callable[[], Mapping[Any, Any]]) -> None:
        self._factory = factory

    def __getitem__(self, key: Any) -> Any:
        return self._factory()[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._factory())

    def __len__(self) -> int:
        return len(self._factory())


class LazySequence(Sequence):
    """Read-only sequence rebuilt from ``factory`` on every access (language-aware)."""

    def __init__(self, factory: Callable[[], Sequence[Any]]) -> None:
        self._factory = factory

    def __getitem__(self, index: Any) -> Any:
        return self._factory()[index]

    def __len__(self) -> int:
        return len(self._factory())

    def __iter__(self) -> Iterator[Any]:
        return iter(self._factory())
