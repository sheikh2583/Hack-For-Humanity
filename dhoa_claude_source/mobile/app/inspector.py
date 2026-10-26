"""Inspector helpers (module P4): distance grid, legend, heatmap points.

Input schema: one kiln row (mapping/Series with ``dist_<feature>_m`` columns), the
siting rules from ``config/rules.yaml`` (``feature``, ``buffer_m``) and
already-translated labels. Output schema: plain dicts/lists and escaped HTML strings.
No Streamlit import, so it is unit-testable. Thresholds are read from the rules passed
in; nothing is hard-coded here and no value is estimated.
"""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

# Decorative icon per configured feature id; the visible text label is always present.
FEATURE_ICONS: dict[str, str] = {
    "schools": "🏫",
    "hospitals": "🏥",
    "settlements": "🏘",
    "railways": "🚆",
    "water": "💧",
    "government_forest": "🌳",
}
DEFAULT_ICON = "📍"
INSIDE_DOT = "●"
OUTSIDE_DOT = "○"
UNKNOWN_DOT = "–"
BANDS: tuple[tuple[str, str], ...] = (("High", "▲"), ("Medium", "◆"), ("Low", "●"))
MAX_HEAT_POINTS = 5000


def _float(value: object) -> float:
    """Return ``value`` as a finite float, or NaN."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def distance_rows(row: Mapping[str, Any] | pd.Series, rules: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One entry per configured rule: feature, icon, distance and threshold state.

    Output keys: ``id``, ``feature``, ``icon``, ``distance_m`` (float or None),
    ``buffer_m`` (float or None) and ``state`` (``inside`` when the distance is
    below the configured buffer, ``outside``, or ``unknown`` when either is missing).
    """
    out: list[dict[str, Any]] = []
    for rule in rules:
        feature = str(rule.get("feature", ""))
        distance = _float(row.get(f"dist_{feature}_m"))
        buffer_m = _float(rule.get("buffer_m"))
        if math.isnan(distance) or math.isnan(buffer_m):
            state = "unknown"
        else:
            state = "inside" if distance < buffer_m else "outside"
        out.append(
            {
                "id": str(rule.get("id", feature)),
                "feature": feature,
                "icon": FEATURE_ICONS.get(feature, DEFAULT_ICON),
                "distance_m": None if math.isnan(distance) else distance,
                "buffer_m": None if math.isnan(buffer_m) else buffer_m,
                "state": state,
            }
        )
    return out


def distance_grid_html(
    entries: Sequence[Mapping[str, Any]],
    feature_labels: Mapping[str, str],
    distance_text: Mapping[str, str],
    state_labels: Mapping[str, str],
) -> str:
    """Icon grid: icon, feature label, distance and a threshold dot with text.

    ``distance_text`` maps feature -> formatted distance (or the no-data text);
    ``state_labels`` maps ``inside``/``outside``/``unknown`` -> text that already
    names the configured threshold. The dot shape (●/○/–) plus the text carry the
    state, not colour alone. All text is HTML-escaped.
    """
    dots = {"inside": INSIDE_DOT, "outside": OUTSIDE_DOT, "unknown": UNKNOWN_DOT}
    cells = []
    for entry in entries:
        feature = str(entry["feature"])
        state = str(entry["state"])
        label = html.escape(str(feature_labels.get(feature, feature)))
        distance = html.escape(str(distance_text.get(feature, "")))
        status = html.escape(str(state_labels.get(f"{feature}:{state}", state_labels.get(state, ""))))
        cells.append(
            f"<li class='dhoa-dist dhoa-dist-{state}'>"
            f"<span class='dhoa-dist-icon' aria-hidden='true'>{entry['icon']}</span>"
            f"<span class='dhoa-dist-name'>{label}</span>"
            f"<strong class='dhoa-dist-value'>{distance}</strong>"
            f"<span class='dhoa-dist-state'><i class='dhoa-dot' aria-hidden='true'>{dots.get(state, UNKNOWN_DOT)}</i> {status}</span>"
            f"</li>"
        )
    return f"<ul class='dhoa-dist-grid'>{''.join(cells)}</ul>"


def legend_html(title: str, labels: Mapping[str, str], note: str) -> str:
    """Marker key: glyph + colour + band name, then the optional relative-thirds note."""
    items = "".join(
        f"<li><i class='dhoa-legend-key dhoa-legend-{band.lower()}' aria-hidden='true'>{glyph}</i>"
        f"{html.escape(str(labels.get(band, band)))}</li>"
        for band, glyph in BANDS
    )
    return (
        f"<div class='dhoa-legend' role='group' aria-label='{html.escape(title, quote=True)}'>"
        f"<strong>{html.escape(title)}</strong><ul>{items}</ul>"
        f"{f'<p>{html.escape(note)}</p>' if note else ''}</div>"
    )


def heat_points(frame: pd.DataFrame, limit: int = MAX_HEAT_POINTS) -> list[list[float]]:
    """Unweighted ``[lat, lon]`` pairs for a density layer (rows without coordinates dropped).

    Every kiln counts once, so the layer shows where kilns cluster and implies no
    risk weighting. At most ``limit`` points are returned (evenly strided).
    """
    if frame.empty or "lat" not in frame or "lon" not in frame:
        return []
    pairs = frame[["lat", "lon"]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(pairs) > limit:
        step = math.ceil(len(pairs) / limit)
        pairs = pairs.iloc[::step]
    return [[round(float(a), 5), round(float(b), 5)] for a, b in pairs.to_numpy()]
