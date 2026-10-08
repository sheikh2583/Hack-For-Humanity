"""Filter and present existing KilnWatch candidate fields.

Input schema: candidate DataFrame/GeoDataFrame with optional ``district``,
``class``/``class_name``, ``confidence``, priority, rule-signal, and distance
columns plus a rules mapping. Output schema: a filtered copy with a display-only
``priority_band`` column when existing priority data allows one; other fields
are kept.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

UNKNOWN_SIGNAL = "Unknown / not available"
SIGNAL_PRESENT = "Signal present"
SIGNAL_ABSENT = "Signal absent in available data"
ANY_SIGNAL = "Any"


def _scalar_is_missing(value: object) -> bool:
    """Check missingness for a scalar without treating list values as scalars."""
    if value is None:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if getattr(result, "ndim", 0) == 0 else False
    except (TypeError, ValueError):
        return False


def _signal_ids(value: object) -> set[str] | None:
    """Decode a known rule-ID list; return None when the field is unavailable."""
    if _scalar_is_missing(value):
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, (list, tuple, set)):
        return None
    return {str(item) for item in value if not _scalar_is_missing(item)}


def signal_status(row: Mapping[str, object], rule: Mapping[str, Any]) -> str:
    """Return present, mapped-data absence, or unknown for one configured signal.

    Input schema: one candidate row and one technology/siting rule mapping.
    Output: a status string; missing/non-finite evidence is always unknown.
    """
    rule_id = str(rule.get("id", ""))
    signal_ids = _signal_ids(row.get("breached_rules"))
    if signal_ids is not None and rule_id in signal_ids:
        return SIGNAL_PRESENT

    if rule_id == "technology_flagged":
        value = row.get("technology_flagged")
        if isinstance(value, bool):
            return SIGNAL_PRESENT if value else SIGNAL_ABSENT
        if not _scalar_is_missing(value):
            if str(value).strip().casefold() in {"true", "1"}:
                return SIGNAL_PRESENT
            if str(value).strip().casefold() in {"false", "0"}:
                return SIGNAL_ABSENT
        return UNKNOWN_SIGNAL

    feature = rule.get("feature")
    buffer_m = rule.get("buffer_m")
    if not feature or buffer_m is None:
        return UNKNOWN_SIGNAL
    distance_value = row.get(f"dist_{feature}_m")
    try:
        distance_m = float(distance_value)  # type: ignore[arg-type]
        threshold_m = float(buffer_m)
    except (TypeError, ValueError):
        return UNKNOWN_SIGNAL
    if not math.isfinite(distance_m):
        return UNKNOWN_SIGNAL
    return SIGNAL_PRESENT if distance_m < threshold_m else SIGNAL_ABSENT


def add_signal_status_columns(
    frame: pd.DataFrame, rules: Mapping[str, Any]
) -> pd.DataFrame:
    """Append display-only status fields for configured existing signals.

    Input schema: candidate rows and the active rules mapping. Output: a copy
    with ``screening_signal_status_<rule_id>`` columns; unknown source coverage
    remains explicitly unknown and original pipeline fields are preserved.
    """
    result = frame.copy()
    signal_rules: list[dict[str, Any]] = []
    if rules.get("technology"):
        signal_rules.append({"id": "technology_flagged", **rules["technology"]})
    signal_rules.extend(rules.get("siting_rules", []))
    for rule in signal_rules:
        signal_id = str(rule.get("id", ""))
        if signal_id:
            result[f"screening_signal_status_{signal_id}"] = result.apply(
                signal_status, axis=1, rule=rule
            )
    return result


def add_priority_bands(frame: pd.DataFrame) -> pd.DataFrame:
    """Add display-only relative thirds from existing band, rank, or score.

    Input schema: candidate rows, optionally containing ``priority_band``,
    ``priority_rank`` (1 is highest), or continuous ``priority``. Output:
    copied rows, with ``priority_band`` when priority data exists; relative
    thirds are derived only when no stored band exists. Scores and rule fields
    are not changed.
    """
    result = frame.copy()
    if "priority_band" in result.columns:
        result["priority_band"] = result["priority_band"].astype("object").where(
            result["priority_band"].notna(), UNKNOWN_SIGNAL
        )
        return result

    if "priority_rank" in result.columns:
        rank = pd.to_numeric(result["priority_rank"], errors="coerce")
        if not rank.notna().any() and "priority" in result.columns:
            rank = pd.to_numeric(result["priority"], errors="coerce").rank(
                method="min", ascending=False
            )
    elif "priority" in result.columns:
        priority = pd.to_numeric(result["priority"], errors="coerce")
        rank = priority.rank(method="min", ascending=False)
    else:
        return result

    valid = rank.notna()
    count = int(valid.sum())
    if not count:
        result["priority_band"] = UNKNOWN_SIGNAL
        return result

    high_cutoff = math.ceil(count / 3)
    medium_cutoff = math.ceil(2 * count / 3)
    result["priority_band"] = UNKNOWN_SIGNAL
    result.loc[valid & (rank <= high_cutoff), "priority_band"] = "High"
    result.loc[valid & (rank > high_cutoff) & (rank <= medium_cutoff), "priority_band"] = "Medium"
    result.loc[valid & (rank > medium_cutoff), "priority_band"] = "Low"
    return result


def apply_candidate_filters(
    frame: pd.DataFrame,
    rules: Mapping[str, Any],
    *,
    districts: set[str] | None = None,
    classes: set[str] | None = None,
    confidence_range: tuple[float, float] | None = None,
    priority_bands: set[str] | None = None,
    signal_filters: Mapping[str, str] | None = None,
    priority_order: str = "High to Low",
) -> pd.DataFrame:
    """Apply active area, detector, priority, and signal filters with AND logic.

    Input schema: candidate frame, rules mapping, and optional filter values.
    Output schema: filtered copy using the same rows/columns plus a display-only
    priority band. Unavailable fields are not interpreted as negative signals.
    """
    result = frame.copy()
    if "class" not in result.columns and "class_name" in result.columns:
        result["class"] = result["class_name"]
    result = add_priority_bands(result)
    mask = pd.Series(True, index=result.index)

    if districts and "district" in result.columns:
        mask &= result["district"].astype("string").isin(districts)
    if classes and "class" in result.columns:
        mask &= result["class"].astype("string").isin(classes)
    if confidence_range is not None and "confidence" in result.columns:
        confidence = pd.to_numeric(result["confidence"], errors="coerce")
        low, high = confidence_range
        mask &= confidence.between(low, high, inclusive="both")
    if priority_bands:
        if "priority_band" in result.columns:
            mask &= result["priority_band"].astype("string").isin(priority_bands)
        else:
            mask &= False

    signal_filters = signal_filters or {}
    configured_rules = list(rules.get("siting_rules", []))
    if rules.get("technology"):
        configured_rules.insert(
            0,
            {
                "id": "technology_flagged",
                "feature": None,
                "buffer_m": None,
                **dict(rules["technology"]),
            },
        )
    rules_by_id = {str(rule.get("id", "")): rule for rule in configured_rules}
    for rule_id, requested_status in signal_filters.items():
        if requested_status == ANY_SIGNAL or rule_id not in rules_by_id:
            continue
        statuses = result.apply(signal_status, axis=1, rule=rules_by_id[rule_id])
        mask &= statuses.eq(requested_status)

    result = result.loc[mask].copy()
    rank_values = (
        pd.to_numeric(result["priority_rank"], errors="coerce")
        if "priority_rank" in result.columns else pd.Series(dtype=float)
    )
    if rank_values.notna().any():
        ascending = priority_order != "Low to High"
        result = result.assign(_dashboard_rank=rank_values).sort_values(
            "_dashboard_rank", ascending=ascending, na_position="last"
        ).drop(columns="_dashboard_rank")
    elif "priority" in result.columns:
        ascending = priority_order == "Low to High"
        result = result.sort_values("priority", ascending=ascending, na_position="last")
    elif "priority_band" in result.columns:
        present_bands = set(result["priority_band"].astype(str))
        known_order = ["High", "Medium", "Low", UNKNOWN_SIGNAL]
        if not present_bands.issubset(set(known_order)):
            return result
        order = [band for band in known_order if band in present_bands]
        if priority_order == "Low to High":
            order = list(reversed(order))
        result["priority_band"] = pd.Categorical(
            result["priority_band"], categories=order, ordered=True
        )
        result = result.sort_values("priority_band", na_position="last")
    return result
