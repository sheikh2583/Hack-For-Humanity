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
    # --- navigation ---
    "NAV_INSPECTOR": {"bn": "🔒 পরিদর্শক পোর্টাল", "en": "🔒 Inspector Portal"},
    # --- community / nearby view ---
    "C_PLACE_SUGGESTIONS": {"bn": "মিল থাকা এলাকা", "en": "Matching areas"},
    "C_PLACE_SUGGESTION_PLACEHOLDER": {
        "bn": "মিল থাকা এলাকা বেছে নিন", "en": "Choose a matching area",
    },
    "C_GEO_SUGGESTION_FMT": {
        "bn": "বাংলাদেশে “{0}” খুঁজুন", "en": "Search Bangladesh for “{0}”",
    },
    "C_GPS_LABEL": {"bn": "📍 আমার অবস্থান ব্যবহার করুন", "en": "📍 Use my location"},
    "C_GPS_BUSY": {"bn": "অবস্থান খোঁজা হচ্ছে…", "en": "Finding your location…"},
    "C_GPS_HINT": {
        "bn": "ব্রাউজার অবস্থানের অনুমতি চাইবে। অনুমতি না দিলে ওপরের অনুসন্ধান বাক্স ব্যবহার করুন।",
        "en": "Your browser will ask for location permission. If blocked, use the search box above.",
    },
    "C_STEP2": {"bn": "২. কত দূর পর্যন্ত?", "en": "2. How far?"},
    "C_RADIUS_LABEL": {"bn": "দূরত্ব", "en": "Distance"},
    "C_RADIUS_OPTION_FMT": {"bn": "{0:g} কিমি", "en": "{0:g} km"},
    "C_RADIUS_HELP": {
        "bn": "বাছাই করা জায়গা থেকে এই দূরত্বের মধ্যের ভাটা দেখানো হবে।",
        "en": "Kilns within this distance of the chosen place will be shown.",
    },
    # --- public hero / overview ---
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
    # --- inspector / work status ---
    "WORK_NOT_VISITED": {"bn": "পরিদর্শন হয়নি", "en": "Not visited"},
    "WORK_ASSIGNED": {"bn": "দায়িত্ব দেওয়া হয়েছে", "en": "Assigned"},
    "WORK_VISITED": {"bn": "পরিদর্শন হয়েছে", "en": "Visited"},
    "WORK_CONFIRMED_ACTIVE": {"bn": "সক্রিয় ভাটা নিশ্চিত", "en": "Confirmed active"},
    "WORK_NOT_A_KILN": {"bn": "ভাটা নয়", "en": "Not a kiln"},
    # --- inspector portal sign-in ---
    "PORTAL_SIGNIN_UNAVAILABLE": {
        "bn": "কর্মীদের প্রবেশ এই মুহূর্তে চালু নেই।",
        "en": "Staff sign-in is not available right now.",
    },
    "PORTAL_SIGNIN_HINT": {
        "bn": "এই অংশটি কর্মীদের জন্য। চালিয়ে যেতে কর্মীদের পাসকোড দিন।",
        "en": "This area is for staff. Enter the staff passcode to continue.",
    },
    "PORTAL_PASSCODE": {"bn": "পাসকোড", "en": "Passcode"},
    "PORTAL_NAME": {"bn": "আপনার নাম", "en": "Your name"},
    "PORTAL_SIGN_IN": {"bn": "প্রবেশ করুন", "en": "Sign in"},
    "PORTAL_WRONG_PASSCODE": {
        "bn": "পাসকোডটি সঠিক নয়। আবার চেষ্টা করুন।",
        "en": "That passcode is not correct. Please try again.",
    },
    "PORTAL_DEMO_CREDENTIALS_HINT": {
        "bn": "ডেমো অ্যাকাউন্ট: Demo · নিচের বোতামে চাপলে তথ্যগুলো পূরণ হবে।",
        "en": "Demo account: Demo · click below to fill the credentials.",
    },
    "PORTAL_FILL_DEMO_CREDENTIALS": {
        "bn": "ডেমো তথ্য পূরণ করুন", "en": "Fill demo credentials",
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
