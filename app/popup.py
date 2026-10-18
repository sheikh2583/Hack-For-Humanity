"""Build traceable advisory map popups from prioritized GeoParquet rows.

Input schema: one row containing detection, screening, and optional provenance
columns. Output schema: escaped popup HTML with candidate state and provenance.
"""

from __future__ import annotations

import ast
import html
import json
import math
import re
import sys
from collections.abc import Mapping
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

ADVISORY_NOTICE = (
    "Screening outputs only. Model detections and mapped-feature signals are "
    "candidates for human review. Distances are to mapped feature geometries "
    "and may not be distances to legally controlling boundaries."
)

_POPUP_TERM_REPLACEMENTS = (
    (re.compile(r"non[-_ ]compliant", re.IGNORECASE), "flagged for review"),
    (re.compile(r"confirmed", re.IGNORECASE), "unverified candidate"),
    (re.compile(r"unverified(?:_candidate)?|verified", re.IGNORECASE), "screened"),
    (re.compile(r"violation", re.IGNORECASE), "candidate signal"),
    (re.compile(r"illegal", re.IGNORECASE), "kiln candidate"),
    (re.compile(r"breach(?:ed|es)?", re.IGNORECASE), "rule signal"),
    (re.compile(r"legal\s+findings?", re.IGNORECASE), "screening output"),
)


def sanitize_popup_text(value: object) -> str:
    """Replace legal or developer-facing terms in visible marker text.

    Input schema: a scalar destined for map popup text. Output schema: an
    HTML-escaped, user-facing string with prohibited terms replaced.
    """
    text = str(value)
    for pattern, replacement in _POPUP_TERM_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return html.escape(text)


def _area_component(value: object) -> str | None:
    """Return a cleaned administrative area component, or None if absent."""
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return None if text.casefold() in {"", "<na>", "nan", "nat", "none"} else text


def format_district_label(value: object) -> str:
    """Translate known district values while preserving other names."""
    text = _area_component(value)
    if text is None:
        return "অজানা এলাকা"
    return {
        "All Districts": "সব জেলা",
        "Chapainawabganj": "চাঁপাইনবাবগঞ্জ",
        "Gazipur": "গাজীপুর",
        "Rajshahi": "রাজশাহী",
        "Dhaka": "ঢাকা",
        "Chittagong": "চট্টগ্রাম",
    }.get(text, text)


def format_area_name(row: Mapping[str, object]) -> str:
    """Format an administrative area as upazila, district with safe fallback.

    Input schema: mapping with optional ``upazila`` and ``district`` values.
    Output schema: ``upazila, district``, district only, or ``অজানা এলাকা``.
    """
    upazila = _area_component(row.get("upazila"))
    district = _area_component(row.get("district"))
    if district is not None:
        district = format_district_label(district)
    if upazila and district:
        return f"{upazila}, {district}"
    return upazila or district or "অজানা এলাকা"


def parse_candidate_signals(value: object) -> list[str]:
    """Safely normalize a signal-ID attribute without evaluating code."""
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    if not isinstance(value, str) or not value:
        return []
    if not value.startswith("["):
        return [value]
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return [value]
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed
    return [value]


def parse_signal_provenance(value: object) -> list[dict[str, object]]:
    """Parse serialized per-signal provenance, returning an empty list if absent."""
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [dict(item) for item in parsed if isinstance(item, Mapping)]


def unavailable_provenance(
    signal_ids: list[str], row: Mapping[str, object] | None = None
) -> list[dict[str, object]]:
    """Describe missing provenance for signals from pre-provenance datasets."""
    if row is None:
        row = {}
    return [
        {
            "signal_id": signal_id,
            "review_state": "unverified_candidate",
            "rule_config_version": row.get("rules_version"),
            "source_layer_id": None,
            "source_authority": None,
            "source_url": None,
            "source_version_date": None,
            "source_accessed_at": None,
            "instrument_id": None,
            "effective_dates": None,
            "feature_id": None,
            "geometry_provenance": "Not retained in this legacy dataset",
            "distance_m": None,
            "measurement_method": "Not retained in this legacy dataset",
            "detector_model": row.get("detector_model"),
            "detector_version": row.get("detector_version"),
            "detector_model_version": " / ".join(
                str(row[key]) for key in ("detector_model", "detector_version")
                if row.get(key) is not None
            ) or None,
            "detector_confidence": row.get("confidence"),
            "imagery_date": row.get("imagery_date"),
            "reviewer": None,
            "reviewed_at": None,
            "evidence_references": [],
            "review_notes": "Legacy data predates per-signal provenance; missing provenance is not evidence that the signal was absent.",
        }
        for signal_id in signal_ids
    ]


def _display(value: object) -> str:
    """Escape a scalar for safe insertion into popup HTML.

    Input schema: scalar popup value. Output schema: escaped Bengali display text.
    """
    if value is None:
        return "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    try:
        if math.isnan(value):
            return "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    except (TypeError, ValueError):
        pass
    text = str(value)
    text = text if text and text not in {"<NA>", "nan", "NaT"} else "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    return sanitize_popup_text(text)


def build_marker_popup(row: Mapping[str, object], rank: int, total: int) -> str:
    """Render concise Bengali marker details for one candidate row.

    Input schema: one row with kiln, area, class, priority, confidence, and
    optional score/signal/distance fields. Output schema: escaped popup HTML.
    """
    confidence = row.get("confidence")
    try:
        confidence_value = float(confidence)
        confidence_text = f"{confidence_value:.2%}" if math.isfinite(confidence_value) else _display(None)
    except (TypeError, ValueError):
        confidence_text = _display(None)

    kiln_id = _display(row.get("kiln_id"))
    class_value = str(row.get("class", ""))
    class_label = {
        "FCBK": "\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf",
        "Zigzag": "\u099c\u09bf\u0997\u099c\u09be\u0997",
    }.get(class_value, "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987")
    area = _display(format_area_name(row))
    priority = {
        "High": "\u0989\u099a\u09cd\u099a",
        "Medium": "\u09ae\u09be\u099d\u09be\u09b0\u09bf",
        "Low": "\u09a8\u09bf\u09ae\u09cd\u09a8",
    }.get(str(row.get("priority_band", "")), "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987")
    score = _display(row.get("breach_score"))
    signal_labels = {
        "near_school": "\u09b6\u09bf\u0995\u09cd\u09b7\u09be \u09aa\u09cd\u09b0\u09a4\u09bf\u09b7\u09cd\u09a0\u09be\u09a8\u09c7\u09b0 \u0995\u09be\u099b\u09c7",
        "near_hospital": "\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2\u09c7\u09b0 \u0995\u09be\u099b\u09c7",
        "near_railway": "\u09b0\u09c7\u09b2\u09aa\u09a5\u09c7\u09b0 \u0995\u09be\u099b\u09c7",
        "near_forest": "\u09ac\u09a8\u09c7\u09b0 \u0995\u09be\u099b\u09c7",
        "near_waterbody": "\u099c\u09b2\u09be\u09b6\u09df\u09c7\u09b0 \u0995\u09be\u099b\u09c7",
        "technology_flagged": "\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf \u09aa\u09cd\u09b0\u09af\u09c1\u0995\u09cd\u09a4\u09bf",
    }
    signals = parse_candidate_signals(row.get("breached_rules", []))
    signal_text = ", ".join(signal_labels.get(str(signal), "\u0985\u09a8\u09cd\u09af\u09be\u09a8\u09cd\u09af \u09b8\u0999\u09cd\u0995\u09c7\u09a4") for signal in signals)
    if not signal_text:
        signal_text = "\u0995\u09cb\u09a8\u09cb \u09b8\u0999\u09cd\u0995\u09c7\u09a4 \u09a8\u09c7\u0987"

    parts = [
        "<div style='min-width:260px;font-family:sans-serif'>",
        f"<h4>\u09ad\u09be\u099f\u09be \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 {kiln_id}</h4>",
        "<table>",
        f"<tr><th>\u09ad\u09be\u099f\u09be\u09b0 \u09a7\u09b0\u09a8</th><td>{class_label}</td></tr>",
        f"<tr><th>\u098f\u09b2\u09be\u0995\u09be</th><td>{area}</td></tr>",
        f"<tr><th>\u09ae\u09a1\u09c7\u09b2\u09c7\u09b0 \u0986\u09a4\u09cd\u09ae\u09ac\u09bf\u09b6\u09cd\u09ac\u09be\u09b8</th><td>{confidence_text}</td></tr>",
        f"<tr><th>\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0</th><td>{priority} (#{int(rank)} / {int(total)})</td></tr>",
        f"<tr><th>\u09a8\u09bf\u09df\u09ae\u09c7\u09b0 \u09b8\u0999\u09cd\u0995\u09c7\u09a4</th><td>{signal_text}</td></tr>",
        f"<tr><th>\u09b8\u0999\u09cd\u0995\u09c7\u09a4 \u09b8\u0999\u09cd\u0996\u09cd\u09af\u09be</th><td>{score}</td></tr>",
        "</table>",
    ]
    distance_labels = {
        "school": "\u09b6\u09bf\u0995\u09cd\u09b7\u09be \u09aa\u09cd\u09b0\u09a4\u09bf\u09b7\u09cd\u09a0\u09be\u09a8",
        "hospital": "\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2",
        "railway": "\u09b0\u09c7\u09b2\u09aa\u09a5",
        "forest": "\u09ac\u09a8",
        "waterbody": "\u099c\u09b2\u09be\u09b6\u09df",
    }
    distances = [column for column in row if column.startswith("dist_") and column.endswith("_m")]
    if distances:
        parts.append("<p><b>\u09a8\u09bf\u0995\u099f\u09ac\u09b0\u09cd\u09a4\u09c0 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac</b></p><ul>")
        for column in distances:
            try:
                value_text = f"{float(row[column]):.0f} \u09ae\u09bf\u099f\u09be\u09b0" if math.isfinite(float(row[column])) else _display(None)
            except (TypeError, ValueError):
                value_text = _display(None)
            feature = column[5:-2]
            parts.append(f"<li>{distance_labels.get(feature, '\u0985\u099e\u09be\u09a4')} : {_display(value_text)}</li>")
        parts.append("</ul>")
    parts.append("</div>")
    return "".join(parts)
