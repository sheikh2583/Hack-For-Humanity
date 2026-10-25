"""Landing hero and view navigation helpers (module P2).

Input schema: the prepared kiln frame (``priority_band``, ``district`` columns) and
already-translated text. Output schema: plain ints / one escaped HTML string. No Streamlit
import, so it is unit-testable. Numbers come only from the frame; nothing is estimated.
"""

from __future__ import annotations

import html
from collections.abc import Sequence

import pandas as pd

#: Top-navigation order. ``overview`` is the landing page, ``inspector`` the map,
#: ``community`` the "near me" view. (Stored session values keep the older names.)
VIEW_MODES: tuple[str, ...] = ("overview", "inspector", "community", "about")
DEFAULT_VIEW = "overview"


def hero_counts(frame: pd.DataFrame) -> dict[str, int]:
    """Return ``total``, ``high`` and ``districts`` counts of ``frame`` (zeros when columns are missing)."""
    total = int(len(frame))
    high = int(frame["priority_band"].eq("High").sum()) if "priority_band" in frame else 0
    if "district" in frame:
        names = frame["district"].dropna().astype(str).str.strip()
        districts = int(names[names.ne("")].nunique())
    else:
        districts = 0
    return {"total": total, "high": high, "districts": districts}


def hero_html(mission: str, subline: str, metrics: Sequence[tuple[str, str]]) -> str:
    """Build the hero block: mission line, one supporting sentence and the metric tiles.

    Input: translated ``mission``/``subline`` and ``(value, label)`` pairs. Output: HTML with
    every text escaped. The buttons are native Streamlit widgets rendered below it.
    """
    tiles = "".join(
        f"<div class='dhoa-metric'><strong>{html.escape(str(value))}</strong>"
        f"<span>{html.escape(str(label))}</span></div>"
        for value, label in metrics
    )
    return (
        "<section class='dhoa-hero'>"
        f"<div class='dhoa-hero-title' role='heading' aria-level='2'>{html.escape(mission)}</div>"
        f"<p class='dhoa-hero-sub'>{html.escape(subline)}</p>"
        f"<div class='dhoa-metrics dhoa-hero-metrics'>{tiles}</div>"
        "</section>"
    )
