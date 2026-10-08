"""Offline-safe advisory map for KilnWatch detection candidates.

Input schema: a processed ``kilns*.parquet`` GeoParquet with point or polygon
geometry and a class label. Output: filtered interactive map, candidate table,
and advisory CSV export.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import streamlit as st
import yaml

from app.dashboard_filters import add_priority_bands, apply_candidate_filters
from app.data_loader import load_kilns
from app.popup import ADVISORY_NOTICE
from app.presentation import screening_csv
from src.rules.engine import _ensure_class_column

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/processed"
RULES = ROOT / "config/rules.yaml"


def load_data(path: Path = DATA_DIR / "kilns.parquet") -> gpd.GeoDataFrame:
    """Load candidate GeoParquet into the canonical class and WGS84 schema."""
    return _ensure_class_column(load_kilns(path))


def latest_kilns_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Return the most recently modified processed candidate GeoParquet."""
    candidates = [path for path in data_dir.glob("kilns*.parquet") if path.is_file()]
    return max(candidates, key=lambda path: path.stat().st_mtime, default=None)


def _distance_label(row: pd.Series, column: str) -> str:
    """Format a recorded mapped-feature distance for a marker popup."""
    value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
    return f"{value:,.0f} m" if pd.notna(value) else "Not recorded"


def main() -> None:
    """Render the candidate map, compact filters, table, and CSV export."""
    st.set_page_config(
        page_title="KilnWatch BD", page_icon=":material/map:", layout="wide"
    )
    st.title("KilnWatch BD")
    st.caption("Satellite-based kiln screening across Bangladesh")
    kilns_file = latest_kilns_file()
    if kilns_file is None:
        st.info("No screening results are available yet.")
        return

    with RULES.open(encoding="utf-8") as stream:
        rules: dict[str, Any] = yaml.safe_load(stream)
    frame = add_priority_bands(load_data(kilns_file))

    st.sidebar.header("Explore candidates")
    if st.sidebar.button("Clear filters", key="clear_candidate_filters"):
        for key in list(st.session_state):
            if key.startswith("kiln_filter_"):
                del st.session_state[key]
        st.rerun()

    district_values = (
        sorted(frame["district"].dropna().astype(str).unique())
        if "district" in frame.columns else []
    )
    selected_districts = set(st.sidebar.multiselect(
        "District", district_values, key="kiln_filter_district"
    )) or None if district_values else None

    class_values = sorted(frame["class"].dropna().astype(str).unique())
    selected_classes = set(st.sidebar.multiselect(
        "Kiln class", class_values, key="kiln_filter_class"
    )) or None if class_values else None

    confidence_range: tuple[float, float] | None = None
    if "confidence" in frame.columns:
        confidence = pd.to_numeric(frame["confidence"], errors="coerce").dropna()
        if len(confidence) and confidence.min() < confidence.max():
            confidence_range = st.sidebar.slider(
                "Detector confidence",
                float(confidence.min()), float(confidence.max()),
                (float(confidence.min()), float(confidence.max())),
                key="kiln_filter_confidence",
            )

    priority_values = (
        sorted(frame["priority_band"].dropna().astype(str).unique())
        if "priority_band" in frame.columns else []
    )
    selected_bands = set(st.sidebar.multiselect(
        "Inspection priority", priority_values, key="kiln_filter_priority_band"
    )) or None if priority_values else None

    filtered = apply_candidate_filters(
        frame, rules, districts=selected_districts, classes=selected_classes,
        confidence_range=confidence_range, priority_bands=selected_bands,
    )
    fcbk_count = int((filtered["class"] == "FCBK").sum())
    zigzag_count = int((filtered["class"] == "Zigzag").sum())
    count_col, fcbk_col, zigzag_col = st.columns(3)
    count_col.metric("Candidates shown", f"{len(filtered):,}")
    fcbk_col.metric("FCBK", f"{fcbk_count:,}")
    zigzag_col.metric("Zigzag", f"{zigzag_count:,}")

    if filtered.empty:
        st.info("No candidates match these filters.")
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
    st.caption("Select a marker for candidate details. Switch between street and satellite map styles with the layer control.")

    rule_names = {
        str(rule.get("id")): str(rule.get("id", "")).replace("_", " ").title()
        for rule in rules.get("siting_rules", [])
    }
    if rules.get("technology"):
        rule_names["technology_flagged"] = "Technology screening signal"
    colors = {"High": "red", "Medium": "orange", "Low": "green"}
    for _, row in filtered.iterrows():
        band = str(row.get("priority_band", ""))
        color = colors.get(band, "blue")
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
            rule_names.get(str(signal), str(signal).replace("_", " ").title())
            for signal in signals
        ) or "None recorded"
        confidence = pd.to_numeric(pd.Series([row.get("confidence")]), errors="coerce").iloc[0]
        confidence_text = f"{confidence:.1%}" if pd.notna(confidence) else "Not recorded"
        popup = (
            f"<b>Kiln candidate</b><br>Class: {row.get('class', 'Unknown')}<br>"
            f"Confidence: {confidence_text}<br>Screening signals: {signal_text}<br>"
            f"Nearest mapped school: {_distance_label(row, 'dist_schools_m')}<br>"
            f"Inspection priority: {band or 'Not ranked'}"
        )
        folium.CircleMarker(
            [float(row.lat), float(row.lon)], radius=7, color=color,
            fill=True, fill_color=color,
            popup=folium.Popup(popup, max_width=320),
        ).add_to(map_obj)
    st.markdown(":red-badge[High] :orange-badge[Medium] :green-badge[Low]  Relative inspection priority")
    st_folium(map_obj, width=None, height=600, returned_objects=[])

    st.subheader("Candidate details")
    table = filtered.drop(columns=["geometry", "__index_level_0__"], errors="ignore")
    table = table.rename(columns={
        "class": "Kiln class", "confidence": "Detector confidence",
        "priority_band": "Inspection priority", "priority_rank": "Priority rank",
        "breached_rules": "Screening signals", "dist_schools_m": "School distance (m)",
        "dist_hospitals_m": "Hospital distance (m)",
    })
    display_columns = [
        name for name in ["kiln_id", "district", "Kiln class", "Detector confidence",
                          "Inspection priority", "Priority rank", "Screening signals",
                          "School distance (m)", "Hospital distance (m)"]
        if name in table.columns
    ]
    st.dataframe(table[display_columns], width="stretch", hide_index=True)
    st.download_button(
        "Download candidate data (CSV)", screening_csv(filtered),
        "kiln_screening_candidates.csv", "text/csv",
    )
    with st.expander("About this screening"):
        st.caption(ADVISORY_NOTICE)
        st.caption("Mapped-feature signals support review; they do not determine legal compliance.")


if __name__ == "__main__":
    main()
