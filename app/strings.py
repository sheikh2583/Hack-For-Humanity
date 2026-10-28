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
    # --- FAQ and local navigation chatbot ---
    "FAQ_TITLE": {"bn": "সাধারণ জিজ্ঞাসা", "en": "Frequently Asked Questions"},
    "FAQ_Q1": {"bn": "ধোয়া কী?", "en": "What is Dhoa?"},
    "FAQ_A1": {"bn": "ধোয়া বাংলাদেশের স্যাটেলাইট ছবি থেকে শনাক্ত করা ইটভাটার প্রার্থীদের একটি পাবলিক মানচিত্র। এটি স্থানীয় মানুষ ও গবেষকদের কাছাকাছি ভাটা খুঁজে পেতে ও প্রতিবেদন দিতে সাহায্য করে।", "en": "Dhoa is a public map of brick kiln candidates detected from satellite images in Bangladesh. It helps communities and researchers find and report kilns in their area."},
    "FAQ_Q2": {"bn": "আমার গ্রামের কাছের ভাটা কীভাবে খুঁজব?", "en": "How do I find kilns near my village?"},
    "FAQ_A2": {"bn": "'কাছের ভাটা' পাতায় যান এবং অনুসন্ধান বাক্সে আপনার গ্রাম বা জেলার নাম লিখুন, অথবা 'আমার অবস্থান ব্যবহার করুন' বোতামে চাপ দিন।", "en": "Go to 'Kilns near me', type your village or district name in the search box, or tap 'Use my location' to let the app find you automatically."},
    "FAQ_Q3": {"bn": '"প্রার্থী" মানে কী?', "en": 'What does "candidate" mean?'},
    "FAQ_A3": {"bn": "প্রার্থী হলো এমন একটি স্থান যেখানে স্যাটেলাইট মডেল ইটভাটা থাকার সম্ভাবনা চিহ্নিত করেছে।", "en": "A candidate is a location the satellite model flagged as likely being a brick kiln."},
    "FAQ_Q4": {"bn": "কোনো ভাটা কীভাবে রিপোর্ট করব?", "en": "How do I report a kiln?"},
    "FAQ_A4": {"bn": "'কাছের ভাটা' পাতায় তালিকা থেকে ভাটাটি খুঁজে 'এই ভাটিটি রিপোর্ট করুন' বোতামে চাপ দিন। আপনার পর্যবেক্ষণ লিখে জমা দিন — এটি আমাদের পর্যালোচনা দলের কাছে যাবে।", "en": "In 'Kilns near me', find the kiln on the list and tap 'Report this kiln'. Fill in what you observed and submit — it goes to our review team."},
    "FAQ_Q5": {"bn": "ভাটা রিপোর্ট করার পর কী হয়?", "en": "What happens after I report a kiln?"},
    "FAQ_A5": {"bn": "আপনার রিপোর্ট পরিদর্শক পোর্টালে পর্যালোচনার জন্য যায়। পরিদর্শক মানচিত্রে অবস্থান দেখতে, প্রতিবেদন ডাউনলোড করতে এবং পর্যালোচিত বা সমাধান হয়েছে হিসেবে চিহ্নিত করতে পারেন।", "en": "Your report appears in the Inspector Portal for review. Inspectors can view its map location, download its report, and mark it reviewed or resolved."},
    "FAQ_Q6": {"bn": "ভাষা কীভাবে বদলাব?", "en": "How do I switch to English or Bangla?"},
    "FAQ_A6": {"bn": "পাতার উপরে EN / বাং টগল ব্যবহার করে ইংরেজি ও বাংলার মধ্যে যাওয়া-আসা করা যাবে।", "en": "Use the language toggle (EN / বাং) at the top of the page to switch between English and Bangla."},
    "CHAT_PLACEHOLDER": {"bn": "প্রশ্ন করুন বা এলাকা, জেলা, উপজেলা কিংবা স্থানের নাম লিখুন…", "en": "Ask a question or type an area, district, upazila, or landmark…"},
    "CHAT_TITLE": {"bn": "💬 সাহায্য", "en": "💬 Help"},
    "CHAT_WELCOME": {"bn": "হ্যালো! কাছের ভাটা খুঁজতে জেলা, উপজেলা বা কোনো পরিচিত স্থানের নাম লিখুন। ধোঁয়া ব্যবহার নিয়েও প্রশ্ন করতে পারেন।", "en": "Hi! I can help find nearby kilns. Tell me a district, upazila, or landmark, or ask me how to use Dhoa."},
    "CHAT_FALLBACK": {"bn": "ধোঁয়া, প্রতিবেদন বা কাছের ভাটার প্রার্থী খুঁজতে আমি সাহায্য করতে পারি। “প্রার্থী বলতে কী বোঝায়?” জিজ্ঞাসা করুন, অথবা কোনো স্থানের নাম লিখে খুঁজুন।", "en": "I can help with Dhoa, reports, and nearby candidate searches. Try a question such as “What does candidate mean?” or enter a place name to search."},
    "CHAT_FOLLOW_UP": {"bn": "আর কী জানতে চান?", "en": "What else would you like to know?"},
    "CHAT_GO_DISTRICT": {"bn": "{0}-এর ভাটা দেখাচ্ছি। মানচিত্র খুলছে…", "en": "Showing kilns in {0}. Opening the map now…"},
    "CHAT_AREA_AMBIGUOUS": {"bn": "একাধিক এলাকার সাথে মিলেছে। সঠিকটি খুঁজতে স্থানের সাথে জেলা বা উপজেলার নাম লিখুন: {0}।", "en": "More than one area matches. Add its district or upazila to narrow it down: {0}."},
    "CHAT_SEARCH_PLACE_FMT": {"bn": "কাছের ভাটা খুলেছি এবং {0} খুঁজছি। মিল পাওয়া গেলে কাছাকাছি ফলাফল দেখাব।", "en": "I’ve opened Kilns near me and started searching for {0}. Nearby results will appear when a match is found."},
    "CHAT_GO_NEAR_ME": {"bn": "'কাছের ভাটা' খুলছে…", "en": "Opening 'Kilns near me'…"},
    "CHAT_GO_OVERVIEW": {"bn": "ওভারভিউ মানচিত্র খুলছে…", "en": "Opening the Overview map…"},
    "CHAT_GO_ABOUT": {"bn": "পরিচিতি পাতা খুলছে…", "en": "Opening the About page…"},
    "CHAT_GO_INSPECTOR": {"bn": "পরিদর্শক পোর্টাল খুলছে…", "en": "Opening the Inspector Portal…"},
    "CHAT_HOW_REPORT": {"bn": "'কাছের ভাটা' পাতায় ভাটাটি খুঁজুন, তারপর সেই সারিতে 'এই ভাটিটি রিপোর্ট করুন' বোতামে চাপ দিন।", "en": "Find your kiln in 'Kilns near me', then tap 'Report this kiln' on that row."},
    "CHAT_WHAT_CANDIDATE": {"bn": "প্রার্থী হলো স্যাটেলাইট মডেলের চিহ্নিত সম্ভাব্য ইটভাটা।", "en": "A candidate is a location the satellite model flagged as a possible brick kiln."},
    "CHAT_HOW_LANGUAGE": {"bn": "পাতার উপরে EN / বাং টগল ব্যবহার করে ভাষা পরিবর্তন করুন।", "en": "Use the EN / বাং toggle at the top of the page to switch language."},
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
