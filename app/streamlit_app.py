"""Dhoa dashboard: one cached data load, one map builder, and plain-English UI."""

from __future__ import annotations

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
DISTRICT_CENTERS = {
    "All Districts": (23.80, 90.30),
    "Chapainawabganj": (24.60, 88.35),
    "Gazipur": (24.10, 90.20),
    "Rajshahi": (24.30, 88.45),
    "Dhaka": (23.80, 90.30),
    "Chittagong": (22.50, 91.90),
}


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
        return f"near {label} {distance:,.0f} m" if pd.notna(distance) else f"{label} signal"
    return "no rule signal recorded"


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
    """Build plain-English popup details for one candidate row."""
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
        "schools": "school",
        "hospitals": "hospital",
        "railways": "railway",
        "settlements": "settlement",
        "forests": "forest",
        "water": "wetland",
        "wetlands": "wetland",
    }
    lines = []
    for feature in features:
        key = "water" if feature == "wetlands" else feature
        value = pd.to_numeric(pd.Series([row.get(f"dist_{key}_m")]), errors="coerce").iloc[0]
        distance = "No mapping data" if pd.isna(value) else (f"{value / 1000:.1f} km" if value >= 1000 else f"{value:,.0f} m")
        rule = configured.get(feature, {})
        threshold = rule.get("buffer_m")
        warning = " \u26a0\ufe0f" if threshold is not None and pd.notna(value) and value < float(threshold) else ""
        severity = int(rule.get("severity", 0))
        severity_name = {3: "critical", 2: "moderate", 1: "low"}.get(severity)
        severity_text = f" (severity: {severity_name})" if severity_name else ""
        title = "Near" if rule else "Nearest"
        lines.append(f"{title} {labels.get(feature, feature)}: {distance}{severity_text}{warning}")
    if any(rule.get("id") == "near_wetland" for rule in rules):
        lines.append(
            "Note: water layer is an OSM proxy. Legal definition requires land submerged \u2265 6 months/year (Act s.8 explanation (\u0996))."
        )
    if any(rule.get("id") == "near_government_forest" for rule in rules):
        lines.append(
            "Forest layer: HDX/LGED 2013 archive. May not reflect current legal boundaries. Replace with Protected Planet BFD 2025 for production use."
        )
    badge = "\U0001f195 New 2025-26\n" if row.get("detection_status") == "New candidate (2025-26)" else ""
    return f"{badge}Kiln Candidate #{row.get('kiln_id', 'unknown')}\nType: {_type_label(row.get('class'))}\nPriority: {row.get('priority_band', 'Not ranked')} — {_priority_reason(row)}\nDistrict: {row.get('district', 'Not recorded')}\n\U0001f4cd {lat:.4f}° N, {lon:.4f}° E\n" + "\n".join(lines)


def build_google_maps_url(latitude: float, longitude: float, zoom: int, satellite: bool = False) -> str:
    """Build a no-key Google Maps embed URL from WGS84 center coordinates."""
    satellite_parameter = "&t=k" if satellite else ""
    return f"https://www.google.com/maps?q={latitude:.6f},{longitude:.6f}&z={zoom}{satellite_parameter}&output=embed"


def _kiln_list_frame(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build a selectable candidate table aligned to its filtered source rows."""
    records: list[dict[str, object]] = []
    icons = {"High": "\U0001f534 High", "Medium": "\U0001f7e0 Medium", "Low": "\U0001f7e2 Low"}
    for position, (_, row) in enumerate(gdf.iterrows(), start=1):
        rank = row.get("priority_rank", position)
        confidence = pd.to_numeric(pd.Series([row.get("confidence")]), errors="coerce").iloc[0]
        signal = row.get("top_rule_signal")
        if signal is None or pd.isna(signal) or str(signal) == "None":
            signal = _priority_reason(row)
        records.append({"#": int(rank) if pd.notna(rank) else position, "Priority": icons.get(str(row.get("priority_band", "")), str(row.get("priority_band", "Unknown"))), "Type": "FCBK" if str(row.get("class", "")) == "FCBK" else "Zigzag", "Confidence": f"{confidence * 100:.1f}%" if pd.notna(confidence) else "No data", "Top Rule Signal": str(signal), "District": str(row.get("district", "Not recorded"))})
    return pd.DataFrame(records, columns=["#", "Priority", "Type", "Confidence", "Top Rule Signal", "District"])


def _filtered(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> gpd.GeoDataFrame:
    """Apply the sidebar filter state without rendering UI."""
    result = apply_candidate_filters(
        gdf,
        load_config()["rules"],
        districts=None if filters["district"] == "All Districts" else {filters["district"]},
        classes=None if filters["kiln_type"] == "All types" else {"FCBK" if "FCBK" in filters["kiln_type"] else "Zigzag"},
        confidence_range=filters.get("confidence_range", (0.0, 1.0)),
        priority_bands=filters["priorities"] or {"__none__"},
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
    """Render the app identity, advisory, and four metric chips."""
    st.markdown("<h1 style='margin-bottom:0'>Dhoa</h1>", unsafe_allow_html=True)
    st.caption("Satellite Kiln Inspection Tool — Bangladesh")
    high = int(gdf["priority_band"].eq("High").sum())
    new_count = int(gdf.get("detection_status", pd.Series("Known", index=gdf.index)).eq("New candidate (2025-26)").sum())
    flagged = _flagged_count(gdf, load_config()["rules"])
    st.markdown(f"<div style='display:flex;gap:28px;margin:18px 0'><div><b>{len(gdf):,}</b><br><small>Total Candidates</small></div><div><b>{high:,}</b><br><small>High Priority</small></div><div><b>{new_count:,}</b><br><small>New Candidates</small></div><div><b>{flagged:,}</b><br><small>Flagged for rule review</small></div><div><b>{datetime.now(UTC).date().isoformat()}</b><br><small>Last Updated</small></div></div>", unsafe_allow_html=True)


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
        str(rule.get("id")): f"Near {str(rule.get('feature', '')).rstrip('s')}"
        for rule in load_config()["rules"].get("siting_rules", [])
    }
    rule_names["technology_flagged"] = "FCBK technology"
    top_rule_signal = (
        rule_names.get(str(signal_counts.index[0]), str(signal_counts.index[0]))
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
        ("Total Candidates", "High Priority", "Estimated Coverage (km²)", "Top rule signal"),
        (len(selected), high_count, f"{coverage_km2:,.2f}", top_rule_signal),
    ):
        column.metric(label, value)
    risk_count = len(high_risk_rows) if near else len(high_rows)
    st.info(f"{risk_count} high-priority candidates near {risk_scope} detected in {district}.")


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
            on_change=_sync_google_map_mode_from_sidebar,
        )
        severity = st.selectbox(
            "Severity", ["All severities", "High", "Medium", "Low"],
            key="dhoa_severity_filter",
        )
        priorities = {severity} if severity != "All severities" else {"High", "Medium", "Low"}
        confidence_range = st.slider(
            "Confidence",
            min_value=0.0,
            max_value=1.0,
            value=(0.0, 1.0),
            step=0.05,
        )
        new_only = st.checkbox("🆕 New candidates only", value=False, key="dhoa_new_only")
    filters = {
        "district": district,
        "kiln_type": kiln_type,
        "map_style": map_style,
        "priorities": priorities,
        "confidence_range": confidence_range,
        "new_only": new_only,
    }
    visible = _filtered(gdf, filters)
    with st.sidebar:
        st.markdown(f"**Showing {len(visible):,} of {len(gdf):,} candidates**")
        slug = district.lower().replace(" ", "_") if district != "All Districts" else "all_districts"
        today = datetime.now(UTC).strftime("%Y%m%d")
        st.download_button("⬇ Export Filtered CSV", _export_csv(visible), f"dhoa_{slug}_{today}.csv", "text/csv", width="stretch")
    return filters


def _sync_google_map_mode_from_sidebar() -> None:
    """Keep the map radio in sync with the existing sidebar map filter."""
    st.session_state["dhoa_google_map_mode"] = "\U0001f6f0 Satellite" if st.session_state.get("dhoa_map_style_filter") == "Satellite imagery" else "\U0001f5fa Street Map"


def _sync_sidebar_style_from_google_map() -> None:
    """Keep the existing sidebar map filter in sync with the map radio."""
    st.session_state["dhoa_map_style_filter"] = "Satellite imagery" if st.session_state.get("dhoa_google_map_mode") == "\U0001f6f0 Satellite" else "Street map"


def _render_selected_candidate(row: pd.Series) -> None:
    """Render selected kiln details, navigation links, and PDF download control."""
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", "unknown"))
    st.subheader(f"Kiln Candidate #{candidate_id}")
    st.write(f"**Type:** {_type_label(row.get('class'))}")
    confidence = pd.to_numeric(pd.Series([row.get("confidence")]), errors="coerce").iloc[0]
    st.write(f"**Confidence:** {confidence:.1%}" if pd.notna(confidence) else "**Confidence:** No data")
    st.write(f"**Priority:** {row.get('priority_band', 'Not ranked')} — {_priority_reason(row)}")
    st.write(f"**District:** {row.get('district', 'Not recorded')}")
    st.write(f"**Detection status:** {row.get('detection_status', 'Known')}")
    st.write(f"**Coordinates:** {lat:.5f}, {lon:.5f}")
    for line in build_popup(row).splitlines():
        if line.startswith(("Near ", "Nearest ")):
            st.write(line)
    columns = st.columns(4)
    directions = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving"
    street_view = f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},3a,90y,0h,90t/data=!3m1!1e3"
    earth = f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y"
    columns[0].link_button("\U0001f5fa Get Directions", directions, width="stretch")
    columns[1].link_button("\U0001f4cd Street View", street_view, width="stretch")
    columns[2].link_button("\U0001f30d Google Earth", earth, width="stretch")
    try:
        report = _report_from_json(json.dumps(row.to_dict(), default=_json_default, sort_keys=True))
        if report is None:
            st.error("Could not generate the inspection report.")
        else:
            safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in candidate_id)
            filename = f"kilnrank_report_{safe_id}_{datetime.now(UTC):%Y%m%d}.pdf"
            columns[3].download_button("\U0001f4c4 Download Report", report, filename, "application/pdf", width="stretch")
    except Exception as exc:  # noqa: BLE001 - report generation boundary
        st.error(f"Could not generate the inspection report: {exc}")


def build_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render a selectable candidate list beside a no-key Google Maps iframe."""
    filtered = _filtered(gdf, filters)
    mode = "\U0001f6f0 Satellite" if filters.get("map_style") == "Satellite imagery" else "\U0001f5fa Street Map"
    st.session_state.setdefault("dhoa_google_map_mode", mode)
    st.radio("Map style", ["\U0001f5fa Street Map", "\U0001f6f0 Satellite"], horizontal=True, key="dhoa_google_map_mode", on_change=_sync_sidebar_style_from_google_map)
    satellite = st.session_state["dhoa_google_map_mode"] == "\U0001f6f0 Satellite"
    list_panel, map_panel = st.columns([2, 3])
    with list_panel:
        st.markdown(f"**Showing {len(filtered):,} of {len(gdf):,} candidates**")
        table = _kiln_list_frame(filtered)
        selection = st.dataframe(table, hide_index=True, height=600, on_select="rerun", selection_mode="single-row", key="dhoa_candidate_list")
    selected_id = st.session_state.get("selected_kiln_id")
    selected_rows = selection.selection.rows
    if selected_rows:
        selected_id = str(filtered.iloc[selected_rows[0]].get("kiln_id"))
        st.session_state["selected_kiln_id"] = selected_id
    row = None
    if selected_id is not None and "kiln_id" in filtered.columns:
        matches = filtered[filtered["kiln_id"].astype(str).eq(str(selected_id))]
        if not matches.empty:
            row = matches.iloc[0]
        else:
            st.session_state["selected_kiln_id"] = None
    with map_panel:
        if row is not None:
            lat, lon, zoom = float(row.lat), float(row.lon), 15
        else:
            lat, lon = DISTRICT_CENTERS.get(str(filters.get("district", "All Districts")), DISTRICT_CENTERS["All Districts"])
            zoom = 7 if filters.get("district") == "All Districts" else 10
        st.iframe(build_google_maps_url(lat, lon, zoom, satellite), height=600)
        if row is not None:
            _render_selected_candidate(row)
        else:
            st.info("Select a kiln from the list to view its details.")


def render_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the candidate list and Google Maps panel."""
    build_map(gdf, filters)


def render_footer(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the single summary line below the map."""
    visible = _filtered(gdf, filters)
    high = int(visible["priority_band"].eq("High").sum())
    flagged = _flagged_count(visible, load_config()["rules"])
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
    if "detection_status" not in gdf.columns:
        gdf["detection_status"] = "Known"
    render_header(gdf)
    filters = render_sidebar(gdf)
    render_district_summary(str(filters["district"]), gdf)
    render_map(gdf, filters)
    render_footer(gdf, filters)


if __name__ == "__main__":
    main()
