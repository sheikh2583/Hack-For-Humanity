"""Dhoa dashboard with shared Bangla labels and two public-facing views."""

from __future__ import annotations

import hashlib
import html
from io import BytesIO
import json
import json as _json
import logging
import math
import pathlib as _pathlib
import sys
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

import strings as T  # noqa: E402

DASHBOARD_TITLE = unicodedata.normalize("NFC", T.APP_TITLE)
assert T.CHANDRABINDU in DASHBOARD_TITLE, repr(DASHBOARD_TITLE)

st.set_page_config(page_title=DASHBOARD_TITLE, layout="wide", initial_sidebar_state="expanded")

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from branca.element import Element
from pyproj import Transformer
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

# isort: off
import kiln_data as kd
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
ALL_KILN_TYPES = kd.ALL_KILN_TYPES
ALL_DISTRICTS = kd.ALL_DISTRICTS
ALL_AREAS = kd.ALL_AREAS
KILN_TYPE_LABELS = {
    ALL_KILN_TYPES: T.ALL_TYPES,
    "Zigzag": T.ZIGZAG_KILN,
    "FCBK": T.FIXED_CHIMNEY_KILN,
}
INSPECTOR_CSV_COLUMNS = [
    ("kiln_id", T.COL_KILN_ID),
    ("lat", T.COL_LATITUDE),
    ("lon", T.COL_LONGITUDE),
    ("district", T.DISTRICT),
    ("upazila", T.COL_UPAZILA),
    ("nearest_place", T.COL_NEAREST_PLACE),
    ("nearest_place_dist_m", T.COL_DISTANCE_M),
    ("priority_band", T.PRIORITY),
    ("breach_count", T.COL_BREACH_COUNT),
]
COMMUNITY_CSV_COLUMNS = [
    ("kiln_id", T.COL_KILN_ID),
    ("lat", T.COL_LATITUDE),
    ("lon", T.COL_LONGITUDE),
    ("district", T.DISTRICT),
    ("upazila", T.COL_UPAZILA),
    ("nearest_place", T.COL_NEAREST_PLACE),
    ("nearest_place_dist_m", T.COL_DISTANCE_M),
    ("priority_band", T.PRIORITY),
]
METRIC_LABELS = {
    "total_kilns": T.METRIC_TOTAL_KILNS,
    "high_priority_kilns": T.METRIC_HIGH_PRIORITY_KILNS,
    "rule_violations": T.METRIC_RULE_VIOLATIONS,
    "last_updated": T.METRIC_LAST_UPDATED,
    "total_candidates": T.METRIC_TOTAL_CANDIDATES,
    "estimated_area": T.METRIC_ESTIMATED_AREA,
    "primary_signal": T.METRIC_PRIMARY_SIGNAL,
    "new_candidates": T.METRIC_NEW_CANDIDATES,
    "rule_signals": T.METRIC_RULE_SIGNALS,
}


DISTRICT_CENTERS = {
    "All Districts": (23.80, 90.30),
    "Chapainawabganj": (24.60, 88.35),
    "Gazipur": (24.10, 90.20),
    "Rajshahi": (24.30, 88.45),
    "Dhaka": (23.80, 90.30),
    "Chittagong": (22.50, 91.90),
}


_RESPONSIVE_CSS = """
<style>
/* Self-hosted Noto Sans Bengali (SIL OFL), served from app/static/fonts by Streamlit static serving. */
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 400;
  src: url("/app/static/fonts/noto-sans-bengali-bengali-400-normal.woff2") format("woff2");
  unicode-range: U+0951-0952,U+0964-0965,U+0980-09FE,U+1CD0,U+1CD2,U+1CD5-1CD6,U+1CD8,U+1CE1,U+1CEA,U+1CED,U+1CF2,U+1CF5-1CF7,U+200C-200D,U+20B9,U+25CC,U+A8F1; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 400;
  src: url("/app/static/fonts/noto-sans-bengali-latin-400-normal.woff2") format("woff2");
  unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 500;
  src: url("/app/static/fonts/noto-sans-bengali-bengali-500-normal.woff2") format("woff2");
  unicode-range: U+0951-0952,U+0964-0965,U+0980-09FE,U+1CD0,U+1CD2,U+1CD5-1CD6,U+1CD8,U+1CE1,U+1CEA,U+1CED,U+1CF2,U+1CF5-1CF7,U+200C-200D,U+20B9,U+25CC,U+A8F1; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 500;
  src: url("/app/static/fonts/noto-sans-bengali-latin-500-normal.woff2") format("woff2");
  unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 600;
  src: url("/app/static/fonts/noto-sans-bengali-bengali-600-normal.woff2") format("woff2");
  unicode-range: U+0951-0952,U+0964-0965,U+0980-09FE,U+1CD0,U+1CD2,U+1CD5-1CD6,U+1CD8,U+1CE1,U+1CEA,U+1CED,U+1CF2,U+1CF5-1CF7,U+200C-200D,U+20B9,U+25CC,U+A8F1; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 600;
  src: url("/app/static/fonts/noto-sans-bengali-latin-600-normal.woff2") format("woff2");
  unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 700;
  src: url("/app/static/fonts/noto-sans-bengali-bengali-700-normal.woff2") format("woff2");
  unicode-range: U+0951-0952,U+0964-0965,U+0980-09FE,U+1CD0,U+1CD2,U+1CD5-1CD6,U+1CD8,U+1CE1,U+1CEA,U+1CED,U+1CF2,U+1CF5-1CF7,U+200C-200D,U+20B9,U+25CC,U+A8F1; }
@font-face { font-family: "Noto Sans Bengali"; font-style: normal; font-display: swap; font-weight: 700;
  src: url("/app/static/fonts/noto-sans-bengali-latin-700-normal.woff2") format("woff2");
  unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
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
    content: "__PAGE_LOADING__";
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


def responsive_css() -> str:
    """Return responsive CSS for desktop, tablet, and phone layouts.

    Input schema: none. Output schema: CSS string for the dashboard page.
    """
    return _RESPONSIVE_CSS.replace("__PAGE_LOADING__", T.PAGE_LOADING)


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


@st.cache_resource(show_spinner=False)
def _prepared_data(path_text: str, mtime_ns: int, size: int) -> gpd.GeoDataFrame | None:
    """Build the display-ready dataset once per data file version.

    Input: data path plus its mtime/size (cache key, so a replaced file is
    picked up). Output: the loaded frame with priority bands, a default
    detection status and the precomputed ``ui_*`` display columns, or None when
    the file cannot be loaded. The object is shared by every session and must
    be treated as read-only; all consumers copy via ``iloc``/``loc``.
    """
    gdf = load_data(Path(path_text))
    if gdf is None:
        return None
    return kd.prepare_display_frame(
        add_priority_bands(gdf), _siting_rules(), version=f"{mtime_ns}-{size}-{len(gdf)}"
    )


def get_prepared_data(path: Path = DATA_PATH) -> gpd.GeoDataFrame | None:
    """Return the cached display-ready dataset, or None when the file is missing."""
    if not path.is_file():
        return None
    stat = path.stat()
    return _prepared_data(str(path), stat.st_mtime_ns, stat.st_size)


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


def _siting_rules() -> list[dict[str, Any]]:
    """Return the configured siting rules (thresholds come only from rules.yaml)."""
    return list(load_config()["rules"].get("siting_rules", []))


# Label helpers live in app/kiln_data.py (pure, unit-tested); the underscore
# names stay as the app's public-in-module API.
_type_label = kd.type_label
_priority_label = kd.priority_label
_district_label = kd.district_label


def _area_display_name(row: Mapping[str, object]) -> str:
    """Format a kiln's administrative area in Bangla."""
    return kd.area_display_name(row.get("upazila"), row.get("district"))


def _signal_label(value: object) -> str:
    """Translate known rule identifiers for dashboard display."""
    labels = {
        "near_school": T.NEAR_SCHOOL,
        "near_hospital": T.NEAR_HOSPITAL,
        "near_settlement": T.NEAR_SETTLEMENT,
        "near_railway": T.NEAR_RAILWAY,
        "near_wetland": T.NEAR_WETLAND,
        "near_government_forest": T.NEAR_GOVERNMENT_FOREST,
        "technology_flagged": T.FIXED_CHIMNEY_TECHNOLOGY,
    }
    return labels.get(str(value), str(value).replace("_", " "))


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
        "near_school": (T.SCHOOL, ("dist_schools_m", "dist_school_m")),
        "near_hospital": (T.HOSPITAL, ("dist_hospitals_m", "dist_hospital_m")),
        "near_settlement": (T.SETTLEMENT, ("dist_settlements_m", "dist_settlement_m")),
        "near_railway": (T.RAILWAY, ("dist_railways_m", "dist_railway_m")),
        "near_wetland": (T.WETLAND, ("dist_water_m", "dist_wetland_m")),
        "near_government_forest": (
            T.GOVERNMENT_FOREST,
            ("dist_government_forest_m", "dist_forests_m"),
        ),
        "technology_flagged": (T.FIXED_CHIMNEY_TECHNOLOGY, ()),
    }
    reasons: list[str] = []
    for signal in _signals(row):
        label, columns = names.get(str(signal), (str(signal).replace("_", " "), ()))
        distance = next(
            (
                value
                for column in columns
                if not math.isnan(value := kd.to_float(row.get(column)))
            ),
            None,
        )
        reasons.append(
            T.REASON_FROM_FMT.format(label, distance)
            if distance is not None
            else label
        )
    return " · ".join(reasons) if reasons else T.NO_RULE_SIGNALS_RECORDED


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
    return pd.Series(
        kd.distances_from_point_m(
            pd.to_numeric(gdf["lat"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan),
            pd.to_numeric(gdf["lon"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan),
            latitude,
            longitude,
        ),
        index=gdf.index,
    )


def _community_area_centroid(gdf: gpd.GeoDataFrame) -> tuple[float, float]:
    """Return the mean projected position of candidate points as WGS84 lat/lon.

    Input schema: non-empty GeoDataFrame with numeric lat/lon columns in
    EPSG:4326. Output schema: (latitude, longitude) at the selected area's
    candidate-point centroid (average of the projected coordinates, which is
    the centroid of the point set).
    """
    from src.geo.crs import get_projected_crs

    lat = pd.to_numeric(gdf["lat"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
    lon = pd.to_numeric(gdf["lon"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
    projected_crs = get_projected_crs(float(np.nanmean(lon)))
    to_metres = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
    to_degrees = Transformer.from_crs(projected_crs, "EPSG:4326", always_xy=True)
    x, y = to_metres.transform(lon, lat)
    centroid_lon, centroid_lat = to_degrees.transform(np.nanmean(x), np.nanmean(y))
    return float(centroid_lat), float(centroid_lon)


def _add_map_base_layers(
    map_view: folium.Map, *, with_layer_control: bool = True, tile: str | None = None
) -> None:
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
    selected_tile = tile if tile is not None else st.session_state.get("map_tile", "street")
    if selected_tile not in {"street", "satellite"}:
        selected_tile = "street"
    folium.TileLayer(
        "OpenStreetMap",
        name=T.STREET_MAP,
        overlay=False,
        control=True,
        show=selected_tile == "street",
    ).add_to(map_view)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name=T.SATELLITE_IMAGERY,
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
    widget_key = "map_tile_widget"
    st.session_state[widget_key] = st.session_state["map_tile"]
    selected_tile = st.selectbox(
        T.MAP_TYPE,
        ["street", "satellite"],
        format_func=lambda value: T.STREET_MAP if value == "street" else T.SATELLITE_IMAGERY,
        key=widget_key,
        index=["street", "satellite"].index(st.session_state["map_tile"]),
        on_change=_sync_map_tile,
        args=(widget_key,),
    )
    st.session_state["map_tile"] = selected_tile
    return selected_tile


def _empty_with_distance(frame: pd.DataFrame) -> pd.DataFrame:
    """Return an empty copy of ``frame`` that still has a ``distance_m`` column."""
    empty = frame.iloc[0:0].copy()
    empty["distance_m"] = pd.Series(dtype="float64", index=empty.index)
    return empty


def _inspector_filter_key() -> kd.FilterKey:
    """Read the inspector filter widgets once and return their fingerprint.

    Input schema: ``filter_district``, ``filter_upazila``, ``filter_kiln_type``
    and ``filter_priority`` in session state (priorities may be Bangla labels).
    Output: a hashable ``kd.FilterKey`` used as the cache key everywhere.
    """
    state = st.session_state
    return kd.make_filter_key(
        state.get("filter_district", ALL_DISTRICTS),
        state.get("filter_upazila", ALL_AREAS),
        state.get("filter_kiln_type", ALL_KILN_TYPES),
        state.get("filter_priority") or (),
    )


def _data_version(frame: pd.DataFrame) -> str | None:
    """Return the dataset version token set by ``prepare_display_frame``, if any."""
    version = getattr(frame, "attrs", {}).get("dhoa_data_version")
    return str(version) if version else None


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_filter_positions(version: str, key: tuple, _frame: pd.DataFrame) -> np.ndarray:
    """Cache the filtered row positions per (dataset version, filter key).

    ``_frame`` is excluded from hashing on purpose (hashing 2,135 rows every
    rerun is the cost this avoids); ``version`` identifies its content.
    """
    return kd.filter_positions(_frame, kd.FilterKey(*key))


def get_filtered_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return candidates for the active view using its canonical session filters.

    Input schema: prioritized GeoDataFrame with district, upazila, lat/lon,
    kiln class, and priority_band. Output: an independent GeoDataFrame after
    district, upazila, kiln type, and priority filtering (inspector) or the
    radius search (community). The inspector result is computed from a cached
    row-position array keyed by the filter fingerprint, so repeated calls in
    one rerun are cheap; callers should still compute it once and pass it down.
    """
    active_view = st.session_state.get("dhoa_active_view", "inspector")
    if active_view == "community":
        st.session_state.pop("community_centroid", None)
        district = st.session_state.get("community_filter_district", ALL_DISTRICTS)
        upazila = st.session_state.get("community_filter_upazila", ALL_AREAS)
        district_selected = district != ALL_DISTRICTS
        search_point = st.session_state.get("community_search_point")
        # When no district AND no search point, we cannot determine a location.
        if not district_selected and search_point is None:
            return _empty_with_distance(gdf)
        result = gdf
        # Apply district filter only when selected.
        if district_selected:
            if "district" not in result.columns:
                return _empty_with_distance(gdf)
            result = result[result["district"].astype(str).eq(str(district))]
        if upazila != ALL_AREAS:
            if "upazila" not in result.columns:
                return _empty_with_distance(gdf)
            result = result[result["upazila"].astype(str).eq(str(upazila))]
        if result.empty:
            return _empty_with_distance(result)
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

    key = _inspector_filter_key()
    version = _data_version(gdf)
    if version is not None:
        positions = _cached_filter_positions(version, tuple(key), gdf)
    else:
        positions = kd.filter_positions(gdf, key)
    return kd.take_candidates(gdf, positions)


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
        pdf.multi_cell(0, 6, T.REPORT_COMMUNITY_NOTE, new_x="LMARGIN", new_y="NEXT")
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


_PDF_COLUMNS = (("distance_m", None), ("class", "Unknown"), ("priority_band", "Unknown"), ("lat", None), ("lon", None))


@st.cache_data(show_spinner=False, max_entries=16)
def _cached_community_pdf(location: str, radius_m: int, rows: tuple, day: str) -> bytes:
    """Build the community PDF once per (place, radius, result rows, day).

    ``day`` is part of the key because the report prints its generation date.
    """
    frame = pd.DataFrame(list(rows), columns=[name for name, _ in _PDF_COLUMNS])
    return community_alert_pdf(location, frame, radius_m)


def _community_report(location: str, rows: pd.DataFrame, radius_m: int) -> bytes:
    """Return the community PDF, reusing the cached bytes while the results are unchanged."""
    columns = [
        rows[name].tolist() if name in rows.columns else [default] * len(rows)
        for name, default in _PDF_COLUMNS
    ]
    return _cached_community_pdf(
        location, int(radius_m), tuple(zip(*columns)), f"{datetime.now(UTC):%Y-%m-%d}"
    )


@st.cache_resource(show_spinner=False, max_entries=8)
def _cached_community_map(
    version: str, key: tuple, tile: str, _frame: pd.DataFrame
) -> folium.Map:
    """Cache the Community base map per (data version, search, radius, area, basemap)."""
    latitude, longitude, radius_m = key[2], key[3], key[4]
    return _marker_map(_frame, tile, kd.radius_bounds(latitude, longitude, radius_m), radius=7)


def _render_community_map(
    nearby: pd.DataFrame,
    source: pd.DataFrame,
    search_lat: float,
    search_lon: float,
    radius_m: int,
    area_name: str,
) -> None:
    """Render the Community map and the details of a clicked kiln.

    Input: kilns within the radius (with ``distance_m``), the dataset they came
    from, the search point, radius (metres) and its label. Output: a stable map
    (fitted to the radius once; pan/zoom do not rerun) whose search point and
    radius circle are sent via ``feature_group_to_add``, plus a detail card for
    the clicked kiln. Runs as a fragment, so a click reruns only this block.
    """
    tile = _current_tile()
    fingerprint = (
        str(st.session_state.get("community_filter_district", "")),
        str(st.session_state.get("community_filter_upazila", "")),
        round(float(search_lat), 5), round(float(search_lon), 5), int(radius_m),
    )
    version = _data_version(source)
    if version is None:
        map_view = _marker_map(nearby, tile, kd.radius_bounds(search_lat, search_lon, radius_m), radius=7)
    else:
        map_view = _cached_community_map(version, fingerprint, tile, nearby)
    overlay = folium.FeatureGroup(name="dhoa_search")
    folium.CircleMarker(
        [search_lat, search_lon], radius=8, color=DESIGN_COLORS["new"],
        fill=True, fill_color=DESIGN_COLORS["new"], fill_opacity=1, tooltip=html.escape(area_name),
    ).add_to(overlay)
    folium.Circle(
        [search_lat, search_lon], radius=radius_m, color=DESIGN_COLORS["new"], fill=False,
    ).add_to(overlay)
    selected_id = st.session_state.get("community_selected_kiln_id")
    selected = (
        nearby[nearby["kiln_id"].astype(str).eq(str(selected_id))]
        if selected_id is not None and "kiln_id" in nearby.columns
        else nearby.iloc[0:0]
    )
    if selected.empty and selected_id is not None:
        st.session_state["community_selected_kiln_id"] = None
    groups = [overlay]
    if not selected.empty:
        groups.append(_selected_feature_group(float(selected.iloc[0]["lat"]), float(selected.iloc[0]["lon"])))
    result = st_folium(
        map_view,
        key=_map_key("dhoa_community_map", fingerprint, tile),
        height=MAP_HEIGHT,
        width="100%",
        returned_objects=["last_object_clicked"],
        feature_group_to_add=groups,
    )
    point = _clicked_point(result)
    if (
        point is not None
        and point != st.session_state.get("dhoa_community_click_signature")
        and not nearby.empty
    ):
        st.session_state["dhoa_community_click_signature"] = point
        clicked_row = _nearest_row(nearby, point)
        if clicked_row is not None:
            st.session_state["community_selected_kiln_id"] = str(clicked_row["kiln_id"])
            _rerun_local()
    if selected.empty:
        st.caption(T.TAP_ANY_KILN_MARKER_ON_THE_MAP_TO_VIEW_D)
    else:
        _render_selected_candidate(selected.iloc[0])


_render_community_map_fragment = st.fragment(_render_community_map)


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
            st.session_state["community_search_name"] = T.MY_LOCATION
            st.query_params.clear()
        except Exception:
            pass
    st.markdown(f"<div class='dhoa-section-title'>{T.FIND_KILNS_NEAR_YOU}</div>", unsafe_allow_html=True)

    # Audio guide
    with st.container(border=True):
        st.markdown(T.LISTEN_TO_THE_GUIDE)
        community_guide = _ROOT / "app" / "static" / "community_guide.mp3"
        if community_guide.is_file():
            st.audio(str(community_guide))
        else:
            st.info(T.AUDIO_GUIDE_COMING_SOON)

    # District and upazila filters
    all_districts = ALL_DISTRICTS
    all_areas = ALL_AREAS
    district_values = (
        sorted(gdf["district"].dropna().astype(str).unique().tolist())
        if "district" in gdf.columns else []
    )
    district_options = [all_districts, *district_values]
    if st.session_state.get("community_filter_district") not in district_options:
        st.session_state["community_filter_district"] = all_districts
    sel_district = st.selectbox(
        T.DISTRICT,
        district_options,
        format_func=lambda value: all_districts if value == all_districts else _district_label(value),
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
        T.AREA_THANA,
        upazila_options,
        format_func=lambda value: all_areas if value == all_areas else value,
        key="community_filter_upazila",
        disabled=not district_selected,
    )

    # Radius slider (always visible)
    radius_m = int(st.slider(
        T.SEARCH_RADIUS_METRES,
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
            T.SEARCH_BY_NAME,
            placeholder=T.E_G_ASHULIA,
            key="community_location_name",
            disabled=not district_selected,
        )
        submitted = st.form_submit_button(
            T.SEARCH,
            width="stretch",
            disabled=not district_selected,
        )

    st.divider()

    # Option B: use GPS location
    st.markdown(T.OR_USE_YOUR_CURRENT_LOCATION)
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
">📍 """ + T.USE_MY_LOCATION + """</button>
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
            st.session_state["community_search_name"] = T.YOUR_LOCATION
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
            st.warning(T.PLEASE_ENTER_A_LOCATION_NAME)
            return
        with st.spinner(T.SEARCHING):
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
            st.warning(T.LOCATION_NOT_FOUND_TRY_A_DIFFERENT_SPELL)
            return
        search_point = (float(loc.latitude), float(loc.longitude))
        st.session_state["community_search_point"] = search_point
        st.session_state["community_search_name"] = location_name

    # No search yet
    search_point = st.session_state.get("community_search_point")
    selected_location_name = st.session_state.get("community_search_name", "")
    if search_point is None:
        st.info(T.SELECT_A_DISTRICT_AND_SEARCH_FOR_A_PLACE)
        return
    if not district_selected:
        st.info(T.SELECT_A_DISTRICT_AND_SEARCH_FOR_A_PLACE)
        return

    st.session_state["community_filter_district"] = sel_district
    st.session_state["community_filter_upazila"] = sel_upazila
    search_lat, search_lon = search_point
    location_name = (
        selected_location_name or sel_upazila
        if sel_upazila != all_areas
        else selected_location_name or _district_label(sel_district)
    )
    area_name = location_name
    # Display columns are precomputed on the prepared dataset; this is a no-op
    # there and only computes them for a frame that lacks them.
    nearby = kd.with_display_columns(get_filtered_gdf(gdf), _siting_rules())

    result_column, map_column = st.columns([2, 3], gap="medium")
    with result_column:
        st.subheader(T.NEARBY_KILN_CANDIDATES)
        with st.container(border=True):
            if nearby.empty:
                st.success(T.NO_KILNS_IN_RADIUS_FMT.format(radius_m / 1000))
            else:
                st.metric(
                    T.KILNS_WITHIN_RADIUS_FMT.format(radius_m / 1000),
                    f"{len(nearby):,}",
                )
            try:
                report = _community_report(area_name, nearby, radius_m)
                st.session_state["community_report"] = report
                st.download_button(
                    T.DOWNLOAD_REPORT, report,
                    "dhoa_community_report.pdf", "application/pdf",
                    width="stretch", key="community_alert_download",
                )
            except Exception:
                logging.exception("Community PDF generation failed")
                st.error(T.REPORT_GENERATION_FAILED_PLEASE_TRY_AGAI)
            if not nearby.empty:
                distance_header = T.DISTANCE_M
                area_header = T.AREA
                type_header = T.KILN_TYPE
                priority_header = T.PRIORITY
                directions_header = T.DIRECTIONS
                nearby["directions_url"] = [
                    f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f}%2C{lon:.6f}"
                    for lat, lon in zip(
                        nearby["lat"].astype(float).tolist(),
                        nearby["lon"].astype(float).tolist(),
                    )
                ]
                table = pd.DataFrame({
                    distance_header: nearby["distance_m"].round(0).astype("Int64").astype("string").fillna(T.NO_DATA).to_numpy(),
                    area_header: nearby["ui_area"].tolist(),
                    type_header: nearby["ui_type"].tolist(),
                    priority_header: nearby["ui_priority"].tolist(),
                    directions_header: nearby["directions_url"].tolist(),
                })
                st.dataframe(
                    table, hide_index=True, width="stretch",
                    column_config={directions_header: st.column_config.LinkColumn(display_text=T.GET_DIRECTIONS)},
                )
            st.download_button(
                T.DOWNLOAD_COMMUNITY_CSV,
                make_download_csv(nearby, COMMUNITY_CSV_COLUMNS),
                "dhoa_community_candidates.csv", "text/csv",
                width="stretch", key="community_candidates_csv_download",
            )

    with map_column:
        st.subheader(T.AREA_MAP)
        center_label_bn = (
            T.SEARCH_POINT_LABEL
            if selected_location_name
            else T.AREA_CENTROID_LABEL
        )
        center_description_bn = (
            location_name
            if selected_location_name
            else T.CENTROID_OF_AREA_FMT.format(location_name)
        )
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:.5rem;margin:.4rem 0'>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{DESIGN_COLORS['new']}'>&#9679;</b> {center_label_bn}</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['High']}'>&#9679;</b> {T.HIGH_PRIORITY}</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['Medium']}'>&#9679;</b> {T.MEDIUM}</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['Low']}'>&#9679;</b> {T.LOW}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(T.COMMUNITY_MAP_CAPTION_FMT.format(center_description_bn, radius_m / 1000))
        with st.container(border=True):
            _render_community_map_fragment(nearby, gdf, search_lat, search_lon, radius_m, area_name)
            # Mobile users should rotate their device for a wider map.


def _popup_content(row: Mapping[str, object]) -> dict[str, Any]:
    """Build sanitized Bangla display fields shared by all kiln popups.

    Input schema: one kiln row with optional type, place, priority, rule,
    coordinate, and detection fields. Output schema: sanitized display values.
    """
    def present(value: object, fallback: str = T.NO_DATA) -> str:
        return fallback if value is None or pd.isna(value) or not str(value).strip() else str(value)

    area = _area_display_name(row)
    priority = _priority_label(row.get("priority_band"))
    latitude = kd.to_float(row.get("lat"))
    longitude = kd.to_float(row.get("lon"))
    coordinates = (
        T.COORDS_FMT.format(latitude, longitude)
        if pd.notna(latitude) and pd.notna(longitude)
        else T.NO_DATA
    )
    signals: list[str] = []
    rules = _siting_rules()
    breaches = set(_signals(pd.Series(dict(row))))
    labels = {
        "schools": T.SCHOOL,
        "hospitals": T.HOSPITAL,
        "settlements": T.SETTLEMENT,
        "railways": T.RAILWAY,
        "water": T.WETLAND,
        "government_forest": T.FOREST,
    }
    for rule in sorted(rules, key=lambda item: float(item.get("severity", 0)), reverse=True):
        rule_id = str(rule.get("id", ""))
        feature = str(rule.get("feature", ""))
        label = labels.get(feature, feature.replace("_", " "))
        distance = kd.to_float(row.get(f"dist_{feature}_m"))
        if pd.isna(distance) and feature == "government_forest":
            distance = kd.to_float(row.get("dist_forests_m"))
        if pd.isna(distance):
            signals.append(T.FOREST_DATA_UNAVAILABLE if feature == "government_forest" else f"⚪ {label}: {T.NO_DATA}")
            continue
        threshold = float(rule.get("buffer_m", 0))
        inside = rule_id in breaches or float(distance) < threshold
        icon = "🔴" if inside and int(rule.get("severity", 1)) >= 3 else "🟡" if inside else "🟢"
        description = T.M_DOT_FMT.format(float(distance)) if inside else T.OUTSIDE_THRESHOLD
        signals.append(f"{icon} {label}: {description}")
    if not signals:
        signals.append(T.NO_DATA)
    detection_status = str(row.get("detection_status", ""))
    is_new = detection_status == "New candidate (2025-26)"
    detection_label = {
            "New candidate (2025-26)": T.NEW_CANDIDATE_2025_26,
        "Known (2023-24 survey)": T.PREVIOUSLY_DETECTED_2023_24,
    }.get(detection_status, T.NO_DATA)
    class_name = row.get("class_name")
    if class_name is None or pd.isna(class_name):
        class_name = row.get("class")
    return {"type": _type_label(class_name), "is_new": is_new,
            "detection_label": detection_label,
            "area": area, "priority": priority, "coordinates": coordinates,
            "signals": signals, "kiln_id": present(row.get("kiln_id"), T.NO_DATA),
            "latitude": float(latitude) if pd.notna(latitude) else None,
            "longitude": float(longitude) if pd.notna(longitude) else None}


def build_popup(row: pd.Series) -> str:
    """Build ordered plain-text popup content for a kiln candidate."""
    content = _popup_content(row)
    badges = f"[{content['type']}]" + (T.NEW_SUFFIX if content["is_new"] else "")
    separator = "─" * 32
    return "\n".join([badges, T.POPUP_TITLE_FMT.format(content['area']), separator,
        T.POPUP_PRIORITY_FMT.format(content['priority']),
        T.POPUP_AREA_FMT.format(content['area']),
        content["coordinates"], separator,
        T.RULE_SIGNALS_HEADING, *content["signals"], separator,
        T.POPUP_LINKS,
        T.POPUP_REPORT_ID_FMT.format(content['kiln_id']), separator])


def _popup_html(row: pd.Series) -> str:
    """Render one map popup through the shared escaped 320px template.

    Input schema: one kiln row (precomputed ``ui_popup_html`` is reused when
    present). Output: popup HTML; the markup is built by
    ``kiln_data.popup_html_list`` so a single code path serves one row or all.
    """
    cached = row.get("ui_popup_html")
    if isinstance(cached, str):
        return cached
    return kd.popup_html_list(pd.DataFrame([dict(row)]), _siting_rules())[0]


def _popup_rule_signal_html(row: pd.Series) -> str:
    """Render configured proximity rules with threshold-based status dots.

    Input schema: one kiln row with rule distances and optional breached_rules.
    Output schema: escaped HTML rows with dot, Bengali feature label, and distance.
    """
    return kd.rule_signal_rows_html(pd.DataFrame([dict(row)]), _siting_rules())[0]


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
    values = np.array([kd.to_float(row.get(f"dist_{feature}_m"))])
    return kd.distance_cells(values, kd.to_float(rule.get("buffer_m")))[0]


def _kiln_list_frame(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build a selectable distance table without repeating rule labels per row.

    Input schema: filtered candidate GeoDataFrame with district, coordinates,
    priority, and configured distance fields. Output schema: visible location,
    priority, and one distance column per active siting rule. Built column-wise
    by ``kiln_data.build_list_frame`` (no per-row Python calls).
    """
    return kd.build_list_frame(gdf, _siting_rules())


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
    st.markdown(f"<h1 class='dhoa-brand-title'>{html.escape(DASHBOARD_TITLE)}</h1>", unsafe_allow_html=True)
    loaded = dashboard_kilns_file()
    subtitle = T.BANGLADESH_BRICK_KILN_MONITORING_DASHBOA
    if loaded is not None:
        updated = datetime.fromtimestamp(loaded.stat().st_mtime, tz=UTC).date().isoformat()
        subtitle += T.SUBTITLE_UPDATED_FMT.format(updated)
    st.caption(subtitle)
    view_options = ["inspector", "community"]
    if st.session_state.get("dhoa_view_mode") not in view_options:
        st.session_state["dhoa_view_mode"] = "inspector"
    mode = st.segmented_control(
        T.CHOOSE_VIEW,
        view_options,
        format_func=lambda value: (
            T.VIEW_INSPECTOR if value == "inspector"
            else T.VIEW_COMMUNITY
        ),
        key="dhoa_view_mode", width="stretch",
    )
    is_community = mode == "community"
    with st.popover(T.HOW_TO_USE, icon=":material/help:", width="stretch"):
        if is_community:
            st.markdown(T.HELP_COMMUNITY)
        else:
            st.markdown(T.HELP_INSPECTOR)
    if is_community:
        st.caption(T.CHOOSE_A_DISTRICT_AND_UPAZILA_YOU_MAY_EN)
        selected_mode = "community"
    else:
        st.caption(T.BROWSE_THE_KILN_LIST_AND_MAP_USE_FILTERS)
        selected_mode = "inspector"
    high = int(gdf["priority_band"].eq("High").sum())
    flagged = _flagged_count(gdf, load_config()["rules"])
    items = (
        (f"{len(gdf):,}", METRIC_LABELS["total_kilns"]),
        (f"{high:,}", METRIC_LABELS["high_priority_kilns"]),
        (f"{flagged:,}", METRIC_LABELS["rule_violations"]),
        (datetime.now(UTC).date().isoformat(), METRIC_LABELS["last_updated"]),
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
    if district in {ALL_DISTRICTS, "All Districts"}:
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
        else T.NONE
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
            METRIC_LABELS["total_candidates"],
            METRIC_LABELS["high_priority_kilns"],
            METRIC_LABELS["estimated_area"],
            METRIC_LABELS["primary_signal"],
        ),
        (len(selected), high_count, f"{coverage_km2:,.2f}", top_rule_signal),
    ):
        column.metric(label, value)
    risk_count = len(high_risk_rows) if near else len(high_rows)
    risk_scope_label = T.RISK_SCOPE_SCHOOLS_HOSPITALS if risk_scope == "schools and hospitals" else T.NEAR_SCHOOL if risk_scope == "schools" else T.NEAR_HOSPITAL if risk_scope == "hospitals" else T.RISK_SCOPE_SIGNALS
    st.info(T.RISK_INFO_FMT.format(_district_label(district), risk_scope_label, risk_count))


def _reset_upazila_filter() -> None:
    """Reset the dependent area selection when district changes."""
    st.session_state["filter_upazila"] = ALL_AREAS


def _reset_community_upazila_filter() -> None:
    """Reset the Community area when its selected district changes."""
    st.session_state["community_filter_upazila"] = ALL_AREAS


def _reset_community_location_filters() -> None:
    """Restore Community district and area filters to their defaults."""
    st.session_state["community_filter_district"] = ALL_DISTRICTS
    st.session_state["community_filter_upazila"] = ALL_AREAS
    st.session_state["community_location_name"] = ""
    st.session_state.pop("community_search_point", None)
    st.session_state.pop("community_search_name", None)


def _sync_map_tile(widget_key: str) -> None:
    """Keep the selected basemap in canonical session state."""
    st.session_state["map_tile"] = st.session_state.get(widget_key, "street")


def _reset_inspector_filters() -> None:
    """Restore the Inspector filter widgets to their defaults."""
    st.session_state["filter_district"] = ALL_DISTRICTS
    st.session_state["filter_upazila"] = ALL_AREAS
    st.session_state["filter_priority"] = [
        T.HIGH, T.MEDIUM, T.LOW
    ]
    st.session_state["filter_kiln_type"] = ALL_KILN_TYPES


@st.cache_data(show_spinner=False, max_entries=32)
def _cached_inspector_csv(version: str, key: tuple, _frame: pd.DataFrame) -> bytes:
    """Cache the filtered-list CSV per (dataset version, filter key)."""
    return make_download_csv(_frame, INSPECTOR_CSV_COLUMNS)


def _inspector_csv_bytes(visible: pd.DataFrame, source: pd.DataFrame) -> bytes:
    """Return the Inspector CSV, reusing the cached bytes while filters are unchanged."""
    version = _data_version(source)
    if version is None:
        return make_download_csv(visible, INSPECTOR_CSV_COLUMNS)
    return _cached_inspector_csv(version, tuple(_inspector_filter_key()), visible)


def render_sidebar(gdf: gpd.GeoDataFrame, mode: str) -> dict[str, Any]:
    """Render Inspector filters and the persistent export/contact actions.

    Input schema: prepared kiln GeoDataFrame and the active view. Output: the
    widget values, plus (Inspector only) ``filters["visible"]``, the filtered
    frame computed exactly once for this rerun and meant to be passed down.

    The district picker stays outside the form because the area list depends on
    it. Area, priority and kiln type sit in a form, so any number of edits
    cost one rerun, triggered by the apply button.
    """
    st.session_state["dhoa_active_view"] = mode
    filters: dict[str, Any] = {}
    with st.sidebar:
        if mode == "inspector":
            st.markdown(f"### {T.SEARCH_2}")
            district_values = (
                sorted(gdf["district"].dropna().astype(str).unique().tolist())
                if "district" in gdf else []
            )
            district_options = [ALL_DISTRICTS, *district_values]
            if st.session_state.get("filter_district") not in district_options:
                st.session_state["filter_district"] = ALL_DISTRICTS
            filters["district"] = st.selectbox(
                T.DISTRICT,
                district_options,
                format_func=lambda value: (
                    T.ALL_DISTRICTS
                    if value == ALL_DISTRICTS
                    else _district_label(value)
                ),
                key="filter_district",
                on_change=_reset_upazila_filter,
            )

            district_selected = filters["district"] != ALL_DISTRICTS
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
            upazila_options = [ALL_AREAS, *upazila_values]
            if st.session_state.get("filter_upazila") not in upazila_options:
                st.session_state["filter_upazila"] = ALL_AREAS
            # Priority options are always stored as Bengali keys (the filter key maps them).
            _priority_opts = [T.HIGH, T.MEDIUM, T.LOW]
            # Sanitise stored value: clear English labels or an empty selection.
            _stored_p = st.session_state.get("filter_priority", _priority_opts)
            if not _stored_p or any(v in ("High", "Medium", "Low") for v in _stored_p):
                st.session_state["filter_priority"] = _priority_opts
            type_column = "class" if "class" in gdf.columns else "class_name"
            available_types = (
                sorted(gdf[type_column].dropna().astype(str).unique().tolist())
                if type_column in gdf.columns else []
            )
            type_options = [ALL_KILN_TYPES, *available_types]
            with st.form("dhoa_inspector_filters", border=False):
                filters["upazila"] = st.selectbox(
                    T.AREA_THANA,
                    upazila_options,
                    format_func=lambda value: T.ALL_AREAS if value == ALL_AREAS else value,
                    key="filter_upazila",
                    disabled=not district_selected,
                )
                st.markdown(f"### {T.FILTERS}")
                filters["priorities"] = st.multiselect(
                    T.PRIORITY,
                    _priority_opts,
                    default=_priority_opts,
                    key="filter_priority",
                )
                filters["kiln_type"] = st.selectbox(
                    T.KILN_TYPE,
                    type_options,
                    format_func=lambda value: T.ALL_TYPES if value == ALL_KILN_TYPES else _type_label(value),
                    key="filter_kiln_type",
                )
                st.form_submit_button(T.APPLY_FILTERS, type="primary", width="stretch")
            filters["map_tile"] = _render_map_type_filter()

            # The one filter computation of this rerun; everything below and the
            # main area read ``filters["visible"]`` instead of filtering again.
            visible = get_filtered_gdf(gdf)
            filters["visible"] = visible
            export_filename = _export_filename(
                district=None if filters["district"] == ALL_DISTRICTS else filters["district"],
                area=None if filters["upazila"] == ALL_AREAS else filters["upazila"],
                kiln_type="all" if filters["kiln_type"] == ALL_KILN_TYPES else filters["kiln_type"],
                rule_signals=["all"],
                radius_m=None,
                extension="csv",
            )
            st.download_button(
                T.DOWNLOAD_FILTERED_CSV,
                _inspector_csv_bytes(visible, gdf),
                export_filename,
                "text/csv",
                width="stretch",
                key="sidebar_export_list",
            )
        st.divider()
        st.markdown(T.DEPARTMENT_OF_ENVIRONMENT_HOTLINE_16131_)
        if mode == "inspector":
            st.button(
                T.RESET_FILTERS,
                key="reset_inspector_filters",
                on_click=_reset_inspector_filters,
                width="stretch",
            )
    return filters


def _render_selected_candidate(row: pd.Series) -> None:
    """Render selected kiln details and navigation without confidence scores."""
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", T.NO_DATA))
    forest_distance = kd.to_float(row.get("dist_government_forest_m"))
    if pd.isna(forest_distance):
        forest_distance = kd.to_float(row.get("dist_forests_m"))
    st.subheader(T.SELECTED_KILN_TITLE_FMT.format(candidate_id))
    forest_distance_label = (
        T.METRES_FMT.format(float(forest_distance))
        if pd.notna(forest_distance)
        else T.NO_DATA
    )
    st.markdown(f"**{T.DISTANCE_FROM_GOVERNMENT_FOREST}:** {forest_distance_label}")
    st.markdown(f"**{T.KILN_TYPE_2}:** {_type_label(row.get('class'))}")
    st.markdown(f"**{T.PRIORITY}:** {_priority_label(row.get('priority_band'))} — {_priority_reason(row)}")
    st.markdown(f"**{T.AREA}:** {_area_display_name(row)}")
    is_new = row.get("detection_status") == "New candidate (2025-26)"
    detection = T.STATUS_NEW if is_new else T.STATUS_KNOWN
    st.markdown(f"**{T.DETECTION_STATUS}:** {detection}")
    st.markdown(f"**{T.COORDINATES}:** {lat:.5f}, {lon:.5f}")
    columns = st.columns(3)
    columns[0].link_button(T.DIRECTIONS_2, f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving", width="stretch")
    columns[1].link_button(T.STREET_VIEW, f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},3a,90y,0h,90t/data=!3m1!1e3", width="stretch")
    columns[2].link_button(T.GOOGLE_EARTH, f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y", width="stretch")


def _render_report_download(row: pd.Series) -> None:
    """Render the one selected-candidate PDF download control."""
    candidate_id = str(row.get("kiln_id", "unknown"))
    try:
        # Display-only ``ui_*`` columns (popup HTML etc.) are not report inputs;
        # leaving them out keeps the report cache key small and stable.
        report_fields = {
            name: value for name, value in row.to_dict().items() if not str(name).startswith("ui_")
        }
        report = _report_from_json(json.dumps(report_fields, default=_json_default, sort_keys=True))
        if report is None:
            st.error(T.COULD_NOT_GENERATE_THE_REPORT_PLEASE_TRY)
            return
        safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in candidate_id)
        filename = f"dhoa_report_{safe_id}_{datetime.now(UTC):%Y%m%d}.pdf"
        st.download_button(
            T.DOWNLOAD_SELECTED_KILN_PDF,
            report,
            filename,
            "application/pdf",
            width="stretch",
            key=f"kiln_report_{safe_id}",
        )
    except Exception as _exc:  # noqa: BLE001
        logging.exception("Inspector report generation failed")
        st.error(T.COULD_NOT_GENERATE_THE_REPORT)


MAP_HEIGHT = 580
DEFAULT_ZOOM = 7
SELECTED_ZOOM = 15
_MARKER_OPTIONS = {"disableClusteringAtZoom": 12}


def _current_tile() -> str:
    """Return the selected basemap (``street`` or ``satellite``) from session state."""
    tile = st.session_state.get("map_tile", "street")
    return tile if tile in {"street", "satellite"} else "street"


def _marker_callback_js(payload: Mapping[str, Any], radius: int = 8) -> str:
    """Return the JS factory that turns one compact row into a tooltip circle marker.

    Input: ``kiln_data.marker_payload`` output. Output: a JS function expression
    for ``FastMarkerCluster``; labels are looked up from small arrays so each
    kiln costs ~40 bytes on the wire. Label strings arrive HTML-escaped.
    """
    lookups = json.dumps(
        {
            "colors": [
                PRIORITY_COLORS["High"], PRIORITY_COLORS["Medium"], PRIORITY_COLORS["Low"],
                DESIGN_COLORS["advisory"],
            ],
            "bands": payload["bands"],
            "types": payload["types"],
            "areas": payload["areas"],
        },
        ensure_ascii=False,
    )
    return (
        "(function(){var D=" + lookups + ";"
        "return function(row){var c=D.colors[row[2]];"
        f"var m=L.circleMarker([row[0],row[1]],{{radius:{int(radius)},color:c,weight:2,"
        "fill:true,fillColor:c,fillOpacity:0.85});"
        'm.bindTooltip(D.bands[row[2]]+" | "+D.types[row[3]]+" | "+D.areas[row[4]],{sticky:true});'
        "return m;};})()"
    )


def _new_map(tile: str, bounds: list[list[float]] | None) -> folium.Map:
    """Create an empty map with the two basemaps, fitted to ``bounds`` when given.

    The view is fixed here (Leaflet ``fitBounds`` at creation); after that only
    the user, or an explicit ``center``/``zoom`` request, moves it.
    """
    map_view = folium.Map(
        location=DISTRICT_CENTERS["All Districts"], zoom_start=DEFAULT_ZOOM,
        control_scale=True, tiles=None,
    )
    _add_map_base_layers(map_view, with_layer_control=False, tile=tile)
    if bounds:
        map_view.fit_bounds(bounds, max_zoom=SELECTED_ZOOM, padding=(24, 24))
    return map_view


def _marker_map(
    frame: pd.DataFrame, tile: str, bounds: list[list[float]] | None, radius: int = 8
) -> folium.Map:
    """Build a base map with one lightweight clustered marker layer for ``frame``."""
    payload = kd.marker_payload(frame, _siting_rules())
    map_view = _new_map(tile, bounds if bounds is not None else kd.bounds_of(frame))
    if payload["rows"]:
        FastMarkerCluster(
            payload["rows"], callback=_marker_callback_js(payload, radius),
            options=dict(_MARKER_OPTIONS),
        ).add_to(map_view)
    return map_view


@st.cache_resource(show_spinner=False, max_entries=8)
def _cached_inspector_map(version: str, key: tuple, tile: str, _frame: pd.DataFrame) -> folium.Map:
    """Cache the Inspector base map per (dataset version, filter key, basemap)."""
    return _marker_map(_frame, tile, None)


def build_map(
    gdf: gpd.GeoDataFrame,
    filters: Mapping[str, Any],
    filtered: gpd.GeoDataFrame | None = None,
) -> folium.Map:
    """Return the Inspector base map for the filtered candidate set.

    Input schema: prioritized candidate GeoDataFrame, sidebar state (unused) and
    optionally the already-filtered frame. Output schema: a Folium map fitted to
    the filtered kilns, with one ``FastMarkerCluster`` of tooltip circle
    markers (no popups, no LayerControl) that depends only on the filter
    fingerprint and basemap; it is cached and reused until those change. The
    selected kiln and the community radius are *not* part of it: they are drawn
    through ``feature_group_to_add`` so the map never remounts.
    """
    filtered = get_filtered_gdf(gdf) if filtered is None else filtered
    tile = _current_tile()
    version = _data_version(gdf)
    if version is None:
        return _marker_map(filtered, tile, None)
    return _cached_inspector_map(version, tuple(_inspector_filter_key()), tile, filtered)


def _map_key(prefix: str, *parts: object) -> str:
    """Return a short stable widget key from a fingerprint (changes => remount)."""
    digest = hashlib.md5(repr(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _selected_feature_group(latitude: float, longitude: float) -> folium.FeatureGroup:
    """Return the highlight ring for the selected kiln (sent without a remount)."""
    group = folium.FeatureGroup(name="dhoa_selected")
    folium.CircleMarker(
        [latitude, longitude], radius=14, color="#111827", weight=4,
        fill=False,
    ).add_to(group)
    return group


def _rerun_local() -> None:
    """Rerun only the enclosing fragment (full rerun when not inside one)."""
    try:
        st.rerun(scope="fragment")
    except Exception:  # noqa: BLE001 - raised only when not inside a fragment
        st.rerun()


def _clicked_point(map_result: object) -> tuple[float, float] | None:
    """Extract ``(lat, lng)`` of ``last_object_clicked`` from an st_folium result."""
    clicked = map_result.get("last_object_clicked") if isinstance(map_result, dict) else None
    if not isinstance(clicked, dict):
        return None
    lat, lng = kd.to_float(clicked.get("lat")), kd.to_float(clicked.get("lng"))
    if math.isnan(lat) or math.isnan(lng):
        return None
    return round(lat, 6), round(lng, 6)


def _nearest_row(frame: pd.DataFrame, point: tuple[float, float]) -> pd.Series | None:
    """Return the kiln in ``frame`` nearest to ``point`` (vectorised), or None."""
    position = kd.nearest_position(
        pd.to_numeric(frame["lat"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan),
        pd.to_numeric(frame["lon"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan),
        point[0],
        point[1],
    )
    return None if position is None else frame.iloc[position]


def _list_payload(
    visible: pd.DataFrame, source: pd.DataFrame
) -> tuple[list[str], list[list[str]], list[str]]:
    """Return (columns, rows, kiln ids) for the priority-list component.

    Input: the filtered frame and the dataset it came from. Output: plain
    lists the component serialises. Cached per (dataset version, filter key)
    so an unchanged filter does not rebuild 2,000+ rows on every rerun.
    """
    version = _data_version(source)
    if version is None:
        return _build_list_payload(visible)
    return _cached_list_payload(version, tuple(_inspector_filter_key()), visible)


def _build_list_payload(
    visible: pd.DataFrame,
) -> tuple[list[str], list[list[str]], list[str]]:
    """Build the list payload from a filtered frame (see ``_list_payload``)."""
    list_frame = _kiln_list_frame(visible)
    return (
        list_frame.columns.tolist(),
        list_frame.astype(str).values.tolist(),
        visible["kiln_id"].astype(str).tolist(),
    )


@st.cache_data(show_spinner=False, max_entries=32)
def _cached_list_payload(
    version: str, key: tuple, _frame: pd.DataFrame
) -> tuple[list[str], list[list[str]], list[str]]:
    """Cache ``_build_list_payload`` per (dataset version, filter key)."""
    return _build_list_payload(_frame)


def render_map(
    gdf: gpd.GeoDataFrame,
    filters: Mapping[str, Any],
    visible: gpd.GeoDataFrame | None = None,
) -> None:
    """Render the priority list, the stable map and the selected-kiln panel.

    Input schema: candidate GeoDataFrame, sidebar filter mapping and, normally,
    the already-filtered frame (``filters["visible"]``). Output: list, map and
    detail card. Pan and zoom never reach Python (``returned_objects`` is only
    ``last_object_clicked``), so they cannot rerun the script or snap the view
    back; the view changes only when a list row is chosen (``center``/``zoom``)
    or the filters change (new base map fitted to the results).
    """
    if visible is None:
        visible = filters.get("visible") if isinstance(filters, Mapping) else None
    if visible is None:
        visible = get_filtered_gdf(gdf)
    selected_upazila = st.session_state.get("filter_upazila", ALL_AREAS)
    if selected_upazila != ALL_AREAS and visible.empty:
        st.info(T.NO_KILNS_IN_AREA_FMT.format(selected_upazila))
        return
    tile = _current_tile()
    map_key = _map_key("dhoa_map", tuple(_inspector_filter_key()), tile)
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
        st.subheader(T.PRIORITY_LIST)
        st.caption(T.CANDIDATES_MATCH_FMT.format(len(list_candidates)))
        if list_candidates.empty:
            st.info(T.NO_CANDIDATES_MATCH_THESE_FILTERS)
        else:
            list_columns, list_rows, list_kiln_ids = _list_payload(list_candidates, gdf)
            list_choice = _priority_candidate_list(
                columns=list_columns,
                rows=list_rows,
                kiln_ids=list_kiln_ids,
                select_label=T.VIEW_KILN,
                selected_label=T.SELECTED,
                selected_id=(
                    str(st.session_state.get("selected_kiln_id"))
                    if st.session_state.get("selected_kiln_id") is not None
                    else None
                ),
                height=640,
                key="dhoa_priority_list",
                default=None,
            )
            if isinstance(list_choice, dict):
                click_token = list_choice.get("selection_token")
                _token_key = "dhoa_list_selection_token"
                if click_token and click_token != st.session_state.get(_token_key):
                    chosen_id = list_choice.get("kiln_id")
                    chosen_rows = visible[visible["kiln_id"].astype(str).eq(str(chosen_id))] if chosen_id else visible.iloc[0:0]
                    if not chosen_rows.empty:
                        chosen_row = chosen_rows.iloc[0]
                        chosen_lat, chosen_lng = float(chosen_row["lat"]), float(chosen_row["lon"])
                        st.session_state["selected_kiln_id"] = str(chosen_id)
                        st.session_state["selected_lat"] = chosen_lat
                        st.session_state["selected_lng"] = chosen_lng
                        # Programmatic view change: honoured only for this map.
                        st.session_state["dhoa_map_view"] = {
                            "map_key": map_key,
                            "center": [chosen_lat, chosen_lng],
                            "zoom": SELECTED_ZOOM,
                        }
                    st.session_state[_token_key] = click_token
    with map_panel:
        st.caption(T.MARKER_COLOUR_SHOWS_PRIORITY_BOLD_BORDER)
        selected_id_for_report = st.session_state.get("selected_kiln_id")
        selected_for_report = (
            visible[visible["kiln_id"].astype(str).eq(str(selected_id_for_report))]
            if selected_id_for_report is not None
            else visible.iloc[0:0]
        )
        if selected_for_report.empty:
            st.caption(T.SELECT_A_CANDIDATE_FROM_THE_LIST_OR_MAP_)
        else:
            _render_report_download(selected_for_report.iloc[0])
        try:
            _m = build_map(gdf, filters, filtered=visible)
        except Exception as _exc:
            logging.exception("Inspector map rendering failed")
            st.error(T.COULD_NOT_RENDER_THE_MAP)
            _m = None
        map_result: dict[str, Any] = {}
        if _m is not None:
            view_request = st.session_state.get("dhoa_map_view")
            view_args: dict[str, Any] = (
                {"center": view_request["center"], "zoom": view_request["zoom"]}
                if isinstance(view_request, dict) and view_request.get("map_key") == map_key
                else {}
            )
            highlight = (
                _selected_feature_group(
                    float(selected_for_report.iloc[0]["lat"]), float(selected_for_report.iloc[0]["lon"])
                )
                if not selected_for_report.empty
                else None
            )
            with st.container(key="dhoa_map_frame"):
                result = st_folium(
                    _m,
                    key=map_key,
                    height=MAP_HEIGHT,
                    width="100%",
                    returned_objects=["last_object_clicked"],
                    feature_group_to_add=highlight,
                    **view_args,
                )
                map_result = result if isinstance(result, dict) else {}
    click_signature = _clicked_point(map_result)
    if (
        click_signature is not None
        and click_signature != st.session_state.get("dhoa_last_map_click_signature")
        and not visible.empty
    ):
        st.session_state["dhoa_last_map_click_signature"] = click_signature
        clicked_row = _nearest_row(visible, click_signature)
        if clicked_row is not None:
            st.session_state["selected_kiln_id"] = str(clicked_row["kiln_id"])
            st.session_state["selected_lat"] = float(clicked_row["lat"])
            st.session_state["selected_lng"] = float(clicked_row["lon"])
            _rerun_local()

    selected_id = st.session_state.get("selected_kiln_id")
    selected = visible[visible["kiln_id"].astype(str).eq(str(selected_id))] if selected_id is not None else visible.iloc[0:0]
    if selected.empty:
        st.info(T.TAP_ANY_KILN_MARKER_ON_THE_MAP_TO_VIEW_D)
    else:
        if st.button(T.CLEAR_KILN_SELECTION_SHOW_ALL_KILNS, key="dhoa_clear_kiln_selection"):
            st.session_state["selected_kiln_id"] = None
            st.session_state["selected_lat"] = None
            st.session_state["selected_lng"] = None
            st.session_state["dhoa_list_selection_token"] = None
            _rerun_local()
        _render_selected_candidate(selected.iloc[0])


# Selecting a kiln reruns only this fragment, not the header, sidebar or data layer.
render_map_fragment = st.fragment(render_map)


def render_footer() -> None:
    """Render the shared hotline footer at the end of either view."""
    st.markdown(
        f"<div class='dhoa-footer'>{T.HOTLINE_LABEL}: 16131 | doe.gov.bd</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Run the shared Dhoa header, sidebar, and selected mode flow.

    Input schema: local configuration and prioritized GeoParquet.
    Output schema: one Inspector or Community dashboard view.
    """
    st.markdown(responsive_css(), unsafe_allow_html=True)
    try:
        with st.spinner(T.LOADING_KILN_DATA_THIS_MAY_TAKE_A_FEW_SE):
            load_config()
            gdf = get_prepared_data()
    except Exception:
        logging.getLogger(__name__).exception("Dashboard data/configuration load failed")
        st.error(T.COULD_NOT_LOAD_DASHBOARD_DATA_PLEASE_TRY)
        if st.button(T.RETRY_LOADING_DATA, key="dhoa_retry_data_load"):
            st.rerun()
        return
    if gdf is None:
        st.error(T.DASHBOARD_DATA_IS_UNAVAILABLE)

        if st.button(T.RETRY_LOADING_DATA, key="dhoa_retry_missing_data"):
            st.rerun()
        return
    from src.geo.crs import get_projected_crs

    centroid_longitude = float(gdf["lon"].mean()) if not gdf.empty else 90.0
    try:
        get_projected_crs(centroid_longitude)
        mode = render_header(gdf)
        with st.expander(T.RELEVANT_LAW_BRICK_MANUFACTURING_AND_KIL):
            st.markdown(T.LAW_TEXT)
        filters = render_sidebar(gdf, mode)
        if mode == "community":
            render_community_view(gdf)
            render_footer()
            return
        visible = filters["visible"]  # computed once in render_sidebar
        render_map_fragment(gdf, filters, visible)
        high_count = int(visible.get("priority_band", pd.Series(index=visible.index, dtype="string")).astype(str).eq("High").sum())
        flagged_count = _flagged_count(visible, load_config()["rules"])
        new_status = visible.get("detection_status", pd.Series("Known", index=visible.index))
        new_count = int(new_status.eq("New candidate (2025-26)").sum())
        st.markdown(
            f"**{high_count:,} {METRIC_LABELS['high_priority_kilns']} | "
            f"{flagged_count:,} {METRIC_LABELS['rule_signals']} | "
            f"{new_count:,} {METRIC_LABELS['new_candidates']}**"
        )
        render_footer()
    except Exception as _exc:
        logging.getLogger(__name__).exception("Dashboard view rendering failed")
        st.error(T.COULD_NOT_RENDER_THE_DASHBOARD)
if __name__ == "__main__":
    main()
