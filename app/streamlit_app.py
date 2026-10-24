"""Dhoa dashboard with shared Bangla labels and two public-facing views."""

from __future__ import annotations

import hashlib
import html
from io import BytesIO
import json
import json as _json
import logging
import math
import os
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
import community as cm
import design_tokens as tokens
import styles
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
DATA_DIR = Path(os.environ.get("DHOA_DATA_DIR") or BASE_DIR / "data" / "processed")  # env override: hermetic tests
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
_geolocate = components.declare_component(
    "dhoa_geolocate",
    path=str(_ROOT / "app" / "components" / "geolocate"),
)
DESIGN_COLORS = {
    key: tokens.COLORS[key]
    for key in ("high", "medium", "low", "new", "advisory", "background", "card", "text")
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


def responsive_css() -> str:
    """Return responsive CSS for desktop, tablet, and phone layouts.

    Input schema: none. Output schema: CSS string for the dashboard page.
    """
    return styles.page_css(T.PAGE_LOADING)


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
        result = _community_result(gdf)
        return _empty_with_distance(gdf) if result is None else result.rows

    key = _inspector_filter_key()
    version = _data_version(gdf)
    if version is not None:
        positions = _cached_filter_positions(version, tuple(key), gdf)
    else:
        positions = kd.filter_positions(gdf, key)
    return kd.take_candidates(gdf, positions)


def community_alert_pdf(location: str, rows: pd.DataFrame, radius_m: int) -> bytes:  # radius_m == 0: whole area
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
    scope = f"within {radius_m / 1000:g} km of {pdf_location}" if radius_m else f"in {pdf_location}"
    pdf.multi_cell(
        0, 6,
        f"{len(rows)} kiln candidates were identified {scope} using satellite imagery analysis of the 2025-26 dry season.",
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
            f"{row['distance_m']:.0f} m" if radius_m and pd.notna(row["distance_m"]) else "-",
            str(row.get("class", "Unknown")),
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


def _render_community_map(
    nearby: pd.DataFrame,
    source: pd.DataFrame,
    search_lat: float,
    search_lon: float,
    radius_m: int | None,
    area_name: str,
    place_key: str,
) -> None:
    """Render the Community map and the details of a clicked kiln.

    Input: kilns to show (with ``distance_m``), the dataset they came from, the
    search point, the radius in metres (``None`` = whole area: no circle, view
    fitted to the kilns), its label and the place key. Output: a stable map
    (fitted once; pan/zoom do not rerun) whose search point and radius circle
    are sent via ``feature_group_to_add``, plus a detail card for the clicked
    kiln. Runs as a fragment, so a click reruns only this block.
    """
    tile = _current_tile()
    fingerprint = (str(place_key), int(radius_m or 0), round(float(search_lat), 5), round(float(search_lon), 5))
    bounds = (
        kd.radius_bounds(search_lat, search_lon, radius_m) if radius_m else kd.bounds_of(nearby)
    )
    version = _data_version(source)
    if version is None:
        map_view = _marker_map(nearby, tile, bounds, radius=7)
    else:
        payload = _cached_marker_payload(version, ("community", *fingerprint), nearby)
        map_view = _marker_map(nearby, tile, bounds, radius=7, payload=payload)
    groups: list[folium.FeatureGroup] = []
    if radius_m:
        overlay = folium.FeatureGroup(name="dhoa_search")
        folium.CircleMarker(
            [search_lat, search_lon], radius=8, color=DESIGN_COLORS["new"],
            fill=True, fill_color=DESIGN_COLORS["new"], fill_opacity=1, tooltip=html.escape(area_name),
        ).add_to(overlay)
        folium.Circle(
            [search_lat, search_lon], radius=radius_m, color=DESIGN_COLORS["new"], fill=False,
        ).add_to(overlay)
        groups.append(overlay)
    selected_id = st.session_state.get("community_selected_kiln_id")
    selected = (
        nearby[nearby["kiln_id"].astype(str).eq(str(selected_id))]
        if selected_id is not None and "kiln_id" in nearby.columns
        else nearby.iloc[0:0]
    )
    if selected.empty and selected_id is not None:
        st.session_state["community_selected_kiln_id"] = None
    if not selected.empty:
        groups.append(_selected_feature_group(float(selected.iloc[0]["lat"]), float(selected.iloc[0]["lon"])))
    result = st_folium(
        map_view,
        key=_map_key("dhoa_community_map", fingerprint, tile),
        height=MAP_HEIGHT,
        width="100%",
        returned_objects=["last_object_clicked"],
        feature_group_to_add=groups or None,
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


# --------------------------------------------------------------------------
# Community view (M5): where -> how far -> results
# --------------------------------------------------------------------------
def _community_version_key(frame: pd.DataFrame) -> str:
    """Cache token for per-dataset community lookups."""
    return _data_version(frame) or f"rows-{len(frame)}"


@st.cache_data(show_spinner=False, max_entries=4)
def _cached_places(version: str, _frame: pd.DataFrame) -> list[cm.Place]:
    """Selectable places (districts, upazilas with data, known place names)."""
    return cm.build_places(
        _frame, label_fmt=T.C_PLACE_LABEL_FMT, district_name=kd.district_label
    )


@st.cache_data(ttl=86400, show_spinner=False, max_entries=256)
def _cached_geocode(query: str) -> tuple[float, float] | None:
    """Geocode a Bangladesh place name; not-found is cached, outages are not."""
    return cm.geocode_bangladesh(query)


def _community_places(gdf: pd.DataFrame) -> dict[str, cm.Place]:
    """Return ``{key: Place}`` for the dataset."""
    return {place.key: place for place in _cached_places(_community_version_key(gdf), gdf)}


def _community_place(gdf: pd.DataFrame) -> cm.Place | None:
    """Resolve the active search origin from session state.

    A geocoded/GPS point (``community_origin``) wins over the picker, because
    choosing in the picker clears it.
    """
    origin = st.session_state.get("community_origin")
    if isinstance(origin, dict):
        return cm.point_place(str(origin["name"]), float(origin["lat"]), float(origin["lon"]))
    return _community_places(gdf).get(st.session_state.get("community_place_key"))


def _community_result(gdf: pd.DataFrame) -> cm.SearchResult | None:
    """Search the dataset for the active origin and radius (None if no origin)."""
    place = _community_place(gdf)
    if place is None:
        return None
    radius = int(st.session_state.get("community_radius_m") or cm.DEFAULT_RADIUS_M)
    return cm.search(gdf, place, radius)


def _on_community_pick() -> None:
    """A list choice replaces any GPS/geocoded origin and old notices."""
    st.session_state["community_origin"] = None
    st.session_state.pop("community_notice", None)
    st.session_state["community_selected_kiln_id"] = None


def _set_community_radius(radius_m: int) -> None:
    """Button callback: widen the radius to ``radius_m``."""
    st.session_state["community_radius_m"] = int(radius_m)


def _set_community_origin(name: str, lat: float, lon: float) -> None:
    """Make a point the origin; the picker is cleared on the next run."""
    st.session_state["community_origin"] = {"name": name, "lat": float(lat), "lon": float(lon)}
    st.session_state["community_picker_reset"] = True
    st.session_state["community_selected_kiln_id"] = None


_GPS_ERRORS = {
    "denied": T.C_GPS_DENIED,
    "unsupported": T.C_GPS_UNSUPPORTED,
    "insecure": T.C_GPS_INSECURE,
    "timeout": T.C_GPS_TIMEOUT,
    "unavailable": T.C_GPS_UNAVAILABLE,
}


def _handle_gps_event(event: object) -> None:
    """Apply a new GPS component value once (by token); never reloads the page."""
    if not isinstance(event, dict):
        return
    token = event.get("token")
    if token is None or token == st.session_state.get("community_gps_token"):
        return
    st.session_state["community_gps_token"] = token
    lat, lon = kd.to_float(event.get("lat")), kd.to_float(event.get("lon"))
    if not (math.isnan(lat) or math.isnan(lon)):
        _set_community_origin(T.MY_LOCATION, lat, lon)
        st.session_state["community_notice"] = ("success", T.C_GPS_OK)
    else:
        message = _GPS_ERRORS.get(str(event.get("error")), T.C_GPS_UNAVAILABLE)
        st.session_state["community_notice"] = ("warning", message)
    st.rerun()


def _submit_community_geocode(query: str) -> None:
    """Run the optional free-text fallback and store the outcome in session state."""
    text = " ".join(query.split())
    if not text:
        st.session_state["community_notice"] = ("warning", T.C_GEO_EMPTY)
        return
    try:
        with st.spinner(T.C_GEO_SEARCHING):
            hit = _cached_geocode(text.casefold())
    except cm.GeocodeUnavailable:
        st.session_state["community_notice"] = ("warning", T.C_GEO_UNAVAILABLE)
        return
    except Exception:  # noqa: BLE001 - never break the page on a provider error
        logging.exception("Community geocoding failed")
        st.session_state["community_notice"] = ("warning", T.C_GEO_UNAVAILABLE)
        return
    if hit is None:
        st.session_state["community_notice"] = ("warning", T.C_GEO_NOT_FOUND)
        return
    st.session_state.pop("community_notice", None)
    _set_community_origin(text, hit[0], hit[1])
    st.rerun()


def _render_community_inputs(gdf: pd.DataFrame) -> cm.Place | None:
    """Render steps 1 and 2 and return the chosen origin (or None)."""
    if st.session_state.pop("community_picker_reset", False):
        st.session_state["community_place_key"] = None
    places = _community_places(gdf)
    st.session_state.setdefault("community_radius_m", cm.DEFAULT_RADIUS_M)
    if st.session_state.get("community_place_key") not in places:
        st.session_state["community_place_key"] = None

    with st.container(border=True, key="dhoa_community_step1"):
        st.markdown(f"**{T.C_STEP1}**")
        st.selectbox(
            T.C_PLACE_LABEL,
            list(places),
            index=None,
            format_func=lambda key: places[key].label if key in places else str(key),
            placeholder=T.C_PLACE_PLACEHOLDER,
            help=T.C_PLACE_HELP,
            key="community_place_key",
            on_change=_on_community_pick,
        )
        event = _geolocate(
            label=T.C_GPS_LABEL, busy_label=T.C_GPS_BUSY, key="community_gps", default=None
        )
        with st.expander(T.C_GEO_EXPANDER):
            with st.form("community_geocode_form", border=False):
                typed = st.text_input(T.C_GEO_INPUT, help=T.C_GEO_HELP, key="community_geocode_text")
                submitted = st.form_submit_button(T.C_GEO_BUTTON, width="stretch")
        _handle_gps_event(event)
        if submitted:
            _submit_community_geocode(typed)
        notice = st.session_state.get("community_notice")
        if notice:
            getattr(st, notice[0], st.info)(notice[1])

    place = _community_place(gdf)
    with st.container(border=True, key="dhoa_community_step2"):
        st.markdown(f"**{T.C_STEP2}**")
        whole_area = place is not None and not place.radius_applies
        st.segmented_control(
            T.C_RADIUS_LABEL,
            list(cm.RADIUS_CHOICES_M),
            format_func=lambda value: T.C_RADIUS_OPTION_FMT.format(value / 1000),
            help=T.C_RADIUS_HELP,
            key="community_radius_m",
            disabled=whole_area,
            width="stretch",
        )
        if whole_area:
            st.caption(T.C_RADIUS_AREA_NOTE)
    return place


def _render_community_empty(
    gdf: pd.DataFrame, result: cm.SearchResult, radius_m: int
) -> None:
    """Explain an empty radius result and offer the one-click next step."""
    nearest = cm.nearest_beyond(gdf, result.place.lat, result.place.lon)
    if nearest is None:
        st.info(T.C_EMPTY_NONE)
        return
    distance_m, row = nearest
    area = str(row.get("ui_area") or _area_display_name(row))
    target = cm.radius_to_reach(distance_m)
    template = T.C_EMPTY_NEAREST_FMT if target is not None else T.C_EMPTY_FAR_FMT
    st.info(template.format(radius_m / 1000, distance_m / 1000, area))
    if target is not None and target > radius_m:
        st.button(
            T.C_SHOW_WITHIN_FMT.format(target / 1000),
            key="community_widen",
            on_click=_set_community_radius,
            args=(target,),
            type="primary",
            width="stretch",
        )


def _render_community_table(nearby: pd.DataFrame, show_distance: bool) -> None:
    """Render the result list with a directions link per kiln."""
    directions = [
        f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f}%2C{lon:.6f}"
        for lat, lon in zip(nearby["lat"].astype(float), nearby["lon"].astype(float))
    ]
    columns: dict[str, Any] = {}
    if show_distance:
        columns[T.DISTANCE_M] = (
            nearby["distance_m"].round(0).astype("Int64").astype("string").fillna(T.NO_DATA).to_numpy()
        )
    columns[T.AREA] = nearby["ui_area"].tolist()
    columns[T.KILN_TYPE] = nearby["ui_type"].tolist()
    columns[T.PRIORITY] = nearby["ui_priority"].tolist()
    columns[T.DIRECTIONS] = directions
    st.dataframe(
        pd.DataFrame(columns), hide_index=True, width="stretch",
        column_config={T.DIRECTIONS: st.column_config.LinkColumn(display_text=T.GET_DIRECTIONS)},
    )


def _render_community_summary(result: cm.SearchResult) -> None:
    """Summary card: how many kilns, and how many are high priority."""
    counts = result.summary
    if result.radius_m is None:
        headline = T.C_SUMMARY_AREA_FMT.format(result.place.name, counts["total"])
    else:
        headline = T.C_SUMMARY_RADIUS_FMT.format(
            result.radius_m / 1000, result.place.name, counts["total"]
        )
    glyphs = kd.PRIORITY_GLYPHS
    with st.container(border=True, key="dhoa_community_summary"):
        st.markdown(f"#### {headline}")
        st.markdown(T.C_SUMMARY_HIGH_FMT.format(counts["high"]))
        st.caption(
            f"{glyphs['High']} {T.SUMMARY_HIGH}: {counts['high']:,} · "
            f"{glyphs['Medium']} {T.SUMMARY_MEDIUM}: {counts['medium']:,} · "
            f"{glyphs['Low']} {T.SUMMARY_LOW}: {counts['low']:,}"
        )


def _render_community_results(gdf: pd.DataFrame, place: cm.Place | None) -> None:
    """Render step 3: summary, list, map, downloads, or a clear next step."""
    st.markdown(f"**{T.C_STEP3}**")
    if place is None:
        st.info(T.C_PICK_PROMPT)
        return
    if place.kind == cm.KIND_POINT and cm.covered_district(gdf, place.lat, place.lon) is None:
        districts = ", ".join(
            kd.district_label(name) for name in sorted(gdf["district"].dropna().astype(str).unique())
        )
        st.warning(T.C_OUTSIDE_FMT.format(place.name, districts))
        return
    result = _community_result(gdf)
    if result is None:
        st.info(T.C_PICK_PROMPT)
        return
    st.session_state.pop("community_centroid", None)
    nearby = kd.with_display_columns(result.rows, _siting_rules())
    radius_m = result.radius_m
    _render_community_summary(result)
    if nearby.empty:
        if radius_m is None:
            st.info(T.NO_KILNS_IN_AREA_FMT.format(place.name))
        else:
            _render_community_empty(gdf, result, radius_m)
        return

    report_name = place.name
    list_column, map_column = st.columns([2, 3], gap="medium")
    with list_column:
        st.subheader(T.C_LIST_TITLE)
        _render_community_table(nearby, show_distance=radius_m is not None)
        try:
            st.download_button(
                T.DOWNLOAD_REPORT, _community_report(report_name, nearby, radius_m or 0),
                "dhoa_community_report.pdf", "application/pdf",
                width="stretch", key="community_alert_download",
            )
        except Exception:
            logging.exception("Community PDF generation failed")
            st.error(T.REPORT_GENERATION_FAILED_PLEASE_TRY_AGAI)
        st.download_button(
            T.DOWNLOAD_COMMUNITY_CSV,
            make_download_csv(nearby, COMMUNITY_CSV_COLUMNS),
            "dhoa_community_candidates.csv", "text/csv",
            width="stretch", key="community_candidates_csv_download",
        )
    with map_column:
        st.subheader(T.AREA_MAP)
        st.caption(
            T.C_MAP_CAPTION_AREA_FMT.format(place.name)
            if radius_m is None
            else T.C_MAP_CAPTION_RADIUS_FMT.format(place.name, radius_m / 1000)
        )
        with st.container(border=True):
            _render_community_map_fragment(
                nearby, gdf, place.lat, place.lon, radius_m, place.name, place.key
            )


def render_community_view(gdf: gpd.GeoDataFrame) -> None:
    """Render the Community view as three steps on one screen.

    Input schema: prepared kiln frame (lat/lon, district, upazila, class,
    priority_band, optional nearest_place). Output schema: 1) a searchable
    place picker built from the data plus "use my location" and an optional
    geocoder fallback, 2) radius choices 1/2/5/10 km (default 5; whole-area
    choices list every kiln), 3) a summary, list, map and PDF/CSV downloads,
    or a clear next step when nothing is found. No page reload anywhere.
    """
    st.markdown(f"<div class='dhoa-section-title'>{T.FIND_KILNS_NEAR_YOU}</div>", unsafe_allow_html=True)
    place = _render_community_inputs(gdf)
    _render_community_results(gdf, place)
    with st.expander(T.LISTEN_TO_THE_GUIDE):
        community_guide = _ROOT / "app" / "static" / "community_guide.mp3"
        if community_guide.is_file():
            st.audio(str(community_guide))
        else:
            st.info(T.AUDIO_GUIDE_COMING_SOON)


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


def _data_date_label(path: Path | None) -> str:
    """Return the data file's modification date (UTC, ISO) or the no-data label.

    Input: path of the loaded kilns file (or None). Output: ``YYYY-MM-DD`` of
    the file's mtime, i.e. when the dataset was produced, never today's date.
    """
    if path is None:
        return T.NO_DATA
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime, tz=UTC).date().isoformat()
    except OSError:
        return T.NO_DATA


def render_header(gdf: gpd.GeoDataFrame) -> str:
    """Render the Dhoa header, mode navigation, and candidate summary metrics."""
    st.markdown(f"<h1 class='dhoa-brand-title'>{html.escape(DASHBOARD_TITLE)}</h1>", unsafe_allow_html=True)
    loaded = dashboard_kilns_file()
    subtitle = T.BANGLADESH_BRICK_KILN_MONITORING_DASHBOA
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
        (_data_date_label(loaded), METRIC_LABELS["last_updated"]),
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
            st.caption(T.RAIL_HINT)
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
                    format_func=lambda value: (
                        f"{kd.PRIORITY_GLYPHS[band]} {value}"
                        if (band := {T.HIGH: "High", T.MEDIUM: "Medium", T.LOW: "Low"}.get(value))
                        else value
                    ),
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
    """Render the selected-kiln detail card with navigation links.

    Input: one kiln row. Output: a bordered card with the id, a priority badge
    (shape + text), type, area, detection status, distance to government
    forest, coordinates and Google Maps / Street View / Earth links. No
    confidence scores are shown.
    """
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", T.NO_DATA))
    forest_distance = kd.to_float(row.get("dist_government_forest_m"))
    if pd.isna(forest_distance):
        forest_distance = kd.to_float(row.get("dist_forests_m"))
    forest_distance_label = (
        T.METRES_FMT.format(float(forest_distance)) if pd.notna(forest_distance) else T.NO_DATA
    )
    is_new = row.get("detection_status") == "New candidate (2025-26)"
    detection = T.STATUS_NEW if is_new else T.STATUS_KNOWN
    with st.container(border=True, key="dhoa_detail_card"):
        st.subheader(T.SELECTED_KILN_TITLE_FMT.format(candidate_id))
        st.markdown(f"**{kd.priority_badge(row.get('priority_band'))}** — {_priority_reason(row)}")
        left, right = st.columns(2)
        with left:
            st.markdown(f"**{T.KILN_TYPE_2}:** {_type_label(row.get('class'))}")
            st.markdown(f"**{T.AREA}:** {_area_display_name(row)}")
            st.markdown(f"**{T.DETECTION_STATUS}:** {detection}")
        with right:
            st.markdown(f"**{T.DISTANCE_FROM_GOVERNMENT_FOREST}:** {forest_distance_label}")
            st.markdown(f"**{T.COORDINATES}:** {lat:.5f}, {lon:.5f}")
        with st.container(key="dhoa_action_row"):
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
    """Return the JS factory that turns one compact row into a shaped marker.

    Priority is encoded by shape *and* colour (triangle = High, diamond =
    Medium, circle = Low, square = unclassified), so it never relies on colour
    alone. The shape is a small inline SVG ``divIcon`` sized from ``radius``.

    Input: ``kiln_data.marker_payload`` output. Output: a JS function expression
    for ``FastMarkerCluster``. Each marker gets a hover tooltip and, on click, a
    light details popup (priority, type, area, coordinates and Google Maps
    directions / map / Earth links) that is built *in the browser* from the
    row's own coordinates, so nothing per-kiln is embedded in the page. Labels
    come from small arrays (~40 bytes per kiln on the wire) and arrive
    HTML-escaped; the popup is opened with ``L.popup().openOn`` rather than
    ``bindPopup`` so no popup content is attached to the 2,000+ markers.
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
            "rules": payload["rules"],
            "text": payload["text"],
            "labels": {
                "kiln": html.escape(T.KILN_CANDIDATE),
                "area": html.escape(T.AREA),
                "directions": html.escape(T.DIRECTIONS),
                "map": html.escape(T.MAP),
            },
        },
        ensure_ascii=False,
    )
    popup_js = r"""var sg="<strong>"+D.text.signals+":</strong>";
for(var i=0;i<D.rules.length;i++){var st=row[5].charAt(i),dv=row[6][i];
sg+="<div class='rule-signal-row'><span>"+['🔴','🟡','🟢','⚪'][st]+"</span> "+D.rules[i]+": "
+(st==='3'?D.text.nodata:st==='2'?D.text.outside:dv.toLocaleString('en-US')+D.text.unit)+"</div>";}
var la=row[0],lo=row[1],q=la.toFixed(6)+','+lo.toFixed(6),g='https://www.google.com/maps',
h="<div class='dhoa-popup'><div class='badges'><span class='badge'>"+D.types[row[3]]+"</span>"
+"<span class='badge priority-badge'>"+D.bands[row[2]]+"</span></div>"
+"<strong>"+D.labels.kiln+" · "+D.areas[row[4]]+"</strong><hr>"
+"📍 "+D.labels.area+": "+D.areas[row[4]]+"<br>"+la.toFixed(5)+", "+lo.toFixed(5)+"<hr>"
+sg+"<hr><div class='popup-actions'>"
+"<a href='"+g+"/dir/?api=1&destination="+q+"&travelmode=driving' target='_blank' rel='noopener'>🗺️ "+D.labels.directions+"</a>"
+"<a href='"+g+"?q="+q+"' target='_blank' rel='noopener'>📍 "+D.labels.map+"</a>"
+"<a href='https://earth.google.com/web/@"+la.toFixed(6)+","+lo.toFixed(6)+",500a,500d,35y' target='_blank' rel='noopener'>🌍 Google Earth</a>"
+"</div></div>";"""
    factory = r"""(function(){var D=__LOOKUPS__;
return function(row){var c=D.colors[row[2]];var S=__SIZE__;
var sh=["<polygon points='11,2 21,19 1,19'","<polygon points='11,1 21,11 11,21 1,11'",
"<circle cx='11' cy='11' r='9'","<rect x='3' y='3' width='16' height='16'"];
var ic=L.divIcon({className:'dhoa-pin',iconSize:[S,S],iconAnchor:[S/2,S/2],
html:"<svg width='"+S+"' height='"+S+"' viewBox='0 0 22 22'>"+sh[row[2]]+" fill='"+c+"' fill-opacity='0.92' stroke='#fff' stroke-width='1.6'/></svg>"});
var m=L.marker([row[0],row[1]],{icon:ic,riseOnHover:true});
m.bindTooltip(D.bands[row[2]]+" | "+D.types[row[3]]+" | "+D.areas[row[4]],{sticky:true});
__POPUP__
m.on('click',function(e){var mp=e.target._map;if(!mp){return;}
L.popup({maxWidth:300,autoPan:true}).setLatLng(e.target.getLatLng()).setContent(h).openOn(mp);});
return m;};})()"""
    return (
        factory.replace("__LOOKUPS__", lookups)
        .replace("__SIZE__", str(int(radius) * 2 + 8))
        .replace("__POPUP__", popup_js)
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


@st.cache_data(show_spinner=False, max_entries=32)
def _cached_marker_payload(version: str, key: tuple, _frame: pd.DataFrame) -> dict[str, Any]:
    """Cache the compact marker rows per (dataset version, filter/search key).

    Only plain lists/dicts are cached. A ``folium.Map`` must never be cached and
    reused: ``st_folium`` rewrites element ids while rendering, so a second
    render of the same object emits a script that references undefined
    variables and the map iframe collapses to height 0 (the map "disappears").
    """
    return kd.marker_payload(_frame, _siting_rules())


def _marker_map(
    frame: pd.DataFrame,
    tile: str,
    bounds: list[list[float]] | None,
    radius: int = 8,
    payload: dict[str, Any] | None = None,
) -> folium.Map:
    """Build a *fresh* base map with one clustered marker layer for ``frame``.

    ``payload`` is the cached ``kd.marker_payload`` output; a new ``folium.Map``
    is created on every call because ``st_folium`` mutates the object it renders.
    """
    if payload is None:
        payload = kd.marker_payload(frame, _siting_rules())
    map_view = _new_map(tile, bounds if bounds is not None else kd.bounds_of(frame))
    if payload["rows"]:
        FastMarkerCluster(
            payload["rows"], callback=_marker_callback_js(payload, radius),
            options=dict(_MARKER_OPTIONS),
        ).add_to(map_view)
    return map_view


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
    payload = _cached_marker_payload(version, ("inspector", *tuple(_inspector_filter_key())), filtered)
    return _marker_map(filtered, tile, None, payload=payload)


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


def _render_empty_results(selected_upazila: str) -> None:
    """Show the empty state for a filter combination with no kilns.

    Input: the selected upazila (or ``ALL_AREAS``). Output: a message that says
    what happened, a hint, and a one-click reset that reruns the whole app so
    the sidebar widgets pick up the cleared filters.
    """
    st.info(
        T.NO_KILNS_IN_AREA_FMT.format(selected_upazila)
        if selected_upazila != ALL_AREAS
        else T.NO_CANDIDATES_MATCH_THESE_FILTERS
    )
    st.caption(T.EMPTY_FILTER_HINT)
    # The reset runs as a callback (the only place widget-keyed state may be
    # changed); the app-wide rerun then redraws the sidebar with cleared filters.
    if st.button(T.RESET_FILTERS, key="dhoa_empty_reset_filters", on_click=_reset_inspector_filters):
        st.rerun(scope="app")


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
    if visible.empty:
        _render_empty_results(selected_upazila)
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
            with st.spinner(T.LOADING_MAP):
                _m = build_map(gdf, filters, filtered=visible)
        except Exception as _exc:
            logging.exception("Inspector map rendering failed")
            st.error(T.COULD_NOT_RENDER_THE_MAP)
            if st.button(T.RETRY, key="dhoa_retry_map"):
                st.rerun(scope="app")
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
        detail_slot = st.container()
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
    with detail_slot:
        if selected.empty:
            st.info(T.DETAIL_HINT)
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


def _render_summary_strip(visible: pd.DataFrame) -> None:
    """Render the filtered-results summary strip and the priority explanation.

    Input: the already-filtered frame. Output: one row of counts (matching,
    High, Medium, Low, new) with shape glyphs as well as colours, plus a short
    note that the bands are relative shares of the ranking, not absolute risk.
    """
    counts = kd.priority_summary(visible)
    glyphs = kd.PRIORITY_GLYPHS
    items = (
        (f"{counts['total']:,}", T.SUMMARY_MATCHING, "#475569"),
        (f"{glyphs['High']} {counts['high']:,}", T.SUMMARY_HIGH, PRIORITY_COLORS["High"]),
        (f"{glyphs['Medium']} {counts['medium']:,}", T.SUMMARY_MEDIUM, PRIORITY_COLORS["Medium"]),
        (f"{glyphs['Low']} {counts['low']:,}", T.SUMMARY_LOW, PRIORITY_COLORS["Low"]),
        (f"{counts['new']:,}", T.SUMMARY_NEW, "#475569"),
    )
    cells = "".join(
        f"<div class='dhoa-metric' style='border-left-color:{color}'>"
        f"<strong>{value}</strong><span>{html.escape(label)}</span></div>"
        for value, label, color in items
    )
    st.markdown(f"<div class='dhoa-metrics dhoa-summary'>{cells}</div>", unsafe_allow_html=True)
    st.caption(T.PRIORITY_NOTE)


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
        filters = render_sidebar(gdf, mode)
        if mode == "community":
            render_community_view(gdf)
            render_footer()
            return
        visible = filters["visible"]  # computed once in render_sidebar
        _render_summary_strip(visible)
        render_map_fragment(gdf, filters, visible)
        render_footer()
    except Exception as _exc:
        logging.getLogger(__name__).exception("Dashboard view rendering failed")
        st.error(T.COULD_NOT_RENDER_THE_DASHBOARD)
if __name__ == "__main__":
    main()
