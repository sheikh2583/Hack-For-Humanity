"""Dashboard labels and advisory CSV serialization.

Input schema: prioritized kiln DataFrame from the pipeline. Output schema:
user-facing labels and a CSV with non-conclusive names plus an advisory notice.
"""

from __future__ import annotations

import html
import json
import math

import pandas as pd

from app.popup import (
    ADVISORY_NOTICE,
    parse_candidate_signals,
    parse_signal_provenance,
    unavailable_provenance,
)

DASHBOARD_LABELS = {
    "page_title": "KilnWatch BD — Screening Candidates",
    "subtitle": "Satellite-based kiln-candidate screening dashboard",
    "map_title": "Kiln Candidate Map",
    "table_title": "Kiln Candidate Details",
    "count": "Kiln Candidates",
    "signals": "Candidates with Rule Signals",
    "technology": "Technology Candidate Signals",
    "max_score": "Maximum Screening Score",
    "priority_filter": "Show Top N by Screening Priority",
    "export": "📥 Export screening candidates as CSV",
    "advisory": ADVISORY_NOTICE,
}

EXPORT_RENAMES = {
    "breached_rules": "candidate_rule_signals",
    "breach_count": "candidate_rule_signal_count",
    "breach_score": "screening_score",
    "priority": "screening_priority",
    "priority_rank": "screening_priority_rank",
    "technology_flagged": "technology_candidate_signal",
    "rules_version": "rule_config_version",
    "class": "detected_class",
    "confidence": "detector_confidence",
}

DETAIL_COLUMN_RENAMES = {
    "class": "detected_class",
    "confidence": "detector_confidence",
    "breached_rules": "candidate_rule_signals",
    "signal_provenance_json": "signal_provenance",
    "breach_count": "candidate_rule_signal_count",
    "breach_score": "screening_score",
    "priority_rank": "screening_priority_rank",
    "priority": "screening_priority",
}


def with_signal_provenance(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with JSON provenance, marking missing legacy details explicitly."""
    result = df.copy()
    result["signal_provenance_json"] = [
        json.dumps(
            parse_signal_provenance(row.get("signal_provenance_json"))
            or unavailable_provenance(
                parse_candidate_signals(row.get("breached_rules", [])), row
            ),
            ensure_ascii=False,
            default=str,
        )
        for _, row in result.iterrows()
    ]
    return result


def marker_tooltip(row: pd.Series, rank: int) -> str:
    """Format the concise, non-conclusive marker tooltip."""
    try:
        confidence_value = float(row["confidence"])
        confidence = f"{confidence_value:.0%}" if math.isfinite(confidence_value) else "not recorded"
    except (KeyError, TypeError, ValueError):
        confidence = "not recorded"
    return (
        f"Screening priority #{int(rank)} | Kiln candidate | "
        f"{html.escape(str(row.get('class', 'unknown')))} | detector {confidence}"
    )


def screening_csv(df: pd.DataFrame) -> str:
    """Serialize advisory candidate rows with traceable, non-conclusive fields."""
    exported = with_signal_provenance(df).drop(
        columns=["geometry", "rules_verified"], errors="ignore"
    )
    exported = exported.rename(columns=EXPORT_RENAMES)
    exported = exported.rename(
        columns={
            column: f"distance_to_mapped_{column[5:-2]}_m"
            for column in exported.columns
            if column.startswith("dist_") and column.endswith("_m")
        }
    )
    for column in ("candidate_rule_signals", "signal_provenance_json"):
        if column in exported.columns:
            exported[column] = exported[column].map(
                lambda value: json.dumps(value, ensure_ascii=False, default=str)
                if isinstance(value, (list, dict, tuple))
                else value
            )
    exported["advisory_use_notice"] = ADVISORY_NOTICE
    order = ["advisory_use_notice"] + [
        column for column in exported.columns if column != "advisory_use_notice"
    ]
    exported = exported[order]
    preamble = (
        "# KilnWatch BD advisory screening export. Detections and mapped-feature "
        "signals are unverified candidates, not legal or administrative findings. "
        "Distances are to mapped feature geometries and may not be distances to "
        "legally controlling boundaries.\n"
    )
    return preamble + exported.to_csv(index=False)
