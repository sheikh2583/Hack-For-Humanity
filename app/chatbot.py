"""Simple navigation chatbot for the Dhoa dashboard.

Input: user text string + list of known district names.
Output: ChatResponse dataclass — a reply string and an optional navigation
action (view name + optional district).  No external API is used; all
matching is keyword-based against a static intent table so the bot is
instant and never fails due to network issues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


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


_FAQ_STOP_WORDS = {
    "what", "how", "does", "do", "is", "are", "the", "a", "an", "i", "my", "me",
    "can", "you", "it", "to", "of", "in", "on", "for", "near", "from", "and", "will",
    "কী", "কি", "কীভাবে", "কিভাবে", "কেন", "আমি", "আমার", "আমাকে", "এটা", "এই", "ও", "এর", "তে", "জন্য",
}


_FAQ_VARIANTS: dict[int, tuple[str, ...]] = {
    1: (
        "what is dhoa", "what does dhoa do", "what does dhoa actually do", "tell me about dhoa", "how does dhoa work",
        "ধোঁয়া কী", "ধোয়া কী", "ধোঁয়া কীভাবে কাজ করে", "ধোয়া কীভাবে কাজ করে",
        "ধোঁয়া দিয়ে কী করা যায়", "ধোঁয়া কী কাজ করে",
    ),
    2: (
        "find kilns near my village", "kilns near my home", "check kilns around my area",
        "search my neighborhood for kilns", "how can i see nearby kilns", "আমার গ্রামের কাছে ভাটা",
        "আমার এলাকার কাছের ভাটা", "কাছাকাছি ভাটা কীভাবে দেখব", "বাড়ির পাশে ভাটা খুঁজব",
    ),
    3: (
        "confirmed kiln", "is this a real kiln", "are these confirmed kilns", "is every candidate a kiln",
        "are candidates verified", "প্রার্থী মানে", "নিশ্চিত ইটভাটা", "এগুলো কি আসল ভাটা",
        "সব প্রার্থী কি ইটভাটা", "প্রার্থী কি যাচাই করা",
    ),
    4: (
        "submit a kiln report", "how to send a report", "tell you about a kiln", "report a listed kiln",
        "ভাটা রিপোর্ট করার উপায়", "ভাটার তথ্য জানাব কীভাবে", "কীভাবে প্রতিবেদন দেব",
    ),
    5: (
        "after submitting a report", "what happens after i submit a report", "report status",
        "what happens to my report", "who reviews my report",
        "রিপোর্ট জমা দেওয়ার পর", "আমার রিপোর্ট কে দেখবে", "প্রতিবেদনের পরে কী হয়",
    ),
    6: (
        "change language", "switch language", "use english instead", "how to change to bangla",
        "ভাষা পরিবর্তন", "ভাষা বদল", "ইংরেজি থেকে বাংলা করব কীভাবে",
    ),
}


def _tokens(text: str) -> set[str]:
    """Normalize English/Bangla text into meaningful word tokens for FAQ retrieval."""
    return {
        token for token in re.findall(r"\w+", _normalise(text), flags=re.UNICODE)
        if len(token) > 1 and token not in _FAQ_STOP_WORDS
    }


def _faq_reply(user_text: str, language: str, texts: object) -> str | None:
    """Retrieve an approved FAQ answer for close wording and curated paraphrases.

    The small FAQ corpus is indexed in memory on each call; answer text always comes from
    the active language catalogue. No generated or unverified answer is produced.
    """
    normalized_query = _normalise(user_text).rstrip("?？.! ")
    best_score = 0.0
    best_answer: str | None = None
    for index in range(1, 7):
        question = texts.text(f"FAQ_Q{index}", language)
        answer = texts.text(f"FAQ_A{index}", language)
        for candidate in (question, *texts.variants(f"FAQ_Q{index}"), *_FAQ_VARIANTS[index]):
            normalized_candidate = _normalise(candidate).rstrip("?？.! ")
            if normalized_query == normalized_candidate:
                return answer
            query_tokens = _tokens(user_text)
            candidate_tokens = _tokens(candidate)
            if not query_tokens:
                continue
            intersection = len(query_tokens & candidate_tokens)
            if intersection < 2 and len(query_tokens) > 1:
                continue
            recall = intersection / max(1, len(query_tokens))
            precision = intersection / max(1, len(candidate_tokens))
            token_score = 2 * recall * precision / max(1e-9, recall + precision)
            char_score = SequenceMatcher(None, _normalise(user_text), _normalise(candidate)).ratio()
            score = max(token_score, char_score * 0.58) if len(query_tokens) > 1 else char_score
            if score > best_score:
                best_score, best_answer = score, answer
    return best_answer if best_score >= 0.34 else None


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

    tr = lambda key: T_mod.text(key, lang)  # noqa: E731

    # 1. District match — highest priority
    district = _match_district(user_text, districts)
    if district:
        return ChatResponse(
            text=tr("CHAT_GO_DISTRICT").format(district),
            navigate_to="community",
            district=district,
        )

    # 2. Exact navigation commands keep their existing behavior; questions can
    # retrieve FAQs before broad navigation keywords such as "find kilns".
    intent = _match_intent(user_text)
    normalized = _normalise(user_text).rstrip("?？.! ")
    explicit_navigation = (
        normalized in {"near me", "nearby", "কাছের", "আশেপাশে", "overview", "main map", "home", "inspector", "staff", "পরিদর্শক"}
        or normalized.startswith(("open ", "go to ", "show map", "open the map", "ওভারভিউ খুলুন", "পরিদর্শক পোর্টাল খুলুন"))
    )
    if explicit_navigation and intent in {"near_me", "overview", "inspector"}:
        if intent == "near_me":
            return ChatResponse(text=tr("CHAT_GO_NEAR_ME"), navigate_to="community")
        if intent == "overview":
            return ChatResponse(text=tr("CHAT_GO_OVERVIEW"), navigate_to="overview")
        return ChatResponse(text=tr("CHAT_GO_INSPECTOR"), navigate_to="inspector")

    # 3. Curated FAQ retrieval. Answers are returned verbatim from the active catalogue.
    faq_answer = _faq_reply(user_text, lang, T_mod)
    if faq_answer:
        return ChatResponse(text=faq_answer)

    # 4. Remaining existing intents and fallback.
    if intent in {"near_me", "overview", "inspector"}:
        if intent == "near_me":
            return ChatResponse(text=tr("CHAT_GO_NEAR_ME"), navigate_to="community")
        if intent == "overview":
            return ChatResponse(text=tr("CHAT_GO_OVERVIEW"), navigate_to="overview")
        return ChatResponse(text=tr("CHAT_GO_INSPECTOR"), navigate_to="inspector")

    if intent == "about":
        return ChatResponse(text=tr("CHAT_GO_ABOUT"), navigate_to="about")
    if intent == "how_report":
        return ChatResponse(text=tr("CHAT_HOW_REPORT"))
    if intent == "what_candidate":
        return ChatResponse(text=tr("CHAT_WHAT_CANDIDATE"))
    if intent == "how_language":
        return ChatResponse(text=tr("CHAT_HOW_LANGUAGE"))

    # 3. Fallback
    return ChatResponse(text=tr("CHAT_FALLBACK"))
