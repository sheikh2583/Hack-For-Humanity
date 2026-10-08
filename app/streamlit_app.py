"""Offline-safe advisory map for KilnWatch demo detections.

Input schema: ``data/processed/kilns.parquet`` GeoParquet points with
kiln_id, geometry, class_name, confidence, district, lat, lon. Output: Streamlit
map and CSV export; rule IDs and priority are shown only when present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/processed"
RULES = ROOT / "config/rules.yaml"


def rules_are_verified(config: dict[str, Any]) -> bool:
    """Return false when any technology or siting rule is explicitly unverified."""
    return bool(config.get("technology", {}).get("verified", True)) and all(
        bool(rule.get("verified", True)) for rule in config.get("siting_rules", [])
    )


def load_data(path: Path = DATA_DIR / "kilns.parquet") -> gpd.GeoDataFrame:
    """Load the declared GeoParquet detection schema."""
    return gpd.read_parquet(path)


def latest_kilns_file(data_dir: Path = DATA_DIR) -> Path | None:
    """Return the most recently modified ``kilns*.parquet`` file, if any."""
    candidates = [path for path in data_dir.glob("kilns*.parquet") if path.is_file()]
    return max(candidates, key=lambda path: path.stat().st_mtime, default=None)


def main() -> None:
    """Render advisory-only map, summary and CSV export."""
    st.set_page_config(page_title="KilnWatch BD", layout="wide")
    st.error("Advisory only — not legal evidence")
    with RULES.open(encoding="utf-8") as stream:
        rules = yaml.safe_load(stream)
    verified = rules_are_verified(rules)
    if not verified:
        st.warning("Rules not verified")
    kilns_file = latest_kilns_file()
    if kilns_file is None:
        st.info("Run demo_inference.py first")
        return
    frame = load_data(kilns_file)
    classes = frame.get("class_name", pd.Series(dtype=str))
    fcbk = int((classes == "FCBK").sum())
    zigzag = int((classes == "Zigzag").sum())
    st.sidebar.metric("Total detections", len(frame))
    st.sidebar.metric("FCBK count", fcbk)
    st.sidebar.metric("Zigzag count", zigzag)
    district_names = sorted(str(value) for value in frame.get("district", pd.Series(dtype=str)).dropna().unique())
    st.sidebar.metric("District", ", ".join(district_names) or "Unknown")
    st.sidebar.metric("Rules verified", "Yes" if verified else "No")
    if frame.empty:
        center = [23.7, 90.4]
    else:
        center = [float(frame.lat.mean()), float(frame.lon.mean())]
    import folium
    from streamlit_folium import st_folium

    map_obj = folium.Map(location=center, zoom_start=7, tiles=None)
    # Optional basemap; the base map remains blank and usable when the tile host is offline.
    folium.TileLayer("CartoDB positron", name="CartoDB (online)", overlay=False, control=True).add_to(map_obj)
    for index, row in frame.iterrows():
        rank = row.get("priority_rank")
        try:
            rank_num = int(rank)
        except (TypeError, ValueError):
            rank_num = index + 1
        color = "red" if rank_num <= max(1, len(frame) // 3) else "orange" if rank_num <= max(2, 2 * len(frame) // 3) else "green"
        breached = row.get("breached_rules", [])
        if not isinstance(breached, (list, tuple)):
            breached = []
        confidence = float(row.confidence)
        popup = (
            f"<b>{row.get('class_name', 'Unknown')}</b><br>Confidence: {confidence:.3f}<br>"
            f"Breached rule IDs: {', '.join(map(str, breached)) or 'None recorded'}<br>"
            f"Priority rank: {rank if pd.notna(rank) else 'Not calculated'}"
            + ("<br><b>Needs verification</b>" if confidence < 0.3 else "")
        )
        folium.CircleMarker([row.lat, row.lon], radius=7, color=color, fill=True,
                            fill_color=color, popup=folium.Popup(popup, max_width=300)).add_to(map_obj)
    folium.LayerControl().add_to(map_obj)
    st_folium(map_obj, width=None, height=620, returned_objects=[])
    csv_frame = pd.DataFrame(frame.drop(columns="geometry", errors="ignore"))
    st.download_button("Export CSV", csv_frame.to_csv(index=False), "kilns.csv", "text/csv")


if __name__ == "__main__":
    main()
