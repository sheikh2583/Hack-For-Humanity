"""Streamlit-free data layer for the Dhoa dashboard (module M2).

Everything here is a pure function of a kiln table plus the siting rules read
from ``config/rules.yaml``; nothing imports Streamlit, folium or geopandas, so
it can be unit-tested with tiny synthetic frames.

Input schema
------------
A kiln ``pandas.DataFrame`` (or ``geopandas.GeoDataFrame`` in EPSG:4326) with,
when available: ``kiln_id``, ``lat``, ``lon`` (WGS84 degrees), ``district``,
``upazila``, ``class`` / ``class_name``, ``priority_band`` (High / Medium /
Low), ``priority``, ``detection_status``, ``breached_rules`` (list of rule
ids) and ``dist_<feature>_m`` distance columns. Rules are the ``siting_rules``
list from ``config/rules.yaml`` (dicts with ``id``, ``feature``, ``buffer_m``).
Legal distances are never hard-coded here; they are always read from ``rules``.

Output schema
-------------
* ``FilterKey`` / ``filter_positions`` / ``take_candidates``: the filtered rows
  of the input, sorted by ``priority`` descending (NaN last).
* ``with_display_columns`` / ``prepare_display_frame`` / ``popup_html_list``: the same rows plus the
  precomputed display columns in ``DISPLAY_COLUMNS`` (Bangla labels, map
  tooltip, popup HTML) so the app never formats text row by row at render time.
* ``build_list_frame``: the priority-list table (Bangla headers, one distance
  column per rule).
* ``distances_from_point_m`` / ``nearest_position``: metre distances measured
  in the projected CRS chosen by ``src.geo.crs.get_projected_crs``.
"""

from __future__ import annotations

import html
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

from app import strings as T  # noqa: E402
from popup import format_district_label  # noqa: E402

ALL_KILN_TYPES = "__all__"
ALL_DISTRICTS = "__all_districts__"
ALL_AREAS = "__all_areas__"
UNKNOWN_PRIORITY = "Unknown / not available"
PRIORITY_ORDER: tuple[str, ...] = ("High", "Medium", "Low")
NEW_CANDIDATE_STATUS = "New candidate (2025-26)"
KNOWN_CANDIDATE_STATUS = "Known (2023-24 survey)"

# Display-only "amber" band of the popup traffic light: a distance up to this
# multiple of a rule's buffer is shown yellow. It is not a legal number.
NEAR_THRESHOLD_FACTOR = 1.5

DISPLAY_COLUMNS: tuple[str, ...] = (
    "ui_area",
    "ui_type",
    "ui_priority",
    "ui_tooltip",
    "ui_popup_html",
)
"""Columns added by ``with_display_columns`` (all prefixed ``ui_``)."""

_KNOWN_DISTRICTS = {"Dhaka", "Gazipur", "Rajshahi", "Chittagong", "Chapainawabganj"}
_NULLISH = {"", "nan", "none", "<na>", "nat"}
_PRIORITY_FROM_LABEL = T.LazyMapping(
    lambda: {
        **{"High": "High", "Medium": "Medium", "Low": "Low"},
        **{label: "High" for label in T.variants("HIGH")},
        **{label: "Medium" for label in T.variants("MEDIUM")},
        **{label: "Low" for label in T.variants("LOW")},
    }
)
"""Any spelling of a priority (canonical English or a label in any language) -> canonical."""
_PRIORITY_LABELS = T.LazyMapping(
    lambda: {
        "High": T.HIGH, "Medium": T.MEDIUM, "Low": T.LOW,
        **{label: T.HIGH for label in T.variants("HIGH")},
        **{label: T.MEDIUM for label in T.variants("MEDIUM")},
        **{label: T.LOW for label in T.variants("LOW")},
    }
)
# Priority is shown by shape AND colour (never colour alone): triangle / diamond / circle.
PRIORITY_GLYPHS = {"High": "▲", "Medium": "◆", "Low": "●"}
_PRIORITY_ICONS = PRIORITY_GLYPHS
_DISTRICT_LABELS = T.LazyMapping(
    lambda: {
        "Chapainawabganj": T.DISTRICT_CHAPAINAWABGANJ,
        "Gazipur": T.DISTRICT_GAZIPUR,
        "Rajshahi": T.DISTRICT_RAJSHAHI,
        "Dhaka": T.DISTRICT_DHAKA,
        "Chittagong": T.DISTRICT_CHITTAGONG,
    }
)
_FEATURE_LABELS = T.LazyMapping(
    lambda: {
        "schools": T.SCHOOL,
        "hospitals": T.HOSPITAL,
        "railways": T.RAILWAY,
        "settlements": T.SETTLEMENT,
        "government_forest": T.GOVERNMENT_FOREST,
        "water": T.WETLAND,
    }
)
# (rule id, Bangla label, candidate distance columns in priority order)
_POPUP_RULES = T.LazySequence(
    lambda: (
        ("near_school", T.SCHOOL, ("dist_school_m", "dist_schools_m")),
        ("near_hospital", T.HOSPITAL, ("dist_hospital_m", "dist_hospitals_m")),
        ("near_railway", T.RAILWAY, ("dist_rail_m", "dist_railway_m", "dist_railways_m")),
        (
            "near_government_forest",
            T.FOREST,
            ("dist_forest_m", "dist_government_forest_m", "dist_forests_m"),
        ),
        ("near_settlement", T.SETTLEMENT, ("dist_settlement_m", "dist_settlements_m")),
        ("near_wetland", T.WETLAND, ("dist_water_m",)),
    )
)
_WARNING_MARK = " ⚠️"


# --------------------------------------------------------------------------
# Scalar and column helpers
# --------------------------------------------------------------------------
def to_float(value: object) -> float:
    """Convert one scalar to ``float``; anything unparsable becomes NaN.

    Input: any object. Output: a float, NaN for None, NA, blanks and text.
    Replaces the per-call ``pd.to_numeric(pd.Series([value]))`` pattern.
    """
    if value is None:
        return math.nan
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return math.nan


def numeric_column(frame: pd.DataFrame, names: Iterable[str]) -> np.ndarray:
    """Return the first non-missing numeric value across ``names`` per row.

    Input: a frame and candidate column names in priority order. Output: a
    float64 array aligned to ``frame`` (NaN where every candidate is missing
    or the columns do not exist).
    """
    result = np.full(len(frame), np.nan, dtype="float64")
    for name in names:
        if name not in frame.columns:
            continue
        values = pd.to_numeric(frame[name], errors="coerce").to_numpy(
            dtype="float64", na_value=np.nan
        )
        result = np.where(np.isnan(result), values, result)
    return result


def parse_signal_ids(value: object) -> frozenset[str]:
    """Decode a ``breached_rules`` cell into a set of rule ids.

    Input: list/tuple/set/ndarray of ids, a JSON list string, a comma
    separated string, or a missing value. Output: a frozenset of non-blank
    ids (empty when the value is missing or unreadable).
    """
    if value is None:
        return frozenset()
    loaded: object
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return frozenset()
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            loaded = [part.strip() for part in text.split(",")]
    elif hasattr(value, "tolist"):
        loaded = value.tolist()
    else:
        loaded = value
    if not isinstance(loaded, (list, tuple, set, frozenset)):
        return frozenset()
    ids: set[str] = set()
    for item in loaded:
        if item is None:
            continue
        text = str(item).strip()
        if text.casefold() not in _NULLISH:
            ids.add(text)
    return frozenset(ids)


def _breached_sets(frame: pd.DataFrame) -> list[frozenset[str]]:
    """Parse the ``breached_rules`` column once for every row."""
    if "breached_rules" not in frame.columns:
        return [frozenset()] * len(frame)
    return [parse_signal_ids(value) for value in frame["breached_rules"].tolist()]


def _clean_text(value: object) -> str | None:
    """Return a stripped string, or None for missing/blank values."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


# --------------------------------------------------------------------------
# Bangla labels (scalar + per-column)
# --------------------------------------------------------------------------
def type_label(value: object) -> str:
    """Return the Bangla kiln-type label (anything except FCBK is Zigzag)."""
    return T.FIXED_CHIMNEY_KILN if str(value) == "FCBK" else T.ZIGZAG_KILN


def priority_label(value: object) -> str:
    """Translate an English or Bangla priority band; unknown -> UNCLASSIFIED."""
    return _PRIORITY_LABELS.get(str(value), T.UNCLASSIFIED)


def priority_badge(value: object) -> str:
    """Return ``glyph + label`` for a priority band (shape plus text, not colour only)."""
    glyph = PRIORITY_GLYPHS.get(str(value), "")
    return f"{glyph} {priority_label(value)}".strip()


def priority_summary(frame: pd.DataFrame) -> dict[str, int]:
    """Count the filtered kilns for the Inspector summary strip.

    Input: kiln frame with optional ``priority_band`` and ``detection_status``
    columns. Output: ``{"total", "high", "medium", "low", "new"}`` integers
    (missing columns count as zero), computed column-wise.
    """
    bands = (
        frame["priority_band"].astype(str) if "priority_band" in frame.columns
        else pd.Series("", index=frame.index)
    )
    status = (
        frame["detection_status"].astype(str) if "detection_status" in frame.columns
        else pd.Series("", index=frame.index)
    )
    return {
        "total": int(len(frame)),
        "high": int(bands.eq("High").sum()),
        "medium": int(bands.eq("Medium").sum()),
        "low": int(bands.eq("Low").sum()),
        "new": int(status.eq(NEW_CANDIDATE_STATUS).sum()),
    }


def district_label(value: object) -> str:
    """Translate a district name; unknown names pass through formatted."""
    text = str(value)
    if text == ALL_DISTRICTS:
        return T.ALL_DISTRICTS
    return _DISTRICT_LABELS.get(text, format_district_label(value))


def area_display_name(upazila: object, district: object) -> str:
    """Format a kiln's area as ``upazila, district`` in Bangla.

    Input: raw upazila and district values (either may be missing). Output:
    the joined label, the lone district/upazila, or ``T.UNKNOWN_AREA``.
    """
    parts = [part for part in (_clean_text(upazila), _clean_text(district)) if part]
    if not parts:
        return T.UNKNOWN_AREA
    if len(parts) > 1:
        parts[-1] = district_label(parts[-1])
    elif parts[0] in _KNOWN_DISTRICTS:
        parts[0] = district_label(parts[0])
    return ", ".join(parts)


def _column_list(frame: pd.DataFrame, name: str) -> list[object]:
    """Return a column as a python list, or Nones when it does not exist."""
    if name in frame.columns:
        return frame[name].tolist()
    return [None] * len(frame)


def area_labels(frame: pd.DataFrame) -> list[str]:
    """Return ``area_display_name`` for every row (memoised per pair)."""
    memo: dict[tuple[object, object], str] = {}
    labels: list[str] = []
    for pair in zip(_column_list(frame, "upazila"), _column_list(frame, "district")):
        label = memo.get(pair)
        if label is None:
            label = area_display_name(*pair)
            memo[pair] = label
        labels.append(label)
    return labels


def _type_source(frame: pd.DataFrame) -> list[object]:
    """Kiln class per row, preferring ``class_name`` and falling back to ``class``."""
    names = _column_list(frame, "class_name")
    classes = _column_list(frame, "class")
    return [
        fallback if (name is None or _is_na(name)) else name
        for name, fallback in zip(names, classes)
    ]


def _is_na(value: object) -> bool:
    """Scalar-safe ``pd.isna`` (list-like cells are not missing)."""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------
class FilterKey(NamedTuple):
    """Hashable fingerprint of the inspector filters (cache key)."""

    district: str = ALL_DISTRICTS
    upazila: str = ALL_AREAS
    kiln_type: str = ALL_KILN_TYPES
    priorities: tuple[str, ...] = PRIORITY_ORDER


def make_filter_key(
    district: object = ALL_DISTRICTS,
    upazila: object = ALL_AREAS,
    kiln_type: object = ALL_KILN_TYPES,
    priorities: Iterable[object] | None = None,
) -> FilterKey:
    """Normalise raw widget values into a canonical ``FilterKey``.

    Input: widget values; priorities may be English (High) or Bangla labels,
    in any order. Output: a key whose priorities are canonical English values
    in High/Medium/Low order; an empty or unrecognised selection means all.
    """
    chosen = {
        _PRIORITY_FROM_LABEL[str(item)]
        for item in (priorities or ())
        if str(item) in _PRIORITY_FROM_LABEL
    }
    selected = tuple(band for band in PRIORITY_ORDER if band in chosen) or PRIORITY_ORDER
    return FilterKey(str(district), str(upazila), str(kiln_type), selected)


def filter_positions(frame: pd.DataFrame, key: FilterKey) -> np.ndarray:
    """Return row positions (for ``iloc``) matching ``key``, in display order.

    Input: kiln frame and a ``FilterKey``. Output: int array of positions;
    a missing filter column yields no rows, a frame without any known priority
    band skips the priority filter, and rows are sorted by ``priority``
    descending (NaN last, ties keep source order).
    """
    empty = np.empty(0, dtype=np.intp)
    mask = np.ones(len(frame), dtype=bool)
    if key.district != ALL_DISTRICTS:
        if "district" not in frame.columns:
            return empty
        mask &= frame["district"].astype(str).eq(str(key.district)).to_numpy()
    if key.upazila != ALL_AREAS:
        if "upazila" not in frame.columns:
            return empty
        mask &= frame["upazila"].astype(str).eq(str(key.upazila)).to_numpy()
    if key.kiln_type != ALL_KILN_TYPES:
        type_column = "class" if "class" in frame.columns else "class_name"
        if type_column not in frame.columns:
            return empty
        mask &= frame[type_column].astype(str).eq(str(key.kiln_type)).to_numpy()
    if "priority_band" in frame.columns:
        band = frame["priority_band"].astype(str)
        known = band.isin(PRIORITY_ORDER).to_numpy()
        # Same rule as the original filter: when no remaining row has a known
        # band, skip the priority filter instead of showing an empty map.
        if (known & mask).any():
            mask &= band.isin(key.priorities).to_numpy()
    positions = np.flatnonzero(mask)
    if "priority" in frame.columns and positions.size > 1:
        values = pd.to_numeric(frame["priority"], errors="coerce").to_numpy(
            dtype="float64", na_value=np.nan
        )[positions]
        order = (
            pd.Series(values)
            .sort_values(ascending=False, na_position="last", kind="stable")
            .index.to_numpy()
        )
        positions = positions[order]
    return positions


def take_candidates(frame: pd.DataFrame, positions: np.ndarray) -> pd.DataFrame:
    """Return an independent copy of ``frame`` rows at ``positions``.

    Adds ``priority_band = "Unknown / not available"`` when the source has no
    priority column, so downstream code can rely on it.
    """
    result = frame.iloc[np.asarray(positions, dtype=np.intp)].copy()
    if "priority_band" not in result.columns:
        result["priority_band"] = UNKNOWN_PRIORITY
    return result


def filter_candidates(frame: pd.DataFrame, key: FilterKey) -> pd.DataFrame:
    """Filter ``frame`` by ``key`` (pure; see ``filter_positions``)."""
    return take_candidates(frame, filter_positions(frame, key))


# --------------------------------------------------------------------------
# List table
# --------------------------------------------------------------------------
def distance_cells(values: np.ndarray, threshold: float) -> list[str]:
    """Format metre distances for the list: m / km text, warning inside buffer.

    Input: float array (NaN = unknown) and the rule buffer in metres (NaN =
    no warning). Output: one display string per value.
    """
    check = not math.isnan(threshold)
    cells: list[str] = []
    for value in values.tolist():
        if value != value:
            cells.append(T.NO_DATA)
            continue
        text = T.KM_FMT.format(value / 1000) if value >= 1000 else T.M_FMT.format(value)
        if check and value < threshold:
            text += _WARNING_MARK
        cells.append(text)
    return cells


def rule_column_label(rule: Mapping[str, Any]) -> str:
    """Return the Bangla list-column header for one siting rule."""
    feature = str(rule.get("feature"))
    return T.DISTANCE_FROM_FMT.format(_FEATURE_LABELS.get(feature, feature))


def build_list_frame(frame: pd.DataFrame, rules: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Build the selectable priority-list table without per-row Python calls.

    Input: kiln frame (optionally with ``ui_area``) and ``siting_rules``.
    Output: columns [view button, area, priority] plus one distance column per
    rule, one row per input row, default RangeIndex.
    """
    count = len(frame)
    areas = frame["ui_area"].tolist() if "ui_area" in frame.columns else area_labels(frame)
    bands = (
        [str(value) for value in frame["priority_band"].tolist()]
        if "priority_band" in frame.columns
        else [""] * count
    )
    data: dict[str, list[str]] = {
        T.VIEW_KILN: [T.VIEW_KILN] * count,
        T.AREA: [f"📍 {area}" for area in areas],
        T.PRIORITY: [
            priority_badge(band) for band in bands
        ],
    }
    for rule in rules:
        values = numeric_column(frame, (f"dist_{rule.get('feature')}_m",))
        data[rule_column_label(rule)] = distance_cells(values, to_float(rule.get("buffer_m")))
    return pd.DataFrame(data)


# --------------------------------------------------------------------------
# Popup / tooltip / display columns
# --------------------------------------------------------------------------
def rule_signal_rows_html(
    frame: pd.DataFrame, rules: Sequence[Mapping[str, Any]]
) -> list[str]:
    """Render the popup rule-signal rows (traffic-light dot + distance).

    Input: kiln frame and ``siting_rules``. Output: one escaped HTML string
    per row. Thresholds come from ``rules``; a rule absent from ``rules`` or a
    missing distance renders as the grey "no data" dot.
    """
    if len(frame) == 0:
        return []
    rules_by_id = {str(rule.get("id")): rule for rule in rules}
    breached = _breached_sets(frame)
    per_rule: list[list[str]] = []
    for rule_id, label, columns in _POPUP_RULES:
        threshold = to_float(rules_by_id.get(rule_id, {}).get("buffer_m"))
        near_limit = threshold * NEAR_THRESHOLD_FACTOR
        label_html = html.escape(label)
        cells: list[str] = []
        for distance, ids in zip(numeric_column(frame, columns).tolist(), breached):
            if distance != distance or threshold != threshold:
                icon, text = "⚪", T.NO_DATA
            elif rule_id in ids or distance <= threshold:
                icon, text = "🔴", T.M_DOT_FMT.format(distance)
            elif distance <= near_limit:
                icon, text = "🟡", T.M_DOT_FMT.format(distance)
            else:
                icon, text = "🟢", T.OUTSIDE_THRESHOLD
            cells.append(
                f"<div class='rule-signal-row'><span>{icon}</span> "
                f"{label_html}: {html.escape(text)}</div>"
            )
        per_rule.append(cells)
    return ["".join(parts) for parts in zip(*per_rule)]


def popup_html_list(frame: pd.DataFrame, rules: Sequence[Mapping[str, Any]]) -> list[str]:
    """Render the 320 px kiln popup HTML for every row in one pass.

    Input: kiln frame and ``siting_rules``. Output: one escaped HTML string
    per row, identical in structure to the former per-row ``_popup_html``.
    """
    count = len(frame)
    if count == 0:
        return []
    escape = html.escape
    types = [type_label(value) for value in _type_source(frame)]
    statuses = (
        [str(value) for value in frame["detection_status"].tolist()]
        if "detection_status" in frame.columns
        else [""] * count
    )
    areas = frame["ui_area"].tolist() if "ui_area" in frame.columns else area_labels(frame)
    bands = (
        [str(item) for item in frame["priority_band"].tolist()]
        if "priority_band" in frame.columns
        else ["None"] * count
    )
    priorities = [priority_label(band) for band in bands]
    latitudes = numeric_column(frame, ("lat",)).tolist()
    longitudes = numeric_column(frame, ("lon",)).tolist()
    ids = [
        T.NO_DATA if (text := _clean_text(value)) is None else text
        for value in _column_list(frame, "kiln_id")
    ]
    signals = rule_signal_rows_html(frame, rules)
    detection_labels = {
        NEW_CANDIDATE_STATUS: T.NEW_CANDIDATE_2025_26,
        KNOWN_CANDIDATE_STATUS: T.PREVIOUSLY_DETECTED_2023_24,
    }
    out: list[str] = []
    for kind, status, area, priority, lat, lon, kiln_id, signal_lines in zip(
        types, statuses, areas, priorities, latitudes, longitudes, ids, signals
    ):
        valid = lat == lat and lon == lon
        coordinates = T.COORDS_FMT.format(lat, lon) if valid else T.NO_DATA
        directions = (
            f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f}%2C{lon:.6f}"
            if valid
            else "#"
        )
        maps = f"https://www.google.com/maps?q={lat:.6f}%2C{lon:.6f}" if valid else "#"
        earth = (
            f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y" if valid else "#"
        )
        detection = detection_labels.get(status, T.NO_DATA)
        status_class = "new-badge" if status == NEW_CANDIDATE_STATUS else "status-badge"
        out.append(
            "<div class='dhoa-popup'><div class='badges'>"
            f"<span class='badge {status_class}'>{escape(kind)} — {escape(detection)}</span></div>"
            f"<strong>{T.KILN_CANDIDATE} · {escape(area)}</strong><hr>"
            f"<span class='badge priority-badge'>{T.PRIORITY}: {escape(priority)}</span><br>"
            f"📍 {T.AREA}: {escape(area)}<br>"
            f"{escape(coordinates)}<hr>"
            f"<strong>{T.RULE_SIGNALS}:</strong>{signal_lines}<hr>"
            "<div class='popup-actions'>"
            f"<a href='{escape(directions, quote=True)}' target='_blank' rel='noopener'>"
            f"🗺️ {T.DIRECTIONS}</a>"
            f"<a href='{escape(maps, quote=True)}' target='_blank' rel='noopener'>"
            f"📍 {T.MAP}</a>"
            f"<a href='{escape(earth, quote=True)}' target='_blank' rel='noopener'>"
            "🌍 Google Earth</a></div>"
            f"<div>📄 {T.REPORT_ID}: {escape(kiln_id)}</div><hr></div>"
        )
    return out


def with_display_columns(
    frame: pd.DataFrame,
    rules: Sequence[Mapping[str, Any]],
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Return ``frame`` with the ``DISPLAY_COLUMNS`` present.

    Input: kiln frame and ``siting_rules``. Output: the same object when every
    display column already exists (and ``force`` is false), otherwise a copy
    with the missing ones computed in one vectorised pass.
    """
    missing = [name for name in DISPLAY_COLUMNS if force or name not in frame.columns]
    if not missing:
        return frame
    result = frame.copy()
    areas = area_labels(result)
    result["ui_area"] = areas
    classes = _column_list(result, "class")
    bands = (
        [str(value) for value in result["priority_band"].tolist()]
        if "priority_band" in result.columns
        else ["None"] * len(result)
    )
    kinds = [type_label(value) for value in classes]
    priorities = [priority_label(value) for value in bands]
    result["ui_type"] = kinds
    result["ui_priority"] = priorities
    result["ui_tooltip"] = [
        f"{priority} {T.PRIORITY} | {kind} | {area}"
        for priority, kind, area in zip(priorities, kinds, areas)
    ]
    result["ui_popup_html"] = popup_html_list(result, rules)
    return result


def prepare_display_frame(
    frame: pd.DataFrame, rules: Sequence[Mapping[str, Any]], version: str
) -> pd.DataFrame:
    """Prepare the full dataset once at load time (read-only afterwards).

    Input: the kiln frame with priority bands already added, the siting rules
    and a data-version token (file mtime/size). Output: a copy with a default
    ``detection_status``, the display columns, and
    ``attrs["dhoa_data_version"] = version`` used as the cache key.
    """
    result = frame.copy()
    if "detection_status" not in result.columns:
        result["detection_status"] = "Known"
    result = with_display_columns(result, rules, force=True)
    result.attrs["dhoa_data_version"] = version
    return result


# --------------------------------------------------------------------------
# Public / staff data split (S2)
# --------------------------------------------------------------------------
STAFF_ONLY_COLUMNS: tuple[str, ...] = (
    # priority (src/score/priority.py)
    "priority", "priority_rank", "priority_band", "exposure", "breach_severity_score",
    "n_schools", "n_hospitals", "settlement_area",
    "n_schools_normalized", "n_hospitals_normalized", "settlement_area_normalized",
    # rule signals (src/rules/engine.py)
    "breached_rules", "breach_count", "breach_score", "rule_signals_count", "rule_data_notes",
    "rules_version", "rules_verified", "signal_provenance_json", "technology_flagged",
    # distance to the nearest mapped feature, including the alias spellings the popup accepts
    "dist_schools_m", "dist_school_m", "dist_hospitals_m", "dist_hospital_m",
    "dist_settlements_m", "dist_settlement_m", "dist_rail_m", "dist_railway_m", "dist_railways_m",
    "dist_government_forest_m", "dist_forest_m", "dist_forests_m", "dist_water_m",
    # detector score: only the priority score and the staff card use it
    "confidence",
)
"""Pipeline columns that only the Inspector Portal may receive (documented in the pipeline modules)."""

STAFF_ONLY_PREFIXES: tuple[str, ...] = ("priority", "breach", "rule", "dist_", "signal_")
"""Safety net: any other column starting with these (or ending ``_normalized``) is staff-only too."""

STAFF_ONLY_DISPLAY_COLUMNS: tuple[str, ...] = ("ui_priority", "ui_tooltip", "ui_popup_html")
"""Display columns derived from staff-only data (priority label, rule-signal popup)."""

PUBLIC_DISPLAY_COLUMNS: tuple[str, ...] = ("ui_area", "ui_type")
"""Display columns the public frame carries (no priority, no rule signals)."""


def is_staff_only_column(name: object) -> bool:
    """True when column ``name`` must never reach the public side (explicit list, then prefixes)."""
    text = str(name)
    lowered = text.lower()
    return (
        text in STAFF_ONLY_COLUMNS
        or text in STAFF_ONLY_DISPLAY_COLUMNS
        or lowered.startswith(STAFF_ONLY_PREFIXES)
        or lowered.endswith("_normalized")
    )


def public_view(frame: pd.DataFrame) -> pd.DataFrame:
    """Return ``frame`` without any staff-only column (a copy; the input is untouched).

    Input: a kiln frame (pandas or geopandas). Output: the same rows minus
    ``STAFF_ONLY_COLUMNS``, the prefix matches and the staff display columns, so no
    public payload, table, map or PDF can be built from a priority or rule value.
    """
    drop = [name for name in frame.columns if is_staff_only_column(name)]
    result = frame.drop(columns=drop)
    result.attrs = {}
    return result


def leaked_columns(frame: pd.DataFrame) -> list[str]:
    """Names in ``frame`` that are staff-only (empty list for a safe public frame)."""
    return [str(name) for name in frame.columns if is_staff_only_column(name)]


def with_public_display_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return ``frame`` with ``ui_area`` and ``ui_type`` present (same object when they are)."""
    if all(name in frame.columns for name in PUBLIC_DISPLAY_COLUMNS):
        return frame
    result = frame.copy()
    result["ui_area"] = area_labels(result)
    result["ui_type"] = [type_label(value) for value in _column_list(result, "class")]
    return result


def prepare_public_frame(frame: pd.DataFrame, version: str) -> pd.DataFrame:
    """Prepare the public dataset once at load time (read-only afterwards).

    Input: the raw loaded kiln frame and a data-version token. Output: ``public_view`` of it
    plus a default ``detection_status`` and ``PUBLIC_DISPLAY_COLUMNS``; the cache key in
    ``attrs["dhoa_data_version"]`` carries ``-public`` so staff and public caches never mix.
    """
    result = public_view(frame)
    if "detection_status" not in result.columns:
        result["detection_status"] = "Known"
    result = with_public_display_columns(result)
    result.attrs["dhoa_data_version"] = f"{version}-public"
    return result


def public_marker_payload(frame: pd.DataFrame) -> dict[str, Any]:
    """Pack kilns into the public map structure: position, type and area only.

    Output: ``{"rows": [[lat, lon, type_index, area_index], ...], "types": [...],
    "areas": [...]}``; labels are HTML-escaped. There is no band, colour class or
    rule-signal field, so nothing about priority can be read from the page.
    """
    frame = with_public_display_columns(frame)
    lat = numeric_column(frame, ("lat",))
    lon = numeric_column(frame, ("lon",))
    valid = np.isfinite(lat) & np.isfinite(lon)
    types: list[str] = []
    areas: list[str] = []
    type_pos: dict[str, int] = {}
    area_pos: dict[str, int] = {}
    rows: list[list[Any]] = []
    for ok, la, lo, kind, area in zip(
        valid.tolist(), lat.tolist(), lon.tolist(), frame["ui_type"].tolist(), frame["ui_area"].tolist()
    ):
        if not ok:
            continue
        kind_i = type_pos.setdefault(kind, len(type_pos))
        if kind_i == len(types):
            types.append(html.escape(kind))
        area_i = area_pos.setdefault(area, len(area_pos))
        if area_i == len(areas):
            areas.append(html.escape(area))
        rows.append([round(la, 5), round(lo, 5), kind_i, area_i])
    return {"rows": rows, "types": types, "areas": areas}


# --------------------------------------------------------------------------
# Compact map payload (M3)
# --------------------------------------------------------------------------
def popup_signal_codes(
    frame: pd.DataFrame, rules: Sequence[Mapping[str, Any]]
) -> tuple[list[str], list[list[int]]]:
    """Return compact per-kiln rule-signal data for the on-click popup.

    Input: kiln frame and ``siting_rules`` (thresholds are read from them, never
    hardcoded). Output: ``(states, distances)`` aligned to the frame. ``states``
    is one string per kiln with one digit per ``_POPUP_RULES`` entry:
    ``0`` inside the configured buffer or flagged, ``1`` near it (within
    ``NEAR_THRESHOLD_FACTOR`` x the buffer, display-only), ``2`` outside,
    ``3`` no data. ``distances`` holds the rounded metres per rule (``-1`` when
    missing). Same decision logic as ``rule_signal_rows_html``.
    """
    count = len(frame)
    if count == 0:
        return [], []
    rules_by_id = {str(rule.get("id")): rule for rule in rules}
    breached = _breached_sets(frame)
    digits: list[list[str]] = []
    metres: list[list[int]] = []
    for rule_id, _label, columns in _POPUP_RULES:
        threshold = to_float(rules_by_id.get(rule_id, {}).get("buffer_m"))
        near_limit = threshold * NEAR_THRESHOLD_FACTOR
        state_col: list[str] = []
        dist_col: list[int] = []
        for distance, ids in zip(numeric_column(frame, columns).tolist(), breached):
            if distance != distance or threshold != threshold:
                state_col.append("3")
            elif rule_id in ids or distance <= threshold:
                state_col.append("0")
            elif distance <= near_limit:
                state_col.append("1")
            else:
                state_col.append("2")
            dist_col.append(-1 if distance != distance else int(round(distance)))
        digits.append(state_col)
        metres.append(dist_col)
    return ["".join(parts) for parts in zip(*digits)], [list(parts) for parts in zip(*metres)]


BAND_INDEX = {"High": 0, "Medium": 1, "Low": 2}
OTHER_BAND_INDEX = 3


def marker_payload(frame: pd.DataFrame, rules: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Pack kilns into a small JSON-ready structure for the map layer.

    Input: kiln frame (display columns are computed when missing, using
    ``rules``). Output: ``{"rows": [[lat, lon, band, type, area, states, metres], ...],
    "bands": [...], "types": [...], "areas": [...]}`` where band/type/area are
    indexes into the label lists. Labels are HTML-escaped because Leaflet
    renders tooltip strings as HTML. Rows without finite coordinates are
    dropped. Roughly 40 bytes per kiln instead of ~1 KB for a folium marker.
    """
    frame = with_display_columns(frame, rules)
    lat = numeric_column(frame, ("lat",))
    lon = numeric_column(frame, ("lon",))
    valid = np.isfinite(lat) & np.isfinite(lon)
    bands_raw = frame["priority_band"].astype(str).tolist() if "priority_band" in frame.columns else [""] * len(frame)
    band_idx = [BAND_INDEX.get(band, OTHER_BAND_INDEX) for band in bands_raw]
    states, distances = popup_signal_codes(frame, rules)
    types, areas = [], []
    type_pos: dict[str, int] = {}
    area_pos: dict[str, int] = {}
    rows: list[list[Any]] = []
    for ok, la, lo, band, kind, area, state, dist in zip(
        valid.tolist(), lat.tolist(), lon.tolist(), band_idx,
        frame["ui_type"].tolist(), frame["ui_area"].tolist(), states, distances,
    ):
        if not ok:
            continue
        kind_i = type_pos.setdefault(kind, len(type_pos))
        if kind_i == len(types):
            types.append(html.escape(kind))
        area_i = area_pos.setdefault(area, len(area_pos))
        if area_i == len(areas):
            areas.append(html.escape(area))
        rows.append([round(la, 5), round(lo, 5), band, kind_i, area_i, state, dist])
    return {
        "rows": rows,
        "bands": [T.HIGH + " " + T.PRIORITY, T.MEDIUM + " " + T.PRIORITY,
                  T.LOW + " " + T.PRIORITY, T.UNCLASSIFIED + " " + T.PRIORITY],
        "types": types,
        "areas": areas,
        "rules": [html.escape(label) for _id, label, _cols in _POPUP_RULES],
        "text": {
            "signals": html.escape(T.RULE_SIGNALS),
            "outside": html.escape(T.OUTSIDE_THRESHOLD),
            "nodata": html.escape(T.NO_DATA),
            "unit": html.escape(T.M_DOT_FMT.format(0)[1:]),
        },
    }


def bounds_of(frame: pd.DataFrame) -> list[list[float]] | None:
    """Return ``[[south, west], [north, east]]`` of finite points, or None."""
    lat = numeric_column(frame, ("lat",))
    lon = numeric_column(frame, ("lon",))
    valid = np.isfinite(lat) & np.isfinite(lon)
    if not valid.any():
        return None
    return [[float(lat[valid].min()), float(lon[valid].min())],
            [float(lat[valid].max()), float(lon[valid].max())]]


def radius_bounds(latitude: float, longitude: float, radius_m: float) -> list[list[float]]:
    """Approximate lat/lon box around a point, used only to fit the map view.

    Display geometry only (a degree is ~110.6 km north-south and ~111.3 km x
    cos(lat) east-west); distances for filtering use the projected CRS.
    """
    d_lat = radius_m / 110_574.0
    d_lon = radius_m / (111_320.0 * max(math.cos(math.radians(latitude)), 0.01))
    return [[latitude - d_lat, longitude - d_lon], [latitude + d_lat, longitude + d_lon]]


# --------------------------------------------------------------------------
# Geometry (projected CRS, vectorised)
# --------------------------------------------------------------------------
@lru_cache(maxsize=2)
def _transformer(east_of_90: bool) -> Any:
    """Build (once) the WGS84 -> projected-metres transformer.

    ``get_projected_crs`` only depends on the longitude through the 90 deg E
    split of its UTM fallback, so two cached transformers cover every input.
    """
    from pyproj import Transformer

    from src.geo.crs import get_projected_crs

    crs = get_projected_crs(91.0 if east_of_90 else 89.0)
    return Transformer.from_crs("EPSG:4326", crs, always_xy=True)


def distances_from_point_m(
    lats: Sequence[float] | np.ndarray,
    lons: Sequence[float] | np.ndarray,
    latitude: float,
    longitude: float,
) -> np.ndarray:
    """Distance in metres from many WGS84 points to one WGS84 point.

    Input: arrays of latitudes/longitudes (degrees) and the search point.
    Output: float array aligned to the inputs, measured in the projected CRS
    from ``src.geo.crs`` (EPSG:9680 with UTM fallback); non-finite inputs give
    ``inf`` so they never match a radius.
    """
    transformer = _transformer(float(longitude) >= 90.0)
    x, y = transformer.transform(
        np.asarray(lons, dtype="float64"), np.asarray(lats, dtype="float64")
    )
    sx, sy = transformer.transform(float(longitude), float(latitude))
    distance = np.hypot(np.asarray(x) - sx, np.asarray(y) - sy)
    return np.where(np.isfinite(distance), distance, np.inf)


def nearest_position(
    lats: Sequence[float] | np.ndarray,
    lons: Sequence[float] | np.ndarray,
    latitude: float,
    longitude: float,
) -> int | None:
    """Return the position of the point closest to the search point, or None."""
    if len(lats) == 0:
        return None
    distance = distances_from_point_m(lats, lons, latitude, longitude)
    if not np.isfinite(distance).any():
        return None
    return int(np.argmin(distance))
