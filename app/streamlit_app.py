"""KilnWatch BD — advisory screening dashboard.

Streamlit app displaying detected kilns on a Folium map with:
- Sidebar filters (district, kiln class, min confidence)
- Priority-coloured markers
- Candidate rule signals, mapped-feature distances, and source provenance
- Advisory-only notices on the page and every marker popup
- CSV export of filtered list

Loads only from data/processed/. Runs fully offline with no external API calls.

Usage
-----
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from app.data_loader import load_kilns as load_kilns_from_parquet
from app.popup import build_marker_popup
from app.presentation import (
    DASHBOARD_LABELS,
    DETAIL_COLUMN_RENAMES,
    marker_tooltip,
    screening_csv,
    with_signal_provenance,
)

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=DASHBOARD_LABELS["page_title"],
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data" / "processed"
KILNS_FILE = DATA_DIR / "kilns_prioritised.parquet"


@st.cache_data
def load_kilns() -> pd.DataFrame:
    """Load prioritised kilns from GeoParquet."""
    if not KILNS_FILE.exists():
        st.error(
            f"Data file not found: `{KILNS_FILE}`.\n\n"
            "Run the full pipeline first:\n"
            "```\n"
            "kilnwatch convert ...\n"
            "kilnwatch infer ...\n"
            "kilnwatch check-rules\n"
            "kilnwatch score\n"
            "```"
        )
        st.stop()

    return load_kilns_from_parquet(KILNS_FILE)


# ---------------------------------------------------------------------------
# Banners
# ---------------------------------------------------------------------------

def show_banners(df: pd.DataFrame) -> None:
    """Display an advisory that distinguishes screening from confirmation."""
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #ff6b35, #f7931e);
                    color: white; padding: 12px 20px; border-radius: 8px;
                    margin-bottom: 16px; font-weight: 600; text-align: center;
                    font-size: 1.1em;">
            ⚠️ {DASHBOARD_LABELS['advisory']}
        </div>
        """,
        unsafe_allow_html=True,
    )



# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters and return filtered DataFrame."""
    st.sidebar.markdown("## 🔍 Filters")

    # District filter
    districts = sorted(df["district"].unique().tolist())
    selected_districts = st.sidebar.multiselect(
        "District",
        options=districts,
        default=districts,
    )

    # Class filter
    classes = sorted(df["class"].unique().tolist())
    selected_classes = st.sidebar.multiselect(
        "Detected Class",
        options=classes,
        default=classes,
    )

    # Confidence filter
    min_conf = st.sidebar.slider(
        "Minimum Detector Confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.05,
    )

    # Priority filter
    if "priority_rank" in df.columns:
        max_rank = int(df["priority_rank"].max())
        top_n = st.sidebar.slider(
            DASHBOARD_LABELS["priority_filter"],
            min_value=1,
            max_value=max(max_rank, 1),
            value=min(50, max_rank),
        )
    else:
        top_n = len(df)

    # Apply filters
    mask = (
        df["district"].isin(selected_districts)
        & df["class"].isin(selected_classes)
        & (df["confidence"] >= min_conf)
    )
    if "priority_rank" in df.columns:
        mask = mask & (df["priority_rank"] <= top_n)

    return df[mask].copy()


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

def render_map(df: pd.DataFrame) -> None:
    """Render the Folium map with colour-coded kiln markers."""
    import folium
    from streamlit_folium import st_folium

    if df.empty:
        st.warning("No kiln candidates match the current filters.")
        return

    # Centre map on mean location
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles=None,
    )

    # Screening-priority colour scale
    def _priority_color(priority_rank: int, total: int) -> str:
        """Map priority rank to a colour from red (highest) to green (lowest)."""
        if total <= 1:
            return "#e74c3c"
        ratio = (priority_rank - 1) / (total - 1)
        if ratio < 0.33:
            return "#e74c3c"   # high priority — red
        elif ratio < 0.66:
            return "#f39c12"   # medium — orange
        else:
            return "#27ae60"   # low — green

    total = len(df)

    for _, row in df.iterrows():
        rank = row.get("priority_rank", 1)
        color = _priority_color(int(rank), total)

        popup_html = build_marker_popup(row, int(rank), total)

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=marker_tooltip(row, int(rank)),
        ).add_to(m)

    st_folium(m, width=None, height=600, returned_objects=[])


# ---------------------------------------------------------------------------
# Stats panel
# ---------------------------------------------------------------------------

def render_stats(df: pd.DataFrame) -> None:
    """Render summary statistics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(DASHBOARD_LABELS["count"], len(df))
    with col2:
        signaled = (df.get("breach_count", pd.Series([0])) > 0).sum()
        st.metric(DASHBOARD_LABELS["signals"], int(signaled))
    with col3:
        flagged = df.get("technology_flagged", pd.Series([False])).sum()
        st.metric(DASHBOARD_LABELS["technology"], int(flagged))
    with col4:
        if "priority" in df.columns:
            st.metric(DASHBOARD_LABELS["max_score"], f"{df['priority'].max():.1f}")


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def csv_export(df: pd.DataFrame) -> None:
    """Provide a CSV download button for the filtered data."""
    csv = screening_csv(df)
    st.download_button(
        label=DASHBOARD_LABELS["export"],
        data=csv,
        file_name="kilnwatch_filtered.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Main dashboard entry point."""
    st.markdown(
        f"""
        <h1 style="text-align: center; margin-bottom: 0;">
            🏭 KilnWatch BD
        </h1>
        <p style="text-align: center; color: #888; margin-top: 4px; margin-bottom: 20px;">
            {DASHBOARD_LABELS['subtitle']}
        </p>
        """,
        unsafe_allow_html=True,
    )

    df = load_kilns()
    show_banners(df)

    filtered = sidebar_filters(df)

    render_stats(filtered)

    st.markdown("---")

    # Map
    st.subheader("🗺️ " + DASHBOARD_LABELS["map_title"])
    render_map(filtered)

    st.markdown("---")

    # Data table
    st.subheader("📋 " + DASHBOARD_LABELS["table_title"])
    display_cols = [
        "kiln_id", "class", "confidence", "district", "breached_rules",
        "signal_provenance_json", "breach_count", "breach_score", "priority_rank",
    ]
    detail_rows = with_signal_provenance(filtered)
    display_cols = [c for c in display_cols if c in detail_rows.columns]
    st.dataframe(
        detail_rows[display_cols].rename(columns=DETAIL_COLUMN_RENAMES),
        use_container_width=True,
        hide_index=True,
    )

    csv_export(filtered)

    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888; font-size: 0.85em;'>"
        "KilnWatch BD · Hack for Humanity Bangladesh 2026 · "
        "Data: SentinelKilnDB (CC BY-NC 4.0)"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
