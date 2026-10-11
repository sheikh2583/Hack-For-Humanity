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

st.set_page_config(page_title="Dhoa", layout="wide", initial_sidebar_state="expanded")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

import geopandas as gpd
import pandas as pd
import yaml

# isort: off
from dashboard_filters import add_priority_bands, apply_candidate_filters
from data_loader import load_kilns
from src.rules.engine import _ensure_class_column
# isort: on

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_PATH = DATA_DIR / "kilns_prioritised.parquet"
PRIORITY_COLORS = {"High": "red", "Medium": "orange", "Low": "green"}
DISTRICTS = ["All Districts", "Chapainawabganj", "Gazipur", "Rajshahi", "Dhaka", "Chittagong"]


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
    confidence = float(row.get("confidence", 0) or 0)
    confidence_label = "High confidence detection" if confidence >= 0.7 else "Review confidence"
    directions = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving"
    location = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
    earth = f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y,0h,0t,0r"
    return (
        f"<b>Kiln Candidate #{html.escape(str(row.get('kiln_id', 'unknown')))}</b><br>"
        f"Type: {html.escape(_type_label(row.get('class')))}<br>"
        f"Confidence: {confidence:.0%} — {confidence_label}<br>"
        f"Priority: {html.escape(str(row.get('priority_band', 'Not ranked')))} — {html.escape(_priority_reason(row))}<br>"
        f"District: {html.escape(str(row.get('district', 'Not recorded')))}<br>"
        f"📍 {lat:.4f}° N, {lon:.4f}° E<br>"
        f'<a href="{directions}" target="_blank">🗺 Get Directions</a> | '
        f'<a href="{location}" target="_blank">📍 View Location</a> | '
        f'<a href="{earth}" target="_blank">🌍 Google Earth</a><br>'
        '<small style="color:#aaa">This is a screening candidate. Verify on the ground before any action.</small>'
    )


def _filtered(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> gpd.GeoDataFrame:
    """Apply the sidebar filter state without rendering UI."""
    return apply_candidate_filters(
        gdf,
        load_config()["rules"],
        districts=None if filters["district"] == "All Districts" else {filters["district"]},
        classes=None if filters["kiln_type"] == "All types" else {"FCBK" if "FCBK" in filters["kiln_type"] else "Zigzag"},
        confidence_range=(filters["confidence"], 1.0),
        priority_bands=filters["priorities"] or {"__none__"},
    )


def _export_csv(gdf: pd.DataFrame) -> str:
    """Create the requested plain-English export."""
    confidence = pd.to_numeric(gdf["confidence"], errors="coerce")
    output = pd.DataFrame({
        "ID": gdf["kiln_id"], "District": gdf["district"], "Type": gdf["class"].map(_type_label),
        "Confidence_Pct": confidence.mul(100).round(1), "Priority": gdf["priority_band"],
        "Latitude": gdf["lat"], "Longitude": gdf["lon"],
        "Nearest_School_m": gdf.get("dist_schools_m"), "Nearest_Hospital_m": gdf.get("dist_hospitals_m"),
        "Rule_Signals": gdf.apply(lambda row: "; ".join(_signals(row)), axis=1),
    })
    return output.to_csv(index=False)


def render_header(gdf: gpd.GeoDataFrame) -> None:
    """Render the app identity, advisory, and four metric chips."""
    st.markdown("<h1 style='margin-bottom:0'>Dhoa</h1>", unsafe_allow_html=True)
    st.caption("Satellite Kiln Inspection Tool — Bangladesh")
    high = int(gdf["priority_band"].eq("High").sum())
    st.markdown(f"<div style='display:flex;gap:28px;margin:18px 0'><div><b>{len(gdf):,}</b><br><small>Total Candidates</small></div><div><b>{high:,}</b><br><small>High Priority</small></div><div><b>{gdf['district'].nunique()}</b><br><small>Districts Scanned</small></div><div><b>{datetime.now(UTC).date().isoformat()}</b><br><small>Last Updated</small></div></div>", unsafe_allow_html=True)


def render_sidebar(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Render controls and return a filter mapping."""
    with st.sidebar, st.expander("Filter", expanded=False):
        st.caption("Find candidates by district, type, severity, and confidence.")
        district = st.selectbox("Select district", DISTRICTS, key="dhoa_district_filter")
        kiln_type = st.selectbox(
            "Kiln type",
            ["All types", "Fixed-chimney (FCBK)", "Zigzag"],
            key="dhoa_kiln_type_filter",
        )
        severity = st.selectbox(
            "Severity", ["All severities", "High", "Medium", "Low"],
            key="dhoa_severity_filter",
        )
        priorities = {severity} if severity != "All severities" else {"High", "Medium", "Low"}
        confidence_pct = st.slider(
            "How certain should the detection be?",
            10,
            90,
            35,
            5,
            format="%d%%",
            key="dhoa_confidence_filter",
        )
        confidence = confidence_pct / 100
    filters = {
        "district": district,
        "kiln_type": kiln_type,
        "priorities": priorities,
        "confidence": confidence,
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
    filtered = _filtered(gdf, filters)
    selected = gdf if filters["district"] == "All Districts" else gdf[gdf["district"].astype(str) == filters["district"]]
    selected = selected if not selected.empty else gdf
    center = [float(selected.lat.mean()), float(selected.lon.mean())]
    fmap = folium.Map(
        location=center,
        zoom_start=7 if filters["district"] == "All Districts" else 10,
        tiles="OpenStreetMap",
    )
    folium.TileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite imagery",
    ).add_to(fmap)
    for _, row in filtered.iterrows():
        color = color_for_kiln(row)
        folium.CircleMarker([float(row.lat), float(row.lon)], radius=7, color=color, fill=True, fill_color=color, fill_opacity=.8, popup=folium.Popup(build_popup(row), max_width=360)).add_to(fmap)
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


def main() -> None:
    """Run the fixed Dhoa page flow."""
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


if __name__ == "__main__":
    main()
