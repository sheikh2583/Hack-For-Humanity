"""Build traceable advisory map popups from prioritized GeoParquet rows.

Input schema: one row containing detection, screening, and optional provenance
columns. Output schema: escaped popup HTML with candidate state and provenance.
"""

from __future__ import annotations

import ast
import html
import json
import math
from collections.abc import Mapping

ADVISORY_NOTICE = (
    "Screening candidates only. Model detections and mapped-feature signals are "
    "not legal or administrative findings. Distances are to mapped feature geometries "
    "and may not be distances to legally controlling boundaries."
)


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
    """Escape a scalar for safe insertion into popup HTML."""
    if value is None:
        return "Not recorded"
    try:
        if value != value:  # NaN
            return "Not recorded"
    except (TypeError, ValueError):
        pass
    text = str(value)
    return html.escape(text if text and text not in {"<NA>", "nan", "NaT"} else "Not recorded")


def build_marker_popup(row: Mapping[str, object], rank: int, total: int) -> str:
    """Render one marker popup with advisory language and signal provenance."""
    signals = parse_candidate_signals(row.get("breached_rules", []))
    provenance = parse_signal_provenance(row.get("signal_provenance_json"))
    if not provenance and signals:
        provenance = unavailable_provenance(signals, row)
    confidence = row.get("confidence")
    try:
        confidence_value = float(confidence)
        confidence_text = f"{confidence_value:.2%}" if math.isfinite(confidence_value) else "Not recorded"
    except (TypeError, ValueError):
        confidence_text = "Not recorded"
    kiln_id = _display(row.get("kiln_id", "Not recorded"))
    klass = _display(row.get("class", "Not recorded"))
    score = _display(row.get("breach_score", "Not recorded"))
    signal_text = ", ".join(_display(signal) for signal in signals) or "None recorded"
    parts = [
        "<div style='min-width:260px;font-family:sans-serif'>",
        f"<h4>Kiln candidate {kiln_id}</h4>",
        "<table>",
        f"<tr><th>Detected class</th><td>{klass}</td></tr>",
        f"<tr><th>Detector confidence</th><td>{confidence_text}</td></tr>",
        f"<tr><th>Screening priority</th><td>#{int(rank)} of {int(total)}</td></tr>",
        f"<tr><th>Screening score</th><td>{score}</td></tr>",
        f"<tr><th>Candidate rule signals</th><td>{signal_text}</td></tr>",
        "</table>",
    ]
    distance_cols = [
        column for column in row
        if column.startswith("dist_") and column.endswith("_m")
    ]
    if distance_cols:
        parts.append("<p><b>Distance to mapped feature geometry</b></p><ul>")
        for column in distance_cols:
            value = row[column]
            try:
                value_text = f"{float(value):.0f} m" if float(value) != float("inf") else "Not available"
            except (TypeError, ValueError):
                value_text = "Not available"
            parts.append(f"<li>{_display(column[5:-2])}: {_display(value_text)}</li>")
        parts.append("</ul>")
    parts.append("<details><summary>Signal source and method</summary>")
    if not provenance:
        parts.append("<p>Per-signal provenance was not recorded in this dataset.</p>")
    else:
        for item in provenance:
            parts.append("<section><hr><b>" + _display(item.get("signal_id")) + "</b><table>")
            for label, key in [
                ("Review state", "review_state"),
                ("Rule config version", "rule_config_version"),
                ("Source layer ID", "source_layer_id"),
                ("Source authority", "source_authority"),
                ("Source URL", "source_url"),
                ("Source version/date", "source_version_date"),
                ("Source accessed at", "source_accessed_at"),
                ("Feature ID", "feature_id"),
                ("Feature geometry provenance", "geometry_provenance"),
                ("Distance (m)", "distance_m"),
                ("Measurement method", "measurement_method"),
                ("Legal instrument ID", "instrument_id"),
                ("Effective dates", "effective_dates"),
                ("Detector model", "detector_model"),
                ("Detector version", "detector_version"),
                ("Detector model/version", "detector_model_version"),
                ("Detector confidence", "detector_confidence"),
                ("Imagery date", "imagery_date"),
                ("Reviewer", "reviewer"),
                ("Review date", "reviewed_at"),
                ("Evidence references", "evidence_references"),
                ("Review notes", "review_notes"),
            ]:
                value = item.get(key)
                if key == "source_url" and isinstance(value, str) and value.startswith(("https://", "http://")):
                    shown = f"<a href='{html.escape(value, quote=True)}' rel='noopener'>{html.escape(value)}</a>"
                else:
                    shown = _display(value)
                parts.append(f"<tr><th>{html.escape(label)}</th><td>{shown}</td></tr>")
            parts.append("</table></section>")
    parts.extend(["</details>", f"<p class='advisory'>{html.escape(ADVISORY_NOTICE)}</p>", "</div>"])
    return "".join(parts)
