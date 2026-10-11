"""Offline-safe advisory map for KilnWatch detection candidates.

Input schema: a processed ``kilns*.parquet`` GeoParquet with point or polygon
geometry and a class label. Output: filtered interactive map, candidate table,
and advisory CSV export.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

# isort: off
from collections.abc import Mapping
from typing import Any

import geopandas as gpd
import pandas as pd
import streamlit as st
import yaml

from dashboard_filters import add_priority_bands, apply_candidate_filters
from data_loader import load_kilns
from popup import sanitize_popup_text
from presentation import screening_csv
from startup import check_prioritised_data
from src.rules.engine import _ensure_class_column
# isort: on

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
RULES = CONFIG_DIR / "rules.yaml"
PRIORITY_COLORS = {"High": "red", "Medium": "orange", "Low": "green"}


def color_for_kiln(row: Mapping[str, object]) -> str:
    """Return the map marker colour for one display-banded candidate row.

    Input schema: a candidate mapping with display-only ``priority_band`` set
    to High, Medium, or Low. Output: the corresponding Folium colour; rows
    without a known priority band use blue.
    """
    return PRIORITY_COLORS.get(str(row.get("priority_band", "")), "blue")


def load_data(path: Path = DATA_DIR / "kilns.parquet") -> gpd.GeoDataFrame:
    """Load candidate GeoParquet into the canonical class and WGS84 schema."""
    return _ensure_class_column(load_kilns(path))


def class_counts(frame: pd.DataFrame) -> tuple[int, int]:
    """Return FCBK and Zigzag counts from a candidate-frame class schema."""
    classes = frame.get("class", pd.Series(dtype="string")).astype("string")
    return int(classes.eq("FCBK").sum()), int(classes.eq("Zigzag").sum())


def rules_are_verified(rules: dict[str, Any]) -> bool:
    """Return whether every configured technology and siting rule has a true status flag."""
    configured = [rules.get("technology", {})] + list(rules.get("siting_rules", []))
    return all(rule.get("verified", True) for rule in configured)


def latest_kilns_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Return the most recently modified processed candidate GeoParquet."""
    candidates = [path for path in data_dir.glob("kilns*.parquet") if path.is_file()]
    return max(candidates, key=lambda path: path.stat().st_mtime, default=None)


def dashboard_kilns_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Return the final prioritised output, with safe processed-file fallbacks."""
    for name in ("kilns_prioritised.parquet", "kilns_scored.parquet", "kilns.parquet"):
        candidate = data_dir / name
        if candidate.is_file():
            return candidate
    return latest_kilns_file(data_dir)


def _distance_label(row: pd.Series, column: str) -> str:
    """Format a recorded mapped-feature distance for a marker popup."""
    value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
    return f"{value:,.0f} m" if pd.notna(value) else "Not recorded"


def main() -> None:
    """Render the candidate map, compact filters, table, and CSV export."""
    st.set_page_config(
        page_title="KilnWatch BD", page_icon=":material/map:", layout="wide"
    )
    st.title("KilnWatch BD", icon=":material/public:")
    st.caption("Explore kiln candidates across Bangladesh")
    missing_data = check_prioritised_data()
    if missing_data is not None:
        st.error(missing_data)
        return
    kilns_file = dashboard_kilns_file()
    if kilns_file is None:
        st.info("No screening results are available yet.")
        return

    with RULES.open(encoding="utf-8") as stream:
        rules: dict[str, Any] = yaml.safe_load(stream)
    frame = add_priority_bands(load_data(kilns_file))

    with st.sidebar:
        st.header("Filters", icon=":material/tune:")
    if st.sidebar.button("Reset filters", icon=":material/restart_alt:", key="clear_candidate_filters"):
        for key in list(st.session_state):
            if key.startswith("kiln_filter_"):
                del st.session_state[key]
        st.rerun()

    district_values = (
        sorted(frame["district"].dropna().astype(str).unique())
        if "district" in frame.columns else []
    )
    selected_district = st.sidebar.selectbox(
        "District", ["All", *district_values], key="kiln_filter_district"
    ) if district_values else "All"
    selected_districts = {selected_district} if selected_district != "All" else None
    class_values = sorted(frame["class"].dropna().astype(str).unique())
    selected_classes = set(st.sidebar.multiselect(
        "Kiln class", class_values, key="kiln_filter_class"
    )) or None if class_values else None

    min_confidence = st.sidebar.slider(
        "Minimum confidence",
        min_value=0.10,
        max_value=0.90,
        value=0.35,
        step=0.05,
        key="kiln_filter_confidence",
    )

    priority_values = (
        sorted(frame["priority_band"].dropna().astype(str).unique())
        if "priority_band" in frame.columns else []
    )
    selected_bands = set(st.sidebar.multiselect(
        "Priority band", priority_values, key="kiln_filter_priority_band"
    )) or None if priority_values else None

    filtered = apply_candidate_filters(
        frame, rules, districts=selected_districts, classes=selected_classes,
        confidence_range=(min_confidence, 1.0), priority_bands=selected_bands,
    )
    fcbk_count = int((filtered["class"] == "FCBK").sum())
    zigzag_count = int((filtered["class"] == "Zigzag").sum())
    count_col, fcbk_col, zigzag_col = st.columns(3)
    count_col.metric("Candidates", f"{len(filtered):,}")
    fcbk_col.metric("FCBK", f"{fcbk_count:,}")
    zigzag_col.metric("Zigzag", f"{zigzag_count:,}")

    if filtered.empty:
        st.info("No candidates match these filters.")
    center_data = (
        frame[frame["district"].astype(str) == selected_district]
        if selected_district != "All" and "district" in frame.columns
        else frame
    )
    if center_data.empty:
        center_data = filtered if not filtered.empty else frame
    center = [float(center_data.lat.mean()), float(center_data.lon.mean())]

    import folium
    from streamlit_folium import st_folium

    map_obj = folium.Map(location=center, zoom_start=7, tiles="OpenStreetMap")
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite", overlay=False, control=True,
    ).add_to(map_obj)
    folium.LayerControl().add_to(map_obj)
    st.subheader("Candidate map", icon=":material/location_on:")
    st.caption("Choose a marker to see its class, confidence, signals, and nearby mapped features.")

    rule_names = {
        str(rule.get("id")): str(rule.get("id", "")).replace("_", " ").title()
        for rule in rules.get("siting_rules", [])
    }
    if rules.get("technology"):
        rule_names["technology_flagged"] = "Technology screening signal"
    for _, row in filtered.iterrows():
        band = str(row.get("priority_band", ""))
        color = color_for_kiln(row)
        signals = row.get("breached_rules", [])
        if isinstance(signals, str):
            try:
                import json
                signals = json.loads(signals)
            except json.JSONDecodeError:
                signals = [signals]
        if not isinstance(signals, (list, tuple)):
            signals = []
        signal_text = ", ".join(
            sanitize_popup_text(rule_names.get(str(signal), str(signal).replace("_", " ").title()))
            for signal in signals
        ) or "None recorded"
        confidence = pd.to_numeric(pd.Series([row.get("confidence")]), errors="coerce").iloc[0]
        confidence_text = f"{confidence:.1%}" if pd.notna(confidence) else "Not recorded"
        popup = (
            f"<b>Kiln candidate</b><br>Class: {sanitize_popup_text(row.get('class', 'Unknown'))}<br>"
            f"Confidence: {confidence_text}<br>Screening signals: {signal_text}<br>"
            f"Nearest mapped school: {sanitize_popup_text(_distance_label(row, 'dist_schools_m'))}<br>"
            f"Priority band: {sanitize_popup_text(band or 'Not ranked')}"
        )
        folium.CircleMarker(
            [float(row.lat), float(row.lon)], radius=7, color=color,
            fill=True, fill_color=color,
            popup=folium.Popup(popup, max_width=320),
        ).add_to(map_obj)
    st.markdown(":red-badge[High] :orange-badge[Medium] :green-badge[Low]  Priority band")
    st_folium(map_obj, width=None, height=600, returned_objects=[])

    st.subheader("Candidate details", icon=":material/table_chart:")
    table = filtered.drop(columns=["geometry", "__index_level_0__"], errors="ignore")
    table = table.rename(columns={
        "class": "Kiln class", "confidence": "Detector confidence",
        "kiln_id": "Candidate ID", "priority_band": "Priority band", "priority_rank": "Rank",
        "breached_rules": "Screening signals", "dist_schools_m": "School distance (m)",
        "dist_hospitals_m": "Hospital distance (m)",
    })
    display_columns = [
        name for name in ["Candidate ID", "district", "Kiln class", "Detector confidence",
                          "Priority band", "Rank", "Screening signals",
                          "School distance (m)", "Hospital distance (m)"]
        if name in table.columns
    ]
    st.dataframe(table[display_columns], width="stretch", hide_index=True)
    st.download_button(
        "Download results (CSV)", screening_csv(filtered),
        "kiln_screening_candidates.csv", "text/csv",
        icon=":material/download:",
    )


if __name__ == "__main__":
    main()
