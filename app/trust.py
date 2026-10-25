"""Trust, About and state helpers (module P7).

Input schema: the ``dashboard`` config mapping (``contact``/``about`` keys) and already
translated text. Output schema: plain values or one escaped HTML string. No Streamlit import,
so everything is unit-testable. Nothing is invented: a missing or unverified config value
simply hides the element that needs it.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from typing import Any

_PHONE = re.compile(r"^[0-9+]{3,16}$")
_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def contact_settings(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return ``number`` (or None), ``verified`` and ``website`` from the config."""
    section = (config or {}).get("contact") or {}
    number = str(section.get("hotline_number") or "").strip()
    verified = section.get("hotline_verified") is True and bool(_PHONE.match(number))
    return {
        "number": number if verified else None,
        "verified": verified,
        "website": str(section.get("website") or "https://doe.gov.bd").strip(),
    }


def localise_digits(text: str, lang: str) -> str:
    """Use Bangla digits for ``lang == "bn"``."""
    return text.translate(_BN_DIGITS) if lang == "bn" else text


def contact_footer_html(
    settings: Mapping[str, Any], label: str, web_label: str, call: str, sms: str, lang: str = "bn"
) -> str:
    """Footer line. Unverified: website only. Verified: number with call and SMS links."""
    site = html.escape(str(settings["website"]), quote=True)
    link = f"<a href='{site}' target='_blank' rel='noopener noreferrer'>{html.escape(web_label)}</a>"
    number = settings.get("number")
    if not number:
        return f"<div class='dhoa-footer'>{link}</div>"
    shown = html.escape(localise_digits(number, lang))
    raw = html.escape(number, quote=True)
    return (
        f"<div class='dhoa-footer'>{html.escape(label)}: {shown} · "
        f"<a href='tel:{raw}'>{html.escape(call)}</a> · <a href='sms:{raw}'>{html.escape(sms)}</a> · {link}</div>"
    )


def steps_html(title: str, steps: Sequence[tuple[str, str]]) -> str:
    """Numbered "How it works" panel: ``(heading, sentence)`` pairs, every text escaped."""
    items = "".join(
        f"<li class='dhoa-step'><span class='dhoa-step-no' aria-hidden='true'>{index}</span>"
        f"<div><strong>{html.escape(head)}</strong><span>{html.escape(body)}</span></div></li>"
        for index, (head, body) in enumerate(steps, start=1)
    )
    return (
        f"<section class='dhoa-panel' aria-label='{html.escape(title, quote=True)}'>"
        f"<div class='dhoa-panel-title' role='heading' aria-level='3'>{html.escape(title)}</div>"
        f"<ol class='dhoa-steps'>{items}</ol></section>"
    )


def facts_html(title: str, rows: Sequence[tuple[str, str]]) -> str:
    """Definition list (label, value) used for the data date and sources."""
    items = "".join(
        f"<div><dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd></div>" for k, v in rows if v
    )
    return (
        f"<section class='dhoa-panel'><div class='dhoa-panel-title' role='heading' aria-level='3'>"
        f"{html.escape(title)}</div><dl class='dhoa-facts'>{items}</dl></section>"
    )


def team_names(config: Mapping[str, Any] | None) -> list[str]:
    """Team names from the config (empty list when none have been agreed)."""
    raw = ((config or {}).get("about") or {}).get("team") or []
    return [str(name).strip() for name in raw if str(name).strip()]


def methodology_url(config: Mapping[str, Any] | None) -> str | None:
    """The methodology link when it is an http(s) URL, else None."""
    url = str(((config or {}).get("about") or {}).get("methodology_url") or "").strip()
    return url if url.startswith(("https://", "http://")) else None


def state_html(kind: str, title: str, body: str) -> str:
    """Friendly state card. ``kind``: ``error`` (announced to screen readers) or ``empty``."""
    role = "alert" if kind == "error" else "status"
    glyph = "!" if kind == "error" else "i"
    return (
        f"<div class='dhoa-state dhoa-state--{html.escape(kind, quote=True)}' role='{role}'>"
        f"<span class='dhoa-state-glyph' aria-hidden='true'>{glyph}</span>"
        f"<div><strong>{html.escape(title)}</strong><span>{html.escape(body)}</span></div></div>"
    )


def skeleton_html(label: str, blocks: int = 3) -> str:
    """Placeholder shimmer blocks shown while data loads (never a blank screen)."""
    bars = "".join("<div class='dhoa-skel-bar'></div>" for _ in range(max(1, blocks)))
    return (
        f"<div class='dhoa-skeleton' role='status' aria-live='polite' aria-label='{html.escape(label, quote=True)}'>"
        f"<div class='dhoa-skel-tiles'><div class='dhoa-skel-tile'></div><div class='dhoa-skel-tile'></div>"
        f"<div class='dhoa-skel-tile'></div></div>{bars}"
        f"<p class='dhoa-skel-text'>{html.escape(label)}</p></div>"
    )
