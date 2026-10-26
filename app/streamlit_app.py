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
import time
import textwrap
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

try:  # works both as a package import and when Streamlit puts app/ on sys.path
    from app import storage as public_storage  # noqa: E402
except ImportError:  # pragma: no cover - Streamlit script execution
    import storage as public_storage  # type: ignore[no-redef]  # noqa: E402
from app import strings as T  # noqa: E402

DASHBOARD_TITLE = unicodedata.normalize("NFC", T.APP_TITLE)
assert T.CHANDRABINDU in DASHBOARD_TITLE, repr(DASHBOARD_TITLE)

_FAVICON = _ROOT / "app" / "static" / "favicon.png"
st.set_page_config(
    page_title=DASHBOARD_TITLE, page_icon=str(_FAVICON) if _FAVICON.is_file() else None,
    layout="wide", initial_sidebar_state="expanded",
)

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from branca.element import Element
from pyproj import Transformer
from folium.plugins import FastMarkerCluster, HeatMap
from streamlit_folium import st_folium

# isort: off
import community as cm
import roles
import design_tokens as tokens
import hero
import trust
import voice
import styles
import kiln_data as kd
import inspector as ins
import staff_tools
import overview as ov
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
APP_DB_PATH = Path(os.environ.get("DHOA_APP_DB") or BASE_DIR / "data" / "app.db")
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
_voice_player = components.declare_component(
    "dhoa_voice_guide",
    path=str(_ROOT / "app" / "components" / "voice_guide"),
)
DESIGN_COLORS = {
    key: tokens.COLORS[key]
    for key in (
        "high", "medium", "low", "new", "unclassified", "background", "card", "text",
        "text_muted", "border_strong", "marker_outline", "marker_halo",
        "popup_text", "popup_badge", "popup_rule", "high_text", "new_text",
    )
}
PRIORITY_COLORS = {
    "High": DESIGN_COLORS["high"],
    "Medium": DESIGN_COLORS["medium"],
    "Low": DESIGN_COLORS["low"],
}
# Text-safe variants (>= 4.5:1 on the card surface) for priority words in tables.
PRIORITY_TEXT_COLORS = {
    band: tokens.COLORS[spec["text_color"]] for band, spec in tokens.PRIORITY.items()
}
ALL_KILN_TYPES = kd.ALL_KILN_TYPES
ALL_DISTRICTS = kd.ALL_DISTRICTS
ALL_AREAS = kd.ALL_AREAS
KILN_TYPE_LABELS = T.LazyMapping(
    lambda: {
        ALL_KILN_TYPES: T.ALL_TYPES,
        "Zigzag": T.ZIGZAG_KILN,
        "FCBK": T.FIXED_CHIMNEY_KILN,
    }
)
INSPECTOR_CSV_COLUMNS = T.LazySequence(
    lambda: [
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
)
METRIC_LABELS = T.LazyMapping(
    lambda: {
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
)


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
def _prepared_data(path_text: str, mtime_ns: int, size: int, lang: str) -> gpd.GeoDataFrame | None:
    """Build the display-ready dataset once per data file version.

    Input: data path plus its mtime/size (cache key, so a replaced file is
    picked up). Output: the loaded frame with priority bands, a default
    detection status and the precomputed ``ui_*`` display columns (in ``lang``;
    the language is part of the cache key and of the data version, so every
    cache keyed by the version is per-language too), or None when
    the file cannot be loaded. The object is shared by every session and must
    be treated as read-only; all consumers copy via ``iloc``/``loc``.
    """
    gdf = load_data(Path(path_text))
    if gdf is None:
        return None
    return kd.prepare_display_frame(
        add_priority_bands(gdf), _siting_rules(), version=f"{mtime_ns}-{size}-{len(gdf)}-{lang}"
    )


@st.cache_resource(show_spinner=False)
def _public_data(path_text: str, mtime_ns: int, size: int, lang: str) -> gpd.GeoDataFrame | None:
    """Build the PUBLIC dataset once per data file version and language.

    Input: data path plus its mtime/size and the language (cache key). Output: the cached
    prepared frame passed through ``kd.public_view`` (no priority, rule or distance column, no staff
    display column) with only ``ui_area``/``ui_type`` added; ``attrs["dhoa_data_version"]``
    ends in ``-public`` so every cache keyed by it is separate from the staff data. The
    object is shared by every session and must be treated as read-only.
    """
    prepared = _prepared_data(path_text, mtime_ns, size, lang)  # reuse the cached load: no second read
    if prepared is None:
        return None
    version = str(prepared.attrs.get("dhoa_data_version", mtime_ns))
    prepare_public = getattr(kd, "prepare_public_frame", None)
    if callable(prepare_public):
        return prepare_public(prepared, version=version)
    public_view = getattr(kd, "public_view", None)
    public_display = getattr(kd, "with_public_display_columns", None)
    if not callable(public_view) or not callable(public_display):
        raise AttributeError("kiln_data must provide public frame preparation helpers")
    result = public_display(public_view(prepared))
    result.attrs["dhoa_data_version"] = f"{version}-public"
    return result


def get_public_data(path: Path = DATA_PATH) -> gpd.GeoDataFrame | None:
    """Return the cached public dataset (what Overview, Kilns near me and About may use)."""
    if not path.is_file():
        return None
    stat = path.stat()
    return _public_data(str(path), stat.st_mtime_ns, stat.st_size, T.get_language())


def get_prepared_data(path: Path = DATA_PATH) -> gpd.GeoDataFrame | None:
    """Return the cached display-ready dataset, or None when the file is missing."""
    if not path.is_file():
        return None
    stat = path.stat()
    return _prepared_data(str(path), stat.st_mtime_ns, stat.st_size, T.get_language())


def class_counts(frame: pd.DataFrame) -> tuple[int, int]:
    """Return fixed-chimney and zigzag counts for compatibility callers."""
    classes = frame.get("class", pd.Series(dtype="string")).astype("string")
    return int(classes.eq("FCBK").sum()), int(classes.eq("Zigzag").sum())


def color_for_kiln(row: Mapping[str, object]) -> str:
    """Return the map color for an existing priority band."""
    return PRIORITY_COLORS.get(str(row.get("priority_band", "")), DESIGN_COLORS["unclassified"])


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
    """Format a kiln's administrative area (``upazila, district``) in the active language."""
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
def _report_from_json(row_json: str, lang: str = "bn") -> bytes | None:
    """Build and cache a candidate report from serialized row fields (per language)."""
    from src.eval.generate_report import generate_kiln_report

    return generate_kiln_report(json.loads(row_json), lang)


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
        no_wrap=True,
        max_zoom=19,
        max_native_zoom=19,
        keep_buffer=4,
    ).add_to(map_view)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name=T.SATELLITE_IMAGERY,
        overlay=False,
        control=True,
        show=selected_tile == "satellite",
        no_wrap=True,
        max_zoom=19,
        max_native_zoom=17,
        keep_buffer=4,
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
    widget_key = _seed("map_tile", st.session_state["map_tile"])
    selected_tile = st.selectbox(
        T.MAP_TYPE,
        ["street", "satellite"],
        index=None,
        format_func=lambda value: T.STREET_MAP if value == "street" else T.SATELLITE_IMAGERY,
        label_visibility="collapsed",
        key=widget_key,
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


def _contact() -> dict[str, Any]:
    """Contact settings from config/dashboard.yaml (hotline number only when verified)."""
    try:
        return trust.contact_settings(load_config().get("dashboard"))
    except Exception:
        return trust.contact_settings(None)


def community_alert_pdf(
    location: str, rows: pd.DataFrame, radius_m: int, lang: str | None = None
) -> bytes:  # radius_m == 0: whole area
    """Create the community PDF in the active (or given) language.

    Input schema: searched location label, rows with distance_m, class, priority band,
    lat, lon, upazila, district, and the radius in metres. Output: A4 PDF bytes
    (empty bytes if generation failed).
    """
    from src.eval.generate_community_report import generate_community_report

    return generate_community_report(
        location, rows, radius_m, lang or T.get_language(), hotline=_contact()["number"]
    ) or b""


_PDF_COLUMNS = (
    ("distance_m", None), ("class", "Unknown"), ("lat", None), ("lon", None),
    ("upazila", ""), ("district", ""),
)


@st.cache_data(show_spinner=False, max_entries=16)
def _cached_community_pdf(location: str, radius_m: int, rows: tuple, day: str, lang: str) -> bytes:
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
        location, int(radius_m), tuple(zip(*columns)), f"{datetime.now(UTC):%Y-%m-%d}", T.get_language()
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
        map_view = _marker_map(nearby, tile, bounds, radius=7, public=True)
    else:
        payload = _cached_public_marker_payload(version, ("community", "public", *fingerprint), nearby)
        map_view = _marker_map(nearby, tile, bounds, radius=7, payload=payload, public=True)
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
        _render_public_candidate(selected.iloc[0])


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


def _community_place_suggestions(places: dict[str, cm.Place], query: str) -> list[str]:
    """Match typed text against place names; return at most 12 ranked place keys.

    Input schema: dataset place keys and ``Place`` values plus user-entered text.
    Output schema: matching keys ordered by name-prefix match, then label.
    """
    needle = query.strip().casefold()
    if not needle:
        return []
    matches = [
        place for place in places.values()
        if needle in " ".join((place.name, place.district, place.upazila, place.label)).casefold()
    ]
    matches.sort(key=lambda place: (not place.name.casefold().startswith(needle), place.label.casefold()))
    return [place.key for place in matches[:12]]


_COMMUNITY_GEOCODE_OPTION_PREFIX = "__dhoa_geocode_place__:"


def _community_geocode_option(query: str) -> str | None:
    """Return a namespaced suggestion for a typed name outside local matches.

    Input schema: typed place name. Output: one selectbox option to geocode on
    selection, or ``None`` for blank input.
    """
    text = " ".join(query.split())
    return f"{_COMMUNITY_GEOCODE_OPTION_PREFIX}{text}" if text else None


def _community_place(gdf: pd.DataFrame) -> cm.Place | None:
    """Resolve the active search origin from session state.

    A geocoded/GPS point (``community_origin``) wins over the picker, because
    choosing in the picker clears it.
    """
    origin = st.session_state.get("community_origin")
    if isinstance(origin, dict):
        # A GPS fix stores no text: its label is looked up now, in the active language.
        name = T.MY_LOCATION if origin.get("gps") else str(origin["name"])
        return cm.point_place(name, float(origin["lat"]), float(origin["lon"]))
    return _community_places(gdf).get(st.session_state.get("community_place_key"))


def _community_result(gdf: pd.DataFrame) -> cm.SearchResult | None:
    """Search the dataset for the active origin and radius (None if no origin)."""
    place = _community_place(gdf)
    if place is None:
        return None
    radius = int(st.session_state.get("community_radius_m") or cm.DEFAULT_RADIUS_M)
    return cm.search(gdf, place, radius)


def _on_community_pick(gdf: pd.DataFrame) -> None:
    """Apply a matched area or queue geocoding of the typed search option."""
    selected = st.session_state.get(_wkey("community_suggestion"))
    if isinstance(selected, str) and selected.startswith(_COMMUNITY_GEOCODE_OPTION_PREFIX):
        st.session_state["community_place_key"] = None
        st.session_state["community_origin"] = None
        st.session_state.pop("community_notice", None)
        st.session_state["community_selected_kiln_id"] = None
        st.session_state["community_pending_geocode"] = selected[len(_COMMUNITY_GEOCODE_OPTION_PREFIX):]
        return
    st.session_state["community_place_key"] = None
    st.session_state["community_origin"] = None
    st.session_state.pop("community_notice", None)
    st.session_state["community_selected_kiln_id"] = None
    if selected is None:
        return
    place = _community_places(gdf).get(selected) if isinstance(selected, str) else None
    if place is not None:
        st.session_state["community_place_key"] = place.key
        st.session_state["community_search_query"] = place.name
        return


def _on_community_search() -> None:
    """Clear the old result as soon as the user starts a different search."""
    st.session_state["community_place_key"] = None
    st.session_state["community_origin"] = None
    st.session_state.pop("community_notice", None)
    st.session_state["community_selected_kiln_id"] = None


def _set_community_radius(radius_m: int) -> None:
    """Button callback: widen the radius to ``radius_m``."""
    st.session_state["community_radius_m"] = int(radius_m)


def _set_community_origin(name: str | None, lat: float, lon: float) -> None:
    """Make a searched place or GPS fix the origin; GPS clears the picker next run."""
    st.session_state["community_origin"] = {
        "name": name or "", "gps": name is None, "lat": float(lat), "lon": float(lon),
    }
    if name is None:
        st.session_state["community_picker_reset"] = True
        st.session_state["community_search_reset"] = True
    st.session_state["community_selected_kiln_id"] = None


# Notices are stored as catalogue *names* (never translated text), so a language
# switch re-renders them in the new language.
_NOTICE_NAMES = {
    "gps_ok": "C_GPS_OK", "gps_denied": "C_GPS_DENIED", "gps_unsupported": "C_GPS_UNSUPPORTED",
    "gps_insecure": "C_GPS_INSECURE", "gps_timeout": "C_GPS_TIMEOUT", "gps_unavailable": "C_GPS_UNAVAILABLE",
    "geo_empty": "C_GEO_EMPTY", "geo_unavailable": "C_GEO_UNAVAILABLE", "geo_not_found": "C_GEO_NOT_FOUND",
}


def _set_community_notice(level: str, code: str) -> None:
    """Remember a notice by level (``success``/``warning``) and code, not by text."""
    st.session_state["community_notice"] = (level, code)


_GPS_ERRORS = T.LazyMapping(
    lambda: {
        "denied": T.C_GPS_DENIED,
        "unsupported": T.C_GPS_UNSUPPORTED,
        "insecure": T.C_GPS_INSECURE,
        "timeout": T.C_GPS_TIMEOUT,
        "unavailable": T.C_GPS_UNAVAILABLE,
    }
)


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
        _set_community_origin(None, lat, lon)
        _set_community_notice("success", "gps_ok")
    else:
        code = f"gps_{event.get('error')}"
        _set_community_notice("warning", code if code in _NOTICE_NAMES else "gps_unavailable")
    st.rerun()


def _submit_community_geocode(query: str) -> None:
    """Geocode a user-submitted name and store the result for the next rerun."""
    text = " ".join(query.split())
    if not text:
        _set_community_notice("warning", "geo_empty")
        return
    try:
        with st.spinner(T.C_GEO_SEARCHING):
            hit = _cached_geocode(text.casefold())
    except cm.GeocodeUnavailable:
        _set_community_notice("warning", "geo_unavailable")
        return
    except Exception:  # noqa: BLE001 - never break the page on a provider error
        logging.exception("Community geocoding failed")
        _set_community_notice("warning", "geo_unavailable")
        return
    if hit is None:
        _set_community_notice("warning", "geo_not_found")
        return
    st.session_state.pop("community_notice", None)
    _set_community_origin(text, hit[0], hit[1])


def _render_community_inputs(gdf: pd.DataFrame) -> cm.Place | None:
    """Render steps 1 and 2 and return the chosen origin (or None)."""
    if st.session_state.pop("community_picker_reset", False):
        st.session_state["community_place_key"] = None
        st.session_state.pop(_wkey("community_suggestion"), None)
    if st.session_state.pop("community_search_reset", False):
        st.session_state["community_search_query"] = ""
    places = _community_places(gdf)
    if st.session_state.get("community_radius_m") not in cm.RADIUS_CHOICES_M:
        st.session_state["community_radius_m"] = cm.DEFAULT_RADIUS_M
    if st.session_state.get("community_place_key") not in places:
        st.session_state["community_place_key"] = None
    _seed("community_radius_m", st.session_state["community_radius_m"])

    with st.container(border=True, key="dhoa_community_step1"):
        st.markdown(f"**{T.C_STEP1}**")
        query = st.text_input(
            T.C_PLACE_LABEL,
            placeholder=T.C_PLACE_PLACEHOLDER,
            help=T.C_PLACE_HELP,
            key="community_search_query",
            on_change=_on_community_search,
        )
        origin = st.session_state.get("community_origin")
        selected_local = st.session_state.get("community_place_key") in places
        selected_geocoded = (
            isinstance(origin, dict)
            and not origin.get("gps")
            and query.strip().casefold() == str(origin.get("name", "")).strip().casefold()
        )
        suggestions = [] if selected_local or selected_geocoded else _community_place_suggestions(places, query)
        geocode_option = _community_geocode_option(query) if query.strip() and not suggestions else None
        if suggestions or geocode_option:
            _seed("community_suggestion", None)
            options = suggestions + ([geocode_option] if geocode_option else [])
            st.selectbox(
                T.C_PLACE_SUGGESTIONS,
                options,
                index=None,
                format_func=lambda value: (
                    T.C_GEO_SUGGESTION_FMT.format(value[len(_COMMUNITY_GEOCODE_OPTION_PREFIX):])
                    if value.startswith(_COMMUNITY_GEOCODE_OPTION_PREFIX)
                    else places[value].label
                ),
                placeholder=T.C_PLACE_SUGGESTION_PLACEHOLDER,
                key=_wkey("community_suggestion"),
                on_change=_on_community_pick,
                args=(gdf,),
            )
        pending_geocode = st.session_state.pop("community_pending_geocode", None)
        if isinstance(pending_geocode, str):
            _submit_community_geocode(pending_geocode)
        event = _geolocate(
            label=T.C_GPS_LABEL, busy_label=T.C_GPS_BUSY, key="community_gps", default=None
        )
        _handle_gps_event(event)
        notice = st.session_state.get("community_notice")
        if notice and notice[1] in _NOTICE_NAMES:
            getattr(st, notice[0], st.info)(T.text(_NOTICE_NAMES[notice[1]]))

    place = _community_place(gdf)
    with st.container(border=True, key="dhoa_community_step2"):
        st.markdown(f"**{T.C_STEP2}**")
        whole_area = place is not None and not place.radius_applies
        st.segmented_control(
            T.C_RADIUS_LABEL,
            list(cm.RADIUS_CHOICES_M),
            format_func=lambda value: T.C_RADIUS_OPTION_FMT.format(value / 1000),
            help=T.C_RADIUS_HELP,
            key=_wkey("community_radius_m"),
            on_change=_commit_radius,
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
    columns[T.DIRECTIONS] = directions
    st.dataframe(
        pd.DataFrame(columns), hide_index=True, width="stretch",
        column_config={T.DIRECTIONS: st.column_config.LinkColumn(display_text=T.GET_DIRECTIONS)},
    )


def _render_community_cards(nearby: pd.DataFrame, show_distance: bool) -> None:
    """Render public search results as touch-friendly candidate cards.

    Input: rows from ``kiln_data.with_public_display_columns`` with coordinates
    and ``distance_m``. Output: localized type/place/distance cards with a
    directions link; no staff-only fields are read or displayed.
    """
    for index, (_, row) in enumerate(nearby.iterrows()):
        with st.container(border=True, key=f"community_candidate_{index}"):
            st.markdown(f"**{row.get('ui_type', T.NO_DATA)}**")
            place = row.get("nearest_place")
            if place is None or pd.isna(place) or not str(place).strip():
                place = row.get("ui_area", T.NO_DATA)
            st.caption(T.C_CARD_PLACE_FMT.format(place))
            if show_distance:
                distance = pd.to_numeric(pd.Series([row.get("distance_m")]), errors="coerce").iloc[0]
                if pd.notna(distance):
                    distance_text = T.M_DOT_FMT.format(float(distance))
                    st.caption(T.C_CARD_DISTANCE_FMT.format(distance_text))
            lat, lon = float(row["lat"]), float(row["lon"])
            url = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f}%2C{lon:.6f}"
            st.link_button(T.GET_DIRECTIONS, url, width="stretch")
            kiln_id = str(row.get("kiln_id", ""))
            report_key = hashlib.sha256(f"{kiln_id}:{index}".encode("utf-8")).hexdigest()[:16]
            st.button(
                T.C_REPORT_CARD_ACTION, key=f"dhoa_report_open_{report_key}", width="stretch",
                on_click=_select_candidate_report, args=(kiln_id,),
            )


def _select_candidate_report(kiln_id: str) -> None:
    """Select a public candidate card as the subject of the correction form."""
    st.session_state["dhoa_report_candidate_id"] = kiln_id


_REPORT_RATE_LIMIT = 3
_REPORT_RATE_WINDOW_S = 3600.0


def _report_rate_allowed() -> bool:
    """Return whether this Streamlit session remains under the public form limit."""
    now = time.monotonic()
    history = [
        float(value) for value in st.session_state.get("dhoa_report_submissions", [])
        if now - float(value) < _REPORT_RATE_WINDOW_S
    ]
    st.session_state["dhoa_report_submissions"] = history
    return len(history) < _REPORT_RATE_LIMIT


def _record_public_report(report: public_storage.NewReport, frame: pd.DataFrame, honeypot: str) -> str:
    """Validate a public report against the current data extent and persist it.

    Input: proposed report, the public kiln frame, and the hidden honeypot value.
    Output: a catalogue-independent result key for localized UI feedback.
    """
    if honeypot.strip():
        return "sent"  # quiet discard so the honeypot does not disclose itself
    extent = public_storage.extent_from_frame(frame)
    if not public_storage.coordinates_in_extent(report.lat, report.lon, extent):
        return "coordinates"
    if not _report_rate_allowed():
        return "rate"
    try:
        public_storage.SQLiteReportStore(APP_DB_PATH).create_report(report)
    except Exception:  # noqa: BLE001 - keep storage details and submitted data out of the UI
        logging.getLogger(__name__).exception("Could not save public report")
        return "failed"
    history = st.session_state.get("dhoa_report_submissions", [])
    history.append(time.monotonic())
    st.session_state["dhoa_report_submissions"] = history
    return "sent"


def _show_report_result(result: str) -> None:
    """Render localized feedback for a report submission result key."""
    messages = {
        "sent": (st.success, T.C_REPORT_SENT),
        "coordinates": (st.warning, T.C_REPORT_INVALID_COORDS),
        "rate": (st.info, T.C_REPORT_RATE_LIMIT),
        "failed": (st.error, T.C_REPORT_FAILED),
    }
    renderer, message = messages[result]
    renderer(message)


def _honeypot_value(key: str) -> str:
    """Render a visually hidden honeypot field and return its value."""
    with st.container(key=f"dhoa_report_trap_{key}"):
        return st.text_input(
            T.C_REPORT_HONEYPOT, key=f"dhoa_report_trap_value_{key}", label_visibility="collapsed"
        )


def _render_existing_candidate_report(row: pd.Series) -> None:
    """Render the public correction form on a candidate card.

    Input: one public candidate row with ``kiln_id``, ``lat`` and ``lon``.
    Output: a localized form that creates an ``existing_candidate`` report.
    """
    kiln_id = str(row.get("kiln_id", ""))
    key = hashlib.sha256(kiln_id.encode("utf-8")).hexdigest()[:16]
    with st.expander(T.C_REPORT_EXISTING_TITLE, expanded=True):
        with st.form(f"dhoa_report_existing_{key}"):
            reason_label = st.selectbox(
                T.C_REPORT_EXISTING_REASON,
                [T.C_REPORT_REASON_LOCATION, T.C_REPORT_REASON_NOT_KILN, T.C_REPORT_REASON_OTHER],
                key=f"dhoa_report_reason_{key}",
            )
            note = st.text_area(T.C_REPORT_NOTE, key=f"dhoa_report_note_{key}", height=90)
            contact = st.text_input(T.C_REPORT_CONTACT, key=f"dhoa_report_contact_{key}")
            trap = _honeypot_value(f"existing_{key}")
            submitted = st.form_submit_button(T.C_REPORT_SUBMIT, width="stretch")
        st.caption(T.C_REPORT_PRIVACY)
        if submitted:
            reason_code = {
                T.C_REPORT_REASON_LOCATION: "wrong_location",
                T.C_REPORT_REASON_NOT_KILN: "not_a_kiln",
                T.C_REPORT_REASON_OTHER: "other",
            }[reason_label]
            result = _record_public_report(
                public_storage.NewReport(
                    kind="existing_candidate", kiln_id=kiln_id or None,
                    lat=float(row["lat"]), lon=float(row["lon"]), reason=reason_code,
                    note=note.strip(), contact=contact.strip() or None,
                ),
                row.to_frame().T,
                trap,
            )
            _show_report_result(result)


def _parse_coordinate(value: str) -> float | None:
    """Parse a finite user-entered coordinate, returning None for invalid input."""
    try:
        parsed = float(value.strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _render_missing_kiln_report(frame: pd.DataFrame) -> None:
    """Render the page-level form for a kiln missing from the map.

    Input: the public kiln frame used to derive the accepted coordinate extent.
    Output: a localized coordinate/note/photo form writing ``not_on_map`` reports.
    """
    with st.expander(T.C_REPORT_NEW_TITLE):
        extent = public_storage.extent_from_frame(frame)
        if extent is None:
            st.info(T.C_REPORT_NO_EXTENT)
            return
        with st.form("dhoa_report_missing_form"):
            latitude_text = st.text_input(T.C_REPORT_LAT, help=T.C_REPORT_COORDS_HELP)
            longitude_text = st.text_input(T.C_REPORT_LON, help=T.C_REPORT_COORDS_HELP)
            note = st.text_area(T.C_REPORT_NOTE, key="dhoa_report_missing_note", height=90)
            contact = st.text_input(T.C_REPORT_CONTACT, key="dhoa_report_missing_contact")
            photo = st.file_uploader(
                T.C_REPORT_PHOTO, type=["jpg", "jpeg", "png", "webp"],
                key="dhoa_report_missing_photo",
            )
            trap = _honeypot_value("missing")
            submitted = st.form_submit_button(T.C_REPORT_SUBMIT, width="stretch")
        st.caption(T.C_REPORT_PRIVACY)
        if submitted:
            latitude, longitude = _parse_coordinate(latitude_text), _parse_coordinate(longitude_text)
            if latitude is None or longitude is None:
                _show_report_result("coordinates")
                return
            report = public_storage.NewReport(
                kind="not_on_map", kiln_id=None, lat=latitude, lon=longitude,
                reason="not_on_map", note=note.strip(), contact=contact.strip() or None,
                photo=photo.getvalue() if photo is not None else None,
                photo_content_type=photo.type if photo is not None else None,
            )
            _show_report_result(_record_public_report(report, frame, trap))


def _render_community_summary(result: cm.SearchResult) -> None:
    """Summary card: how many kilns were found (a plain count; nothing about priority)."""
    counts = result.summary
    if result.radius_m is None:
        headline = T.C_SUMMARY_AREA_FMT.format(result.place.name, counts["total"])
    else:
        headline = T.C_SUMMARY_RADIUS_FMT.format(
            result.radius_m / 1000, result.place.name, counts["total"]
        )
    with st.container(border=True, key="dhoa_community_summary"):
        st.markdown(f"#### {headline}")


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
    nearby = kd.with_public_display_columns(result.rows)
    radius_m = result.radius_m
    _render_community_summary(result)
    if nearby.empty:
        if radius_m is None:
            st.info(T.NO_KILNS_IN_AREA_FMT.format(place.name))
        else:
            _render_community_empty(gdf, result, radius_m)
        return

    report_name = place.name
    map_column, list_column = st.columns([3, 2], gap="medium")  # map left, like the Map view
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
    with list_column:
        st.subheader(T.C_LIST_TITLE)
        _render_community_cards(nearby, show_distance=radius_m is not None)
        try:
            st.download_button(
                T.DOWNLOAD_REPORT, _community_report(report_name, nearby, radius_m or 0),
                "dhoa_community_report.pdf", "application/pdf",
                width="stretch", key="community_alert_download",
            )
        except Exception:
            logging.exception("Community PDF generation failed")
            st.error(T.REPORT_GENERATION_FAILED_PLEASE_TRY_AGAI)
    selected_report_id = st.session_state.get("dhoa_report_candidate_id")
    if selected_report_id is not None:
        candidate = nearby[nearby["kiln_id"].astype(str).eq(str(selected_report_id))]
        if candidate.empty:
            st.session_state.pop("dhoa_report_candidate_id", None)
        else:
            _render_existing_candidate_report(candidate.iloc[0])


def _debug_details(exc: BaseException) -> None:
    """Show the traceback only when the URL has ``?debug=1`` (otherwise users see the friendly card)."""
    try:
        if str(st.query_params.get("debug", "")) == "1":
            st.exception(exc)
    except Exception:  # noqa: BLE001 - debugging aid must never raise
        pass


def render_voice_guide(view: str, where: str = "popover", transcript: bool = False) -> None:
    """Spoken "how to use" guide for ``view`` (DHOA-VOICE-GUIDE v3, self-contained).

    Needs nothing from ``voice.py`` or the string catalogue beyond plain names, so an older local
    copy of those files cannot break it. Shows the heading and the written script always; audio is the
    matching pre-rendered mp3, else the browser "Read aloud" button. Any problem is shown with its real
    message instead of being hidden.
    """
    import hashlib as _hashlib
    import json as _json2
    import logging as _logging

    def _t(name: str, default: str) -> str:
        try:
            return str(getattr(T, name))
        except Exception:  # noqa: BLE001 - missing catalogue name: use app/voice_scripts.py
            pass
        try:
            try:
                from app import voice_scripts as _vs
            except ImportError:
                import voice_scripts as _vs  # type: ignore[no-redef]
            return _vs.TEXTS.get(T.get_language(), _vs.TEXTS["bn"]).get(name, default)
        except Exception:  # noqa: BLE001
            return default

    try:
        try:
            lang = T.get_language()
        except Exception:  # noqa: BLE001
            lang = "bn"
        script = _t("VOICE_COMMUNITY_SCRIPT" if view == "community" else "VOICE_INSPECTOR_SCRIPT", "")
        audio_dir = Path(__file__).resolve().parent / "static" / "audio"
        name = f"guide_{view}_{lang}.mp3"
        audio = None
        try:
            manifest = _json2.loads((audio_dir / "manifest.json").read_text(encoding="utf-8"))
            digest = _hashlib.sha256(script.strip().encode("utf-8")).hexdigest()[:16]
            if (audio_dir / name).is_file() and manifest.get(name) == digest:
                audio = audio_dir / name
        except Exception:  # noqa: BLE001 - no/bad manifest: fall back to browser voice
            audio = None
        st.markdown(f"**{_t('LISTEN_TO_THE_GUIDE', 'Listen to the guide')}**")
        if audio is not None:
            st.audio(str(audio), format="audio/mpeg")
        elif (Path(__file__).resolve().parent / "components" / "voice_guide" / "index.html").is_file():
            _voice_player(
                text=script,
                lang="bn-BD" if lang == "bn" else "en-US",
                read=_t("VOICE_READ_ALOUD", "Read aloud"),
                stop=_t("VOICE_STOP", "Stop"),
                none=_t("VOICE_NO_VOICE", "This browser has no voice for this language."),
                key=f"dhoa_voice_{where}_{view}_{lang}",
                default=None,
            )
        if script:
            with st.expander(_t("VOICE_TRANSCRIPT", "Read the text")):
                st.markdown(script)
        else:
            st.caption("Voice guide text is missing from the string catalogue (VOICE_*_SCRIPT).")
    except Exception as exc:  # noqa: BLE001 - must never break the page
        _logging.getLogger(__name__).exception("Voice guide failed")
        st.caption(f"Voice guide unavailable ({type(exc).__name__}: {exc})")


def render_community_view(gdf: gpd.GeoDataFrame) -> None:
    """Render the Community view as three steps on one screen.

    Input schema: prepared kiln frame (lat/lon, district, upazila, class,
    priority_band, optional nearest_place). Output schema: 1) one searchable
    place picker with data-backed suggestions and typed-name geocoding, plus
    "use my location", 2) radius choices 1/2/5/10 km (default 5; whole-area
    choices list every kiln), 3) a summary, list, map and PDF/CSV downloads,
    or a clear next step when nothing is found. No page reload anywhere.
    """
    st.markdown(
        "<style>div[class*='st-key-dhoa_report_trap_']{display:none!important}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='dhoa-section-title'>{T.FIND_KILNS_NEAR_YOU}</div>", unsafe_allow_html=True)
    place = _render_community_inputs(gdf)
    _render_community_results(gdf, place)
    _render_missing_kiln_report(gdf)


def _popup_content(row: Mapping[str, object]) -> dict[str, Any]:
    """Build sanitized Bangla display fields shared by all kiln popups.

    Input schema: one kiln row with optional type, place, priority, rule,
    coordinate, and detection fields. Output schema: sanitized display values.
    """
    def present(value: object, fallback: str | None = None) -> str:
        fallback = T.NO_DATA if fallback is None else fallback
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
        f".dhoa-popup{{width:290px;color:{DESIGN_COLORS['popup_text']};line-height:1.6}}"
        f".dhoa-popup hr{{border:0;border-top:1px solid {DESIGN_COLORS['popup_rule']};opacity:.45;margin:.45rem 0}}"
        f".dhoa-popup .badge{{background:{DESIGN_COLORS['popup_badge']};color:{DESIGN_COLORS['popup_text']};"
        "padding:.1rem .5rem;border-radius:999px;font-weight:700}"
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
    color = PRIORITY_TEXT_COLORS.get(str(value), DESIGN_COLORS["text_muted"])
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


def _init_language() -> None:
    """Pick the starting language once per session (``?lang=en`` or Bangla)."""
    if st.session_state.get(T.LANGUAGE_KEY) in T.LANGUAGES:
        return
    requested = str(st.query_params.get("lang", "")).lower()
    st.session_state[T.LANGUAGE_KEY] = requested if requested in T.LANGUAGES else T.DEFAULT_LANGUAGE


def _render_language_toggle() -> None:
    """Render the bn/en switch; the choice lives in session state and the URL."""
    with st.container(key="dhoa_lang_toggle"):  # styled as a pill by styles.py
        st.radio(
            "Language / ভাষা",
            T.LANGUAGES,
            format_func=lambda code: T.LANGUAGE_NAMES[code],
            key=T.LANGUAGE_KEY,
            horizontal=True,
            label_visibility="collapsed",
        )
    if st.query_params.get("lang") != st.session_state.get(T.LANGUAGE_KEY):
        st.query_params["lang"] = st.session_state.get(T.LANGUAGE_KEY, T.DEFAULT_LANGUAGE)


def _nav_label(view: str) -> str:
    """Translated top-navigation label for a view key."""
    return {
        "overview": T.NAV_OVERVIEW,
        "inspector": getattr(T, "NAV_INSPECTOR", "🔒 পরিদর্শক পোর্টাল"),
        "community": T.NAV_NEAR_ME, "about": T.NAV_ABOUT,
    }[view]


def _public_text(name: str) -> str:
    """Return a public label with compatibility text for older Cloud catalogues."""
    fallbacks = {
        "PUB_HERO_MISSION": "স্যাটেলাইট ছবি থেকে শনাক্ত করা ইটভাটার প্রার্থী, মানচিত্রে দেখানো।",
        "PUB_HERO_SUB": "আপনার বাড়ি বা গ্রামের কাছের ইটভাটার প্রার্থীগুলো খুঁজে নিন।",
        "PUB_OV_DISTRICTS_HINT": "জেলার নামে চাপলে সেই জেলার ইটভাটার প্রার্থী দেখা যাবে।",
        "PUB_OV_OPEN_DISTRICT_FMT": "{0}-এর ইটভাটার প্রার্থী দেখুন",
        "PUB_HOW_3_HEAD": "কাছের ভাটা খোঁজা",
        "PUB_HOW_3_BODY": "প্রার্থীদের মানচিত্রে দেখানো হয়, যাতে কোনো এলাকার কাছের ভাটাগুলো খুঁজে নেওয়া যায়।",
    }
    return getattr(T, name, fallbacks[name])


def _go_to_view(view: str) -> None:
    """``on_click`` callback for the hero buttons: switch the top navigation to ``view``."""
    if view in hero.VIEW_MODES:
        st.session_state["dhoa_view_mode"] = view


def render_header(gdf: gpd.GeoDataFrame) -> str:
    """Render the Dhoa title, language switch and top navigation; return the active view key.

    Output: one of ``hero.VIEW_MODES`` (``overview``, ``inspector``, ``community``, ``about``).
    The headline metrics live in the Overview hero only, so they are not repeated on every view.
    """
    view_options = list(hero.VIEW_MODES)
    if st.session_state.get("dhoa_view_mode") not in view_options:
        st.session_state["dhoa_view_mode"] = hero.DEFAULT_VIEW
    _seed("dhoa_view_mode", st.session_state["dhoa_view_mode"])
    tool_view = st.session_state["dhoa_view_mode"] in ("inspector", "community")
    # One row: title | navigation | help | language. The tool views (map, near me) keep the
    # header to ~50 px so the map is on screen without scrolling; hero views keep the subtitle.
    with st.container(key="dhoa_header_row"):
        title_col, nav_col, help_col, lang_col = st.columns(
            [1.1, 7.2, 1.7, 1.8], vertical_alignment="center", gap="small"
        )
        with title_col:
            st.markdown(f"<h1 class='dhoa-brand-title'>{html.escape(DASHBOARD_TITLE)}</h1>", unsafe_allow_html=True)
        with nav_col:
            mode = st.segmented_control(
                T.CHOOSE_VIEW,
                view_options,
                format_func=_nav_label,
                key=_wkey("dhoa_view_mode"), width="stretch",
                on_change=_commit_view_mode,
                label_visibility="collapsed",
            )
        if mode in view_options:
            st.session_state["dhoa_view_mode"] = mode
        selected_mode = st.session_state["dhoa_view_mode"]
        with help_col:
            if selected_mode == "community" or (selected_mode == "inspector" and roles.is_staff()):
                with st.popover(T.HOW_TO_USE, icon=":material/help:", width="stretch"):
                    st.markdown(T.HELP_COMMUNITY if selected_mode == "community" else T.HELP_INSPECTOR)
                    render_voice_guide(selected_mode, "popover")
        with lang_col:
            _render_language_toggle()
    if selected_mode not in ("inspector", "community"):
        st.caption(T.BANGLADESH_BRICK_KILN_MONITORING_DASHBOA)
        st.divider()
    return selected_mode


def render_overview(frame: pd.DataFrame) -> None:
    """Public landing view: mission line, three numbers, the Kilns near me button, "How it works"
    and a plain district list.

    Input: the PUBLIC frame (``get_public_data``). Output: the hero (kiln candidates, districts
    covered, data date), one primary button (staff also get a shortcut to the portal map), a
    collapsed "How it works" and the district counts. No priority, High count or kiln-type split.
    """
    counts = hero.hero_counts(frame)
    metrics = (
        (f"{counts['total']:,}", METRIC_LABELS["total_candidates"]),
        (f"{counts['districts']:,}", T.HERO_METRIC_DISTRICTS),
        (_data_date_label(dashboard_kilns_file()), METRIC_LABELS["last_updated"]),
    )
    st.markdown(
        hero.hero_html(_public_text("PUB_HERO_MISSION"), _public_text("PUB_HERO_SUB"), metrics),
        unsafe_allow_html=True,
    )
    with st.container(key="dhoa_action_row"):
        if roles.is_staff():
            left, right = st.columns(2, gap="small")
            left.button(T.HERO_CTA_NEAR_ME, key="dhoa_hero_near", type="primary", width="stretch",
                        on_click=_go_to_view, args=("community",))
            right.button(T.HERO_CTA_MAP, key="dhoa_hero_map", width="stretch",
                         on_click=_go_to_view, args=("inspector",))
        else:
            st.button(T.HERO_CTA_NEAR_ME, key="dhoa_hero_near", type="primary", width="stretch",
                      on_click=_go_to_view, args=("community",))
    with st.expander(T.HOW_TITLE, expanded=False):
        st.markdown(_how_it_works_html(public=True), unsafe_allow_html=True)
    render_public_districts(frame)


def render_public_districts(frame: pd.DataFrame) -> None:
    """Public Overview body: one count per district; each name opens Kilns near me for it."""
    stats = ov.public_district_counts(frame)
    with st.container(key="dhoa_overview_charts"):
        st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.OV_DISTRICTS_TITLE)}</div>",
                    unsafe_allow_html=True)
        if stats.empty:
            st.caption(T.OV_NO_DATA)
            return
        st.caption(_public_text("PUB_OV_DISTRICTS_HINT"))
        maximum = int(stats["total"].max())
        for row in stats.to_dict("records"):
            name_col, bar_col = st.columns([2, 5], vertical_alignment="center", gap="small")
            name_col.button(
                _district_label(row["district"]), key=f"dhoa_ov_open_{row['district']}",
                help=_public_text("PUB_OV_OPEN_DISTRICT_FMT").format(_district_label(row["district"])),
                width="stretch", on_click=_open_district_near_me, args=(str(row["district"]),),
            )
            bar_col.markdown(
                ov.public_district_bar_html(row["total"], maximum, T.OV_SERIES_TOTAL),
                unsafe_allow_html=True,
            )


def _open_district_near_me(district: str) -> None:
    """``on_click`` callback: open Kilns near me with ``district`` chosen (no page reload)."""
    st.session_state["community_place_key"] = cm.place_key(cm.KIND_DISTRICT, district)
    st.session_state["community_origin"] = None
    st.session_state.pop("community_notice", None)
    st.session_state["community_selected_kiln_id"] = None
    st.session_state["dhoa_view_mode"] = "community"


def _open_district(district: str) -> None:
    """``on_click`` callback: open the Map view filtered to ``district`` (no page reload)."""
    st.session_state["filter_district"] = district
    st.session_state["filter_upazila"] = ALL_AREAS
    _drop_widget_state("filter_upazila", "filter_district")
    st.session_state["selected_kiln_id"] = None
    st.session_state["dhoa_view_mode"] = "inspector"
    st.session_state["dhoa_portal_tab"] = "map"
    if not roles.is_staff():  # the staff map is never opened for the public
        st.session_state["dhoa_view_mode"] = "community"


def render_overview_charts(gdf: pd.DataFrame) -> None:
    """Inspector Dashboard body (staff only): district bars (each opens the portal map), top upazilas, kiln-type split.

    Input: the prepared frame. Output: bars with the value printed at the end of every
    bar (colour is never the only cue: High priority also carries the triangle glyph), a
    plain table and a share bar. Every number is a groupby of the frame (see ``overview``).
    """
    if not roles.is_staff():  # High series, upazila table and type split are staff-only
        return
    stats = ov.district_stats(gdf)
    with st.container(key="dhoa_overview_charts"):
        st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.OV_DISTRICTS_TITLE)}</div>",
                    unsafe_allow_html=True)
        if stats.empty:
            st.caption(T.OV_NO_DATA)
        else:
            st.caption(T.OV_DISTRICTS_HINT)
            st.markdown(ov.bars_legend_html(T.OV_SERIES_TOTAL, T.OV_SERIES_HIGH), unsafe_allow_html=True)
            maximum = int(stats["total"].max())
            for row in stats.to_dict("records"):
                name_col, bar_col = st.columns([2, 5], vertical_alignment="center", gap="small")
                name_col.button(
                    _district_label(row["district"]), key=f"dhoa_ov_open_{row['district']}",
                    help=T.OV_OPEN_DISTRICT_FMT.format(_district_label(row["district"])),
                    width="stretch", on_click=_open_district, args=(str(row["district"]),),
                )
                bar_col.markdown(
                    ov.district_bar_html(row, maximum, T.OV_SERIES_TOTAL, T.OV_SERIES_HIGH),
                    unsafe_allow_html=True,
                )
        upazilas = ov.upazila_stats(gdf, limit=10)
        st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.OV_UPAZILAS_TITLE)}</div>",
                    unsafe_allow_html=True)
        if upazilas.empty:
            st.caption(T.OV_NO_DATA)
        else:
            table = pd.DataFrame({
                T.COL_UPAZILA: upazilas["upazila"].tolist(),
                T.DISTRICT: [_district_label(d) if d else "" for d in upazilas["district"]],
                T.OV_COL_CANDIDATES: upazilas["total"].tolist(),
                T.OV_COL_HIGH: upazilas["high"].tolist(),
            })
            st.dataframe(table, hide_index=True, width="stretch")
        st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.OV_TYPES_TITLE)}</div>",
                    unsafe_allow_html=True)
        parts = ov.type_split(gdf)
        if parts:
            labels = {"Zigzag": T.ZIGZAG_KILN, "FCBK": T.FIXED_CHIMNEY_KILN, "other": T.OV_TYPE_OTHER}
            st.markdown(ov.type_split_html(parts, labels, T.OV_SHARE_FMT), unsafe_allow_html=True)
        else:
            st.caption(T.OV_NO_DATA)


def _how_it_works_html(public: bool = False) -> str:
    """The "How it works" panel: four steps for staff; for the public three steps with no rule check or ranking."""
    if public:
        return trust.steps_html(T.HOW_TITLE, (
            (T.HOW_1_HEAD, T.HOW_1_BODY), (T.HOW_2_HEAD, T.HOW_2_BODY),
            (_public_text("PUB_HOW_3_HEAD"), _public_text("PUB_HOW_3_BODY")),
        ))
    return trust.steps_html(T.HOW_TITLE, (
        (T.HOW_1_HEAD, T.HOW_1_BODY), (T.HOW_2_HEAD, T.HOW_2_BODY),
        (T.HOW_3_HEAD, T.HOW_3_BODY), (T.HOW_4_HEAD, T.HOW_4_BODY),
    ))


def render_about(gdf: pd.DataFrame | None = None) -> None:
    """About view: purpose, how it works, data date and sources, coverage, team, methodology link."""
    config = (load_config() or {}).get("dashboard")
    st.markdown(
        f"<div class='dhoa-about'><div class='dhoa-hero-title' role='heading' aria-level='2'>"
        f"{html.escape(T.ABOUT_TITLE)}</div><p>{html.escape(T.ABOUT_BODY)}</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(_how_it_works_html(public=True), unsafe_allow_html=True)
    counts = hero.hero_counts(gdf) if gdf is not None else {"total": 0, "districts": 0}
    rows = [
        (T.ABOUT_DATA_DATE, _data_date_label(dashboard_kilns_file())),
        (T.ABOUT_SOURCES, T.ABOUT_SOURCES_VALUE),
    ]
    if counts["total"]:
        rows.append((T.ABOUT_COVERAGE, T.ABOUT_COVERAGE_FMT.format(counts["districts"], counts["total"])))
    names = trust.team_names(config)
    if names:
        rows.append((T.ABOUT_TEAM, ", ".join(names)))
    st.markdown(trust.facts_html(T.ABOUT_DATA_TITLE, rows), unsafe_allow_html=True)
    st.markdown(
        f"<section class='dhoa-about-methods'><h3>{html.escape(T.ABOUT_METHODS_TITLE)}</h3>"
        f"<p>{html.escape(T.ABOUT_METHODS_BODY)}</p></section>"
        f"<section class='dhoa-about-privacy'><h3>{html.escape(T.ABOUT_PRIVACY_TITLE)}</h3>"
        f"<p>{html.escape(T.ABOUT_PRIVACY_BODY)}</p></section>",
        unsafe_allow_html=True,
    )
    link = trust.methodology_url(config)
    if link:
        st.link_button(T.ABOUT_METHODOLOGY, link, width="content")


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


def _commit_view_mode() -> None:
    """``on_change`` callback for the view switch (a deselect keeps the current view)."""
    value = st.session_state.get(_wkey("dhoa_view_mode"))
    if value in hero.VIEW_MODES:
        st.session_state["dhoa_view_mode"] = value


def _wkey(name: str) -> str:
    """Widget key for ``name`` in the active language.

    Widgets whose options are shown through a translating ``format_func`` get a
    language-suffixed key, so Streamlit mounts a brand-new widget when the
    language changes (a widget re-used under the same key keeps showing the
    previous language's option text). The value that matters is kept under the
    language-neutral name ``name`` (always canonical: ``High``, ``Dhaka``,
    ``street`` ...); ``_seed`` copies it into the widget and ``_commit`` copies
    the user's choice back.
    """
    return f"w_{name}@{T.get_language()}"


def _seed(name: str, value: Any) -> str:
    """Set the widget for ``name`` to the canonical ``value``; return its key."""
    key = _wkey(name)
    st.session_state[key] = value
    return key


def _commit(name: str) -> None:
    """``on_change`` callback: store the widget's choice under the canonical name."""
    st.session_state[name] = st.session_state.get(_wkey(name))


def _commit_radius() -> None:
    """``on_change`` callback for the radius control (a deselect keeps the old radius)."""
    value = st.session_state.get(_wkey("community_radius_m"))
    st.session_state["community_radius_m"] = int(value) if value else cm.DEFAULT_RADIUS_M


_FORM_FILTERS = ("filter_upazila", "filter_priority", "filter_kiln_type")


def _drop_widget_state(*names: str) -> None:
    """Forget the widget copies of ``names`` so the next run re-seeds them from canonical state."""
    for name in names:
        st.session_state.pop(_wkey(name), None)


def _pull_form_values() -> None:
    """Copy the submitted filter-form widget values into canonical state.

    Widgets inside ``st.form`` cannot have ``on_change`` callbacks, so the
    values are read from the widget keys at the start of the run (before
    ``_seed`` would overwrite them). Absent keys (first run, language switch,
    a reset) are skipped and re-seeded from canonical state instead.
    """
    for name in _FORM_FILTERS:
        key = _wkey(name)
        if key in st.session_state:
            st.session_state[name] = st.session_state[key]


def _on_district_change() -> None:
    """A new district clears the dependent area."""
    _commit("filter_district")
    st.session_state["filter_upazila"] = ALL_AREAS
    _drop_widget_state("filter_upazila")


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
    st.session_state["filter_priority"] = ["High", "Medium", "Low"]
    st.session_state["filter_kiln_type"] = ALL_KILN_TYPES
    _drop_widget_state("filter_district", *_FORM_FILTERS)


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
            district_values = (
                sorted(gdf["district"].dropna().astype(str).unique().tolist())
                if "district" in gdf else []
            )
            district_options = [ALL_DISTRICTS, *district_values]
            if st.session_state.get("filter_district") not in district_options:
                st.session_state["filter_district"] = ALL_DISTRICTS
            _seed("filter_district", st.session_state["filter_district"])
            filters["district"] = st.selectbox(
                T.DISTRICT,
                district_options,
                format_func=lambda value: (
                    T.ALL_DISTRICTS
                    if value == ALL_DISTRICTS
                    else _district_label(value)
                ),
                key=_wkey("filter_district"),
                on_change=_on_district_change,
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
            _pull_form_values()
            if st.session_state.get("filter_upazila") not in upazila_options:
                st.session_state["filter_upazila"] = ALL_AREAS
            _seed("filter_upazila", st.session_state["filter_upazila"])
            # Priority options are canonical English keys; only their labels are translated,
            # so the stored selection survives a language switch.
            _priority_opts = ["High", "Medium", "Low"]
            _priority_text = {"High": T.HIGH, "Medium": T.MEDIUM, "Low": T.LOW}
            _stored_p = st.session_state.get("filter_priority", _priority_opts)
            # Map any spelling (old Bangla/English labels) to canonical keys; never keep an unknown one.
            _canonical_p = [v for v in kd.make_filter_key(priorities=_stored_p).priorities] if _stored_p else _priority_opts
            st.session_state["filter_priority"] = _canonical_p
            _seed("filter_priority", _canonical_p)
            type_column = "class" if "class" in gdf.columns else "class_name"
            available_types = (
                sorted(gdf[type_column].dropna().astype(str).unique().tolist())
                if type_column in gdf.columns else []
            )
            type_options = [ALL_KILN_TYPES, *available_types]
            if st.session_state.get("filter_kiln_type") not in type_options:
                st.session_state["filter_kiln_type"] = ALL_KILN_TYPES
            _seed("filter_kiln_type", st.session_state["filter_kiln_type"])
            with st.form("dhoa_inspector_filters", border=False):
                filters["upazila"] = st.selectbox(
                    T.AREA_THANA,
                    upazila_options,
                    format_func=lambda value: T.ALL_AREAS if value == ALL_AREAS else value,
                    key=_wkey("filter_upazila"),
                    disabled=not district_selected,
                )
                filters["priorities"] = st.pills(
                    T.PRIORITY,
                    _priority_opts,
                    selection_mode="multi",
                    format_func=lambda value: f"{kd.PRIORITY_GLYPHS[value]} {_priority_text[value]}",
                    key=_wkey("filter_priority"),
                )
                filters["kiln_type"] = st.selectbox(
                    T.KILN_TYPE,
                    type_options,
                    format_func=lambda value: T.ALL_TYPES if value == ALL_KILN_TYPES else _type_label(value),
                    key=_wkey("filter_kiln_type"),
                )
                st.form_submit_button(T.APPLY_FILTERS, type="primary", width="stretch")

            # The one filter computation of this rerun; everything below and the
            # main area read ``filters["visible"]`` instead of filtering again.
            visible = get_filtered_gdf(gdf)
            filters["visible"] = visible
        if mode == "inspector":
            st.button(
                T.RESET_FILTERS,
                key="reset_inspector_filters",
                on_click=_reset_inspector_filters,
                width="stretch",
            )
        _contact_info = _contact()
        with st.container(key="dhoa_sidebar_contact"):
            st.markdown(
                T.HOTLINE_LINE_FMT.format(trust.localise_digits(_contact_info["number"], T.get_language()))
                + " | [doe.gov.bd](https://doe.gov.bd)"
                if _contact_info["number"] else T.DOE_WEB_LINE
            )
    return filters


def _metres_text(value: float) -> str:
    """Format a metre distance the way the list does (m below 1 km, km above)."""
    return T.KM_FMT.format(value / 1000) if value >= 1000 else T.M_FMT.format(value)


def _render_distance_grid(row: pd.Series) -> None:
    """Render the icon grid of distances with threshold dots (thresholds from rules.yaml)."""
    entries = ins.distance_rows(row, _siting_rules())
    if not entries:
        return
    labels = {entry["feature"]: str(kd._FEATURE_LABELS.get(entry["feature"], entry["feature"])) for entry in entries}
    distances = {
        entry["feature"]: T.NO_DATA if entry["distance_m"] is None else _metres_text(entry["distance_m"])
        for entry in entries
    }
    states = {"unknown": T.DETAIL_STATE_UNKNOWN}
    for entry in entries:
        if entry["buffer_m"] is not None:
            limit = _metres_text(entry["buffer_m"])
            states[f"{entry['feature']}:inside"] = T.DETAIL_WITHIN_FMT.format(limit)
            states[f"{entry['feature']}:outside"] = T.DETAIL_BEYOND_FMT.format(limit)
    st.markdown(f"**{T.DETAIL_DISTANCES_TITLE}**")
    st.markdown(ins.distance_grid_html(entries, labels, distances, states), unsafe_allow_html=True)


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
        _render_distance_grid(row)
        with st.container(key="dhoa_action_row"):
            columns = st.columns(3)
        columns[0].link_button(T.DIRECTIONS_2, f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving", width="stretch")
        columns[1].link_button(T.STREET_VIEW, f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},3a,90y,0h,90t/data=!3m1!1e3", width="stretch")
        columns[2].link_button(T.GOOGLE_EARTH, f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y", width="stretch")


def _render_public_candidate(row: pd.Series) -> None:
    """Public detail card for a clicked kiln: id, type, area, detection status, coordinates, links.

    Input: one row of the PUBLIC frame. Output: a bordered card with no priority, no rule
    signal, no distance breakdown and no report download.
    """
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", T.NO_DATA))
    detection = T.STATUS_NEW if row.get("detection_status") == kd.NEW_CANDIDATE_STATUS else T.STATUS_KNOWN
    with st.container(border=True, key="dhoa_detail_card"):
        st.subheader(T.SELECTED_KILN_TITLE_FMT.format(candidate_id))
        left, right = st.columns(2)
        with left:
            st.markdown(f"**{T.KILN_TYPE_2}:** {_type_label(row.get('class'))}")
            st.markdown(f"**{T.AREA}:** {_area_display_name(row)}")
        with right:
            st.markdown(f"**{T.DETECTION_STATUS}:** {detection}")
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
        report = _report_from_json(
            json.dumps(report_fields, default=_json_default, sort_keys=True), T.get_language()
        )
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
#: Zoom level from which clusters split into individual kilns. Raise it to keep dense
#: areas grouped for longer (each +1 = one more zoom step before they split); lower it to
#: split earlier. Zooming back out below it re-forms the clusters at the same level.
#: Must stay <= SELECTED_ZOOM so a kiln picked from the list is always shown on its own.
CLUSTER_DISABLE_ZOOM = 13
_MARKER_OPTIONS = {"disableClusteringAtZoom": CLUSTER_DISABLE_ZOOM}


def _public_cluster_icon_js() -> str:
    """Return a single-colour cluster icon for public Near me maps.

    Input: Leaflet MarkerCluster's cluster object with ``getChildCount``.
    Output: an icon-create JavaScript function using the same neutral colour as
    public kiln markers, with the cluster count as plain text.
    """
    color = DESIGN_COLORS["unclassified"]
    return (
        "function(cluster){var n=cluster.getChildCount();"
        "return L.divIcon({className:'dhoa-cluster-neutral',iconSize:new L.Point(38,38),"
        "html:\"<div style='background:" + color + ";color:#fff;width:34px;height:34px;"
        "border:2px solid #fff;border-radius:50%;display:flex;align-items:center;"
        "justify-content:center;font-weight:700;box-shadow:0 1px 4px #3338'>\"+n+\"</div>\"});}"
    )


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
                DESIGN_COLORS["unclassified"],
            ],
            "outline": DESIGN_COLORS["marker_outline"],
            "halo": DESIGN_COLORS["marker_halo"],
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
html:"<svg width='"+S+"' height='"+S+"' viewBox='0 0 22 22'>"+sh[row[2]]+" fill='none' stroke='"+D.halo+"' stroke-width='3.6' stroke-linejoin='round'/>"+sh[row[2]]+" fill='"+c+"' stroke='"+D.outline+"' stroke-width='1.3' stroke-linejoin='round'/></svg>"});
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


def _public_marker_callback_js(payload: Mapping[str, Any], radius: int = 8) -> str:
    """Return the JS factory for the PUBLIC map: one neutral marker shape and colour.

    Input: ``kiln_data.public_marker_payload`` output (rows are ``[lat, lon, type, area]``).
    Output: a JS function expression for ``FastMarkerCluster``. Each marker has a hover
    tooltip (type | area) and, on click, a light popup (type, area, coordinates, Google Maps
    directions / map / Earth links) built in the browser. No band, colour class or
    rule-signal field exists in the payload or in this script.
    """
    lookups = json.dumps(
        {
            "color": DESIGN_COLORS["unclassified"],
            "outline": DESIGN_COLORS["marker_outline"],
            "halo": DESIGN_COLORS["marker_halo"],
            "types": payload["types"],
            "areas": payload["areas"],
            "labels": {
                "kiln": html.escape(T.KILN_CANDIDATE),
                "area": html.escape(T.AREA),
                "directions": html.escape(T.DIRECTIONS),
                "map": html.escape(T.MAP),
            },
        },
        ensure_ascii=False,
    )
    factory = r"""(function(){var D=__LOOKUPS__;
return function(row){var S=__SIZE__;
var ic=L.divIcon({className:'dhoa-pin',iconSize:[S,S],iconAnchor:[S/2,S/2],
html:"<svg width='"+S+"' height='"+S+"' viewBox='0 0 22 22'><circle cx='11' cy='11' r='9' fill='none' stroke='"+D.halo+"' stroke-width='3.6'/><circle cx='11' cy='11' r='9' fill='"+D.color+"' stroke='"+D.outline+"' stroke-width='1.3'/></svg>"});
var m=L.marker([row[0],row[1]],{icon:ic,riseOnHover:true});
m.bindTooltip(D.types[row[2]]+" | "+D.areas[row[3]],{sticky:true});
var la=row[0],lo=row[1],q=la.toFixed(6)+','+lo.toFixed(6),g='https://www.google.com/maps',
h="<div class='dhoa-popup'><div class='badges'><span class='badge'>"+D.types[row[2]]+"</span></div>"
+"<strong>"+D.labels.kiln+" · "+D.areas[row[3]]+"</strong><hr>"
+"📍 "+D.labels.area+": "+D.areas[row[3]]+"<br>"+la.toFixed(5)+", "+lo.toFixed(5)+"<hr>"
+"<div class='popup-actions'>"
+"<a href='"+g+"/dir/?api=1&destination="+q+"&travelmode=driving' target='_blank' rel='noopener'>🗺️ "+D.labels.directions+"</a>"
+"<a href='"+g+"?q="+q+"' target='_blank' rel='noopener'>📍 "+D.labels.map+"</a>"
+"<a href='https://earth.google.com/web/@"+la.toFixed(6)+","+lo.toFixed(6)+",500a,500d,35y' target='_blank' rel='noopener'>🌍 Google Earth</a>"
+"</div></div>";
m.on('click',function(e){var mp=e.target._map;if(!mp){return;}
L.popup({maxWidth:300,autoPan:true}).setLatLng(e.target.getLatLng()).setContent(h).openOn(mp);});
return m;};})()"""
    return factory.replace("__LOOKUPS__", lookups).replace("__SIZE__", str(int(radius) * 2 + 8))


def _new_map(tile: str, bounds: list[list[float]] | None) -> folium.Map:
    """Create an empty map with the two basemaps, fitted to ``bounds`` when given.

    The view is fixed here (Leaflet ``fitBounds`` at creation); after that only
    the user, or an explicit ``center``/``zoom`` request, moves it.
    """
    map_view = folium.Map(
        location=DISTRICT_CENTERS["All Districts"], zoom_start=DEFAULT_ZOOM,
        control_scale=True, tiles=None, world_copy_jump=False,
    )
    # folium 0.20 drops min_zoom/max_zoom when ``tiles=None``, which left the map with no zoom
    # limits (zoom out to the whole world, zoom in past the tiles = stretched, blurry imagery).
    map_view.options["minZoom"] = DEFAULT_ZOOM - 1
    map_view.options["maxZoom"] = SELECTED_ZOOM + 3
    _add_map_base_layers(map_view, with_layer_control=False, tile=tile)
    # The density heatmap is sent later through ``feature_group_to_add``, which only ships the
    # layer's own JS, not the leaflet-heat plugin it needs; without this the layer fails
    # silently (``L.heatLayer`` is undefined). Load the plugin with the base map instead.
    for js_name, js_url in getattr(HeatMap, "default_js", []):
        map_view.add_js_link(js_name, js_url)
    if bounds:
        map_view.fit_bounds(bounds, max_zoom=SELECTED_ZOOM, padding=(24, 24))
    map_name = map_view.get_name()
    folium.Element(
        f"""
<script>
(function () {{
    var map = {map_name};
    function resizeMap() {{
        map.invalidateSize({{pan: false, animate: false}});
    }}
    window.addEventListener("resize", resizeMap);
    setTimeout(resizeMap, 0);
    setTimeout(resizeMap, 250);
}})();
</script>
"""
    ).add_to(map_view.get_root().html)
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


@st.cache_data(show_spinner=False, max_entries=32)
def _cached_public_marker_payload(version: str, key: tuple, _frame: pd.DataFrame) -> dict[str, Any]:
    """Cache the PUBLIC compact marker rows per (public data version, search key).

    Plain lists/dicts only (never a ``folium.Map``). The key carries ``"public"`` and the
    version ends in ``-public``, so it can never collide with a staff payload.
    """
    return kd.public_marker_payload(_frame)


def _marker_map(
    frame: pd.DataFrame,
    tile: str,
    bounds: list[list[float]] | None,
    radius: int = 8,
    payload: dict[str, Any] | None = None,
    public: bool = False,
) -> folium.Map:
    """Build a *fresh* base map with one clustered marker layer for ``frame``.

    ``payload`` is the cached ``kd.marker_payload`` output; a new ``folium.Map``
    is created on every call because ``st_folium`` mutates the object it renders.
    """
    if payload is None:
        payload = kd.public_marker_payload(frame) if public else kd.marker_payload(frame, _siting_rules())
    map_view = _new_map(tile, bounds if bounds is not None else kd.bounds_of(frame))
    if payload["rows"]:
        callback = _public_marker_callback_js(payload, radius) if public else _marker_callback_js(payload, radius)
        FastMarkerCluster(
            payload["rows"], callback=callback,
            options=dict(_MARKER_OPTIONS),
            icon_create_function=_public_cluster_icon_js() if public else None,
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


def _selected_feature_group(
    latitude: float | None, longitude: float | None, heat: list[list[float]] | None = None
) -> folium.FeatureGroup | None:
    """Return the overlay group sent through ``feature_group_to_add`` (no remount).

    It holds the highlight ring for the selected kiln and/or the optional density
    heatmap. Returns ``None`` when there is nothing to draw.
    """
    if latitude is None and not heat:
        return None
    group = folium.FeatureGroup(name="dhoa_overlay")
    if heat:
        HeatMap(heat, radius=18, blur=22, min_opacity=0.25).add_to(group)
    if latitude is not None and longitude is not None:
        # white under-ring + accent ring: reads on light and satellite tiles, never a black blob
        folium.CircleMarker(
            [latitude, longitude], radius=13, color=DESIGN_COLORS["marker_halo"], weight=7,
            fill=False, interactive=False,
        ).add_to(group)
        folium.CircleMarker(
            [latitude, longitude], radius=13, color=tokens.COLORS["selected"], weight=3,
            fill=False, interactive=False,
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
    focus = st.session_state.pop("dhoa_report_focus", None)
    if isinstance(focus, (list, tuple)) and len(focus) == 2:
        st.session_state["dhoa_map_view"] = {
            "map_key": map_key, "center": [float(focus[0]), float(focus[1])], "zoom": SELECTED_ZOOM,
        }
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
    map_panel, list_panel = st.columns([3, 2], gap="medium")  # map first: it is the priority
    with list_panel:
        head_text, head_csv = st.columns([3, 2], vertical_alignment="center", gap="small")
        with head_text:
            st.markdown(f"**{T.PRIORITY_LIST}**  \n{T.CANDIDATES_MATCH_FMT.format(len(list_candidates))}")
        with head_csv:
            st.download_button(
                T.DOWNLOAD_FILTERED_CSV,
                _inspector_csv_bytes(visible, gdf),
                _export_filename(
                    district=None if filters.get("district") in (None, ALL_DISTRICTS) else filters["district"],
                    area=None if filters.get("upazila") in (None, ALL_AREAS) else filters["upazila"],
                    kiln_type="all" if filters.get("kiln_type") in (None, ALL_KILN_TYPES) else filters["kiln_type"],
                    rule_signals=["all"],
                    radius_m=None,
                    extension="csv",
                ),
                "text/csv",
                width="stretch",
                key="sidebar_export_list",
            )
        list_columns, list_rows, list_kiln_ids = _list_payload(list_candidates, gdf)
        list_choice = _priority_candidate_list(
            columns=list_columns,
            rows=list_rows,
            kiln_ids=list_kiln_ids,
            select_label=T.VIEW_KILN,
            aria_label=T.LIST_ARIA_LABEL,
            aria_select_fmt=T.LIST_ARIA_SELECT_FMT,
            lang=T.get_language(),
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
    with map_panel, st.container(key="dhoa_map_sticky"):
        with st.container(key="dhoa_map_toolbar"):
            bar_legend, bar_heat, bar_tile = st.columns([5, 3, 3], vertical_alignment="center", gap="small")
            with bar_legend:
                st.markdown(
                    ins.legend_html(
                        T.LEGEND_TITLE,
                        {"High": T.HIGH, "Medium": T.MEDIUM, "Low": T.LOW},
                        "",  # the summary strip above already carries T.PRIORITY_NOTE
                    ),
                    unsafe_allow_html=True,
                )
            with bar_heat:
                st.toggle(T.HEAT_TOGGLE, key="dhoa_heatmap", help=T.HEAT_HELP)
            with bar_tile:
                _render_map_type_filter()
        selected_id_for_report = st.session_state.get("selected_kiln_id")
        selected_for_report = (
            visible[visible["kiln_id"].astype(str).eq(str(selected_id_for_report))]
            if selected_id_for_report is not None
            else visible.iloc[0:0]
        )
        try:
            with st.spinner(T.LOADING_MAP):
                _m = build_map(gdf, filters, filtered=visible)
        except Exception as _exc:
            logging.exception("Inspector map rendering failed")
            st.markdown(trust.state_html("error", T.STATE_ERROR_TITLE, T.COULD_NOT_RENDER_THE_MAP), unsafe_allow_html=True)
            if st.button(T.STATE_RETRY, key="dhoa_retry_map"):
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
            highlight = _selected_feature_group(
                None if selected_for_report.empty else float(selected_for_report.iloc[0]["lat"]),
                None if selected_for_report.empty else float(selected_for_report.iloc[0]["lon"]),
                ins.heat_points(visible) if st.session_state.get("dhoa_heatmap") else None,
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
        # Below the map (not above it) so the map stays at the top of the screen.
        if selected_for_report.empty:
            st.caption(f"{T.SELECT_A_CANDIDATE_FROM_THE_LIST_OR_MAP_} {T.MARKER_COLOUR_SHOWS_PRIORITY_BOLD_BORDER}")
        else:
            _render_report_download(selected_for_report.iloc[0])
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
            if roles.is_staff():
                _render_work_controls(selected.iloc[0])


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
        (f"{counts['total']:,}", T.SUMMARY_MATCHING, DESIGN_COLORS["border_strong"]),
        (f"{glyphs['High']} {counts['high']:,}", T.SUMMARY_HIGH, PRIORITY_COLORS["High"]),
        (f"{glyphs['Medium']} {counts['medium']:,}", T.SUMMARY_MEDIUM, PRIORITY_COLORS["Medium"]),
        (f"{glyphs['Low']} {counts['low']:,}", T.SUMMARY_LOW, PRIORITY_COLORS["Low"]),
        (f"{counts['new']:,}", T.SUMMARY_NEW, DESIGN_COLORS["new"]),
    )
    cells = "".join(
        f"<div class='dhoa-metric' style='border-left-color:{color}'>"
        f"<strong>{value}</strong><span>{html.escape(label)}</span></div>"
        for value, label, color in items
    )
    st.markdown(f"<div class='dhoa-metrics dhoa-summary'>{cells}</div>", unsafe_allow_html=True)
    st.caption(T.PRIORITY_NOTE)


def render_footer() -> None:
    """Render the shared contact footer at the end of every view (website only until verified)."""
    try:
        st.markdown(
            trust.contact_footer_html(
                _contact(), T.HOTLINE_LABEL, T.FOOTER_WEB_LABEL, T.CONTACT_CALL, T.CONTACT_SMS, T.get_language()
            ),
            unsafe_allow_html=True,
        )
    except Exception:  # noqa: BLE001 - a footer problem must not blank the view
        logging.getLogger(__name__).exception("Footer failed")


_PORTAL_TABS: tuple[str, ...] = ("dashboard", "map", "work", "reports")


def _work_store() -> public_storage.SQLiteReportStore:
    """Staff-only visit and note store; input/output follows ``app.storage`` schemas."""
    return public_storage.SQLiteReportStore(APP_DB_PATH)


def _open_report_count() -> int:
    """Count new and reviewed reports for the staff-only navigation badge."""
    try:
        return sum(report.status in {"new", "reviewed"} for report in _work_store().list_reports())
    except Exception:
        logging.exception("Could not load inspector report count")
        return 0


def _portal_tab_label(tab: str) -> str:
    """Translated label of an Inspector Portal sub-tab (Reports carries a count badge)."""
    if tab == "reports":
        count = _open_report_count()
        return T.PORTAL_TAB_REPORTS_FMT.format(count) if count else T.PORTAL_TAB_REPORTS
    return {"dashboard": T.PORTAL_TAB_DASHBOARD, "map": T.PORTAL_TAB_MAP, "work": T.PORTAL_TAB_WORK}[tab]


def _commit_portal_tab() -> None:
    """``on_change`` callback for the portal sub-tabs (a deselect keeps the current tab)."""
    value = st.session_state.get(_wkey("dhoa_portal_tab"))
    if value in _PORTAL_TABS:
        st.session_state["dhoa_portal_tab"] = value


def _sign_out_staff() -> None:
    """``on_click`` callback: end the staff session and return to the Overview."""
    roles.sign_out()
    st.session_state["dhoa_view_mode"] = hero.DEFAULT_VIEW
    st.session_state.pop("dhoa_portal_tab", None)


def _fill_demo_credentials() -> None:
    """Fill the configured demo passcode and display name into the sign-in fields."""
    if not roles.demo_enabled() or not roles.configured_passcode():
        return
    st.session_state["dhoa_signin_passcode"] = roles.configured_passcode()
    st.session_state["dhoa_signin_name"] = roles.DEMO_NAME


def render_staff_signin() -> None:
    """Sign-in page shown in place of the portal while the session is public."""
    with st.container(key="dhoa_signin"):
        st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.PORTAL_SIGNIN_TITLE)}</div>",
                    unsafe_allow_html=True)
        st.markdown(
            textwrap.dedent("""
            <style>
            .dhoa-portal-preview{filter:blur(5px);opacity:.48;pointer-events:none;
              user-select:none;margin:.5rem auto 1rem;max-width:42rem}
            .dhoa-portal-preview-head{height:1.1rem;width:38%;border-radius:8px;
              background:#9aa7b4;margin:0 0 .8rem}
            .dhoa-portal-preview-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:.6rem}
            .dhoa-portal-preview-card{height:4.2rem;border:1px solid #64748b;border-radius:10px;
              background:linear-gradient(135deg,#243447,#17212b)}
            .dhoa-portal-preview-map{height:7rem;margin-top:.6rem;border:1px solid #64748b;
              border-radius:10px;background:radial-gradient(circle at 42% 45%,#5b7180 0 2px,transparent 3px),
              radial-gradient(circle at 66% 60%,#5b7180 0 2px,transparent 3px),#18232e}
            </style>
            <div class="dhoa-portal-preview" aria-hidden="true">
              <div class="dhoa-portal-preview-head"></div>
              <div class="dhoa-portal-preview-cards"><div class="dhoa-portal-preview-card"></div>
                <div class="dhoa-portal-preview-card"></div><div class="dhoa-portal-preview-card"></div></div>
              <div class="dhoa-portal-preview-map"></div>
            </div>
            """),
            unsafe_allow_html=True,
        )
        if not roles.signin_available():
            st.info(T.PORTAL_SIGNIN_UNAVAILABLE)
            return
        st.caption(T.PORTAL_SIGNIN_HINT)
        if roles.configured_passcode():
            with st.form("dhoa_signin_form", clear_on_submit=False):
                passcode = st.text_input(T.PORTAL_PASSCODE, type="password", key="dhoa_signin_passcode")
                name = st.text_input(T.PORTAL_NAME, key="dhoa_signin_name", max_chars=60)
                submitted = st.form_submit_button(
                    T.PORTAL_SIGN_IN, type="primary", key="dhoa_signin_submit"
                )
            if submitted:
                if roles.sign_in(passcode, name):
                    st.session_state["dhoa_portal_tab"] = "map"
                    st.rerun()
                st.error(T.PORTAL_WRONG_PASSCODE)
        if roles.demo_enabled():
            st.caption(T.PORTAL_DEMO_CREDENTIALS_HINT)
            st.button(
                T.PORTAL_FILL_DEMO_CREDENTIALS,
                key="dhoa_fill_demo_credentials",
                on_click=_fill_demo_credentials,
                type="secondary",
            )


def render_portal_bar() -> str:
    """Second-level navigation under the top bar (staff only); return the active sub-tab key."""
    if st.session_state.get("dhoa_portal_tab") not in _PORTAL_TABS:
        st.session_state["dhoa_portal_tab"] = "map"
    _seed("dhoa_portal_tab", st.session_state["dhoa_portal_tab"])
    with st.container(key="dhoa_portal_bar"):
        tabs_col, badge_col, who_col, out_col = st.columns([5.5, 1.4, 2.5, 1.6], vertical_alignment="center", gap="small")
        with tabs_col:
            chosen = st.segmented_control(
                T.PORTAL_TABS_LABEL, list(_PORTAL_TABS), format_func=_portal_tab_label,
                key=_wkey("dhoa_portal_tab"), width="stretch", on_change=_commit_portal_tab,
                label_visibility="collapsed",
            )
        if chosen in _PORTAL_TABS:
            st.session_state["dhoa_portal_tab"] = chosen
        open_count = _open_report_count()
        badge_col.caption("🔔 " + T.PORTAL_OPEN_REPORTS_FMT.format(open_count))
        who_col.caption(T.PORTAL_SIGNED_IN_FMT.format(roles.staff_name()))
        out_col.button(T.PORTAL_SIGN_OUT, key="dhoa_portal_signout", width="stretch",
                       on_click=_sign_out_staff)
    return st.session_state["dhoa_portal_tab"]


def render_portal_dashboard(gdf: gpd.GeoDataFrame) -> None:
    """Inspector > Dashboard: the headline numbers and the overview charts."""
    counts = hero.hero_counts(gdf)
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (
        (METRIC_LABELS["total_candidates"], f"{counts['total']:,}"),
        (METRIC_LABELS["high_priority_kilns"], f"{counts['high']:,}"),
        (T.HERO_METRIC_DISTRICTS, f"{counts['districts']:,}"),
        (METRIC_LABELS["last_updated"], _data_date_label(dashboard_kilns_file())),
    )):
        column.metric(label, value)
    render_overview_charts(gdf)


_VISIT_STATUS_LABELS = {
    "not_visited": T.WORK_NOT_VISITED, "assigned": T.WORK_ASSIGNED,
    "visited": T.WORK_VISITED, "confirmed_active": T.WORK_CONFIRMED_ACTIVE,
    "not_a_kiln": T.WORK_NOT_A_KILN,
}


def _save_current_filter(display_name: str, name: str) -> None:
    """Persist current Inspector sidebar values under the signed-in name."""
    if not roles.is_staff():
        return
    values: dict[str, object] = {
        "district": st.session_state.get("filter_district", ALL_DISTRICTS),
        "upazila": st.session_state.get("filter_upazila", ALL_AREAS),
        "priorities": list(st.session_state.get("filter_priority", ["High", "Medium", "Low"])),
        "kiln_type": st.session_state.get("filter_kiln_type", ALL_KILN_TYPES),
    }
    _work_store().save_filter(display_name, name, values)


def _apply_saved_filter(name: str) -> None:
    """Restore a saved Inspector filter and navigate to the staff map."""
    if not roles.is_staff():
        return
    records = _work_store().list_saved_filters(roles.staff_name())
    record = next((item for item in records if item.name == name), None)
    if record is None:
        return
    values = record.filters
    st.session_state["filter_district"] = values.get("district", ALL_DISTRICTS)
    st.session_state["filter_upazila"] = values.get("upazila", ALL_AREAS)
    st.session_state["filter_priority"] = values.get("priorities", ["High", "Medium", "Low"])
    st.session_state["filter_kiln_type"] = values.get("kiln_type", ALL_KILN_TYPES)
    _drop_widget_state("filter_district", *_FORM_FILTERS)
    st.session_state["dhoa_view_mode"] = "inspector"
    st.session_state["dhoa_portal_tab"] = "map"


def _delete_saved_filter(name: str) -> None:
    """Remove one saved filter from the signed-in display name's collection."""
    if roles.is_staff():
        _work_store().delete_saved_filter(roles.staff_name(), name)


def _render_saved_filters(store: public_storage.SQLiteReportStore, display_name: str) -> None:
    """Render staff filter save, apply and delete actions in the Work section."""
    st.markdown(f"**{T.SAVED_FILTERS}**")
    district = st.session_state.get("filter_district", ALL_DISTRICTS)
    upazila = st.session_state.get("filter_upazila", ALL_AREAS)
    priorities = st.session_state.get("filter_priority", ["High", "Medium", "Low"])
    kiln_type = st.session_state.get("filter_kiln_type", ALL_KILN_TYPES)
    priority_labels = {"High": T.HIGH, "Medium": T.MEDIUM, "Low": T.LOW}
    st.caption(T.SAVED_FILTER_CURRENT_FMT.format(
        T.ALL_DISTRICTS if district == ALL_DISTRICTS else _district_label(str(district)),
        T.ALL_AREAS if upazila == ALL_AREAS else str(upazila),
        ", ".join(priority_labels.get(str(value), str(value)) for value in priorities),
        T.ALL_TYPES if kiln_type == ALL_KILN_TYPES else _type_label(str(kiln_type)),
    ))
    with st.form("dhoa_saved_filter_form"):
        name = st.text_input(T.SAVED_FILTER_NAME, key="dhoa_saved_filter_name")
        submitted = st.form_submit_button(T.SAVED_FILTER_SAVE, width="stretch")
    if submitted:
        if name.strip():
            _save_current_filter(display_name, name)
            st.success(T.SAVED_FILTER_SAVED)
        else:
            st.warning(T.SAVED_FILTER_NAME_REQUIRED)
    records = store.list_saved_filters(display_name)
    if not records:
        st.caption(T.SAVED_FILTER_NONE)
        return
    chosen = st.selectbox(T.SAVED_FILTER_SELECT, records, format_func=lambda item: item.name,
                          key="dhoa_saved_filter_choice")
    apply_col, delete_col = st.columns([2, 1])
    apply_col.button(T.SAVED_FILTER_APPLY, key="dhoa_saved_filter_apply",
                     on_click=_apply_saved_filter, args=(chosen.name,), width="stretch")
    delete_col.button(T.SAVED_FILTER_DELETE, key="dhoa_saved_filter_delete",
                      on_click=_delete_saved_filter, args=(chosen.name,), width="stretch")


def _render_activity_log(store: public_storage.SQLiteReportStore) -> None:
    """Show recent staff changes with actor, target, localized action and time."""
    action_labels = {
        "visit_updated": T.WORK_ACTIVITY_VISIT,
        "note_added": T.WORK_ACTIVITY_NOTE,
        "visit_photo_added": T.WORK_ACTIVITY_PHOTO,
        "saved_filter_saved": T.WORK_ACTIVITY_FILTER_SAVED,
        "saved_filter_deleted": T.WORK_ACTIVITY_FILTER_DELETED,
        "report_status_changed": T.WORK_ACTIVITY_REPORT,
    }
    with st.expander(T.WORK_ACTIVITY):
        entries = store.list_activity(50)
        if not entries:
            st.caption(T.WORK_EMPTY)
            return
        for entry in entries:
            description = action_labels.get(entry.action, entry.action)
            if entry.action == "visit_updated":
                new_values = entry.details.get("to") or {}
                status_code = str(new_values.get("status", ""))
                status_label = _VISIT_STATUS_LABELS.get(status_code, status_code)
                description += " · " + T.WORK_ACTIVITY_STATUS_FMT.format(
                    status_label, new_values.get("assignee") or "—"
                )
            elif entry.action == "report_status_changed":
                to_status = str(entry.details.get("to", ""))
                description += " · " + {
                    "new": T.REPORT_NEW, "reviewed": T.REPORT_REVIEWED,
                    "resolved": T.REPORT_RESOLVED,
                }.get(to_status, to_status)
            st.text(f"{entry.created_at} · {entry.actor} · {description} · {entry.entity_id}")


def _render_work_controls(row: pd.Series) -> None:
    """Render staff visit status, assignment and notes for one candidate row."""
    if not roles.is_staff():
        return
    kiln_id = str(row["kiln_id"])
    store = _work_store()
    visit = store.get_visit(kiln_id)
    current = visit.status if visit else "not_visited"
    assignee = visit.assignee if visit else None
    with st.container(key="dhoa_visit_controls"):
        st.markdown(f"**{T.WORK_STATUS}**")
        with st.form(f"dhoa_visit_form_{hashlib.sha1(kiln_id.encode()).hexdigest()[:10]}"):
            status = st.selectbox(T.WORK_STATUS, list(_VISIT_STATUS_LABELS),
                                  index=list(_VISIT_STATUS_LABELS).index(current),
                                  format_func=lambda value: _VISIT_STATUS_LABELS[value],
                                  label_visibility="collapsed")
            assignee_input = st.text_input(T.WORK_CURRENT_ASSIGNEE.format(assignee or "—"), value=assignee or "")
            save = st.form_submit_button(T.WORK_SAVE_STATUS, width="stretch")
        assign_col, note_col = st.columns([1, 2], gap="small")
        if assign_col.button(T.WORK_ASSIGN_TO_ME, key=f"dhoa_assign_{hashlib.sha1(kiln_id.encode()).hexdigest()[:10]}"):
            store.set_visit(kiln_id, "assigned", roles.staff_name(), roles.staff_name())
            st.rerun()
        note_text = note_col.text_input(T.WORK_NOTE_HINT, key=f"dhoa_note_{hashlib.sha1(kiln_id.encode()).hexdigest()[:10]}")
        if note_col.button(T.WORK_ADD_NOTE, key=f"dhoa_add_note_{hashlib.sha1(kiln_id.encode()).hexdigest()[:10]}"):
            if note_text.strip():
                store.add_note(kiln_id, note_text, roles.staff_name())
                st.rerun()
        if save:
            store.set_visit(kiln_id, status, assignee_input.strip() or None, roles.staff_name())
            st.rerun()
        uploaded = st.file_uploader(
            T.WORK_VISIT_PHOTO, type=["jpg", "jpeg", "png", "webp"],
            key=f"dhoa_visit_photo_upload_{hashlib.sha1(kiln_id.encode()).hexdigest()[:10]}",
        )
        if st.button(T.WORK_ATTACH_PHOTO,
                     key=f"dhoa_visit_photo_save_{hashlib.sha1(kiln_id.encode()).hexdigest()[:10]}"):
            if uploaded is None:
                st.warning(T.WORK_PHOTO_INVALID)
            else:
                try:
                    store.add_visit_photo(kiln_id, uploaded.getvalue(), uploaded.type or "", roles.staff_name())
                    st.success(T.WORK_PHOTO_SAVED)
                    st.rerun()
                except ValueError:
                    st.warning(T.WORK_PHOTO_INVALID)
        for photo in store.list_visit_photos(kiln_id):
            image_path = APP_DB_PATH.parent / photo.photo_ref
            if image_path.is_file():
                st.image(str(image_path), caption=f"{photo.author} · {photo.created_at}", width=260)
        notes = store.list_notes(kiln_id)
        if visit or notes:
            with st.expander(T.WORK_HISTORY):
                if visit:
                    st.text(f"{_VISIT_STATUS_LABELS[visit.status]} · {visit.assignee or '—'} · {visit.updated_by} · {visit.updated_at}")
                for note in notes:
                    st.text(f"{note.author} · {note.created_at}\n{note.text}")


def _open_kiln_on_map(kiln_id: str, lat: float, lon: float) -> None:
    """Staff callback to open a kiln or report coordinate on the Inspector Map."""
    _reset_inspector_filters()
    st.session_state["selected_kiln_id"] = str(kiln_id) if kiln_id else None
    st.session_state["selected_lat"] = float(lat)
    st.session_state["selected_lng"] = float(lon)
    st.session_state["dhoa_report_focus"] = [float(lat), float(lon)]
    st.session_state["dhoa_view_mode"] = "inspector"
    st.session_state["dhoa_portal_tab"] = "map"


def render_portal_work(gdf: gpd.GeoDataFrame) -> None:
    """Render staff assignments with status filtering, data-derived distance sorting and directions."""
    if not roles.is_staff():
        return
    st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.WORK_MY_LIST)}</div>", unsafe_allow_html=True)
    me = roles.staff_name()
    store = _work_store()
    _render_saved_filters(store, me)
    visits = store.list_visits(assignee=me)
    status_codes = list(_VISIT_STATUS_LABELS)
    status = st.selectbox(T.WORK_STATUS_FILTER, ["all", *status_codes],
                          format_func=lambda code: T.WORK_ALL if code == "all" else _VISIT_STATUS_LABELS[code])
    if status != "all":
        visits = [visit for visit in visits if visit.status == status]
    sort_mode = st.radio(T.WORK_SORT, ["priority", "distance"], horizontal=True,
                         format_func=lambda value: T.WORK_SORT_PRIORITY if value == "priority" else T.WORK_SORT_DISTANCE)
    origin = None
    if sort_mode == "distance":
        places = _cached_places(_community_version_key(gdf), gdf)
        if places:
            origin = st.selectbox(T.WORK_DISTANCE_ORIGIN, places, format_func=lambda place: place.label)
    rows = []
    for visit in visits:
        found = gdf[gdf["kiln_id"].astype(str).eq(visit.kiln_id)]
        if found.empty:
            continue
        row = found.iloc[0]
        rows.append((visit, row))
    if sort_mode == "distance" and origin is not None:
        distance = {visit.kiln_id: float(kd.distances_from_point_m(
            [float(row["lat"])], [float(row["lon"])], origin.lat, origin.lon)[0]) for visit, row in rows}
        rows.sort(key=lambda item: distance[item[0].kiln_id])
    else:
        rank = {"High": 0, "Medium": 1, "Low": 2}
        rows.sort(key=lambda item: (rank.get(str(item[1].get("priority_band", "")), 3), item[0].kiln_id))
    if not rows:
        st.info(T.WORK_EMPTY)
        _render_activity_log(store)
        return
    route_links = staff_tools.google_maps_route_links(
        [(float(row["lat"]), float(row["lon"])) for _, row in rows]
    )
    st.markdown(f"**{T.WORK_ROUTES}**")
    st.caption(T.WORK_ROUTE_NOTE)
    for link in route_links:
        st.link_button(
            T.WORK_ROUTE_FMT.format(link.first_stop, link.first_stop, link.last_stop),
            link.url, width="stretch",
        )
    for visit, row in rows:
        title = f"{visit.kiln_id} · {_VISIT_STATUS_LABELS[visit.status]}"
        with st.container(border=True):
            st.markdown(f"**{title}** · {row.get('priority_band', '')}")
            st.caption(f"{row.get('district', '')} · {float(row['lat']):.5f}, {float(row['lon']):.5f}")
            lat, lon = float(row["lat"]), float(row["lon"])
            if origin is not None and sort_mode == "distance":
                st.caption(f"{distance[visit.kiln_id]:,.0f} m")
            map_col, directions_col = st.columns([1, 1])
            map_col.button(T.WORK_OPEN_MAP, key=f"dhoa_work_map_{hashlib.sha1(visit.kiln_id.encode()).hexdigest()[:10]}",
                           on_click=_open_kiln_on_map, args=(visit.kiln_id, lat, lon))
            directions_col.link_button(T.WORK_DIRECTIONS, f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}", width="stretch")
    _render_activity_log(store)


def render_portal_reports(gdf: gpd.GeoDataFrame) -> None:
    """Render the staff-only public report inbox and status actions."""
    if not roles.is_staff():
        return
    st.markdown(f"<div class='dhoa-section-title'>{html.escape(T.REPORT_INBOX)}</div>", unsafe_allow_html=True)
    reports = _work_store().list_reports()
    if not reports:
        st.info(T.REPORT_EMPTY)
        return
    labels = {"new": T.REPORT_NEW, "reviewed": T.REPORT_REVIEWED, "resolved": T.REPORT_RESOLVED}
    for report in reversed(reports):
        with st.container(border=True):
            st.markdown(f"**{labels.get(report.status, report.status)} · {report.reason}**")
            st.caption(f"{report.created_at} · {report.lat:.5f}, {report.lon:.5f}")
            st.text(report.note)
            if report.contact:
                st.text(report.contact)
            if report.photo_ref:
                photo = APP_DB_PATH.parent / report.photo_ref
                if photo.is_file():
                    st.image(str(photo), width=260)
            cols = st.columns([2, 1, 1])
            digest = hashlib.sha1(report.id.encode()).hexdigest()[:10]
            cols[0].button(T.REPORT_OPEN_MAP, key=f"dhoa_report_map_{digest}",
                           on_click=_open_kiln_on_map,
                           args=(report.kiln_id or "", report.lat, report.lon), width="stretch")
            if report.status != "reviewed":
                cols[1].button(T.REPORT_MARK_REVIEWED, key=f"dhoa_report_review_{digest}",
                               on_click=_set_report_status, args=(report.id, "reviewed"), width="stretch")
            if report.status != "resolved":
                cols[2].button(T.REPORT_MARK_RESOLVED, key=f"dhoa_report_resolve_{digest}",
                               on_click=_set_report_status, args=(report.id, "resolved"), width="stretch")


def _set_report_status(report_id: str, status: str) -> None:
    """Staff-only status callback for one inbox record."""
    if roles.is_staff():
        _work_store().set_report_status(report_id, status, roles.staff_name())


def main() -> None:
    """Run the shared Dhoa header, sidebar, and selected mode flow.

    Input schema: local configuration and prioritized GeoParquet.
    Output schema: one Inspector or Community dashboard view.
    """
    _init_language()
    st.markdown(responsive_css(), unsafe_allow_html=True)
    placeholder = st.empty()
    placeholder.markdown(trust.skeleton_html(T.STATE_LOADING), unsafe_allow_html=True)
    try:
        load_config()
        gdf = get_prepared_data()
        public_gdf = get_public_data()
    except Exception as _load_exc:
        logging.getLogger(__name__).exception("Dashboard data/configuration load failed")
        placeholder.empty()
        st.markdown(trust.state_html("error", T.STATE_DATA_TITLE, T.STATE_DATA_BODY), unsafe_allow_html=True)
        _debug_details(_load_exc)
        if st.button(T.STATE_RETRY, key="dhoa_retry_data_load"):
            st.rerun()
        return
    placeholder.empty()
    if gdf is None or public_gdf is None:
        st.markdown(trust.state_html("empty", T.STATE_DATA_TITLE, T.DASHBOARD_DATA_IS_UNAVAILABLE), unsafe_allow_html=True)
        if st.button(T.STATE_RETRY, key="dhoa_retry_missing_data"):
            st.rerun()
        return
    from src.geo.crs import get_projected_crs

    centroid_longitude = float(gdf["lon"].mean()) if not gdf.empty else 90.0
    try:
        get_projected_crs(centroid_longitude)
        mode = render_header(gdf)
        portal_tab = None
        if mode == "inspector" and roles.is_staff():
            portal_tab = render_portal_bar()
        # The sidebar filters belong to the staff map only; every other view keeps the minimal
        # sidebar. It is always rendered so Streamlit never adds/removes it between views.
        staff_map = mode == "inspector" and portal_tab == "map"
        filters = render_sidebar(gdf, "inspector" if staff_map else ("about" if mode == "inspector" else mode))
        if mode == "inspector" and not roles.is_staff():
            render_staff_signin()
            render_footer()
            return
        if mode == "inspector" and portal_tab != "map":
            if portal_tab == "dashboard":
                render_portal_dashboard(gdf)
            elif portal_tab == "work":
                render_portal_work(gdf)
            elif portal_tab == "reports":
                render_portal_reports(gdf)
            else:
                st.markdown(trust.state_html("empty", T.PORTAL_SOON_TITLE, T.PORTAL_SOON_BODY),
                            unsafe_allow_html=True)
            render_footer()
            return
        # Overview, About and Kilns near me are public paths: they only ever receive the public frame.
        if mode == "overview":
            render_overview(public_gdf)
            render_footer()
            return
        if mode == "about":
            render_about(public_gdf)
            render_footer()
            return
        if mode == "community":
            render_community_view(public_gdf)
            render_footer()
            return
        visible = filters["visible"]  # computed once in render_sidebar
        _render_summary_strip(visible)
        render_map_fragment(gdf, filters, visible)
        render_footer()
    except Exception as _exc:
        logging.getLogger(__name__).exception("Dashboard view rendering failed")
        st.markdown(trust.state_html("error", T.STATE_ERROR_TITLE, T.STATE_ERROR_BODY), unsafe_allow_html=True)
        _debug_details(_exc)
        if st.button(T.STATE_RETRY, key="dhoa_retry_render"):
            st.rerun()
if __name__ == "__main__":
    main()
