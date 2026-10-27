"""Simple navigation chatbot for the Dhoa dashboard.

Input: user text string + list of known district names.
Output: ChatResponse dataclass — a reply string and an optional navigation
action (view name + optional district).  No external API is used; all
matching is keyword-based against a static intent table so the bot is
instant and never fails due to network issues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ChatResponse:
    """The bot's reply for one user message."""

    text: str
    navigate_to: str | None = None        # hero VIEW_MODES key or None
    district: str | None = None           # set when navigating to a district
    place_key: str | None = None          # community place key, if known


# ---------------------------------------------------------------------------
# Intent patterns (order matters — first match wins)
# ---------------------------------------------------------------------------

_INTENTS: list[tuple[list[str], str]] = [
    # Navigation intents
    (["near me", "nearby", "কাছের", "কাছে", "আশেপাশে", "find kiln", "kilns near", "location"], "near_me"),
    (["overview", "main map", "home", "মানচিত্র", "ওভারভিউ", "প্রধান"], "overview"),
    (["inspector", "staff", "login", "sign in", "পরিদর্শক", "লগইন", "কর্মী"], "inspector"),
    (["about", "পরিচিতি", "তথ্য", "what is dhoa", "dhoa কী", "ধোয়া কী"], "about"),
    # Info intents
    (["report", "রিপোর্ট", "জানাব", "জানাতে", "জানান"], "how_report"),
    (["candidate", "প্রার্থী", "মানে কী", "what does", "what is candidate"], "what_candidate"),
    (["language", "english", "bangla", "বাংলা", "ভাষা", "toggle", "টগল", "en ", "বাং"], "how_language"),
    (["faq", "help", "সাহায্য", "question", "জিজ্ঞাসা"], "about"),
]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _match_intent(text: str) -> str | None:
    n = _normalise(text)
    for keywords, intent in _INTENTS:
        if any(kw in n for kw in keywords):
            return intent
    return None


def _match_district(text: str, districts: list[str]) -> str | None:
    """Return the district name if the user's text contains it (case-insensitive)."""
    n = _normalise(text)
    for district in districts:
        if district.lower() in n:
            return district
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def respond(
    user_text: str,
    districts: list[str],
    *,
    lang: str = "bn",
) -> ChatResponse:
    """Produce a ChatResponse for one user message.

    Parameters
    ----------
    user_text:
        What the user typed.
    districts:
        All district names from the loaded kiln data (used for navigation).
    lang:
        Active language code (``"bn"`` or ``"en"``), used to pick reply text.
    """
    # Lazy import to avoid circular deps at module load time
    try:
        from app import strings as T_mod  # noqa: N811
    except ImportError:
        import strings as T_mod  # type: ignore[no-redef]

    T = T_mod  # attribute access via T.NAME

    # 1. District match — highest priority
    district = _match_district(user_text, districts)
    if district:
        return ChatResponse(
            text=T.CHAT_GO_DISTRICT.format(district),
            navigate_to="community",
            district=district,
        )

    # 2. Intent match
    intent = _match_intent(user_text)

    if intent == "near_me":
        return ChatResponse(text=T.CHAT_GO_NEAR_ME, navigate_to="community")
    if intent == "overview":
        return ChatResponse(text=T.CHAT_GO_OVERVIEW, navigate_to="overview")
    if intent == "inspector":
        return ChatResponse(text=T.CHAT_GO_INSPECTOR, navigate_to="inspector")
    if intent == "about":
        return ChatResponse(text=T.CHAT_GO_ABOUT, navigate_to="about")
    if intent == "how_report":
        return ChatResponse(text=T.CHAT_HOW_REPORT)
    if intent == "what_candidate":
        return ChatResponse(text=T.CHAT_WHAT_CANDIDATE)
    if intent == "how_language":
        return ChatResponse(text=T.CHAT_HOW_LANGUAGE)

    # 3. Fallback
    return ChatResponse(text=T.CHAT_FALLBACK)
