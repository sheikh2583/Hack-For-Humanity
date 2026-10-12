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

st.set_page_config(page_title="Dhoa", layout="wide", initial_sidebar_state="auto")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

# isort: off
from dashboard_filters import (  # noqa: E402
    SIGNAL_PRESENT,
    add_priority_bands,
    apply_candidate_filters,
)
from data_loader import load_kilns  # noqa: E402
from presentation import screening_csv  # noqa: E402
from src.rules.engine import _ensure_class_column  # noqa: E402
# isort: on

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_PATH = DATA_DIR / "kilns_prioritised.parquet"
PRIORITY_COLORS = {"High": "red", "Medium": "orange", "Low": "green"}
DISTRICTS = ["All Districts", "Chapainawabganj", "Gazipur", "Rajshahi", "Dhaka", "Chittagong"]
ADVISORY_BANNER = "Advisory only: unverified screening candidates"


def responsive_css() -> str:
    """Return the dashboard CSS for desktop, tablet, and phone layouts.

    Input schema: none. Output schema: one CSS string containing the
    responsive dashboard rules; it is injected once by :func:`main`.
    """
    return """
<style>
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100%;
    padding-left: 2rem;
    padding-right: 2rem;
}
[data-testid="stMetric"] { min-width: 0; }
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button,
[data-baseweb="select"] > div,
[data-testid="stSlider"] [role="slider"] { min-height: 44px; }
.dhoa-advisory {
    border: 1px solid #d97706;
    border-radius: 0.35rem;
    background: #fff7ed;
    color: #7c2d12;
    font-size: 1rem;
    padding: 0.75rem 1rem;
    margin: 0 0 1rem;
}
.dhoa-popup { max-width: 260px; overflow-wrap: anywhere; word-break: break-word; }
.dhoa-popup table { width: 100%; table-layout: fixed; }
.dhoa-popup td, .dhoa-popup th { overflow-wrap: anywhere; vertical-align: top; }
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }
    [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.75rem; }
    [data-testid="stMetricContainer"] { min-width: 0; }
    [data-testid="stIFrame"] iframe, iframe[title="streamlit_folium.st_folium"] {
        width: 100% !important;
        height: 60vh !important;
        min-height: 320px !important;
        max-height: 600px !important;
    }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    .dhoa-metrics { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem !important; }
}
@media (max-width: 480px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    body, p, label, [data-testid="stCaptionContainer"] { font-size: 14px; }
    .dhoa-advisory { padding: 0.65rem 0.75rem; }
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
    return "Fixed-chimney kiln (flagged for review)" if str(value) == "FCBK" else "Zigzag kiln"


def _signals(row: pd.Series) -> list[str]:
    value = row.get("breached_rules", [])
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [value]
    return list(value) if isinstance(value, (list, tuple)) else []


def _priority_reason(row: pd.Series) -> str:
    names = {"near_school": ("school", "dist_schools_m"), "near_hospital": ("hospital", "dist_hospitals_m"), "near_settlement": ("settlement", "dist_settlements_m")}
    for signal in _signals(row):
        label, column = names.get(str(signal), ("rule signal", ""))
        distance = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0] if column else None
        return f"near {label} {distance:,.0f} m" if pd.notna(distance) else f"{label} signal"
    return "no rule signal recorded"


def build_popup(row: pd.Series) -> str:
    """Build one self-contained plain-English popup for a candidate row."""
    lat, lon = float(row.lat), float(row.lon)
    directions = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving"
    location = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
    earth = f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y,0h,0t,0r"
    signals = ", ".join(html.escape(signal) for signal in _signals(row)) or "None recorded"
    confidence = pd.to_numeric(pd.Series([row.get("confidence")]), errors="coerce").iloc[0]
    confidence_text = f"{confidence:.1%}" if pd.notna(confidence) else "Not recorded"
    return (
        "<div class='dhoa-popup'>"
        f"<b>Kiln Candidate #{html.escape(str(row.get('kiln_id', 'unknown')))}</b><br>"
        f"Type: {html.escape(_type_label(row.get('class')))}<br>"
        f"Confidence: {confidence_text}<br>"
        f"Candidate rule signals: {signals}<br>"
        f"Priority: {html.escape(str(row.get('priority_band', 'Not ranked')))} — {html.escape(_priority_reason(row))}<br>"
        f"District: {html.escape(str(row.get('district', 'Not recorded')))}<br>"
        f"📍 {lat:.4f}° N, {lon:.4f}° E<br>"
        f'<a href="{directions}" target="_blank">🗺 Get Directions</a> | '
        f'<a href="{location}" target="_blank">📍 View Location</a> | '
        f'<a href="{earth}" target="_blank">🌍 Google Earth</a><br>'
        '<small style="color:#666">This is a screening candidate. Verify on the ground before any action.</small>'
        "</div>"
    )


def _filtered(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> gpd.GeoDataFrame:
    """Apply the sidebar filter state without rendering UI."""
    return apply_candidate_filters(
        gdf,
        load_config()["rules"],
        districts=None if filters["district"] == "All Districts" else {filters["district"]},
        classes=None if filters["kiln_type"] == "All types" else {"FCBK" if "FCBK" in filters["kiln_type"] else "Zigzag"},
        confidence_range=filters["confidence_range"],
        priority_bands=filters["priorities"] or {"__none__"},
        signal_filters=filters["signal_filters"],
    )


def _export_csv(gdf: pd.DataFrame) -> str:
    """Create a full-field advisory export, retaining the district column."""
    return screening_csv(gdf)


def render_header(gdf: gpd.GeoDataFrame) -> None:
    """Render the app identity, advisory, file provenance, and metric chips."""
    st.markdown("<h1 style='margin-bottom:0'>Dhoa</h1>", unsafe_allow_html=True)
    st.caption("Satellite Kiln Inspection Tool — Bangladesh")
    loaded = dashboard_kilns_file()
    if loaded is not None:
        modified = datetime.fromtimestamp(loaded.stat().st_mtime, tz=UTC).isoformat(
            timespec="seconds"
        )
        st.caption(f"Loaded parquet: {loaded.name} | modified {modified}")
    high = int(gdf["priority_band"].eq("High").sum())
    st.markdown(f"<div class='dhoa-metrics' style='display:flex;gap:28px;margin:18px 0'><div><b>{len(gdf):,}</b><br><small>Total Candidates</small></div><div><b>{high:,}</b><br><small>High Priority</small></div><div><b>{gdf['district'].nunique()}</b><br><small>Districts Scanned</small></div><div><b>{datetime.now(UTC).date().isoformat()}</b><br><small>Last Updated</small></div></div>", unsafe_allow_html=True)


def render_sidebar(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Render controls and return a filter mapping."""
    with st.sidebar, st.expander("Filter", expanded=False):
        st.caption("Find candidates by district, type, map, and severity.")
        district = st.selectbox("Select district", DISTRICTS, key="dhoa_district_filter")
        kiln_type = st.selectbox(
            "Kiln type",
            ["All types", "Fixed-chimney (FCBK)", "Zigzag"],
            key="dhoa_kiln_type_filter",
        )
        map_style = st.selectbox(
            "Map view",
            ["Street map", "Satellite imagery"],
            help="Choose the map background for candidate locations.",
            key="dhoa_map_style_filter",
        )
        severity = st.selectbox(
            "Severity", ["All severities", "High", "Medium", "Low"],
            key="dhoa_severity_filter",
        )
        confidence_range = st.slider(
            "Confidence range",
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
            "Candidate rule signals",
            signal_ids,
            key="dhoa_signal_filter",
        )
        priorities = {severity} if severity != "All severities" else {"High", "Medium", "Low"}
    filters = {
        "district": district,
        "kiln_type": kiln_type,
        "map_style": map_style,
        "priorities": priorities,
        "confidence_range": confidence_range,
        "signal_filters": {signal_id: SIGNAL_PRESENT for signal_id in selected_signals},
    }
    visible = _filtered(gdf, filters)
    with st.sidebar:
        st.markdown(f"**Showing {len(visible):,} candidates**")
        slug = district.lower().replace(" ", "_") if district != "All Districts" else "all_districts"
        today = datetime.now(UTC).strftime("%Y%m%d")
        st.download_button("⬇ Export List", _export_csv(visible), f"dhoa_{slug}_{today}.csv", "text/csv", width="stretch")
        if not visible.empty:
            top = visible.iloc[0]
            url = f"https://www.google.com/maps/dir/?api=1&destination={float(top.lat):.6f},{float(top.lon):.6f}&travelmode=driving"
            st.markdown(f'<a href="{url}" target="_blank">🧭 Navigate to Highest Priority</a>', unsafe_allow_html=True)
    return filters


def build_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]):
    """Build and return the complete Folium map for filtered candidates."""
    import folium
    from folium.plugins import MarkerCluster
    filtered = _filtered(gdf, filters)
    selected = gdf if filters["district"] == "All Districts" else gdf[gdf["district"].astype(str) == filters["district"]]
    selected = selected if not selected.empty else gdf
    center = [float(selected.lat.mean()), float(selected.lon.mean())]
    satellite = filters.get("map_style") == "Satellite imagery"
    fmap = folium.Map(
        location=center,
        zoom_start=7 if filters["district"] == "All Districts" else 10,
        tiles=None,
        scrollWheelZoom=False,
        min_zoom=5,
        max_zoom=14,
        control_scale=True,
    )
    folium.TileLayer("OpenStreetMap", name="Street map", show=not satellite).add_to(fmap)
    folium.TileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite imagery",
        show=satellite,
    ).add_to(fmap)
    markers = MarkerCluster(name="Kiln candidates", options={"disableClusteringAtZoom": 12})
    markers.add_to(fmap)
    for _, row in filtered.iterrows():
        color = color_for_kiln(row)
        folium.CircleMarker([float(row.lat), float(row.lon)], radius=7, color=color, fill=True, fill_color=color, fill_opacity=.8, popup=folium.Popup(build_popup(row), max_width=260)).add_to(markers)
    folium.LayerControl(position="topright").add_to(fmap)
    return fmap


def render_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the map and convert any failure into a friendly message."""
    try:
        from streamlit_folium import st_folium
        st_folium(build_map(gdf, filters), height=600, use_container_width=True, returned_objects=[])
    except Exception:  # noqa: BLE001 - user-facing map failure boundary
        st.error("Map failed to load. Try refreshing.")


def render_footer(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the single summary line below the map."""
    visible = _filtered(gdf, filters)
    high = int(visible["priority_band"].eq("High").sum())
    flagged = int(visible.get("breach_count", pd.Series(0, index=visible.index)).fillna(0).gt(0).sum())
    st.caption(f"{len(visible):,} candidates visible | {high:,} high priority | {flagged:,} flagged for rule review")


def render_tables(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render a compact candidate table and the complete table in an expander."""
    visible = _filtered(gdf, filters)
    compact = pd.DataFrame(
        {
            "District": visible.get("district", pd.Series(dtype="string")),
            "Class": visible.get("class", pd.Series(dtype="string")),
            "Confidence": pd.to_numeric(
                visible.get("confidence", pd.Series(dtype=float)), errors="coerce"
            ).map(lambda value: f"{value:.1%}" if pd.notna(value) else "Not recorded"),
            "Candidate rule signals": visible.apply(
                lambda row: ", ".join(_signals(row)) or "None recorded", axis=1
            ),
        },
        index=visible.index,
    )
    st.subheader("Kiln candidate details")
    st.dataframe(compact, use_container_width=True, hide_index=True)
    with st.expander("Full candidate table"):
        st.dataframe(visible.drop(columns="geometry", errors="ignore"), use_container_width=True, hide_index=True)


def main() -> None:
    """Run the fixed Dhoa page flow."""
    st.markdown(responsive_css(), unsafe_allow_html=True)
    st.markdown(f"<div class='dhoa-advisory'>{ADVISORY_BANNER}</div>", unsafe_allow_html=True)
    try:
        load_config()
        gdf = load_data()
    except Exception:  # noqa: BLE001 - user-facing data failure boundary
        st.error("Data could not be loaded. Check the prepared results and configuration files.")
        return
    if gdf is None:
        st.error("Data not found. Contact your administrator.")
        return
    gdf = add_priority_bands(gdf)
    render_header(gdf)
    filters = render_sidebar(gdf)
    render_map(gdf, filters)
    render_footer(gdf, filters)
    render_tables(gdf, filters)


if __name__ == "__main__":
    main()
