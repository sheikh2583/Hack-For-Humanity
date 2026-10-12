"""Dhoa dashboard: one cached data load, one map builder, and plain-English UI."""

from __future__ import annotations

import html
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import streamlit as st

st.set_page_config(page_title="ধোঁয়া", layout="wide", initial_sidebar_state="auto")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

import folium
import geopandas as gpd
import pandas as pd
import yaml
from branca.element import Element
import streamlit.components.v1 as components
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

# isort: off
from dashboard_filters import ( 
    SIGNAL_PRESENT,
    add_priority_bands,
    apply_candidate_filters,
)
from data_loader import load_kilns 
from src.rules.engine import _ensure_class_column 
# isort: on

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_PATH = DATA_DIR / "kilns_prioritised.parquet"
_priority_candidate_list = components.declare_component(
    "dhoa_priority_candidate_list",
    path=str(_ROOT / "app" / "components" / "priority_candidate_list"),
)
PRIORITY_COLORS = {"High": "red", "Medium": "orange", "Low": "green"}
DISTRICTS = ["All Districts", "Chapainawabganj", "Gazipur", "Rajshahi", "Dhaka", "Chittagong"]
DISTRICT_CENTERS = {
    "All Districts": (23.80, 90.30),
    "Chapainawabganj": (24.60, 88.35),
    "Gazipur": (24.10, 90.20),
    "Rajshahi": (24.30, 88.45),
    "Dhaka": (23.80, 90.30),
    "Chittagong": (22.50, 91.90),
}


def responsive_css() -> str:
    """Return responsive CSS for desktop, tablet, and phone layouts.

    Input schema: none. Output schema: CSS string for the dashboard page.
    """
    return """
<style>
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100%; padding: 0.75rem 1.25rem 1.5rem;
}
[data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding-top: 0.75rem !important;
}
[data-testid="stAppViewContainer"] .main h1 {
    margin-top: 0.25rem !important;
    padding: 0.25em 0 0.15em;
    font-family: "Noto Sans Bengali UI", sans-serif !important;
    font-weight: 700 !important;
    line-height: 1.65 !important;
    overflow: visible !important;
}
[data-testid="stMainBlockContainer"] h1 { line-height: 1.65 !important; overflow: visible !important; }
/* Hide heading permalinks only; keep map, navigation, and export links usable. */
[data-testid="stHeaderActionElements"],
h1 a, h2 a, h3 a, h4 a,
[role="heading"] a, [role="heading"] button,
h1 [data-testid="stHeaderActionElements"],
h2 [data-testid="stHeaderActionElements"],
h3 [data-testid="stHeaderActionElements"],
h4 [data-testid="stHeaderActionElements"],
[role="heading"] [data-testid="stHeaderActionElements"] { display: none !important; }
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] { margin-top: 0.2rem; }
[data-testid="stMetric"] { min-width: 0; }
/* Replace Streamlit's developer-oriented status icon with a Bengali loading cue. */
[data-testid="stStatusWidget"],
[data-testid^="stStatusWidget"],
[data-testid="stStatusWidgetRunningIcon"] {
    width: auto !important;
    height: auto !important;
    min-width: 0;
    margin-right: 0.4rem !important;
    overflow: visible !important;
}
[data-testid="stStatusWidget"] > *,
[data-testid^="stStatusWidget"] > *,
[data-testid="stStatusWidgetRunningIcon"] svg,
[data-testid="stStatusWidgetRunningIcon"] img { display: none !important; }
[data-testid="stStatusWidget"]::after,
[data-testid^="stStatusWidget"]::after,
[data-testid="stStatusWidgetRunningIcon"]::after {
    content: "পৃষ্ঠা লোড হচ্ছে, অপেক্ষা করুন…";
    display: block;
    max-width: 220px;
    color: #dbe3ec;
    font-family: "Noto Sans Bengali", "Nirmala UI", "Vrinda", sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.35;
    white-space: nowrap;
}
.dhoa-metrics {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: clamp(0.5rem, 1.2vw, 1rem);
    width: 100%;
    margin: 0.5rem 0 1rem;
}
.dhoa-metric { min-width: 0; padding: 0.35rem 0.65rem; border-left: 2px solid #475569; }
.dhoa-metric strong { display: block; font-size: 1.15rem; line-height: 1.3; }
.dhoa-metric span { display: block; color: #aab4c0; font-size: 0.82rem; line-height: 1.35; }
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button,
[data-baseweb="select"] > div,
[data-testid="stSlider"] [role="slider"] { min-height: 44px; }
.dhoa-mobile-map-hint {
    display: none;
    margin: 0.25rem 0 0.65rem;
    color: #cbd5e1;
    font-size: 0.9rem;
}
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding: 0.65rem 0.75rem 1.5rem;
    }
    [data-testid="stMainBlockContainer"] { padding-top: 1.35rem !important; }
    [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.75rem; }
    [data-testid="stMetricContainer"] { min-width: 0; }
    [data-testid="stStatusWidgetRunningIcon"]::after {
        max-width: 115px;
        font-size: 0.7rem;
        line-height: 1.3;
        white-space: normal;
        text-align: right;
    }
    [data-testid="stIFrame"] iframe {
        width: 100% !important; height: 52vh !important;
        min-height: 280px !important; max-height: 500px !important;
    }
    .st-key-dhoa_map_frame iframe {
        width: 100% !important;
        height: 52vh !important;
        min-height: 300px !important;
        max-height: 500px !important;
    }
    h1 { font-size: 1.9rem !important; line-height: 1.65 !important; padding-top: 0.25em; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    .dhoa-metrics { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem !important; }
    .dhoa-mobile-map-hint { display: block !important; }
}
@media (max-width: 480px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.5rem; padding-right: 0.5rem;
    }
    body, p, label, [data-testid="stCaptionContainer"] { font-size: 14px; }
}
</style>
"""


@st.cache_data
def load_config() -> dict[str, Any]:
    """Read the three dashboard configuration files once."""
    result: dict[str, Any] = {}
    for name in ("rules.yaml", "aoi.yaml", "dashboard.yaml"):
        with (CONFIG_DIR / name).open(encoding="utf-8") as stream:
            result[name.removesuffix(".yaml")] = yaml.safe_load(stream) or {}
    return result


@st.cache_data
def load_data(path: Path = DATA_PATH) -> gpd.GeoDataFrame | None:
    """Load the prioritized GeoParquet once, returning None on any failure."""
    if not path.is_file():
        return None
    return _ensure_class_column(load_kilns(path))


def class_counts(frame: pd.DataFrame) -> tuple[int, int]:
    """Return fixed-chimney and zigzag counts for compatibility callers."""
    classes = frame.get("class", pd.Series(dtype="string")).astype("string")
    return int(classes.eq("FCBK").sum()), int(classes.eq("Zigzag").sum())


def color_for_kiln(row: Mapping[str, object]) -> str:
    """Return the map color for an existing priority band."""
    return PRIORITY_COLORS.get(str(row.get("priority_band", "")), "blue")


def rules_are_verified(rules: dict[str, Any]) -> bool:
    """Compatibility helper; its result is never shown in the UI."""
    return all(rule.get("verified", True) for rule in [rules.get("technology", {}), *rules.get("siting_rules", [])])


def latest_kilns_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Return the latest processed file for existing integrations."""
    candidates = [path for path in data_dir.glob("kilns*.parquet") if path.is_file()]
    return max(candidates, key=lambda path: path.stat().st_mtime, default=None)


def dashboard_kilns_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Return the prioritized output, with legacy fallbacks."""
    for name in ("kilns_prioritised.parquet", "kilns_scored.parquet", "kilns.parquet"):
        path = data_dir / name
        if path.is_file():
            return path
    return latest_kilns_file(data_dir)


def _type_label(value: object) -> str:
    """Return a concise Bengali label for the kiln type."""
    return "\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf \u0987\u099f\u09ad\u09be\u099f\u09be" if str(value) == "FCBK" else "\u099c\u09bf\u0997\u099c\u09cd\u09af\u09be\u0997 \u0987\u099f\u09ad\u09be\u099f\u09be"


def _priority_label(value: object) -> str:
    """Translate an internal priority band for display."""
    return {"High": "উচ্চ", "Medium": "মাঝারি", "Low": "নিম্ন"}.get(str(value), "নির্ধারিত নয়")


def _district_label(value: object) -> str:
    """Translate district options while preserving unknown district names."""
    return {
        "All Districts": "সব জেলা",
        "Chapainawabganj": "চাঁপাইনবাবগঞ্জ",
        "Gazipur": "গাজীপুর",
        "Rajshahi": "রাজশাহী",
        "Dhaka": "ঢাকা",
        "Chittagong": "চট্টগ্রাম",
    }.get(str(value), str(value))


def _signal_label(value: object) -> str:
    """Translate known rule identifiers for dashboard display."""
    translated = {
        "near_school": "স্কুলের কাছে",
        "near_hospital": "হাসপাতালের কাছে",
        "near_settlement": "বসতির কাছে",
        "near_railway": "রেলপথের কাছে",
        "near_wetland": "জলাভূমির কাছে",
        "near_government_forest": "সরকারি বনের কাছে",
        "technology_flagged": "ফিক্সড চিমনি প্রযুক্তি",
    }.get(str(value))
    if translated:
        return translated
    label = str(value)
    for english, bangla in (("Near school", "স্কুলের কাছে"), ("Near hospital", "হাসপাতালের কাছে"), ("Near settlement", "বসতির কাছে"), ("Near railway", "রেলপথের কাছে"), ("Near wetland", "জলাভূমির কাছে"), ("Near government forest", "সরকারি বনের কাছে")):
        label = label.replace(english, bangla)
    return label


def _signals(row: pd.Series) -> list[str]:
    value = row.get("breached_rules", [])
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [value]
    return list(value) if isinstance(value, (list, tuple)) else []


def _priority_reason(row: pd.Series) -> str:
    names = {
        "near_school": ("school", "dist_schools_m"),
        "near_hospital": ("hospital", "dist_hospitals_m"),
        "near_settlement": ("settlement", "dist_settlements_m"),
        "near_railway": ("railway", "dist_railways_m"),
        "near_wetland": ("wetland", "dist_water_m"),
        "near_government_forest": ("government forest", "dist_government_forest_m"),
    }
    for signal in _signals(row):
        label, column = names.get(str(signal), ("rule signal", ""))
        distance = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0] if column else None
        translated = {"school": "স্কুল", "hospital": "হাসপাতাল", "settlement": "বসতি", "railway": "রেলপথ", "wetland": "জলাভূমি", "government forest": "সরকারি বন"}.get(label, label)
        return f"{translated} থেকে {distance:,.0f} মিটার" if pd.notna(distance) else f"{translated}-সংক্রান্ত সংকেত"
    return "কোনো নিয়ম-সংকেত নথিভুক্ত নেই"


@st.cache_data(show_spinner=False)
def _report_from_json(row_json: str) -> bytes | None:
    """Build and cache a candidate report from serialized row fields."""
    from src.eval.generate_report import generate_kiln_report

    return generate_kiln_report(json.loads(row_json))


def _json_default(value: object) -> Any:
    """Convert NumPy and geometry values into JSON-safe cache-key values."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def build_popup(row: pd.Series) -> str:
    """Build Bengali popup details for a candidate row."""
    lat, lon = float(row.lat), float(row.lon)
    rules = load_config()["rules"].get("siting_rules", [])
    configured = {rule.get("feature"): rule for rule in rules}
    features = sorted(configured, key=lambda feature: -float(configured[feature].get("severity", 0)))
    features.extend(
        feature
        for feature in ("railways", "settlements", "forests", "water")
        if feature not in features
    )
    labels = {
        "schools": "স্কুল",
        "hospitals": "হাসপাতাল",
        "railways": "রেলপথ",
        "settlements": "বসতি",
        "forests": "বন",
        "government_forest": "সরকারি বন",
        "water": "জলাভূমি",
        "wetlands": "জলাভূমি",
    }
    lines = []
    for feature in features:
        key = "water" if feature == "wetlands" else feature
        value = pd.to_numeric(pd.Series([row.get(f"dist_{key}_m")]), errors="coerce").iloc[0]
        distance = "মানচিত্রের তথ্য নেই" if pd.isna(value) else (f"{value / 1000:.1f} কিমি" if value >= 1000 else f"{value:,.0f} মিটার")
        rule = configured.get(feature, {})
        threshold = rule.get("buffer_m")
        warning = " \u26a0\ufe0f" if threshold is not None and pd.notna(value) and value < float(threshold) else ""
        severity = int(rule.get("severity", 0))
        severity_name = {3: "গুরুতর", 2: "মাঝারি", 1: "কম"}.get(severity)
        severity_text = f" (গুরুত্ব: {severity_name})" if severity_name else ""
        title = "কাছাকাছি" if rule else "নিকটতম"
        lines.append(f"{title} {labels.get(feature, feature)}: {distance}{severity_text}{warning}")
    if any(rule.get("id") == "near_wetland" for rule in rules):
        lines.append(
            "নোট: পানির স্তরটি OSM-ভিত্তিক আনুমানিক তথ্য। আইনি সংজ্ঞায় বছরে অন্তত ৬ মাস ডুবে থাকা ভূমি বোঝায় (আইন, ধারা ৮ ব্যাখ্যা (খ))।"
        )
    if any(rule.get("id") == "near_government_forest" for rule in rules):
        lines.append(
            "বনের তথ্য: HDX/LGED ২০১৩ সালের আর্কাইভ; বর্তমান সীমানা নাও দেখাতে পারে।"
        )
    badge = "🆕 নতুন (২০২৫–২৬)\n" if row.get("detection_status") == "New candidate (2025-26)" else ""
    return f"{badge}ইটভাটা প্রার্থী #{row.get('kiln_id', 'অজানা')}\nধরন: {_type_label(row.get('class'))}\nঅগ্রাধিকার: {_priority_label(row.get('priority_band'))} — {_priority_reason(row)}\nজেলা: {_district_label(row.get('district', 'নথিভুক্ত নয়'))}\n📍 {lat:.4f}° উত্তর, {lon:.4f}° পূর্ব\n" + "\n".join(lines)


def _popup_html(row: pd.Series) -> str:
    """Build escaped popup markup with direct navigation links for a kiln."""
    latitude, longitude = float(row["lat"]), float(row["lon"])
    directions = (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={latitude:.6f}%2C{longitude:.6f}&travelmode=driving"
    )
    view_location = f"https://www.google.com/maps?q={latitude:.6f}%2C{longitude:.6f}"
    details = html.escape(build_popup(row)).replace("\n", "<br>")
    return (
        '<div class="dhoa-popup">'
        f'<a href="{html.escape(directions, quote=True)}" target="_blank" rel="noopener">'
        "\U0001f5fa\ufe0f \u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be</a> &nbsp;|&nbsp; "
        f'<a href="{html.escape(view_location, quote=True)}" target="_blank" rel="noopener">'
        "\U0001f4cd \u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8 \u09a6\u09c7\u0996\u09c1\u09a8</a><hr>"
        f"{details}</div>"
    )


def _format_distance_cell(row: pd.Series, rule: Mapping[str, Any]) -> str:
    """Format one configured rule distance, marking only in-buffer values.

    Input schema: one candidate row and a siting-rule mapping from rules.yaml.
    Output schema: localized distance text, warning marker, or missing-data text.
    """
    feature = str(rule.get("feature", ""))
    value = pd.to_numeric(
        pd.Series([row.get(f"dist_{feature}_m")]), errors="coerce"
    ).iloc[0]
    if pd.isna(value):
        return "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    rendered = (
        f"{value / 1000:.1f} \u0995\u09bf\u09ae\u09bf"
        if value >= 1000
        else f"{value:,.0f} \u09ae\u09bf"
    )
    threshold = pd.to_numeric(
        pd.Series([rule.get("buffer_m")]), errors="coerce"
    ).iloc[0]
    if pd.notna(threshold) and value < threshold:
        return f"{rendered} \u26a0\ufe0f"
    return rendered

def _kiln_list_frame(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build a selectable distance table without repeating rule labels per row.

    Input schema: filtered candidate GeoDataFrame with district, coordinates,
    priority, and configured distance fields. Output schema: visible location,
    priority, and one distance column per active siting rule.
    """
    rules = load_config()["rules"].get("siting_rules", [])
    feature_labels = {
        "schools": "\u09b8\u09cd\u0995\u09c1\u09b2",
        "hospitals": "\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2",
        "railways": "\u09b0\u09c7\u09b2\u09aa\u09a5",
        "settlements": "\u09ac\u09b8\u09a4\u09bf",
        "government_forest": "\u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09ac\u09a8",
        "water": "\u099c\u09b2\u09be\u09ad\u09c2\u09ae\u09bf",
    }
    select_label = "\u09ad\u09be\u099f\u09be\u099f\u09bf \u09a6\u09c7\u0996\u09c1\u09a8"
    location_label = "\u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8"
    priority_label = "\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0"
    columns = [select_label, location_label, priority_label]
    columns.extend(
        f"{feature_labels.get(str(rule.get('feature')), str(rule.get('feature')))} \u09a5\u09c7\u0995\u09c7 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac"
        for rule in rules
    )
    icons = {
        "High": "\U0001f534 \u0989\u099a\u09cd\u099a",
        "Medium": "\U0001f7e0 \u09ae\u09be\u099d\u09be\u09b0\u09bf",
        "Low": "\U0001f7e2 \u09a8\u09bf\u09ae\u09cd\u09a8",
    }
    records: list[dict[str, object]] = []
    for _, row in gdf.iterrows():
        latitude = pd.to_numeric(pd.Series([row.get("lat")]), errors="coerce").iloc[0]
        longitude = pd.to_numeric(pd.Series([row.get("lon")]), errors="coerce").iloc[0]
        district = _district_label(row.get("district", "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"))
        location = f"\U0001f4cd {district}"
        if pd.notna(latitude) and pd.notna(longitude):
            location += f" \xb7 {latitude:.4f}, {longitude:.4f}"
        record: dict[str, object] = {
            select_label: select_label,
            location_label: location,
            priority_label: icons.get(
                str(row.get("priority_band", "")),
                _priority_label(row.get("priority_band")),
            ),
        }
        for rule, column in zip(rules, columns[3:], strict=True):
            record[column] = _format_distance_cell(row, rule)
        records.append(record)
    return pd.DataFrame(records, columns=columns)


def _filtered(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> gpd.GeoDataFrame:
    """Apply the sidebar filter state without rendering UI."""
    result = apply_candidate_filters(
        gdf,
        load_config()["rules"],
        districts=None if filters["district"] == "All Districts" else {filters["district"]},
        classes=None if filters["kiln_type"] == "All types" else {"FCBK" if "FCBK" in filters["kiln_type"] else "Zigzag"},
        confidence_range=filters.get("confidence_range", (0.0, 1.0)),
        priority_bands=filters["priorities"] or {"__none__"},
        signal_filters=filters.get("signal_filters", {}),
    )
    if filters.get("new_only") and "detection_status" in result.columns:
        result = result[result["detection_status"].eq("New candidate (2025-26)")].copy()
    return result


def _export_csv(gdf: pd.DataFrame) -> str:
    """Create the fixed candidate CSV with configured rule distances."""
    from src.eval.generate_report import generate_candidate_csv

    return generate_candidate_csv(gdf)


def _flagged_count(frame: pd.DataFrame, rules: Mapping[str, Any]) -> int:
    """Count rows with signals or distances inside configured thresholds.

    Input: candidate rows and rules.yaml mapping. Output: count of candidates
    with a positive rule-signal count or a distance under a configured buffer.
    """
    count_column = "rule_signals_count" if "rule_signals_count" in frame else "breach_count"
    flagged = (
        pd.to_numeric(frame[count_column], errors="coerce").fillna(0).gt(0)
        if count_column in frame
        else pd.Series(False, index=frame.index)
    )
    for rule in rules.get("siting_rules", []):
        feature = rule.get("feature")
        buffer_m = rule.get("buffer_m")
        if not feature or buffer_m is None:
            continue
        distance_column = f"dist_{feature}_m"
        if distance_column in frame.columns:
            distances = pd.to_numeric(frame[distance_column], errors="coerce")
            flagged |= distances.lt(float(buffer_m))
    return int(flagged.sum())


def render_header(gdf: gpd.GeoDataFrame) -> None:
    """Render the compact dashboard header and summary metrics.

    Input schema: prioritized candidate GeoDataFrame. Output: page header,
    on-demand Bengali usage guidance, and summary metrics.
    """
    identity, help_column = st.columns([5, 2], gap="small", vertical_alignment="center")
    with identity:
        st.title("\u09a7\u09cb\u0981\u09af\u09bc\u09be")
        loaded = dashboard_kilns_file()
        subtitle = "\u09ac\u09be\u0982\u09b2\u09be\u09a6\u09c7\u09b6\u09c7\u09b0 \u0987\u099f\u09ad\u09be\u099f\u09be \u09aa\u09b0\u09cd\u09af\u09ac\u09c7\u0995\u09cd\u09b7\u09a3 \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1"
        if loaded is not None:
            modified = datetime.fromtimestamp(loaded.stat().st_mtime, tz=UTC).isoformat(
                timespec="seconds"
            )
            subtitle += f" · \u09a4\u09a5\u09cd\u09af \u09b9\u09be\u09b2\u09a8\u09be\u0997\u09be\u09a6 {modified[:10]}"
        st.caption(subtitle)
    with help_column:
        with st.popover("\u0995\u09bf\u09ad\u09be\u09ac\u09c7 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09ac\u09c7\u09a8? \u098f\u0996\u09be\u09a8\u09c7 \u0995\u09cd\u09b2\u09bf\u0995 \u0995\u09b0\u09c1\u09a8", icon=":material/help:", width="stretch"):
            st.write(
                "\u099c\u09c7\u09b2\u09be \u0993 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0\u09c7\u09b0 \u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0 \u09ac\u09be\u099b\u09c1\u09a8। \u09a4\u09be\u09b2\u09bf\u0995\u09be\u09df \u2018\u09ad\u09be\u099f\u09be\u099f\u09bf \u09a6\u09c7\u0996\u09c1\u09a8\u2019 \u099a\u09be\u09aa\u09b2\u09c7 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7 \u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8 \u0993 \u0995\u09be\u099b\u09be\u0995\u09be\u099b\u09bf\u09b0 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac \u09a6\u09c7\u0996\u09c1\u09a8; \u09aa\u09cd\u09b0\u09df\u09cb\u099c\u09a8\u09c7 PDF \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09ac\u09be CSV \u09a4\u09be\u09b2\u09bf\u0995\u09be \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1 \u0995\u09b0\u09c1\u09a8।"
            )
    high = int(gdf["priority_band"].eq("High").sum())
    new_count = int(gdf.get("detection_status", pd.Series("Known", index=gdf.index)).eq("New candidate (2025-26)").sum())
    flagged = _flagged_count(gdf, load_config()["rules"])
    updated_date = datetime.now(UTC).date().isoformat()
    metric_items = (
        (f"{len(gdf):,}", "\u09ae\u09cb\u099f \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0"),
        (f"{high:,}", "\u0989\u099a\u09cd\u099a \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0"),
        (f"{new_count:,}", "\u09a8\u09a4\u09c1\u09a8 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0"),
        (f"{flagged:,}", "\u09a8\u09bf\u09df\u09ae \u09aa\u09b0\u09cd\u09af\u09be\u09b2\u09cb\u099a\u09a8\u09be\u09df"),
        (updated_date, "\u09b8\u09b0\u09cd\u09ac\u09b6\u09c7\u09b7 \u09b9\u09be\u09b2\u09a8\u09be\u0997\u09be\u09a6"),
    )
    items_html = "".join(
        f"<div class='dhoa-metric'><strong>{value}</strong><span>{label}</span></div>"
        for value, label in metric_items
    )
    st.markdown(f"<div class='dhoa-metrics'>{items_html}</div>", unsafe_allow_html=True)


def render_district_summary(district: str, gdf: gpd.GeoDataFrame) -> None:
    """Render totals, estimated spatial footprint, rule signals, and risk summary.

    Input: district name and candidate GeoDataFrame with district,
    priority_band, detection_status and optional rule signal data. Output:
    Streamlit metrics and one info sentence, without mutating the frame.
    """
    if district == "All Districts":
        return
    selected = gdf[gdf["district"].astype(str).eq(district)]
    high_count = int(selected["priority_band"].astype(str).eq("High").sum())
    signal_values = [signal for _, row in selected.iterrows() for signal in _signals(row)]
    signal_counts = pd.Series(signal_values, dtype="string").value_counts()
    rule_names = {
        str(rule.get("id")): _signal_label(rule.get("id", ""))
        for rule in load_config()["rules"].get("siting_rules", [])
    }
    rule_names["technology_flagged"] = "ফিক্সড চিমনি প্রযুক্তি"
    top_rule_signal = (
        rule_names.get(str(signal_counts.index[0]), _signal_label(signal_counts.index[0]))
        if not signal_counts.empty
        else "None"
    )
    if selected.empty or selected.geometry.is_empty.all():
        coverage_km2 = 0.0
    else:
        from src.geo.crs import centroid_longitude, get_projected_crs

        projected = selected.to_crs(get_projected_crs(centroid_longitude(selected)))
        coverage_km2 = float(projected.geometry.union_all().convex_hull.area / 1_000_000)
    high_rows = selected[selected["priority_band"].astype(str).eq("High")]
    school_hospital = {"near_school", "near_hospital"}
    high_risk_rows = high_rows[
        high_rows.apply(lambda row: bool(set(_signals(row)) & school_hospital), axis=1)
    ]
    high_signals = {signal for _, row in high_risk_rows.iterrows() for signal in _signals(row)}
    near = [label for signal, label in (("near_school", "schools"), ("near_hospital", "hospitals")) if signal in high_signals]
    risk_scope = " and ".join(near) if near else "recorded rule signals"
    columns = st.columns(4)
    for column, label, value in zip(
        columns,
        ("মোট প্রার্থী", "উচ্চ অগ্রাধিকার", "আনুমানিক এলাকা (বর্গ কিমি)", "প্রধান নিয়ম-সংকেত"),
        (len(selected), high_count, f"{coverage_km2:,.2f}", top_rule_signal),
    ):
        column.metric(label, value)
    risk_count = len(high_risk_rows) if near else len(high_rows)
    bangla_risk_scope = "স্কুল ও হাসপাতালের কাছে" if risk_scope == "schools and hospitals" else "স্কুলের কাছে" if risk_scope == "schools" else "হাসপাতালের কাছে" if risk_scope == "hospitals" else "নিয়ম-সংকেতযুক্ত"
    st.info(f"{_district_label(district)} জেলায় {bangla_risk_scope} {risk_count}টি উচ্চ অগ্রাধিকারপ্রাপ্ত প্রার্থী পাওয়া গেছে।")


def render_sidebar(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Render controls and return a filter mapping."""
    with st.sidebar, st.expander("ফিল্টার", expanded=False):
        st.caption("জেলা, ধরন, মানচিত্র ও অগ্রাধিকার অনুযায়ী প্রার্থী খুঁজুন।")
        district = st.selectbox("জেলা নির্বাচন", DISTRICTS, format_func=_district_label, key="dhoa_district_filter")
        kiln_type = st.selectbox(
            "ইটভাটার ধরন",
            ["All types", "Fixed-chimney (FCBK)", "Zigzag"],
            format_func=lambda value: {"All types": "সব ধরন", "Fixed-chimney (FCBK)": "ফিক্সড চিমনি (FCBK)", "Zigzag": "জিগজ্যাগ"}.get(value, value),
            key="dhoa_kiln_type_filter",
        )
        map_style = st.selectbox(
            "মানচিত্রের ধরন",
            ["Street map", "Satellite imagery"],
            format_func=lambda value: {"Street map": "রাস্তার মানচিত্র", "Satellite imagery": "স্যাটেলাইট চিত্র"}.get(value, value),
            help="প্রার্থী অবস্থানের মানচিত্রের পটভূমি নির্বাচন করুন।",
            key="dhoa_map_style_filter",
        )
        severity = st.selectbox(
            "অগ্রাধিকার", ["All severities", "High", "Medium", "Low"],
            format_func=lambda value: {"All severities": "সব স্তর", "High": "উচ্চ", "Medium": "মাঝারি", "Low": "নিম্ন"}.get(value, value),
            key="dhoa_severity_filter",
        )
        confidence_range = st.slider(
            "নির্ভরযোগ্যতার মাত্রা (%)",
            min_value=0.0,
            max_value=1.0,
            value=(0.0, 1.0),
            step=0.01,
            format="%.0f%%",
            key="dhoa_confidence_filter",
        )
        signal_ids = [
            str(rule.get("id"))
            for rule in [load_config()["rules"].get("technology", {}), *load_config()["rules"].get("siting_rules", [])]
            if rule.get("id")
        ]
        selected_signals = st.multiselect(
            "নিয়ম-সংকেত",
            signal_ids,
            format_func=_signal_label,
            key="dhoa_signal_filter",
        )
        priorities = {severity} if severity != "All severities" else {"High", "Medium", "Low"}
        new_only = st.checkbox("🆕 শুধু নতুন প্রার্থী", value=False, key="dhoa_new_only")
    filters = {
        "district": district,
        "kiln_type": kiln_type,
        "map_style": map_style,
        "priorities": priorities,
        "confidence_range": confidence_range,
        "new_only": new_only,
        "signal_filters": {signal_id: SIGNAL_PRESENT for signal_id in selected_signals},
    }
    visible = _filtered(gdf, filters)
    with st.sidebar:
        st.markdown(f"**{len(visible):,} / {len(gdf):,} জন প্রার্থী দেখানো হচ্ছে**")
        slug = district.lower().replace(" ", "_") if district != "All Districts" else "all_districts"
        today = datetime.now(UTC).strftime("%Y%m%d")
        st.download_button("⬇ বাছাইকৃত তালিকা CSV ডাউনলোড", _export_csv(visible), f"dhoa_{slug}_{today}.csv", "text/csv", width="stretch")
    return filters


def _render_selected_candidate(row: pd.Series) -> None:
    """Render selected kiln details, navigation links, and PDF download control."""
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", "unknown"))
    st.subheader(f"✅ নির্বাচিত প্রার্থী · ইটভাটা #{candidate_id}")
    st.write(f"**ধরন:** {_type_label(row.get('class'))}")
    confidence = pd.to_numeric(pd.Series([row.get("confidence")]), errors="coerce").iloc[0]
    st.write(f"**নির্ভরযোগ্যতার স্কোর:** {confidence:.1%}" if pd.notna(confidence) else "**নির্ভরযোগ্যতার স্কোর:** তথ্য নেই")
    st.write(f"**অগ্রাধিকার:** {_priority_label(row.get('priority_band'))} — {_priority_reason(row)}")
    st.write(f"**জেলা:** {_district_label(row.get('district', 'নথিভুক্ত নয়'))}")
    detection = "নতুন প্রার্থী (২০২৫–২৬)" if row.get("detection_status") == "New candidate (2025-26)" else "আগে শনাক্ত (২০২৩–২৪ জরিপ)"
    st.write(f"**শনাক্তকরণের অবস্থা:** {detection}")
    st.write(f"**স্থানাঙ্ক:** {lat:.5f}, {lon:.5f}")
    for line in build_popup(row).splitlines():
        if line.startswith(("কাছাকাছি ", "নিকটতম ")):
            st.write(line)
    columns = st.columns(3)
    directions = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving"
    street_view = f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},3a,90y,0h,90t/data=!3m1!1e3"
    earth = f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y"
    columns[0].link_button("🗺️ দিকনির্দেশনা", directions, width="stretch")
    columns[1].link_button("📍 স্ট্রিট ভিউ", street_view, width="stretch")
    columns[2].link_button("🌍 গুগল আর্থ", earth, width="stretch")


def _render_report_download(row: pd.Series) -> None:
    """Render the one selected-candidate PDF download control."""
    candidate_id = str(row.get("kiln_id", "unknown"))
    try:
        report = _report_from_json(json.dumps(row.to_dict(), default=_json_default, sort_keys=True))
        if report is None:
            st.error("পরিদর্শন প্রতিবেদন তৈরি করা যায়নি।")
            return
        safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in candidate_id)
        filename = f"kilnrank_report_{safe_id}_{datetime.now(UTC):%Y%m%d}.pdf"
        st.download_button(
            "📄 নির্বাচিত প্রার্থীর PDF ডাউনলোড",
            report,
            filename,
            "application/pdf",
            width="stretch",
            key=f"kiln_report_{safe_id}",
        )
    except Exception as exc:  # noqa: BLE001 - report generation boundary
        st.error(f"পরিদর্শন প্রতিবেদন তৈরি করা যায়নি: {exc}")


def build_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> folium.Map:
    """Build a Folium map with all filtered candidates and priority layers.

    Input schema: candidate GeoDataFrame containing ``lat``, ``lon``,
    ``priority_band`` and optional screening fields, plus the sidebar filter
    mapping. Output schema: Folium map with visible priority marker layers and
    a hidden-by-default weighted heatmap.
    """
    filtered = _filtered(gdf, filters)
    selected_id = st.session_state.get("selected_kiln_id")
    if selected_id is not None and "kiln_id" in filtered.columns:
        selected = filtered[filtered["kiln_id"].astype(str).eq(str(selected_id))]
        if not selected.empty:
            center = (float(selected.iloc[0]["lat"]), float(selected.iloc[0]["lon"]))
            zoom = 18
        else:
            st.session_state["selected_kiln_id"] = None
            center = DISTRICT_CENTERS.get(
                str(filters.get("district", "All Districts")), DISTRICT_CENTERS["All Districts"]
            )
            zoom = 7 if filters.get("district") == "All Districts" else 10
    elif filters.get("district") == "All Districts" and not filtered.empty:
        center = (float(filtered["lat"].mean()), float(filtered["lon"].mean()))
        zoom = 7
    else:
        center = DISTRICT_CENTERS.get(
            str(filters.get("district", "All Districts")), DISTRICT_CENTERS["All Districts"]
        )
        zoom = 7 if filters.get("district") == "All Districts" else 10

    satellite = filters.get("map_style") == "Satellite imagery"
    map_view = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
    map_view.get_root().html.add_child(
        Element(
            """<style>
            .leaflet-popup-content-wrapper { max-width: min(360px, 76vw); }
            .leaflet-popup-content {
                width: min(300px, 68vw) !important; max-height: 240px;
                overflow-y: auto; overflow-x: hidden; overflow-wrap: anywhere;
            }
            .dhoa-popup { max-width: 280px; overflow-wrap: anywhere; word-break: break-word; }
            @media (max-width: 768px) {
                .leaflet-control-zoom a {
                    width: 40px; height: 40px; line-height: 40px; font-size: 20px;
                }
                .leaflet-control-layers-toggle { width: 40px; height: 40px; }
                .leaflet-control-layers-expanded {
                    max-height: 42vh; overflow-y: auto; font-size: 16px;
                }
                .leaflet-popup-content {
                    width: min(260px, 70vw) !important; max-height: 40vh;
                }
            }
            </style>"""
        )
    )
    folium.TileLayer("OpenStreetMap", name="রাস্তার মানচিত্র", show=not satellite).add_to(map_view)
    folium.TileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="স্যাটেলাইট চিত্র",
        show=satellite,
    ).add_to(map_view)

    heat_points: list[list[float]] = []
    for band, color in PRIORITY_COLORS.items():
        group = MarkerCluster(
        name=f"{_priority_label(band)} অগ্রাধিকার", show=True,
            options={"disableClusteringAtZoom": 12},
        ).add_to(map_view)
        candidates = filtered[filtered["priority_band"].astype(str).eq(band)]
        for _, row in candidates.iterrows():
            latitude, longitude = float(row["lat"]), float(row["lon"])
            marker_label = (
                f"{_priority_label(band)} অগ্রাধিকার | {_type_label(row.get('class'))} | "
                f"{_district_label(row.get('district', 'জেলা নথিভুক্ত নয়'))}"
            )
            popup_html = _popup_html(row)
            is_selected = str(row.get("kiln_id")) == str(selected_id)
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=12 if is_selected else 8,
                color="#111827" if is_selected else color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                weight=4 if is_selected else 2,
                tooltip=f"✓ নির্বাচিত · {marker_label}" if is_selected else marker_label,
                popup=folium.Popup(popup_html, max_width=360),
            ).add_to(group)
            if band == "High":
                raw_weight = pd.to_numeric(pd.Series([row.get("priority")]), errors="coerce").iloc[0]
                weight = float(raw_weight) if pd.notna(raw_weight) else 1.0
                heat_points.append([latitude, longitude, max(0.0, weight)])

    other_candidates = filtered[~filtered["priority_band"].astype(str).isin(PRIORITY_COLORS)]
    if not other_candidates.empty:
        group = folium.FeatureGroup(name="অন্যান্য অগ্রাধিকার", show=True).add_to(map_view)
        for _, row in other_candidates.iterrows():
            popup_html = _popup_html(row)
            is_selected = str(row.get("kiln_id")) == str(selected_id)
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=12 if is_selected else 8,
                color="#111827" if is_selected else "gray",
                fill=True,
                fill_color="gray",
                fill_opacity=0.85,
                weight=4 if is_selected else 2,
                tooltip="✓ নির্বাচিত" if is_selected else None,
                popup=folium.Popup(popup_html, max_width=360),
            ).add_to(group)

    if heat_points:
        HeatMap(
            heat_points,
            name="উচ্চ অগ্রাধিকারের হিটম্যাপ",
            show=False,
            radius=15,
            blur=18,
        ).add_to(map_view)
    folium.LayerControl(collapsed=True).add_to(map_view)
    return map_view


def render_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the Folium map and show details/report for a clicked candidate.

    Input schema: candidate GeoDataFrame and sidebar filter mapping. Output:
    an interactive Folium map plus the selected candidate's detail/report panel.
    """
    visible = _filtered(gdf, filters)
    high_candidates = visible[visible["priority_band"].astype(str).eq("High")]
    list_panel, map_panel = st.columns([2, 3], gap="medium")
    with list_panel:
        st.subheader("\U0001f525 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be")
        st.caption(f"{len(high_candidates):,}\u099f\u09bf \u0989\u099a\u09cd\u099a \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0\u09c7\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0")
        if high_candidates.empty:
            st.info("এই ফিল্টারে উচ্চ অগ্রাধিকারের কোনো প্রার্থী নেই।")
        else:
            list_frame = _kiln_list_frame(high_candidates)
            list_choice = _priority_candidate_list(
                columns=list_frame.columns.tolist(),
                rows=list_frame.astype(str).values.tolist(),
                kiln_ids=high_candidates["kiln_id"].astype(str).tolist(),
                selected_id=(
                    str(st.session_state.get("selected_kiln_id"))
                    if st.session_state.get("selected_kiln_id") is not None
                    else None
                ),
                height=760,
                key="dhoa_high_priority_list",
                default=None,
            )
            if isinstance(list_choice, dict):
                click_token = list_choice.get("selection_token")
                if click_token and click_token != st.session_state.get("dhoa_list_selection_token"):
                    st.session_state["selected_kiln_id"] = str(list_choice.get("kiln_id"))
                    st.session_state["dhoa_list_selection_token"] = click_token
    with map_panel:
        st.markdown(f"**{len(visible):,} / {len(gdf):,} জন প্রার্থী দেখানো হচ্ছে**")
        st.caption("চিহ্নের রং অগ্রাধিকার বোঝায়; গাঢ় সীমানা নির্বাচিত প্রার্থীকে দেখায়।")
        selected_id_for_report = st.session_state.get("selected_kiln_id")
        selected_for_report = (
            visible[visible["kiln_id"].astype(str).eq(str(selected_id_for_report))]
            if selected_id_for_report is not None
            else visible.iloc[0:0]
        )
        if selected_for_report.empty:
            st.caption("PDF পেতে তালিকা বা মানচিত্র থেকে একটি প্রার্থী নির্বাচন করুন।")
        else:
            _render_report_download(selected_for_report.iloc[0])
        map_selection_id = st.session_state.get("selected_kiln_id")
        map_key = f"dhoa_folium_map_{map_selection_id or 'all'}"
        if st.session_state.get("dhoa_map_component_key") != map_key:
            st.session_state["dhoa_last_map_click_count"] = None
            st.session_state["dhoa_map_component_key"] = map_key
        with st.container(key="dhoa_map_frame"):
            map_result = st_folium(
                build_map(gdf, filters),
                key=map_key,
                height=760,
                width=None,
                use_container_width=True,
                returned_objects=["last_object_clicked", "last_object_clicked_count"],
            )
    clicked = map_result.get("last_object_clicked") if isinstance(map_result, dict) else None
    click_count = map_result.get("last_object_clicked_count") if isinstance(map_result, dict) else None
    previous_count = st.session_state.get("dhoa_last_map_click_count")
    if clicked and click_count != previous_count and not visible.empty:
        click_lat = pd.to_numeric(pd.Series([clicked.get("lat")]), errors="coerce").iloc[0]
        click_lon = pd.to_numeric(pd.Series([clicked.get("lng")]), errors="coerce").iloc[0]
        if pd.notna(click_lat) and pd.notna(click_lon):
            from pyproj import Geod

            geod = Geod(ellps="WGS84")
            distances = visible.apply(
                lambda row: abs(
                    geod.inv(
                        float(click_lon),
                        float(click_lat),
                        float(row["lon"]),
                        float(row["lat"]),
                    )[2]
                ),
                axis=1,
            )
            clicked_kiln_id = str(visible.loc[distances.idxmin(), "kiln_id"])
            selection_changed = clicked_kiln_id != st.session_state.get("selected_kiln_id")
            st.session_state["selected_kiln_id"] = clicked_kiln_id
        st.session_state["dhoa_last_map_click_count"] = click_count
        if pd.notna(click_lat) and pd.notna(click_lon) and selection_changed:
            st.rerun()

    selected_id = st.session_state.get("selected_kiln_id")
    selected = visible[visible["kiln_id"].astype(str).eq(str(selected_id))] if selected_id is not None else visible.iloc[0:0]
    if selected.empty:
        st.info("বিস্তারিত ও প্রতিবেদন দেখতে মানচিত্রের কোনো ইটভাটার চিহ্নে চাপ দিন।")
    else:
        _render_selected_candidate(selected.iloc[0])

def render_footer(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the single summary line below the map."""
    visible = _filtered(gdf, filters)
    high = int(visible["priority_band"].eq("High").sum())
    flagged = _flagged_count(visible, load_config()["rules"])
    st.caption(f"দেখানো হচ্ছে {len(visible):,}টি প্রার্থী | উচ্চ অগ্রাধিকার {high:,}টি | নিয়ম পর্যালোচনায় {flagged:,}টি")


def main() -> None:
    """Run the fixed Dhoa page flow."""
    st.markdown(responsive_css(), unsafe_allow_html=True)
    try:
        load_config()
        gdf = load_data()
    except Exception:  # noqa: BLE001 - user-facing data failure boundary
        st.error("তথ্য লোড করা যায়নি। প্রস্তুত ফলাফল ও কনফিগারেশন ফাইল যাচাই করুন।")
        return
    if gdf is None:
        st.error("তথ্য পাওয়া যায়নি। সহায়তার জন্য প্রশাসকের সঙ্গে যোগাযোগ করুন।")
        return
    gdf = add_priority_bands(gdf)
    if "detection_status" not in gdf.columns:
        gdf["detection_status"] = "Known"
    render_header(gdf)
    filters = render_sidebar(gdf)
    st.markdown(
        "<p class='dhoa-mobile-map-hint'>\u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u09a6\u09c7\u0996\u09a4\u09c7 \u09a8\u09bf\u099a\u09c7 \u09b8\u09cd\u0995\u09cd\u09b0\u09b2 \u0995\u09b0\u09c1\u09a8।</p>",
        unsafe_allow_html=True,
    )
    render_district_summary(str(filters["district"]), gdf)
    render_map(gdf, filters)
    render_footer(gdf, filters)
    st.markdown(
        '[\u0986\u0987\u09a8\u0997\u09a4 \u09b0\u09c7\u09ab\u09be\u09b0\u09c7\u09a8\u09cd\u09b8: \u0987\u099f\u09ad\u09be\u099f\u09be \u09b8\u09cd\u09a5\u09be\u09aa\u09a8 \u0993 \u09a8\u09bf\u09af\u09bc\u09a8\u09cd\u09a4\u09cd\u09b0\u09a3 \u0986\u0987\u09a8, \u09e8\u09e6\u09e7\u09e9]'
        '(https://bdlaws.minlaw.gov.bd/act-details-1140.html)'
    )


if __name__ == "__main__":
    main()
