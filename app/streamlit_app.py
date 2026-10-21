"""Dhoa dashboard with shared Bangla labels and two public-facing views."""

from __future__ import annotations

import html
from io import BytesIO
import json
import json as _json
import logging
import pathlib as _pathlib
import sys
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

DASHBOARD_TITLE = unicodedata.normalize("NFC", "\u09a7\u09cb\u0981\u09af\u09bc\u09be")
assert "\u0981" in DASHBOARD_TITLE, repr(DASHBOARD_TITLE)

st.set_page_config(page_title=DASHBOARD_TITLE, layout="wide", initial_sidebar_state="expanded")

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
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

# isort: off
from dashboard_filters import ( 
    add_priority_bands,
)
from data_loader import load_kilns 
from popup import format_district_label
from src.rules.engine import _ensure_class_column 
# isort: on

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_PATH = DATA_DIR / "kilns_prioritised.parquet"
_ADMIN_AREAS_PATH = _pathlib.Path(__file__).parent.parent / "config" / "bd_admin_areas.json"
try:
    BD_ADMIN_AREAS: dict = _json.loads(_ADMIN_AREAS_PATH.read_text(encoding="utf-8"))
except Exception:
    BD_ADMIN_AREAS = {}
_priority_candidate_list = components.declare_component(
    "dhoa_priority_candidate_list",
    path=str(_ROOT / "app" / "components" / "priority_candidate_list"),
)
DESIGN_COLORS = {
    "high": "#e53e3e",
    "medium": "#dd6b20",
    "low": "#38a169",
    "new": "#3182ce",
    "advisory": "#d69e2e",
    "background": "#0e1117",
    "card": "#1e2329",
    "text": "#fafafa",
}
PRIORITY_COLORS = {
    "High": DESIGN_COLORS["high"],
    "Medium": DESIGN_COLORS["medium"],
    "Low": DESIGN_COLORS["low"],
}
ALL_KILN_TYPES = "__all__"
KILN_TYPE_LABELS = {
    ALL_KILN_TYPES: "\u09b8\u09ac \u09a7\u09b0\u09a8",
    "Zigzag": "\u099c\u09bf\u0997\u099c\u09cd\u09af\u09be\u0997 \u0987\u099f\u09ad\u09be\u099f\u09be",
    "FCBK": "\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf \u0987\u099f\u09ad\u09be\u099f\u09be",
}
INSPECTOR_CSV_COLUMNS = [
    ("kiln_id", "\u09ad\u09be\u099f\u09be ID"),
    ("lat", "\u0985\u0995\u09cd\u09b7\u09be\u0982\u09b6"),
    ("lon", "\u09a6\u09cd\u09b0\u09be\u0998\u09bf\u09ae\u09be\u0982\u09b6"),
    ("district", "\u099c\u09c7\u09b2\u09be"),
    ("upazila", "\u0989\u09aa\u099c\u09c7\u09b2\u09be"),
    ("nearest_place", "\u09a8\u09bf\u0995\u099f\u09a4\u09ae \u09b8\u09cd\u09a5\u09be\u09a8"),
    ("nearest_place_dist_m", "\u09a6\u09c2\u09b0\u09a4\u09cd\u09ac (\u09ae\u09bf)"),
    ("priority_band", "\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0"),
    ("breach_count", "\u09b2\u0999\u09cd\u0998\u09a8 \u09b8\u0982\u0996\u09cd\u09af\u09be"),
]
COMMUNITY_CSV_COLUMNS = [
    ("kiln_id", "\u09ad\u09be\u099f\u09be ID"),
    ("lat", "\u0985\u0995\u09cd\u09b7\u09be\u0982\u09b6"),
    ("lon", "\u09a6\u09cd\u09b0\u09be\u0998\u09bf\u09ae\u09be\u0982\u09b6"),
    ("district", "\u099c\u09c7\u09b2\u09be"),
    ("upazila", "\u0989\u09aa\u099c\u09c7\u09b2\u09be"),
    ("nearest_place", "\u09a8\u09bf\u0995\u099f\u09a4\u09ae \u09b8\u09cd\u09a5\u09be\u09a8"),
    ("nearest_place_dist_m", "\u09a6\u09c2\u09b0\u09a4\u09cd\u09ac (\u09ae\u09bf)"),
    ("priority_band", "\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0"),
]
METRIC_LABELS = {
    "total_kilns": "\u09ae\u09cb\u099f \u09ad\u09be\u099f\u09be",
    "high_priority_kilns": "\u09aa\u09b0\u09bf\u09ac\u09c7\u09b6 \u09ac\u09bf\u09aa\u099c\u09cd\u099c\u09a8\u0995 \u09ad\u09be\u099f\u09be",
    "rule_violations": "\u0986\u0987\u09a8 \u09b2\u0999\u09cd\u0998\u09a8",
    "last_updated": "\u09b8\u09b0\u09cd\u09ac\u09b6\u09c7\u09b7 \u09b9\u09be\u09b2\u09a8\u09be\u0997\u09be\u09a6",
    "total_candidates": "\u09ae\u09cb\u099f \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0",
    "estimated_area": "\u0986\u09a8\u09c1\u09ae\u09be\u09a8\u09bf\u0995 \u098f\u09b2\u09be\u0995\u09be (\u09ac\u09b0\u09cd\u0997 \u0995\u09bf\u09ae\u09bf)",
    "primary_signal": "\u09aa\u09cd\u09b0\u09a7\u09be\u09a8 \u09a8\u09bf\u09af\u09bc\u09ae-\u09b8\u0982\u0995\u09c7\u09a4",
    "new_candidates": "\u09a8\u09a4\u09c1\u09a8 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0",
    "rule_signals": "\u09a8\u09bf\u09af\u09bc\u09ae \u09b8\u0982\u0995\u09c7\u09a4",
}


def _english_ui() -> bool:
    """Return whether the visitor selected the English interface."""
    return bool(st.session_state.get("dhoa_english_ui", False))


def _ui_text(bangla: str, english: str) -> str:
    """Choose a display label from the persistent language preference."""
    return english if _english_ui() else bangla


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
@import url("https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap");
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100%; padding: 0.75rem 1.25rem 1.5rem;
}
[data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding-top: 0.75rem !important;
}
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
    grid-template-columns: repeat(4, minmax(0, 1fr));
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
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
    display: block !important;
    box-sizing: border-box !important;
    width: 100% !important;
    padding: 0.38em 0 0.12em !important;
    margin-top: 0.35rem !important;
    line-height: 1.8 !important;
    overflow: visible !important;
    font-family: "Noto Sans Bengali", sans-serif !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
}
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title span {
    font-family: "Noto Sans Bengali", sans-serif !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
    line-height: inherit !important;
    overflow: visible !important;
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
        font-size: 1.9rem !important;
        line-height: 1.8 !important;
        padding-top: 0.38em !important;
        padding-bottom: 0.12em !important;
    }
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
    return PRIORITY_COLORS.get(str(row.get("priority_band", "")), DESIGN_COLORS["advisory"])


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
    """Return a concise label for the kiln type in the selected language."""
    if str(value) == "FCBK":
        return _ui_text("\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf \u0987\u099f\u09ad\u09be\u099f\u09be", "Fixed chimney kiln")
    return _ui_text("\u099c\u09bf\u0997\u099c\u09cd\u09af\u09be\u0997 \u0987\u099f\u09ad\u09be\u099f\u09be", "Zigzag kiln")


def _priority_label(value: object) -> str:
    """Translate an internal or Bengali priority value for display."""
    labels = {
        "High": ("\u0989\u099a\u09cd\u099a", "High"),
        "\u0989\u099a\u09cd\u099a": ("\u0989\u099a\u09cd\u099a", "High"),
        "Medium": ("\u09ae\u09be\u099d\u09be\u09b0\u09bf", "Medium"),
        "\u09ae\u09be\u099d\u09be\u09b0\u09bf": ("\u09ae\u09be\u099d\u09be\u09b0\u09bf", "Medium"),
        "Low": ("\u09a8\u09bf\u09ae\u09cd\u09a8", "Low"),
        "\u09a8\u09bf\u09ae\u09cd\u09a8": ("\u09a8\u09bf\u09ae\u09cd\u09a8", "Low"),
    }
    bangla, english = labels.get(
        str(value),
        ("\u09a8\u09bf\u09b0\u09cd\u09a7\u09be\u09b0\u09bf\u09a4 \u09a8\u09af\u09bc", "Unclassified"),
    )
    return _ui_text(bangla, english)


def _district_label(value: object) -> str:
    """Translate district options while preserving unknown district names."""
    text = str(value)
    labels = {
        "Chapainawabganj": "\u099a\u09be\u0981\u09aa\u09be\u0987\u09a8\u09ac\u09be\u09ac\u0997\u099e\u09cd\u099c",
        "Gazipur": "\u0997\u09be\u099c\u09c0\u09aa\u09c1\u09b0",
        "Rajshahi": "\u09b0\u09be\u099c\u09b6\u09be\u09b9\u09c0",
        "Dhaka": "\u09a2\u09be\u0995\u09be",
        "Chittagong": "\u099a\u099f\u09cd\u099f\u0997\u09cd\u09b0\u09be\u09ae",
    }
    return text if _english_ui() else labels.get(text, format_district_label(value))


def _area_display_name(row: Mapping[str, object]) -> str:
    """Format a kiln's administrative area for the active interface language."""
    upazila = row.get("upazila")
    district = row.get("district")
    parts = [str(value).strip() for value in (upazila, district) if value is not None and pd.notna(value) and str(value).strip()]
    if not parts:
        return _ui_text("\u0985\u099c\u09be\u09a8\u09be \u098f\u09b2\u09be\u0995\u09be", "Unknown area")
    if len(parts) > 1:
        parts[-1] = _district_label(parts[-1])
    elif parts[0] in {"Dhaka", "Gazipur", "Rajshahi", "Chittagong", "Chapainawabganj"}:
        parts[0] = _district_label(parts[0])
    return ", ".join(parts)


def _signal_label(value: object) -> str:
    """Translate known rule identifiers for dashboard display."""
    labels = {
        "near_school": ("\u09b8\u09cd\u0995\u09c1\u09b2\u09c7\u09b0 \u0995\u09be\u099b\u09c7", "Near school"),
        "near_hospital": ("\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2\u09c7\u09b0 \u0995\u09be\u099b\u09c7", "Near hospital"),
        "near_settlement": ("\u09ac\u09b8\u09a4\u09bf\u09b0 \u0995\u09be\u099b\u09c7", "Near settlement"),
        "near_railway": ("\u09b0\u09c7\u09b2\u09aa\u09a5\u09c7\u09b0 \u0995\u09be\u099b\u09c7", "Near railway"),
        "near_wetland": ("\u099c\u09b2\u09be\u09ad\u09c2\u09ae\u09bf\u09b0 \u0995\u09be\u099b\u09c7", "Near wetland"),
        "near_government_forest": ("\u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09ac\u09a8\u09c7\u09b0 \u0995\u09be\u099b\u09c7", "Near government forest"),
        "technology_flagged": ("\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf \u09aa\u09cd\u09b0\u09af\u09c1\u0995\u09cd\u09a4\u09bf", "Fixed chimney technology"),
    }
    bangla, english = labels.get(str(value), (str(value), str(value).replace("_", " ")))
    return _ui_text(bangla, english)


def _signals(row: pd.Series) -> list[str]:
    value = row.get("breached_rules", [])
    if hasattr(value, "tolist") and not isinstance(value, str):
        value = value.tolist()
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(signal) for signal in value if signal is not None and pd.notna(signal) and str(signal).strip().casefold() not in {"", "nan", "none"}]


def _priority_reason(row: pd.Series) -> str:
    names = {
        "near_school": (("স্কুল", "school"), ("dist_schools_m", "dist_school_m")),
        "near_hospital": (("হাসপাতাল", "hospital"), ("dist_hospitals_m", "dist_hospital_m")),
        "near_settlement": (("বসতি", "settlement"), ("dist_settlements_m", "dist_settlement_m")),
        "near_railway": (("রেলপথ", "railway"), ("dist_railways_m", "dist_railway_m")),
        "near_wetland": (("জলাভূমি", "wetland"), ("dist_water_m", "dist_wetland_m")),
        "near_government_forest": (
            ("সরকারি বন", "government forest"),
            ("dist_government_forest_m", "dist_forests_m"),
        ),
        "technology_flagged": (("ফিক্সড চিমনি প্রযুক্তি", "fixed chimney technology"), ()),
    }
    reasons: list[str] = []
    for signal in _signals(row):
        labels, columns = names.get(str(signal), ((str(signal), str(signal).replace("_", " ")), ()))
        label = _ui_text(*labels)
        distance = next(
            (
                value
                for column in columns
                if pd.notna(
                    value := pd.to_numeric(
                        pd.Series([row.get(column)]), errors="coerce"
                    ).iloc[0]
                )
            ),
            None,
        )
        reasons.append(
            _ui_text(f"{label} থেকে {distance:,.0f} মিটার", f"{distance:,.0f} m from {label}")
            if distance is not None
            else label
        )
    return " · ".join(reasons) if reasons else _ui_text("কোনো নিয়ম-সংকেত নথিভুক্ত নেই", "No rule signals recorded")


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


def community_distances(gdf: gpd.GeoDataFrame, latitude: float, longitude: float) -> pd.Series:
    """Calculate kiln distances from a WGS84 point.

    Input schema: kiln GeoDataFrame with numeric ``lat``/``lon`` columns in
    EPSG:4326 and a WGS84 search coordinate. Output: distances in metres,
    indexed like the input frame, measured in the selected local projected CRS.
    """
    from src.geo.crs import get_projected_crs

    projected_crs = get_projected_crs(longitude)
    search_point = gpd.GeoSeries(
        gpd.points_from_xy([longitude], [latitude]), crs="EPSG:4326"
    ).to_crs(projected_crs).iloc[0]
    kiln_points = gpd.GeoSeries(
        gpd.points_from_xy(gdf["lon"], gdf["lat"], crs="EPSG:4326"), index=gdf.index
    ).to_crs(projected_crs)
    return kiln_points.distance(search_point)


def _community_area_centroid(gdf: gpd.GeoDataFrame) -> tuple[float, float]:
    """Return the projected centroid of candidate points as WGS84 latitude/longitude.

    Input schema: non-empty GeoDataFrame with numeric lat/lon columns in
    EPSG:4326. Output schema: (latitude, longitude) at the selected area's
    candidate-point centroid.
    """
    from src.geo.crs import get_projected_crs

    centroid_lon = float(pd.to_numeric(gdf["lon"], errors="coerce").mean())
    projected_crs = get_projected_crs(centroid_lon)
    points = gpd.GeoSeries(
        gpd.points_from_xy(gdf["lon"], gdf["lat"], crs="EPSG:4326"),
        index=gdf.index,
    ).to_crs(projected_crs)
    centroid = points.union_all().centroid
    centroid_wgs84 = gpd.GeoSeries([centroid], crs=projected_crs).to_crs("EPSG:4326").iloc[0]
    return float(centroid_wgs84.y), float(centroid_wgs84.x)


def _add_map_base_layers(map_view: folium.Map, *, with_layer_control: bool = True) -> None:
    """Add the selectable street and satellite basemaps to a Folium map.

    Args:
        map_view: The Folium map to add layers to.
        with_layer_control: If True, also add a LayerControl widget inside the
            map.  Set to False for the inspector map, where streamlit-folium
            remounts the component whenever marker content changes — remounting
            re-executes the map's JavaScript in the same iframe scope, and the
            deterministic variable name ``layer_control_div_2`` (assigned by
            streamlit-folium's ID-normalisation pass) causes a
            "already declared" crash.  The dashboard controls tile selection
            through its main-area Map type selector.
    """
    selected_tile = st.session_state.get("map_tile", "street")
    if selected_tile not in {"street", "satellite"}:
        selected_tile = "street"
    folium.TileLayer(
        "OpenStreetMap",
        name=_ui_text("\u09b0\u09be\u09b8\u09cd\u09a4\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0", "Street map"),
        overlay=False,
        control=True,
        show=selected_tile == "street",
    ).add_to(map_view)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles \u00a9 Esri",
        name=_ui_text("\u09b8\u09cd\u09af\u09be\u099f\u09c7\u09b2\u09be\u0987\u099f \u099b\u09ac\u09bf", "Satellite imagery"),
        overlay=False,
        control=True,
        show=selected_tile == "satellite",
    ).add_to(map_view)
    if with_layer_control:
        folium.LayerControl(collapsed=False).add_to(map_view)


def _render_map_type_filter() -> str:
    """Render the main-area basemap selector and return its canonical value.

    Input schema: Streamlit session state may contain a ``map_tile`` key.
    Output schema: ``street`` or ``satellite``; the selected value is stored in
    session state for both Inspector and Community maps.
    """
    if st.session_state.get("map_tile") not in {"street", "satellite"}:
        st.session_state["map_tile"] = "street"
    widget_key = f"map_tile_{'en' if _english_ui() else 'bn'}"
    st.session_state[widget_key] = st.session_state["map_tile"]
    selected_tile = st.selectbox(
        _ui_text("মানচিত্রের ধরন", "Map type"),
        ["street", "satellite"],
        format_func=lambda value: _ui_text(
            "রাস্তার মানচিত্র" if value == "street" else "স্যাটেলাইট ছবি",
            "Street map" if value == "street" else "Satellite imagery",
        ),
        key=widget_key,
        index=["street", "satellite"].index(st.session_state["map_tile"]),
        on_change=_sync_map_tile,
        args=(widget_key,),
    )
    st.session_state["map_tile"] = selected_tile
    return selected_tile


def get_filtered_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return candidates for the active view using its canonical session filters.

    Input schema: prioritized GeoDataFrame with district, upazila, lat/lon,
    kiln class, and priority_band. Output: copied GeoDataFrame after
    case-insensitive district, upazila, kiln type, and priority filtering.
    """
    active_view = st.session_state.get("dhoa_active_view", "inspector")
    if active_view == "community":
        st.session_state.pop("community_centroid", None)
        result = gdf.copy()
        district = st.session_state.get("community_filter_district", "\u09b8\u09ac \u099c\u09c7\u09b2\u09be")
        upazila = st.session_state.get("community_filter_upazila", "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be")
        if district == "\u09b8\u09ac \u099c\u09c7\u09b2\u09be":
            return result.iloc[0:0].copy()
        if district != "\u09b8\u09ac \u099c\u09c7\u09b2\u09be":
            if "district" not in result.columns:
                return result.iloc[0:0].copy()
            result = result[result["district"].astype(str).eq(str(district))].copy()
        if upazila != "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be":
            if "upazila" not in result.columns:
                return result.iloc[0:0].copy()
            result = result[result["upazila"].astype(str).eq(str(upazila))].copy()
        if result.empty:
            result["distance_m"] = pd.Series(dtype="float64", index=result.index)
            return result
        search_point = st.session_state.get("community_search_point")
        if search_point is None:
            search_lat, search_lon = _community_area_centroid(result)
        else:
            search_lat, search_lon = map(float, search_point)
        st.session_state["community_centroid"] = (search_lat, search_lon)
        radius_m = int(st.session_state.get("community_radius_m", 1000))
        distances = community_distances(result, search_lat, search_lon)
        result = result.loc[distances.le(radius_m)].copy()
        result["distance_m"] = distances.loc[result.index]
        return result.sort_values("distance_m", ascending=True)

    result = gdf.copy()
    district = st.session_state.get("filter_district", "\u09b8\u09ac \u099c\u09c7\u09b2\u09be")
    upazila = st.session_state.get("filter_upazila", "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be")
    kiln_type = st.session_state.get("filter_kiln_type", ALL_KILN_TYPES)
    _default_priorities = ["\u0989\u099a\u09cd\u099a", "\u09ae\u09be\u099d\u09be\u09b0\u09bf", "\u09a8\u09bf\u09ae\u09cd\u09a8"]
    priorities = st.session_state.get("filter_priority") or _default_priorities
    # Guard: remap any English labels that slipped into session state.
    _en_to_bn = {
        "High": "\u0989\u099a\u09cd\u099a",
        "Medium": "\u09ae\u09be\u099d\u09be\u09b0\u09bf",
        "Low": "\u09a8\u09bf\u09ae\u09cd\u09a8",
    }
    priorities = [_en_to_bn.get(p, p) for p in priorities]
    if not priorities:
        priorities = _default_priorities

    if district != "\u09b8\u09ac \u099c\u09c7\u09b2\u09be":
        if "district" not in result:
            return result.iloc[0:0].copy()
        result = result[result["district"].astype(str).eq(str(district))].copy()
    if upazila != "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be":
        if "upazila" not in result:
            return result.iloc[0:0].copy()
        result = result[result["upazila"].astype(str).eq(str(upazila))].copy()

    if kiln_type != ALL_KILN_TYPES:
        type_column = "class" if "class" in result.columns else "class_name"
        if type_column not in result.columns:
            return result.iloc[0:0].copy()
        result = result[result[type_column].astype(str).eq(str(kiln_type))].copy()

    priority_values = {
        "\u0989\u099a\u09cd\u099a": "High",
        "\u09ae\u09be\u099d\u09be\u09b0\u09bf": "Medium",
        "\u09a8\u09bf\u09ae\u09cd\u09a8": "Low",
    }
    selected_priorities = {priority_values[value] for value in priorities if value in priority_values}
    if not selected_priorities:
        # Fallback: session state was completely stale — show all priorities.
        selected_priorities = {"High", "Medium", "Low"}
    if "priority_band" not in result.columns:
        # Source data has no priority columns at all — show everything rather
        # than filtering to zero rows.
        result["priority_band"] = "Unknown / not available"
        if "priority" in result.columns:
            result = result.sort_values("priority", ascending=False, na_position="last")
        return result
    # When priority data exists, apply the user's band filter normally.
    known_bands = result["priority_band"].astype(str).isin(PRIORITY_COLORS)
    if not known_bands.any():
        # All rows are unknown priority — skip the filter to avoid empty map.
        if "priority" in result.columns:
            result = result.sort_values("priority", ascending=False, na_position="last")
        return result
    result = result[result["priority_band"].astype(str).isin(selected_priorities)].copy()
    if "priority" in result.columns:
        result = result.sort_values("priority", ascending=False, na_position="last")
    return result


def community_alert_pdf(location: str, rows: pd.DataFrame, radius_m: int) -> bytes:
    """Create a one-page community screening PDF.

    Input schema: searched location label and rows with distance_m, class,
    priority band, lat, lon, and radius in metres. Output: A4 PDF bytes.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=False, margin=12)
    bengali_font = BASE_DIR / "assets" / "fonts" / "NotoSansBengali-Regular.ttf"
    has_bengali_font = bengali_font.is_file()
    if has_bengali_font:
        pdf.add_font("NotoBengali", fname=str(bengali_font))
        pdf.set_font("NotoBengali", size=10)
        pdf.multi_cell(0, 6, "এই প্রতিবেদনটি কমিউনিটি সচেতনতার জন্য — শুধুমাত্র তথ্যের উদ্দেশ্যে।", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 16)
    title_separator = "—" if has_bengali_font else "-"
    pdf.multi_cell(0, 9, f"Dhoa {title_separator} Community Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf_location = location if has_bengali_font else location.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 7, f"Kiln Candidates Near {pdf_location}", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 7, f"Generated: {datetime.now(UTC):%Y-%m-%d}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.multi_cell(
        0, 6,
        f"{len(rows)} kiln candidates were identified within {radius_m / 1000:g} km of {pdf_location} using satellite imagery analysis of the 2025-26 dry season.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)
    headers = ("Distance", "Kiln type", "Priority", "Coordinates")
    widths = (32, 38, 34, 78)
    pdf.set_font("Helvetica", "B", 8)
    for header, width in zip(headers, widths):
        pdf.cell(width, 7, header, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for _, row in rows.iterrows():
        values = (
            f"{row['distance_m']:.0f} m", str(row.get("class", "Unknown")),
            str(row.get("priority_band", "Unknown")), f"{float(row['lat']):.5f}, {float(row['lon']):.5f}",
        )
        for value, width in zip(values, widths):
            safe_value = str(value) if has_bengali_font else str(value).encode("latin-1", "replace").decode("latin-1")
            pdf.cell(width, 7, safe_value[:38], border=1)
        pdf.ln()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "What you can do:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for action in (
        "File a complaint: DoE hotline 16131 or doe.gov.bd",
        "Contact your Upazila Environment Officer",
        "Share this report with local NGOs or media",
        "Request official inspection through your local administration",
    ):
        pdf.multi_cell(0, 6, f"- {action}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 6, "Generated by Dhoa · Community information · DoE: 16131 | doe.gov.bd", align="C")
    return bytes(pdf.output())


def render_community_view(gdf: gpd.GeoDataFrame) -> None:
    """Render the shared community search, result map/table, and alert PDF.

    Input schema: prioritized kiln GeoDataFrame with lat/lon, class,
    priority, and optional OSM place fields. Output schema: a
    district/upazila filters, adjustable centroid-radius results, map, and table.
    """
    _qp = st.query_params
    if "_geo_lat" in _qp and "_geo_lon" in _qp:
        try:
            _glat = float(_qp["_geo_lat"])
            _glon = float(_qp["_geo_lon"])
            st.session_state["community_search_point"] = (_glat, _glon)
            st.session_state["community_search_name"] = _ui_text("\u0986\u09ae\u09be\u09b0 \u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8", "My location")
            st.query_params.clear()
        except Exception:
            pass
    st.markdown(f"<div class='dhoa-section-title'>{_ui_text('\u0986\u09aa\u09a8\u09be\u09b0 \u098f\u09b2\u09be\u0995\u09be\u09b0 \u0995\u09be\u099b\u09be\u099b\u09bf \u0996\u09c1\u0981\u099c\u09c1\u09a8', 'Find kilns near you')}</div>", unsafe_allow_html=True)

    # Audio guide
    with st.container(border=True):
        st.markdown(_ui_text("\U0001f50a \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09bf\u0995\u09be \u09b6\u09c1\u09a8\u09c1\u09a8", "\U0001f50a Listen to the guide"))
        community_guide = _ROOT / "app" / "static" / "community_guide.mp3"
        if community_guide.is_file():
            st.audio(str(community_guide))
        else:
            st.info(_ui_text("\U0001f50a \u0985\u09a1\u09bf\u0993 \u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09bf\u0995\u09be \u09b6\u09c0\u0998\u09cd\u09b0\u0987 \u0986\u09b8\u099b\u09c7", "\U0001f50a Audio guide coming soon"))

    # District and upazila filters
    all_districts = "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
    all_areas = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"
    district_values = (
        sorted(gdf["district"].dropna().astype(str).unique().tolist())
        if "district" in gdf.columns else []
    )
    district_options = [all_districts, *district_values]
    if st.session_state.get("community_filter_district") not in district_options:
        st.session_state["community_filter_district"] = all_districts
    sel_district = st.selectbox(
        _ui_text("\u099c\u09c7\u09b2\u09be", "District"),
        district_options,
        format_func=lambda value: _ui_text(all_districts, "All districts") if value == all_districts else _district_label(value),
        key="community_filter_district",
        on_change=_reset_community_upazila_filter,
    )
    district_selected = sel_district != all_districts
    upazila_source = gdf if district_selected else gdf.iloc[0:0]
    if district_selected and "district" in upazila_source.columns:
        upazila_source = upazila_source[upazila_source["district"].astype(str).eq(str(sel_district))]
    data_upazilas = (
        sorted(upazila_source["upazila"].dropna().astype(str).unique().tolist())
        if "upazila" in upazila_source.columns else []
    )
    known_upazilas = BD_ADMIN_AREAS.get(sel_district, [])
    upazila_values = sorted(set(known_upazilas) | set(data_upazilas))
    upazila_options = [all_areas, *upazila_values]
    if st.session_state.get("community_filter_upazila") not in upazila_options:
        st.session_state["community_filter_upazila"] = all_areas
    sel_upazila = st.selectbox(
        _ui_text("\u098f\u09b2\u09be\u0995\u09be (\u0989\u09aa\u099c\u09c7\u09b2\u09be)", "Area / Thana"),
        upazila_options,
        format_func=lambda value: _ui_text(all_areas, "All areas") if value == all_areas else value,
        key="community_filter_upazila",
        disabled=not district_selected,
    )

    # Radius slider (always visible)
    radius_m = int(st.slider(
        _ui_text("\u0985\u09a8\u09c1\u09b8\u09a8\u09cd\u09a7\u09be\u09a8\u09c7\u09b0 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7 (\u09ae\u09bf\u099f\u09be\u09b0)", "Search radius (metres)"),
        min_value=250,
        max_value=5000,
        value=st.session_state.get("community_radius_m", 1000),
        step=250,
        key="community_radius_m",
    ))

    st.divider()

    # Option A: type a place name
    with st.form("community_search_form", border=False):
        name = st.text_input(
            _ui_text("\u09a8\u09be\u09ae \u09b2\u09bf\u0996\u09c1\u09a8", "Search by name"),
            placeholder=_ui_text("\u09af\u09c7\u09ae\u09a8: \u0986\u09b6\u09c1\u09b2\u09bf", "e.g. Ashulia"),
            key="community_location_name",
            disabled=not district_selected,
        )
        submitted = st.form_submit_button(
            _ui_text("\U0001f50d \u0985\u09a8\u09c1\u09b8\u09a8\u09cd\u09a7\u09be\u09a8 \u0995\u09b0\u09c1\u09a8", "\U0001f50d Search"),
            width="stretch",
            disabled=not district_selected,
        )

    st.divider()

    # Option B: use GPS location
    st.markdown(_ui_text("**\u0985\u09a5\u09ac\u09be \u0986\u09aa\u09a8\u09be\u09b0 \u09ac\u09b0\u09cd\u09a4\u09ae\u09be\u09a8 \u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09c1\u09a8:**", "**Or use your current location:**"))
    gps_js = """
<script>
function sendLocation() {
    if (!navigator.geolocation) {
        window.parent.postMessage({type:'streamlit:setComponentValue',value:{error:'unsupported'}}, '*');
        return;
    }
    navigator.geolocation.getCurrentPosition(
        function(pos) {
            var params = new URLSearchParams(window.parent.location.search);
            params.set('gps_lat', pos.coords.latitude.toFixed(6));
            params.set('gps_lon', pos.coords.longitude.toFixed(6));
            window.parent.location.search = params.toString();
        },
        function(err) {
            alert('Location access denied. Please allow location access and try again.');
        },
        {enableHighAccuracy: true, timeout: 10000}
    );
}
</script>
<button onclick="sendLocation()" style="
    background:#3b82f6;color:white;border:none;padding:.5rem 1.2rem;
    border-radius:.4rem;font-size:1rem;cursor:pointer;width:100%
">\U0001f4cd """ + _ui_text("\u0986\u09ae\u09be\u09b0 \u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09c1\u09a8", "Use my location") + """</button>
"""
    components.html(gps_js, height=60)

    # Handle GPS query parameters
    gps_params = st.query_params
    gps_lat_str = gps_params.get("gps_lat")
    gps_lon_str = gps_params.get("gps_lon")
    if gps_lat_str and gps_lon_str:
        try:
            search_point = (float(gps_lat_str), float(gps_lon_str))
            st.session_state["community_search_point"] = search_point
            st.session_state["community_search_name"] = _ui_text("\u0986\u09aa\u09a8\u09be\u09b0 \u0985\u09ac\u09b8\u09cd\u09a5\u09be\u09a8", "Your location")
            st.query_params.clear()
        except ValueError:
            pass

    # Handle name-search submit
    if submitted:
        st.session_state.pop("community_search_point", None)
        st.session_state.pop("community_search_name", None)
        st.session_state.pop("community_report", None)
        location_name = name.strip()
        if not location_name:
            st.warning(_ui_text("\u26a0\ufe0f \u0996\u09cb\u0981\u099c\u09be\u09b0 \u099c\u09a8\u09cd\u09af \u098f\u0995\u099f\u09bf \u098f\u09b2\u09be\u0995\u09be\u09b0 \u09a8\u09be\u09ae \u09b2\u09bf\u0996\u09c1\u09a8\u0964", "\u26a0\ufe0f Please enter a location name."))
            return
        with st.spinner(_ui_text("\u0996\u09cb\u0981\u099c\u09be \u09b9\u099a\u09cd\u099b\u09c7\u2026", "Searching\u2026")):
            loc = None
            queries = [f"{location_name}, Bangladesh", f"{location_name}, Dhaka", location_name]
            try:
                from geopy.geocoders import Photon as _Photon
                _geo = _Photon(user_agent="dhoa-bd-v2", timeout=15)
                for query in queries:
                    try:
                        loc = _geo.geocode(query)
                        if loc is not None:
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if loc is None:
                try:
                    from geopy.geocoders import Nominatim as _Nominatim
                    _geo2 = _Nominatim(user_agent="dhoa-bd-v3", timeout=15)
                    for query in queries:
                        try:
                            loc = _geo2.geocode(query, country_codes="BD")
                            if loc is not None:
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
        if loc is None:
            st.warning(_ui_text(
                "\u26a0\ufe0f \u09b8\u09cd\u09a5\u09be\u09a8\u09c7\u09b0 \u09a8\u09be\u09ae \u09aa\u09be\u0993\u09af\u09bc\u09be \u09af\u09be\u09af\u09bc\u09a8\u09bf\u0964 \u0985\u09a8\u09cd\u09af \u09ac\u09be\u09a8\u09be\u09a8 \u09ac\u09be 'Ashulia, Savar' \u098f\u09b0 \u09ae\u09a4\u09cb \u09b2\u09bf\u0996\u09c1\u09a8\u0964",
                "\u26a0\ufe0f Location not found. Try a different spelling or add the district, e.g. 'Ashulia, Savar'.",
            ))
            return
        search_point = (float(loc.latitude), float(loc.longitude))
        st.session_state["community_search_point"] = search_point
        st.session_state["community_search_name"] = location_name

    # No search yet
    search_point = st.session_state.get("community_search_point")
    selected_location_name = st.session_state.get("community_search_name", "")
    if search_point is None:
        st.info(_ui_text("\u09ad\u09be\u099f\u09be \u09a6\u09c7\u0996\u09a4\u09c7 \u098f\u0995\u099f\u09bf \u099c\u09c7\u09b2\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09b0\u09c1\u09a8\u0964", "Select a district and search for a place or use GPS to view kilns."))
        return
    if not district_selected:
        st.info(_ui_text("\u09ad\u09be\u099f\u09be \u09a6\u09c7\u0996\u09a4\u09c7 \u098f\u0995\u099f\u09bf \u099c\u09c7\u09b2\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09b0\u09c1\u09a8\u0964", "Select a district to view kilns."))
        return

    st.session_state["community_filter_district"] = sel_district
    st.session_state["community_filter_upazila"] = sel_upazila
    search_lat, search_lon = search_point
    location_name = selected_location_name or sel_upazila if sel_upazila != all_areas else selected_location_name or sel_district
    area_name = location_name
    nearby = get_filtered_gdf(gdf)

    result_column, map_column = st.columns([2, 3], gap="medium")
    with result_column:
        st.subheader(_ui_text("\u0995\u09be\u099b\u09be\u0995\u09be\u099b\u09bf\u09b0 \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0", "Nearby kiln candidates"))
        with st.container(border=True):
            if nearby.empty:
                st.success(_ui_text(
                    f"\u2705 {radius_m / 1000:g} \u0995\u09bf\u09ae\u09bf \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7\u09c7 \u0995\u09cb\u09a8\u09cb \u09ad\u09be\u099f\u09be \u09aa\u09be\u0993\u09af\u09bc\u09be \u09af\u09be\u09af\u09bc\u09a8\u09bf\u0964",
                    f"\u2705 No kilns found within {radius_m / 1000:g} km."
                ))
            else:
                st.metric(
                    _ui_text(f"{radius_m / 1000:g} \u0995\u09bf\u09ae\u09bf \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7\u09c7\u09b0 \u09ae\u09a7\u09cd\u09af\u09c7 \u09ad\u09be\u099f\u09be", f"Kilns within {radius_m / 1000:g} km"),
                    f"{len(nearby):,}",
                )
            try:
                report = community_alert_pdf(area_name, nearby, radius_m)
                st.session_state["community_report"] = report
                st.download_button(
                    _ui_text("\u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1 \u0995\u09b0\u09c1\u09a8", "Download report"), report,
                    "dhoa_community_report.pdf", "application/pdf",
                    width="stretch", key="community_alert_download",
                )
            except Exception:
                logging.exception("Community PDF generation failed")
                st.error(_ui_text("\u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a4\u09c8\u09b0\u09bf \u0995\u09b0\u09be \u09af\u09be\u09df\u09a8\u09bf\u0964 \u0986\u09ac\u09be\u09b0 \u099a\u09c7\u09b7\u09cd\u099f\u09be \u0995\u09b0\u09c1\u09a8\u0964", "Report generation failed. Please try again."))
            if not nearby.empty:
                distance_header = _ui_text("\u09a6\u09c2\u09b0\u09a4\u09cd\u09ac (\u09ae\u09bf\u099f\u09be\u09b0)", "Distance (m)")
                area_header = _ui_text("\u098f\u09b2\u09be\u0995\u09be", "Area")
                type_header = _ui_text("\u09ad\u09be\u099f\u09be\u09b0 \u09a7\u09b0\u09a8", "Kiln type")
                priority_header = _ui_text("\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0", "Priority")
                directions_header = _ui_text("\u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be", "Directions")
                nearby["directions_url"] = [
                    f"https://www.google.com/maps/dir/?api=1&destination={float(row['lat']):.6f}%2C{float(row['lon']):.6f}"
                    for _, row in nearby.iterrows()
                ]
                table = pd.DataFrame({
                    distance_header: nearby["distance_m"].round(0).astype("Int64").astype("string").fillna(_ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "N/A")).to_numpy(),
                    area_header: [_area_display_name(row) for _, row in nearby.iterrows()],
                    type_header: [_type_label(row.get("class")) for _, row in nearby.iterrows()],
                    priority_header: [_priority_label(row.get("priority_band")) for _, row in nearby.iterrows()],
                    directions_header: nearby["directions_url"].tolist(),
                })
                st.dataframe(
                    table, hide_index=True, width="stretch",
                    column_config={directions_header: st.column_config.LinkColumn(display_text=_ui_text("\u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be \u09aa\u09be\u09a8", "Get directions"))},
                )
            st.download_button(
                _ui_text("\u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf \u09a4\u09be\u09b2\u09bf\u0995\u09be \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1 \u0995\u09b0\u09c1\u09a8", "Download community CSV"),
                make_download_csv(nearby, COMMUNITY_CSV_COLUMNS),
                "dhoa_community_candidates.csv", "text/csv",
                width="stretch", key="community_candidates_csv_download",
            )

    with map_column:
        st.subheader(_ui_text("\u098f\u09b2\u09be\u0995\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0", "Area map"))
        center_label_bn = (
            "\u0996\u09cb\u0981\u099c\u09be\u09b0 \u09b8\u09cd\u09a5\u09be\u09a8"
            if selected_location_name
            else "\u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u098f\u09b2\u09be\u0995\u09be\u09b0 \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0\u09ac\u09bf\u09a8\u09cd\u09a6\u09c1"
        )
        center_description_bn = (
            location_name
            if selected_location_name
            else f"\u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u098f\u09b2\u09be\u0995\u09be {location_name} \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0\u09ac\u09bf\u09a8\u09cd\u09a6\u09c1"
        )
        center_description_en = (
            location_name
            if selected_location_name
            else f"the centroid of {location_name}"
        )
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:.5rem;margin:.4rem 0'>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{DESIGN_COLORS['new']}'>&#9679;</b> {_ui_text(center_label_bn, 'Search point' if selected_location_name else 'Selected area centroid')}</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['High']}'>&#9679;</b> {_ui_text('\u0989\u099a\u09cd\u099a \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0', 'High priority')}</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['Medium']}'>&#9679;</b> {_ui_text('\u09ae\u09be\u099d\u09be\u09b0\u09bf', 'Medium')}</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['Low']}'>&#9679;</b> {_ui_text('\u09a8\u09bf\u09ae\u09cd\u09a8', 'Low')}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(_ui_text(
            f"\u09a8\u09c0\u09b2 \u09ac\u09c3\u09a4\u09cd\u09a4\u09c7\u09b0 \u09b8\u09c0\u09ae\u09be\u09a8\u09be {center_description_bn} \u09a5\u09c7\u0995\u09c7 {radius_m / 1000:g} \u0995\u09bf\u09ae\u09bf \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac \u09a6\u09c7\u0996\u09be\u09df\u0964 \u09b2\u09be\u09b2, \u0995\u09ae\u09b2\u09be \u0993 \u09b8\u09ac\u09c1\u099c \u09ac\u09bf\u09a8\u09cd\u09a6\u09c1 \u09ad\u09be\u099f\u09be\u09b0 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u09a6\u09c7\u0996\u09be\u09df; \u09ac\u09bf\u09a8\u09cd\u09a6\u09c1\u09a4\u09c7 \u099a\u09be\u09aa\u09b2\u09c7 \u09ac\u09bf\u09b8\u09cd\u09a4\u09be\u09b0\u09bf\u09a4 \u09a6\u09c7\u0996\u09c1\u09a8\u0964",
            f"The blue circle shows {radius_m / 1000:g} km from {center_description_en}. Red, orange and green dots show kiln priority; tap a dot for details.",
        ))
        with st.container(border=True):
            map_view = folium.Map(location=[search_lat, search_lon], zoom_start=13, control_scale=True, tiles=None)
            _add_map_base_layers(map_view, with_layer_control=False)
            map_view.get_root().html.add_child(Element(_popup_styles()))
            folium.CircleMarker(
                [search_lat, search_lon], radius=8, color=DESIGN_COLORS["new"],
                fill=True, fill_color=DESIGN_COLORS["new"], fill_opacity=1,
                tooltip=area_name,
            ).add_to(map_view)
            folium.Circle([search_lat, search_lon], radius=radius_m, color=DESIGN_COLORS["new"], fill=False).add_to(map_view)
            for _, row in nearby.iterrows():
                color = PRIORITY_COLORS.get(str(row.get("priority_band")), DESIGN_COLORS["advisory"])
                popup = folium.Popup(_popup_html(row), min_width=320, max_width=320)
                folium.CircleMarker(
                    location=[float(row["lat"]), float(row["lon"])], radius=7,
                    color=color, fill=True, fill_color=color, fill_opacity=0.88,
                    popup=popup,
                ).add_to(map_view)
            st_folium(
                map_view,
                height=580,
                width="100%",
                key=f"dhoa_community_map_{_ui_text('bn', 'en')}",
            )
            # Mobile users should rotate their device for a wider map.


def _popup_content(row: Mapping[str, object]) -> dict[str, Any]:
    """Build sanitized Bangla display fields shared by all kiln popups.

    Input schema: one kiln row with optional type, place, priority, rule,
    coordinate, and detection fields. Output schema: sanitized display values.
    """
    def present(value: object, fallback: str = "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987") -> str:
        return fallback if value is None or pd.isna(value) or not str(value).strip() else str(value)

    area = _area_display_name(row)
    priority = _priority_label(row.get("priority_band"))
    latitude = pd.to_numeric(pd.Series([row.get("lat")]), errors="coerce").iloc[0]
    longitude = pd.to_numeric(pd.Series([row.get("lon")]), errors="coerce").iloc[0]
    coordinates = (
        _ui_text(
            f"{latitude:.5f}\u00b0 \u0989\u09a4\u09cd\u09a4\u09b0, {longitude:.5f}\u00b0 \u09aa\u09c2\u09b0\u09cd\u09ac",
            f"{latitude:.5f}\u00b0 N, {longitude:.5f}\u00b0 E",
        )
        if pd.notna(latitude) and pd.notna(longitude)
        else _ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "No data")
    )
    signals: list[str] = []
    rules = load_config()["rules"].get("siting_rules", [])
    breaches = set(_signals(pd.Series(dict(row))))
    labels = {
        "schools": ("\u09b8\u09cd\u0995\u09c1\u09b2", "school"),
        "hospitals": ("\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2", "hospital"),
        "settlements": ("\u09ac\u09b8\u09a4\u09bf", "settlement"),
        "railways": ("\u09b0\u09c7\u09b2\u09aa\u09a5", "railway"),
        "water": ("\u099c\u09b2\u09be\u09ad\u09c2\u09ae\u09bf", "wetland"),
        "government_forest": ("\u09ac\u09a8", "forest"),
    }
    for rule in sorted(rules, key=lambda item: float(item.get("severity", 0)), reverse=True):
        rule_id = str(rule.get("id", ""))
        feature = str(rule.get("feature", ""))
        label = _ui_text(*labels.get(feature, (feature.replace("_", " "), feature.replace("_", " "))))
        distance = pd.to_numeric(pd.Series([row.get(f"dist_{feature}_m")]), errors="coerce").iloc[0]
        if pd.isna(distance) and feature == "government_forest":
            distance = pd.to_numeric(pd.Series([row.get("dist_forests_m")]), errors="coerce").iloc[0]
        if pd.isna(distance):
            signals.append(_ui_text("\U0001f332 \u09ac\u09a8\u09c7\u09b0 \u09a4\u09a5\u09cd\u09af \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7 \u09a8\u09c7\u0987", "\U0001f332 Forest data unavailable") if feature == "government_forest" else f"\u26aa {label}: {_ui_text('\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987', 'No data')}")
            continue
        threshold = float(rule.get("buffer_m", 0))
        inside = rule_id in breaches or float(distance) < threshold
        icon = "\U0001f534" if inside and int(rule.get("severity", 1)) >= 3 else "\U0001f7e1" if inside else "\U0001f7e2"
        description = _ui_text(f"{float(distance):,.0f} \u09ae\u09bf.", f"{float(distance):,.0f} m") if inside else _ui_text("\u09b8\u09c0\u09ae\u09be\u09b0 \u09ac\u09be\u0987\u09b0\u09c7", "Outside threshold")
        signals.append(f"{icon} {label}: {description}")
    if not signals:
        signals.append(_ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "No data"))
    detection_status = str(row.get("detection_status", ""))
    is_new = detection_status == "New candidate (2025-26)"
    detection_label = {
            "New candidate (2025-26)": _ui_text("\u09a8\u09a4\u09c1\u09a8 (\u09e8\u09e6\u09e8\u09eb\u2013\u09e8\u09ec)", "New candidate (2025-26)"),
        "Known (2023-24 survey)": _ui_text("\u0986\u0997\u09c7 \u099a\u09bf\u09b9\u09cd\u09a8\u09bf\u09a4 (\u09e8\u09e6\u09e8\u09e9\u2013\u09e8\u09ea)", "Previously detected (2023-24)"),
    }.get(detection_status, _ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "No data"))
    class_name = row.get("class_name")
    if class_name is None or pd.isna(class_name):
        class_name = row.get("class")
    return {"type": _type_label(class_name), "is_new": is_new,
            "detection_label": detection_label,
            "area": area, "priority": priority, "coordinates": coordinates,
            "signals": signals, "kiln_id": present(row.get("kiln_id"), _ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "No data")),
            "latitude": float(latitude) if pd.notna(latitude) else None,
            "longitude": float(longitude) if pd.notna(longitude) else None}


def build_popup(row: pd.Series) -> str:
    """Build ordered plain-text popup content for a kiln candidate."""
    content = _popup_content(row)
    badges = f"[{content['type']}]" + (" [\u09a8\u09a4\u09c1\u09a8]" if content["is_new"] else "")
    separator = "\u2500" * 32
    return "\n".join([badges, f"\u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u00b7 {content['area']}", separator,
        f"\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0: {content['priority']}",
        f"\U0001f4cd \u098f\u09b2\u09be\u0995\u09be: {content['area']}",
        content["coordinates"], separator,
        "\u09a8\u09bf\u09af\u09bc\u09ae\u09c7\u09b0 \u09b8\u0982\u0995\u09c7\u09a4:", *content["signals"], separator,
        "[\U0001f5fa\ufe0f \u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be] [\U0001f4cd \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0] [\U0001f30d \u09aa\u09c3\u09a5\u09bf\u09ac\u09c0]",
        f"[\U0001f4c4 \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a8\u09ae\u09cd\u09ac\u09b0: {content['kiln_id']}]", separator])


def _popup_html(row: pd.Series) -> str:
    """Render each map popup through the shared escaped 320px template."""
    content = _popup_content(row)
    latitude, longitude = content["latitude"], content["longitude"]
    directions = f"https://www.google.com/maps/dir/?api=1&destination={latitude:.6f}%2C{longitude:.6f}" if latitude is not None else "#"
    maps = f"https://www.google.com/maps?q={latitude:.6f}%2C{longitude:.6f}" if latitude is not None else "#"
    earth = f"https://earth.google.com/web/@{latitude:.6f},{longitude:.6f},500a,500d,35y" if latitude is not None else "#"
    escaped = html.escape
    status_class = "new-badge" if content["is_new"] else "status-badge"
    signal_lines = _popup_rule_signal_html(row)
    return ("<div class='dhoa-popup'><div class='badges'>"
        f"<span class='badge {status_class}'>{escaped(content['type'])} — {escaped(content['detection_label'])}</span></div>"
        f"<strong>{_ui_text('\u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0', 'Kiln candidate')} \u00b7 {escaped(content['area'])}</strong><hr>"
        f"<span class='badge priority-badge'>{_ui_text('\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0', 'Priority')}: {escaped(content['priority'])}</span><br>"
        f"\U0001f4cd {_ui_text('\u098f\u09b2\u09be\u0995\u09be', 'Area')}: {escaped(content['area'])}<br>"
        f"{escaped(content['coordinates'])}<hr>"
        f"<strong>{_ui_text('\u09a8\u09bf\u09af\u09bc\u09ae\u09c7\u09b0 \u09b8\u0982\u0995\u09c7\u09a4', 'Rule signals')}:</strong>{signal_lines}<hr>"
        "<div class='popup-actions'>"
        f"<a href='{escaped(directions, quote=True)}' target='_blank' rel='noopener'>\U0001f5fa\ufe0f {_ui_text('\u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be', 'Directions')}</a>"
        f"<a href='{escaped(maps, quote=True)}' target='_blank' rel='noopener'>\U0001f4cd {_ui_text('\u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0', 'Map')}</a>"
        f"<a href='{escaped(earth, quote=True)}' target='_blank' rel='noopener'>\U0001f30d Google Earth</a></div>"
        f"<div>\U0001f4c4 {_ui_text('\u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a8\u09ae\u09cd\u09ac\u09b0', 'Report ID')}: {escaped(content['kiln_id'])}</div><hr></div>")


def _popup_rule_signal_html(row: pd.Series) -> str:
    """Render configured proximity rules with threshold-based status dots.

    Input schema: one kiln row with rule distances and optional breached_rules.
    Output schema: escaped HTML rows with dot, Bengali feature label, and distance.
    """
    rules = load_config()["rules"].get("siting_rules", [])
    rules_by_id = {str(rule.get("id")): rule for rule in rules}
    raw_breaches = row.get("breached_rules")
    if hasattr(raw_breaches, "tolist") and not isinstance(raw_breaches, str):
        raw_breaches = raw_breaches.tolist()
    if isinstance(raw_breaches, str):
        breached_ids = {item.strip() for item in raw_breaches.split(",") if item.strip()}
    elif isinstance(raw_breaches, (list, tuple, set)):
        breached_ids = {
            str(item).strip()
            for item in raw_breaches
            if item is not None and not pd.isna(item) and str(item).strip()
        }
    else:
        breached_ids = set()

    rule_rows = (
        (
            "near_school",
            ("\u09b8\u09cd\u0995\u09c1\u09b2", "school"),
            ("dist_school_m", "dist_schools_m"),
        ),
        (
            "near_hospital",
            ("\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2", "hospital"),
            ("dist_hospital_m", "dist_hospitals_m"),
        ),
        (
            "near_railway",
            ("\u09b0\u09c7\u09b2\u09aa\u09a5", "railway"),
            ("dist_rail_m", "dist_railway_m", "dist_railways_m"),
        ),
        (
            "near_government_forest",
            ("\u09ac\u09a8", "forest"),
            ("dist_forest_m", "dist_government_forest_m", "dist_forests_m"),
        ),
        (
            "near_settlement",
            ("\u09ac\u09b8\u09a4\u09bf", "settlement"),
            ("dist_settlement_m", "dist_settlements_m"),
        ),
        (
            "near_wetland",
            ("\u099c\u09b2\u09be\u09ad\u09c2\u09ae\u09bf", "wetland"),
            ("dist_water_m",),
        ),
    )
    rows: list[str] = []
    labels = {
        "red": "\U0001f534",
        "yellow": "\U0001f7e1",
        "green": "\U0001f7e2",
        "unknown": "\u26aa",
    }
    for rule_id, feature_labels, distance_columns in rule_rows:
        label = _ui_text(*feature_labels)
        rule = rules_by_id.get(rule_id, {})
        threshold = pd.to_numeric(
            pd.Series([rule.get("buffer_m")]), errors="coerce"
        ).iloc[0]
        distance = float("nan")
        for distance_column in distance_columns:
            candidate_distance = pd.to_numeric(
                pd.Series([row.get(distance_column)]), errors="coerce"
            ).iloc[0]
            if pd.notna(candidate_distance):
                distance = float(candidate_distance)
                break
        if pd.isna(distance) or pd.isna(threshold):
            icon = labels["unknown"]
            distance_text = _ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "No data")
        else:
            if rule_id in breached_ids or distance <= threshold:
                icon = labels["red"]
                distance_text = _ui_text(f"{distance:,.0f} \u09ae\u09bf.", f"{distance:,.0f} m")
            elif distance <= threshold * 1.5:
                icon = labels["yellow"]
                distance_text = _ui_text(f"{distance:,.0f} \u09ae\u09bf.", f"{distance:,.0f} m")
            else:
                icon = labels["green"]
                distance_text = _ui_text("\u09b8\u09c0\u09ae\u09be\u09b0 \u09ac\u09be\u0987\u09b0\u09c7", "Outside threshold")
        rows.append(
            "<div class='rule-signal-row'>"
            f"<span>{icon}</span> {html.escape(label)}: {html.escape(distance_text)}"
            "</div>"
        )
    return "".join(rows)


def _popup_styles() -> str:
    """Return popup CSS with readable contrast on Leaflet's white popup surface."""
    return (
        "<style>"
        ".dhoa-popup{width:290px;color:#1f2937;line-height:1.45}"
        ".dhoa-popup hr{border:0;border-top:1px solid #64748b;opacity:.45;margin:.45rem 0}"
        f".dhoa-popup .badge{{background:{DESIGN_COLORS['card']};padding:.1rem .35rem;border-radius:.25rem;font-weight:700}}"
        f".dhoa-popup .new-badge{{background:{DESIGN_COLORS['new']}}}"
        ".dhoa-popup .rule-signal-row{margin:.12rem 0}"
        ".dhoa-popup .badges,.dhoa-popup .popup-actions{display:flex;gap:.4rem;flex-wrap:wrap}"
        "</style>"
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
        _ui_text(f"{value / 1000:.1f} \u0995\u09bf\u09ae\u09bf", f"{value / 1000:.1f} km")
        if value >= 1000
        else _ui_text(f"{value:,.0f} \u09ae\u09bf", f"{value:,.0f} m")
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
    select_label = _ui_text("\u09ad\u09be\u099f\u09be\u099f\u09bf \u09a6\u09c7\u0996\u09c1\u09a8", "View kiln")
    location_label = _ui_text("\u098f\u09b2\u09be\u0995\u09be", "Area")
    priority_label = _ui_text("\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0", "Priority")
    columns = [select_label, location_label, priority_label]
    columns.extend(
        (
            _ui_text(
                f"{feature_labels.get(str(rule.get('feature')), str(rule.get('feature')))} \u09a5\u09c7\u0995\u09c7 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac",
                f"Distance from {str(rule.get('feature')).replace('_', ' ')}",
            )
        )
        for rule in rules
    )
    icons = {"High": "\U0001f534", "Medium": "\U0001f7e0", "Low": "\U0001f7e2"}
    records: list[dict[str, object]] = []
    for _, row in gdf.iterrows():
        location = f"\U0001f4cd {_area_display_name(row)}"
        record: dict[str, object] = {
            select_label: select_label,
            location_label: location,
            priority_label: f"{icons.get(str(row.get('priority_band', '')), '')} {_priority_label(row.get('priority_band'))}".strip(),
        }
        for rule, column in zip(rules, columns[3:], strict=True):
            record[column] = _format_distance_cell(row, rule)
        records.append(record)
    return pd.DataFrame(records, columns=columns)


def _priority_table_style(value: object) -> str:
    """Return the centralized design-system style for a priority cell."""
    color = PRIORITY_COLORS.get(str(value), DESIGN_COLORS["advisory"])
    return f"color: {color}; font-weight: 700"


def make_download_csv(
    gdf: pd.DataFrame, columns: list[tuple[str, str]]
) -> bytes:
    """Build an encoded CSV with only the requested fields and display headers.

    Input schema: any candidate DataFrame and one explicit export schema.
    Output schema: UTF-8 CSV bytes without index, geometry, or internal columns.
    """
    export_columns = [column for column, _ in columns if not column.startswith("_")]
    exported = gdf.reindex(columns=export_columns).rename(
        columns={column: label for column, label in columns}
    )
    buffer = BytesIO()
    exported.to_csv(
        buffer, index=False, na_rep="", encoding="utf-8-sig"
    )
    return buffer.getvalue()


def _export_filename(
    *,
    district: object,
    area: object,
    kiln_type: object,
    rule_signals: list[str],
    radius_m: object,
    extension: str,
) -> str:
    """Build a stable filename from the export's active filters and signals.

    Input schema: district, area, kiln type, rule signal IDs, radius, and file
    extension. Output: a filesystem-safe Dhoa export filename.
    """
    def token(value: object) -> str:
        text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
        safe = "".join(char if char.isalnum() else "_" for char in text)
        return "_".join(part for part in safe.split("_") if part) or "none"

    signal_part = "_".join(sorted({token(signal) for signal in rule_signals})) or "none"
    radius_part = f"{token(radius_m)}m" if radius_m is not None else "none"
    suffix = token(extension).lstrip("_")
    return (
        f"dhoa_district_{token(district)}_area_{token(area)}_"
        f"kiln_type_{token(kiln_type)}_rule_signals_{signal_part}_"
        f"radius_{radius_part}_{datetime.now(UTC):%Y%m%d}.{suffix}"
    )


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


def render_header(gdf: gpd.GeoDataFrame) -> str:
    """Render the Dhoa header, mode navigation, and candidate summary metrics."""
    identity, language_control = st.columns([5, 2], gap="small", vertical_alignment="center")
    with identity:
        st.markdown(f"<h1 class='dhoa-brand-title'>{html.escape(DASHBOARD_TITLE)}</h1>", unsafe_allow_html=True)
        loaded = dashboard_kilns_file()
        subtitle = _ui_text(
            "\u09ac\u09be\u0982\u09b2\u09be\u09a6\u09c7\u09b6\u09c7\u09b0 \u0987\u099f\u09ad\u09be\u099f\u09be \u09aa\u09b0\u09cd\u09af\u09ac\u09c7\u0995\u09cd\u09b7\u09a3 \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1",
            "Bangladesh Brick Kiln Monitoring Dashboard",
        )
        if loaded is not None:
            updated = datetime.fromtimestamp(loaded.stat().st_mtime, tz=UTC).date().isoformat()
            subtitle += _ui_text(f" \u00b7 \u09a4\u09a5\u09cd\u09af \u09b9\u09be\u09b2\u09a8\u09be\u0997\u09be\u09a6 {updated}", f" \u00b7 Updated {updated}")
        st.caption(subtitle)
    with language_control:
        st.toggle("English / \u09ac\u09be\u0982\u09b2\u09be", key="dhoa_english_ui")
    view_options = ["inspector", "community"]
    if st.session_state.get("dhoa_view_mode") not in view_options:
        st.session_state["dhoa_view_mode"] = "inspector"
    mode = st.segmented_control(
        _ui_text("\u09ad\u09bf\u0989 \u09ac\u09be\u099b\u09be\u0987 \u0995\u09b0\u09c1\u09a8", "Choose view"),
        view_options,
        format_func=lambda value: (
            "\U0001f3db Inspector" if value == "inspector" and _english_ui()
            else "\U0001f3d8 Community" if _english_ui()
            else "\U0001f3db \u09aa\u09b0\u09bf\u09a6\u09b0\u09cd\u09b6\u0995 \u09ad\u09bf\u0989" if value == "inspector"
            else "\U0001f3d8 \u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf \u09ad\u09bf\u0989"
        ),
        key="dhoa_view_mode", width="stretch",
    )
    is_community = mode == "community"
    with st.popover(_ui_text("\u2754 \u0995\u09c0\u09ad\u09be\u09ac\u09c7 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09ac\u09c7\u09a8?", "\u2754 How to use"), icon=":material/help:", width="stretch"):
        if _english_ui():
            st.markdown(
                "**Community view**\n\n"
                "1. Choose a district and, optionally, an upazila. You may enter a place name; leave it blank to use the selected area's centroid.\n"
                "2. Adjust the radius around the named place or selected area's centroid to update the results, list, and map.\n"
                "3. Select a kiln to review its details and download the report.\n\n"
                "**Inspector view**\n\n"
                "1. Choose a district, then an upazila, and optionally adjust the radius.\n"
                "2. Narrow the candidates by priority and kiln type.\n"
                "3. Select a list row or map marker to review the kiln."
            )
        elif is_community:
            st.markdown("""
**\u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf \u09ad\u09bf\u0989 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0**

1. **\u099c\u09c7\u09b2\u09be** \u09ac\u09be\u099b\u09c1\u09a8, \u099a\u09be\u0987\u09b2\u09c7 **\u098f\u09b2\u09be\u0995\u09be (\u0989\u09aa\u099c\u09c7\u09b2\u09be)** \u09ac\u09be\u099b\u09c1\u09a8. \u099a\u09be\u0987\u09b2\u09c7 \u09a8\u09be\u09ae\u09c7\u09b0 \u0998\u09b0\u09c7 \u098f\u0995\u099f\u09bf \u09b8\u09cd\u09a5\u09be\u09a8\u09c7\u09b0 \u09a8\u09be\u09ae \u09b2\u09bf\u0996\u09c1\u09a8, \u0985\u09a5\u09ac\u09be \u09ab\u09be\u0981\u0995\u09be \u09b0\u09c7\u0996\u09c7 \u09ac\u09be\u099b\u09be \u098f\u09b2\u09be\u0995\u09be\u09b0 \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0\u09ac\u09bf\u09a8\u09cd\u09a6\u09c1 \u09a5\u09c7\u0995\u09c7 \u09ab\u09b2\u09be\u09ab\u09b2 \u09a6\u09c7\u0996\u09c1\u09a8.
2. \u09a8\u09be\u09ae \u09a6\u09bf\u09df\u09c7 \u0996\u09c1\u0981\u099c\u09b2\u09c7 \u0996\u09cb\u0981\u099c\u09be \u09b8\u09cd\u09a5\u09be\u09a8 \u09a5\u09c7\u0995\u09c7, \u0985\u09a8\u09cd\u09af\u09a5\u09be \u098f\u09b2\u09be\u0995\u09be\u09b0 \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0\u09ac\u09bf\u09a8\u09cd\u09a6\u09c1 \u09a5\u09c7\u0995\u09c7 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7\u09c7\u09b0 \u09ad\u09bf\u09a4\u09b0\u09c7 \u09ad\u09be\u099f\u09be\u0997\u09c1\u09b2\u09cb \u09a6\u09c7\u0996\u09c1\u09a8.
3. \u09ab\u09b2\u09be\u09ab\u09b2, \u09a4\u09be\u09b2\u09bf\u0995\u09be \u0993 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u09a5\u09c7\u0995\u09c7 \u09ad\u09be\u099f\u09be \u09ac\u09be\u099b\u09c1\u09a8 \u098f\u09ac\u0982 \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1 \u0995\u09b0\u09c1\u09a8.
""")
        else:
            st.markdown("""
**\u09aa\u09b0\u09bf\u09a6\u09b0\u09cd\u09b6\u0995 \u09ad\u09bf\u0989 \u0995\u09c0\u09ad\u09be\u09ac\u09c7 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09ac\u09c7\u09a8**

\u09e7. \u09ac\u09be\u09ae\u09c7\u09b0 **\u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0** \u0996\u09c1\u09b2\u09c7 \u099c\u09c7\u09b2\u09be, \u098f\u09b2\u09be\u0995\u09be, \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09a7\u09b0\u09a8, \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u0985\u09a5\u09ac\u09be \u09a8\u09bf\u09df\u09ae\u09c7\u09b0 \u09b8\u0982\u0995\u09c7\u09a4 \u09ac\u09be\u099b\u09c1\u09a8\u0964

\u09e8. **\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0\u09c7\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be** \u09a5\u09c7\u0995\u09c7 \u0987\u099f\u09ad\u09be\u099f\u09be \u09ac\u09be\u099b\u09c1\u09a8, \u0985\u09a5\u09ac\u09be \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7\u09b0 \u099a\u09bf\u09b9\u09cd\u09a8\u09c7 \u099a\u09be\u09aa \u09a6\u09bf\u09df\u09c7 \u09a4\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09b0\u09c1\u09a8\u0964 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09a4\u09a5\u09cd\u09af \u09a6\u09c7\u0996\u09a4\u09c7 \u09aa\u09be\u09ac\u09c7\u09a8\u0964

\u09e9. \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7 **\u09b0\u09be\u09b8\u09cd\u09a4\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0** \u0985\u09a5\u09ac\u09be **\u09b8\u09cd\u09af\u09be\u099f\u09c7\u09b2\u09be\u0987\u099f \u099b\u09ac\u09bf** \u09ac\u09be\u099b\u09c1\u09a8\u0964 \u09aa\u09cd\u09b0\u09df\u09cb\u099c\u09a8\u09c7 \u09b8\u09bf\u098f\u09b8\u09ad\u09bf \u09a4\u09be\u09b2\u09bf\u0995\u09be \u0985\u09a5\u09ac\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09bf\u09a1\u09bf\u098f\u09ab \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1 \u0995\u09b0\u09c1\u09a8\u0964
""")
    if is_community:
        st.caption(_ui_text(
            "\u099c\u09c7\u09b2\u09be \u0993 \u099a\u09be\u0987\u09b2\u09c7 \u098f\u09b2\u09be\u0995\u09be (\u0989\u09aa\u099c\u09c7\u09b2\u09be) \u09ac\u09be\u099b\u09c1\u09a8\u0964 \u099a\u09be\u0987\u09b2\u09c7 \u0995\u09cb\u09a8\u09cb \u09b8\u09cd\u09a5\u09be\u09a8\u09c7\u09b0 \u09a8\u09be\u09ae \u09b2\u09bf\u0996\u09c1\u09a8; \u09a8\u09be \u09b2\u09bf\u0996\u09b2\u09c7 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u098f\u09b2\u09be\u0995\u09be\u09b0 \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0\u09ac\u09bf\u09a8\u09cd\u09a6\u09c1\u0995\u09c7 \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0 \u0995\u09b0\u09c7 \u09ab\u09b2\u09be\u09ab\u09b2 \u09a6\u09c7\u0996\u09c1\u09a8\u0964",
            "Choose a district and upazila. You may enter a place name, or leave it blank to search around the selected area's centroid.",
        ))
        selected_mode = "community"
    else:
        st.caption(_ui_text(
            "\u09b8\u09c1\u09b8\u099c\u09cd\u099c\u09bf\u09a4 \u09ad\u09be\u099f\u09be\u099f\u09bf\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be \u0993 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u09a6\u09c7\u0996\u09c1\u09a8, \u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0 \u09a6\u09bf\u09af\u09bc\u09c7 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u0996\u09c1\u0981\u099c\u09c1\u09a8\u0964",
            "Browse the kiln list and map, use filters to find candidates.",
        ))
        selected_mode = "inspector"
    high = int(gdf["priority_band"].eq("High").sum())
    flagged = _flagged_count(gdf, load_config()["rules"])
    items = (
        (f"{len(gdf):,}", _ui_text(METRIC_LABELS["total_kilns"], "Total kilns")),
        (f"{high:,}", _ui_text(METRIC_LABELS["high_priority_kilns"], "Environmentally hazardous kilns")),
        (f"{flagged:,}", _ui_text(METRIC_LABELS["rule_violations"], "Rule violations")),
        (datetime.now(UTC).date().isoformat(), _ui_text(METRIC_LABELS["last_updated"], "Last updated")),
    )
    metrics = "".join(f"<div class='dhoa-metric'><strong>{value}</strong><span>{label}</span></div>" for value, label in items)
    st.markdown(f"<div class='dhoa-metrics'>{metrics}</div>", unsafe_allow_html=True)
    st.divider()
    return selected_mode


def render_district_summary(district: str, gdf: gpd.GeoDataFrame) -> None:
    """Render totals, estimated spatial footprint, rule signals, and risk summary.

    Input: district name and candidate GeoDataFrame with district,
    priority_band, detection_status and optional rule signal data. Output:
    Streamlit metrics and one info sentence, without mutating the frame.
    """
    if district == "\u09b8\u09ac \u099c\u09c7\u09b2\u09be" or district == "All Districts":
        return
    selected = gdf[gdf["district"].astype(str).eq(district)]
    high_count = int(selected["priority_band"].astype(str).eq("High").sum())
    signal_values = [signal for _, row in selected.iterrows() for signal in _signals(row)]
    signal_counts = pd.Series(signal_values, dtype="string").value_counts()
    rule_names = {
        str(rule.get("id")): _signal_label(rule.get("id", ""))
        for rule in load_config()["rules"].get("siting_rules", [])
    }
    rule_names["technology_flagged"] = _signal_label("technology_flagged")
    top_rule_signal = (
        rule_names.get(str(signal_counts.index[0]), _signal_label(signal_counts.index[0]))
        if not signal_counts.empty
        else _ui_text("\u09a8\u09c7\u0987", "None")
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
        (
            _ui_text(METRIC_LABELS["total_candidates"], "Total candidates"),
            _ui_text(METRIC_LABELS["high_priority_kilns"], "High-priority kilns"),
            _ui_text(METRIC_LABELS["estimated_area"], "Estimated area (sq km)"),
            _ui_text(METRIC_LABELS["primary_signal"], "Primary rule signal"),
        ),
        (len(selected), high_count, f"{coverage_km2:,.2f}", top_rule_signal),
    ):
        column.metric(label, value)
    risk_count = len(high_risk_rows) if near else len(high_rows)
    bangla_risk_scope = "স্কুল ও হাসপাতালের কাছে" if risk_scope == "schools and hospitals" else "স্কুলের কাছে" if risk_scope == "schools" else "হাসপাতালের কাছে" if risk_scope == "hospitals" else "নিয়ম-সংকেতযুক্ত"
    english_risk_scope = {
        "schools and hospitals": "near schools and hospitals",
        "schools": "near schools",
        "hospitals": "near hospitals",
    }.get(risk_scope, "with recorded rule signals")
    st.info(_ui_text(
        f"{_district_label(district)} জেলায় {bangla_risk_scope} {risk_count}টি উচ্চ অগ্রাধিকারপ্রাপ্ত প্রার্থী পাওয়া গেছে।",
        f"{_district_label(district)} district has {risk_count} high-priority candidates {english_risk_scope}.",
    ))


def _reset_upazila_filter() -> None:
    """Reset the dependent area selection when district changes."""
    st.session_state["filter_upazila"] = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"


def _reset_community_upazila_filter() -> None:
    """Reset the Community area when its selected district changes."""
    st.session_state["community_filter_upazila"] = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"


def _reset_community_location_filters() -> None:
    """Restore Community district and area filters to their defaults."""
    st.session_state["community_filter_district"] = "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
    st.session_state["community_filter_upazila"] = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"
    st.session_state["community_location_name"] = ""
    st.session_state.pop("community_search_point", None)
    st.session_state.pop("community_search_name", None)


def _sync_map_tile(widget_key: str) -> None:
    """Keep the selected basemap in canonical session state."""
    st.session_state["map_tile"] = st.session_state.get(widget_key, "street")


def _reset_inspector_filters() -> None:
    """Restore the Inspector filter widgets to their defaults."""
    st.session_state["filter_district"] = "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
    st.session_state["filter_upazila"] = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"
    st.session_state["filter_radius_m"] = 1000
    st.session_state["filter_priority"] = [
        "\u0989\u099a\u09cd\u099a", "\u09ae\u09be\u099d\u09be\u09b0\u09bf", "\u09a8\u09bf\u09ae\u09cd\u09a8"
    ]
    st.session_state["filter_kiln_type"] = ALL_KILN_TYPES


def render_sidebar(gdf: gpd.GeoDataFrame, mode: str) -> dict[str, Any]:
    """Render Inspector filters and the persistent export/contact actions."""
    st.session_state["dhoa_active_view"] = mode
    filters: dict[str, Any] = {}
    with st.sidebar:
        if mode == "inspector":
            st.markdown(f"### {_ui_text('\u0985\u09a8\u09c1\u09b8\u09a8\u09cd\u09a7\u09be\u09a8', 'Search')}")
            district_values = (
                sorted(gdf["district"].dropna().astype(str).unique().tolist())
                if "district" in gdf else []
            )
            district_options = ["\u09b8\u09ac \u099c\u09c7\u09b2\u09be", *district_values]
            if st.session_state.get("filter_district") not in district_options:
                st.session_state["filter_district"] = "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
            filters["district"] = st.selectbox(
                _ui_text("\u099c\u09c7\u09b2\u09be", "District"),
                district_options,
                format_func=lambda value: (
                    _ui_text("\u09b8\u09ac \u099c\u09c7\u09b2\u09be", "All districts")
                    if value == "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
                    else _district_label(value)
                ),
                key="filter_district",
                on_change=_reset_upazila_filter,
            )

            district_selected = filters["district"] != "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
            upazila_source = gdf if district_selected else gdf.iloc[0:0]
            if district_selected and "district" in upazila_source:
                upazila_source = upazila_source[
                    upazila_source["district"].astype(str).eq(str(filters["district"]))
                ]
            _data_upazilas = (
                sorted(upazila_source["upazila"].dropna().astype(str).unique().tolist())
                if "upazila" in upazila_source else []
            )
            _known_upazilas = BD_ADMIN_AREAS.get(filters["district"], [])
            upazila_values = sorted(set(_known_upazilas) | set(_data_upazilas))
            upazila_options = ["\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be", *upazila_values]
            if st.session_state.get("filter_upazila") not in upazila_options:
                st.session_state["filter_upazila"] = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"
            filters["upazila"] = st.selectbox(
                _ui_text("\u098f\u09b2\u09be\u0995\u09be (\u0989\u09aa\u099c\u09c7\u09b2\u09be)", "Area / Thana"),
                upazila_options,
                format_func=lambda value: _ui_text("\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be", "All areas") if value == "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be" else value,
                key="filter_upazila",
                disabled=not district_selected,
            )
            has_selected_upazila = filters["upazila"] != "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"
            filters["radius_m"] = st.slider(
                _ui_text("\u0985\u09a8\u09c1\u09b8\u09a8\u09cd\u09a7\u09be\u09a8 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7", "Search radius"),
                min_value=250,
                max_value=5000,
                value=st.session_state.get("filter_radius_m", 1000),
                step=250,
                key="filter_radius_m",
                disabled=not has_selected_upazila,
                help=(
                    None
                    if has_selected_upazila
                    else _ui_text("\u0989\u09aa\u099c\u09c7\u09b2\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09b0\u09b2\u09c7 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7 \u09b8\u0995\u09cd\u09b0\u09bf\u09af\u09bc \u09b9\u09ac\u09c7", "Select an upazila to enable the radius")
                ),
            )
            st.markdown(f"### {_ui_text('\u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0', 'Filters')}")
            # Priority options are always stored as Bengali keys (get_filtered_gdf maps them).
            # format_func translates display label based on current language.
            _priority_opts = ["\u0989\u099a\u09cd\u099a", "\u09ae\u09be\u099d\u09be\u09b0\u09bf", "\u09a8\u09bf\u09ae\u09cd\u09a8"]
            _priority_display = {
                "\u0989\u099a\u09cd\u099a": _ui_text("\u0989\u099a\u09cd\u099a", "High"),
                "\u09ae\u09be\u099d\u09be\u09b0\u09bf": _ui_text("\u09ae\u09be\u099d\u09be\u09b0\u09bf", "Medium"),
                "\u09a8\u09bf\u09ae\u09cd\u09a8": _ui_text("\u09a8\u09bf\u09ae\u09cd\u09a8", "Low"),
            }
            # Sanitise stored value: clear English labels or an empty selection.
            _stored_p = st.session_state.get("filter_priority", _priority_opts)
            if not _stored_p or any(v in ("High", "Medium", "Low") for v in _stored_p):
                st.session_state["filter_priority"] = _priority_opts
            filters["priorities"] = st.multiselect(
                _ui_text("\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0", "Priority"),
                _priority_opts,
                default=_priority_opts,
                format_func=lambda v: _priority_display.get(v, v),
                key="filter_priority",
            )
            type_column = "class" if "class" in gdf.columns else "class_name"
            available_types = (
                sorted(gdf[type_column].dropna().astype(str).unique().tolist())
                if type_column in gdf.columns else []
            )
            type_options = [ALL_KILN_TYPES, *available_types]
            filters["kiln_type"] = st.selectbox(
                _ui_text("\u09ad\u09be\u099f\u09be\u09b0 \u09a7\u09b0\u09a8", "Kiln type"),
                type_options,
                format_func=lambda value: _ui_text("\u09b8\u09ac \u09a7\u09b0\u09a8", "All types") if value == ALL_KILN_TYPES else _type_label(value),
                key="filter_kiln_type",
            )
            filters["map_tile"] = _render_map_type_filter()

            visible = get_filtered_gdf(gdf)
            all_districts = "\u09b8\u09ac \u099c\u09c7\u09b2\u09be"
            all_areas = "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be"
            export_filename = _export_filename(
                district=None if filters["district"] == all_districts else filters["district"],
                area=None if filters["upazila"] == all_areas else filters["upazila"],
                kiln_type="all" if filters["kiln_type"] == ALL_KILN_TYPES else filters["kiln_type"],
                rule_signals=["all"],
                radius_m=filters["radius_m"] if filters["upazila"] != all_areas else None,
                extension="csv",
            )
            st.download_button(
                _ui_text("\u2b07 \u09ac\u09be\u099b\u09be\u0987\u0995\u09c3\u09a4 \u09a4\u09be\u09b2\u09bf\u0995\u09be \u09b8\u09bf\u098f\u09b8\u09ad\u09bf \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1", "\u2b07 Download filtered CSV"),
                make_download_csv(visible, INSPECTOR_CSV_COLUMNS),
                export_filename,
                "text/csv",
                width="stretch",
                key="sidebar_export_list",
            )
        st.divider()
        st.markdown(_ui_text("\u09aa\u09b0\u09bf\u09ac\u09c7\u09b6 \u0985\u09a7\u09bf\u09a6\u09aa\u09cd\u09a4\u09b0\u09c7\u09b0 \u09b9\u099f\u09b2\u09be\u0987\u09a8: \u09e7\u09ec\u09e7\u09e9\u09e7 | [doe.gov.bd](https://doe.gov.bd)", "Department of Environment hotline: 16131 | [doe.gov.bd](https://doe.gov.bd)"))
        if mode == "inspector":
            st.button(
                _ui_text("\U0001f504 \u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0 \u09b0\u09bf\u09b8\u09c7\u099f \u0995\u09b0\u09c1\u09a8", "\U0001f504 Reset filters"),
                key="reset_inspector_filters",
                on_click=_reset_inspector_filters,
                width="stretch",
            )
    return filters


def _render_selected_candidate(row: pd.Series) -> None:
    """Render selected kiln details and navigation without confidence scores."""
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"))
    forest_distance = pd.to_numeric(pd.Series([row.get("dist_government_forest_m")]), errors="coerce").iloc[0]
    if pd.isna(forest_distance):
        forest_distance = pd.to_numeric(pd.Series([row.get("dist_forests_m")]), errors="coerce").iloc[0]
    st.subheader(_ui_text(f"\u2705 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u00b7 \u0987\u099f\u09ad\u09be\u099f\u09be #{candidate_id}", f"\u2705 Selected candidate · Kiln #{candidate_id}"))
    forest_distance_label = (
        _ui_text(f"{float(forest_distance):,.0f} \u09ae\u09bf\u099f\u09be\u09b0", f"{float(forest_distance):,.0f} m")
        if pd.notna(forest_distance)
        else _ui_text("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987", "No data")
    )
    st.markdown(f"**{_ui_text('\u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09ac\u09a8 \u09a5\u09c7\u0995\u09c7 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac', 'Distance from government forest')}:** {forest_distance_label}")
    st.markdown(f"**{_ui_text('\u09a7\u09b0\u09a8', 'Kiln type')}:** {_type_label(row.get('class'))}")
    st.markdown(f"**{_ui_text('\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0', 'Priority')}:** {_priority_label(row.get('priority_band'))} \u2014 {_priority_reason(row)}")
    st.markdown(f"**{_ui_text('\u098f\u09b2\u09be\u0995\u09be', 'Area')}:** {_area_display_name(row)}")
    is_new = row.get("detection_status") == "New candidate (2025-26)"
    detection = _ui_text("\u09a8\u09a4\u09c1\u09a8 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 (\u09e8\u09e6\u09e8\u09eb\u2013\u09e8\u09e8)" if is_new else "\u0986\u0997\u09c7 \u099a\u09bf\u09b9\u09cd\u09a8\u09bf\u09a4 (\u09e8\u09e6\u09e8\u09e9\u2013\u09e8\u09ea \u099c\u09b0\u09bf\u09aa)", "New candidate (2025-26)" if is_new else "Previously detected")
    st.markdown(f"**{_ui_text('\u09b6\u09a8\u09be\u0995\u09cd\u09a4\u0995\u09b0\u09a3\u09c7\u09b0 \u0985\u09ac\u09b8\u09cd\u09a5\u09be', 'Detection status')}:** {detection}")
    st.markdown(f"**{_ui_text('\u09b8\u09cd\u09a5\u09be\u09a8\u09be\u0999\u09cd\u0995', 'Coordinates')}:** {lat:.5f}, {lon:.5f}")
    columns = st.columns(3)
    columns[0].link_button(_ui_text("\U0001f5fa\ufe0f \u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be", "\U0001f5fa\ufe0f Directions"), f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving", width="stretch")
    columns[1].link_button(_ui_text("\U0001f4cd \u09b0\u09be\u09b8\u09cd\u09a4\u09be\u09b0 \u09a6\u09c3\u09b6\u09cd\u09af", "\U0001f4cd Street view"), f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},3a,90y,0h,90t/data=!3m1!1e3", width="stretch")
    columns[2].link_button(_ui_text("\U0001f30d \u09aa\u09c3\u09a5\u09bf\u09ac\u09c0", "\U0001f30d Google Earth"), f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y", width="stretch")


def _render_report_download(row: pd.Series) -> None:
    """Render the one selected-candidate PDF download control."""
    candidate_id = str(row.get("kiln_id", "unknown"))
    try:
        report = _report_from_json(json.dumps(row.to_dict(), default=_json_default, sort_keys=True))
        if report is None:
            st.error(_ui_text('❌ প্রতিবেদন তৈরি করা যায়নি। আবার চেষ্টা করুন।', "Could not generate the report. Please try again."))
            return
        safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in candidate_id)
        filename = f"dhoa_report_{safe_id}_{datetime.now(UTC):%Y%m%d}.pdf"
        st.download_button(
            _ui_text("📄 নির্বাচিত প্রার্থীর \u09aa\u09bf\u09a1\u09bf\u098f\u09ab ডাউনলোড", "📄 Download selected kiln PDF"),
            report,
            filename,
            "application/pdf",
            width="stretch",
            key=f"kiln_report_{safe_id}",
        )
    except Exception as _exc:  # noqa: BLE001
        logging.exception("Inspector report generation failed")
        st.error(_ui_text('প্রতিবেদন তৈরি করা যায়নি।', "Could not generate the report."))


def build_map(
    gdf: gpd.GeoDataFrame,
    filters: Mapping[str, Any],
    filtered: gpd.GeoDataFrame | None = None,
) -> folium.Map:
    """Create a Folium map with kiln markers for the filtered candidate set.

    Input schema: prioritized candidate GeoDataFrame and active sidebar state.
    Output schema: Folium map with session-persistent center, base tile, and
    MarkerCluster markers drawn exclusively from get_filtered_gdf().

    Intentionally minimal: LayerControl, FeatureGroups, HeatMap, and
    Element CSS injection are omitted because each can trigger the branca
    OrderedDict-mutated-during-iteration crash or hang st_folium.
    """
    filtered = get_filtered_gdf(gdf) if filtered is None else filtered
    if "map_center" not in st.session_state:
        center = (
            (float(filtered["lat"].mean()), float(filtered["lon"].mean()))
            if not filtered.empty else DISTRICT_CENTERS["All Districts"]
        )
        st.session_state["map_center"] = center
    if "map_zoom" not in st.session_state:
        st.session_state["map_zoom"] = 7

    center = tuple(st.session_state["map_center"])
    zoom = int(st.session_state["map_zoom"])
    map_view = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
    _add_map_base_layers(map_view, with_layer_control=False)

    # Guard: ensure priority_band column always exists.
    if "priority_band" not in filtered.columns:
        filtered = filtered.copy()
        filtered["priority_band"] = "Unknown / not available"

    selected_id = st.session_state.get("selected_kiln_id")
    marker_cluster = MarkerCluster(options={"disableClusteringAtZoom": 12}).add_to(map_view)
    for _, row in filtered.iterrows():
        band = str(row.get("priority_band", ""))
        color = PRIORITY_COLORS.get(band, DESIGN_COLORS["advisory"])
        latitude, longitude = float(row["lat"]), float(row["lon"])
        marker_label = (
            f"{_priority_label(band)} {_ui_text('\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0', 'priority')} | "
            f"{_type_label(row.get('class'))} | {_area_display_name(row)}"
        )
        is_selected = str(row.get("kiln_id")) == str(selected_id)
        folium.CircleMarker(
            location=[latitude, longitude],
            radius=12 if is_selected else 8,
            color="#111827" if is_selected else color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=4 if is_selected else 2,
            tooltip=f"{_ui_text('\u2713 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4', '\u2713 Selected')} \u00b7 {marker_label}" if is_selected else marker_label,
            popup=folium.Popup(_popup_html(row), min_width=320, max_width=320),
        ).add_to(marker_cluster)
    return map_view


def render_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the Folium map and show details/report for a clicked candidate.

    Input schema: candidate GeoDataFrame and sidebar filter mapping. Output:
    an interactive Folium map plus the selected candidate's detail/report panel.
    """
    visible = get_filtered_gdf(gdf)
    selected_upazila = st.session_state.get("filter_upazila", "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be")
    if selected_upazila != "\u09b8\u09ac \u098f\u09b2\u09be\u0995\u09be" and visible.empty:
        st.info(_ui_text(
            f"'{selected_upazila}' \u098f\u09b2\u09be\u0995\u09be\u09af\u09bc \u0995\u09cb\u09a8\u09cb \u09ad\u09be\u099f\u09be\u09b0 \u09a4\u09a5\u09cd\u09af \u09aa\u09be\u0993\u09af\u09bc\u09be \u09af\u09be\u09af\u09bc\u09a8\u09bf\u0964",
            f"No kiln data found for '{selected_upazila}'.",
        ))
        return
    selected_id = st.session_state.get("selected_kiln_id")
    if selected_id is not None and (
        "kiln_id" not in visible.columns
        or not visible["kiln_id"].astype(str).eq(str(selected_id)).any()
    ):
        st.session_state["selected_kiln_id"] = None
        st.session_state["selected_lat"] = None
        st.session_state["selected_lng"] = None
        st.session_state["dhoa_list_selection_token"] = None
    elif selected_id is not None:
        selected_row = visible.loc[visible["kiln_id"].astype(str).eq(str(selected_id))].iloc[0]
        st.session_state["selected_lat"] = float(selected_row["lat"])
        st.session_state["selected_lng"] = float(selected_row["lon"])
    list_candidates = visible
    list_panel, map_panel = st.columns([2, 3], gap="medium")
    with list_panel:
        st.subheader(_ui_text("\U0001f525 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be", "\U0001f525 Priority list"))
        st.caption(_ui_text(f"{len(list_candidates):,}\u099f\u09bf \u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0\u09c7\u09b0 \u09b8\u09be\u09a5\u09c7 \u09ae\u09c7\u09b2\u09be \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0", f"{len(list_candidates):,} candidates match filters"))
        if list_candidates.empty:
            st.info(_ui_text("এই ফিল্টারে কোনো প্রার্থী নেই।", "No candidates match these filters."))
        else:
            list_frame = _kiln_list_frame(list_candidates)
            st.session_state["_list_lang"] = _ui_text("bn", "en")
            list_choice = _priority_candidate_list(
                columns=list_frame.columns.tolist(),
                rows=list_frame.astype(str).values.tolist(),
                kiln_ids=list_candidates["kiln_id"].astype(str).tolist(),
                select_label=_ui_text("\u09ad\u09be\u099f\u09be\u099f\u09bf \u09a6\u09c7\u0996\u09c1\u09a8", "View kiln"),
                selected_label=_ui_text("\u2713 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4", "\u2713 Selected"),
                selected_id=(
                    str(st.session_state.get("selected_kiln_id"))
                    if st.session_state.get("selected_kiln_id") is not None
                    and st.session_state.get("_list_lang") == _ui_text("bn", "en")
                    else None
                ),
                height=640,
                key=f"dhoa_priority_list_{_ui_text('bn', 'en')}",
                default=None,
            )
            if isinstance(list_choice, dict):
                click_token = list_choice.get("selection_token")
                _lang_key = _ui_text("bn", "en")
                _token_key = f"dhoa_list_selection_token_{_lang_key}"
                if click_token and click_token != st.session_state.get(_token_key):
                    chosen_id = list_choice.get("kiln_id")
                    chosen_rows = visible[visible["kiln_id"].astype(str).eq(str(chosen_id))] if chosen_id else visible.iloc[0:0]
                    if not chosen_rows.empty:
                        chosen_row = chosen_rows.iloc[0]
                        chosen_lat, chosen_lng = float(chosen_row["lat"]), float(chosen_row["lon"])
                        st.session_state["selected_kiln_id"] = str(chosen_id)
                        st.session_state["selected_lat"] = chosen_lat
                        st.session_state["selected_lng"] = chosen_lng
                        st.session_state["map_center"] = (chosen_lat, chosen_lng)
                        st.session_state["map_zoom"] = max(15, int(st.session_state.get("map_zoom", 15)))
                    st.session_state[_token_key] = click_token
                    st.session_state["_list_lang"] = _ui_text("bn", "en")
    with map_panel:
        st.caption(_ui_text(
            "চিহ্নের রং অগ্রাধিকার বোঝায়; গাঢ় সীমানা নির্বাচিত প্রার্থীকে দেখায়।",
            "Marker colour shows priority; bold border shows the selected candidate.",
        ))
        selected_id_for_report = st.session_state.get("selected_kiln_id")
        selected_for_report = (
            visible[visible["kiln_id"].astype(str).eq(str(selected_id_for_report))]
            if selected_id_for_report is not None
            else visible.iloc[0:0]
        )
        if selected_for_report.empty:
            st.caption(_ui_text(
                "\u09aa\u09bf\u09a1\u09bf\u098f\u09ab \u09aa\u09c7\u09a4\u09c7 \u09a4\u09be\u09b2\u09bf\u0995\u09be \u09ac\u09be \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u09a5\u09c7\u0995\u09c7 \u098f\u0995\u099f\u09bf \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09b0\u09c1\u09a8\u0964",
                "Select a candidate from the list or map to generate a PDF report.",
            ))
        else:
            _render_report_download(selected_for_report.iloc[0])
        try:
            _m = build_map(gdf, filters, filtered=visible)
        except Exception as _exc:
            logging.exception("Inspector map rendering failed")
            st.error(_ui_text('মানচিত্র তৈরি করা যায়নি।', "Could not render the map."))
            _m = None
        if _m is not None:
            with st.container(key="dhoa_map_frame"):
                map_result = st_folium(
                    _m,
                    key=f"main_map_{st.session_state.get('filter_district', '')}_{st.session_state.get('filter_upazila', '')}_{_ui_text('bn', 'en')}",
                    height=580,
                    width="100%",
                    returned_objects=["last_object_clicked", "zoom", "bounds"],
                )
                if isinstance(map_result, dict):
                    try:
                        _bounds = map_result["bounds"]
                        _southwest = _bounds["_southWest"]
                        _northeast = _bounds["_northEast"]
                        st.session_state["map_zoom"] = int(map_result["zoom"])
                        st.session_state["map_center"] = (
                            (float(_southwest["lat"]) + float(_northeast["lat"])) / 2,
                            (float(_southwest["lng"]) + float(_northeast["lng"])) / 2,
                        )
                    except (KeyError, TypeError, ValueError):
                        pass
        else:
            map_result = {}
    clicked = map_result.get("last_object_clicked") if isinstance(map_result, dict) else None
    click_signature = (
        round(float(clicked.get("lat")), 6), round(float(clicked.get("lng")), 6)
    ) if isinstance(clicked, dict) and clicked.get("lat") is not None and clicked.get("lng") is not None else None
    previous_signature = st.session_state.get("dhoa_last_map_click_signature")
    if clicked and click_signature != previous_signature and not visible.empty:
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
            nearest_index = distances.idxmin()
            clicked_row = visible.loc[nearest_index]
            st.session_state["selected_kiln_id"] = str(clicked_row["kiln_id"])
            st.session_state["selected_lat"] = float(clicked_row["lat"])
            st.session_state["selected_lng"] = float(clicked_row["lon"])
        st.session_state["dhoa_last_map_click_signature"] = click_signature
        if pd.notna(click_lat) and pd.notna(click_lon):
            st.rerun()

    selected_id = st.session_state.get("selected_kiln_id")
    selected = visible[visible["kiln_id"].astype(str).eq(str(selected_id))] if selected_id is not None else visible.iloc[0:0]
    if selected.empty:
        st.info(_ui_text(
            "বিস্তারিত ও প্রতিবেদন দেখতে মানচিত্রের কোনো ইটভাটার চিহ্নে চাপ দিন।",
            "Tap any kiln marker on the map to view details and generate a report.",
        ))
    else:
        if st.button(_ui_text("\u09ad\u09be\u099f\u09be\u09b0 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u09ac\u09be\u09a4\u09bf\u09b2 \u0995\u09b0\u09c1\u09a8 \u00b7 \u09b8\u09ac \u09ad\u09be\u099f\u09be \u09a6\u09c7\u0996\u09c1\u09a8", "Clear kiln selection \u00b7 Show all kilns"), key="dhoa_clear_kiln_selection"):
            st.session_state["selected_kiln_id"] = None
            st.session_state["selected_lat"] = None
            st.session_state["selected_lng"] = None
            st.session_state["dhoa_list_selection_token"] = None
            st.rerun()
        _render_selected_candidate(selected.iloc[0])


def render_footer() -> None:
    """Render the shared hotline footer at the end of either view."""
    st.markdown(
        f"<div class='dhoa-footer'>{_ui_text('\u09a7\u09cb\u0981\u09af\u09bc\u09be \u00b7 DoE \u09b9\u099f\u09b2\u09be\u0987\u09a8', '\u09a7\u09cb\u0981\u09af\u09bc\u09be \u00b7 DoE hotline')}: 16131 | doe.gov.bd</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Run the shared Dhoa header, sidebar, and selected mode flow.

    Input schema: local configuration and prioritized GeoParquet.
    Output schema: one Inspector or Community dashboard view.
    """
    st.markdown(responsive_css(), unsafe_allow_html=True)
    try:
        load_config()
        gdf = load_data()
    except Exception:
        logging.getLogger(__name__).exception("Dashboard data/configuration load failed")
        st.error(_ui_text("\u274c \u09a4\u09a5\u09cd\u09af \u09ac\u09be \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1 \u09b2\u09cb\u09a1 \u0995\u09b0\u09be \u09af\u09be\u09df\u09a8\u09bf\u0964 \u09a6\u09df\u09be \u0995\u09b0\u09c7 \u09aa\u09b0\u09c7 \u099a\u09c7\u09b7\u09cd\u099f\u09be \u0995\u09b0\u09c1\u09a8\u0964", "Could not load dashboard data. Please try again later."))
        return
    if gdf is None:
        st.error(_ui_text("\u274c \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1\u09c7\u09b0 \u09a4\u09a5\u09cd\u09af \u09aa\u09be\u0993\u09df\u09be \u09af\u09be\u099a\u09cd\u099b\u09c7 \u09a8\u09be\u0964 \u09aa\u09cd\u09b0\u09a5\u09ae\u09c7 \u09a1\u09c7\u099f\u09be \u09aa\u09cd\u09b0\u09b8\u09c7\u09b8 \u0995\u09b0\u09c7 \u09a8\u09bf\u09a8\u0964", "Dashboard data is unavailable."))

        return
    from src.geo.crs import get_projected_crs

    centroid_longitude = float(gdf["lon"].mean()) if not gdf.empty else 90.0
    try:
        get_projected_crs(centroid_longitude)
        gdf = add_priority_bands(gdf)
        if "detection_status" not in gdf.columns:
            gdf["detection_status"] = "Known"
        mode = render_header(gdf)
        with st.expander(_ui_text(
            "\u2696\ufe0f \u09aa\u09cd\u09b0\u09be\u09b8\u0999\u09cd\u0997\u09bf\u0995 \u0986\u0987\u09a8 \u2014 \u0987\u099f \u09aa\u09cd\u09b0\u09b8\u09cd\u09a4\u09c1\u09a4 \u0993 \u09ad\u09be\u099f\u09be \u09b8\u09cd\u09a5\u09be\u09aa\u09a8 (\u09a8\u09bf\u09af\u09bc\u09a8\u09cd\u09a4\u09cd\u09b0\u09a3) \u0986\u0987\u09a8, \u09e8\u09e6\u09e7\u09e9",
            "\u2696\ufe0f Relevant law \u2014 Brick Manufacturing and Kiln Establishment (Control) Act, 2013",
        )):
            if _english_ui():
                st.markdown("""
**Section 8(1)** Kilns may not be established in:
- Residential areas with at least 50 households
- City corporation, municipality, or upazila headquarters
- Government or privately owned forests, wildlife sanctuaries, and wetlands
- Agricultural land
- Ecologically critical areas
- Degraded airsheds
**Section 8(3)** Kilns are prohibited within these distances:
- **1 km** from the boundary of a prohibited area
- **2 km** from a government forest
- **0.5 km** from foothills
- **1 km** from educational institutions, hospitals, and railways
*Source: Brick Manufacturing and Kiln Establishment (Control) Act, 2013 (amended 2019).*
""")
            else:
                st.markdown("""
**ধারা ৮(১)** — নিষিদ্ধ এলাকায় ইটভাটা স্থাপন করা যাবে না:
- আবাসিক এলাকা (কমপক্ষে ৫০টি পরিবার)
- সিটি কর্পোরেশন, পৌরসভা বা উপজেলা সদর
- সরকারি বা ব্যক্তিমালিকানাধীন বন, অভয়ারণ্য, জলাভূমি
- কৃষি জমি
- প্রতিবেশগত সংকটাপন্ন এলাকা
- ডিগ্রেডেড এয়ার শেড

**ধারা ৮(৩)** — নিম্নবর্ণিত দূরত্বের মধ্যে ইটভাটা নিষিদ্ধ:
- নিষিদ্ধ এলাকার সীমা থেকে **১ কিলোমিটার**
- সরকারি বনাঞ্চল থেকে **২ কিলোমিটার**
- পাহাড়ের পাদদেশ থেকে **০.৫ কিলোমিটার**
- শিক্ষা প্রতিষ্ঠান, হাসপাতাল, রেলপথ থেকে **১ কিলোমিটার**

*সূত্র: ইট প্রস্তুত ও ভাটা স্থাপন (নিয়ন্ত্রণ) আইন, ২০১৩ (সংশোধিত ২০১৯)*
                """)
        filters = render_sidebar(gdf, mode)
        if mode == "community":
            render_community_view(gdf)
            render_footer()
            return
        visible = get_filtered_gdf(gdf)
        render_map(gdf, filters)
        high_count = int(visible.get("priority_band", pd.Series(index=visible.index, dtype="string")).astype(str).eq("High").sum())
        flagged_count = _flagged_count(visible, load_config()["rules"])
        new_status = visible.get("detection_status", pd.Series("Known", index=visible.index))
        new_count = int(new_status.eq("New candidate (2025-26)").sum())
        st.markdown(
            f"**{high_count:,} {_ui_text(METRIC_LABELS['high_priority_kilns'], 'High-priority kilns')} | "
            f"{flagged_count:,} {_ui_text(METRIC_LABELS['rule_signals'], 'Rule signals')} | "
            f"{new_count:,} {_ui_text(METRIC_LABELS['new_candidates'], 'New candidates')}**"
        )
        render_footer()
    except Exception as _exc:
        logging.getLogger(__name__).exception("Dashboard view rendering failed")
        st.error(_ui_text('❌ ড্যাশবোর্ড দেখানো যায়নি।', "Could not render the dashboard."))
if __name__ == "__main__":
    main()
