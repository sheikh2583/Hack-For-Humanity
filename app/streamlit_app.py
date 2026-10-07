"""KilnWatch BD — Interactive Compliance Triage Dashboard.

Streamlit app displaying detected kilns on a Folium map with:
- Sidebar filters (district, kiln class, min confidence)
- Priority-coloured markers
- Detail panel with breached rules, distances, nearby sites
- "Needs verification" badges below confidence threshold
- "Advisory only" banner
- "Rules not verified" banner when rules_verified is false
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
from app.popup import parse_breached_rules

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="KilnWatch BD — Compliance Triage",
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
    """Display advisory and verification banners."""
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #ff6b35, #f7931e);
                    color: white; padding: 12px 20px; border-radius: 8px;
                    margin-bottom: 16px; font-weight: 600; text-align: center;
                    font-size: 1.1em;">
            ⚠️ ADVISORY ONLY — Verify all findings before inspection or enforcement action
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "rules_verified" in df.columns and not df["rules_verified"].all():
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #e74c3c, #c0392b);
                        color: white; padding: 12px 20px; border-radius: 8px;
                        margin-bottom: 16px; font-weight: 600; text-align: center;">
                🚨 RULES NOT VERIFIED — Legal thresholds in rules.yaml have not been confirmed
                against the Act. Do not rely on these results.
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
        "Kiln Class",
        options=classes,
        default=classes,
    )

    # Confidence filter
    min_conf = st.sidebar.slider(
        "Minimum Confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.05,
    )

    # Priority filter
    if "priority_rank" in df.columns:
        max_rank = int(df["priority_rank"].max())
        top_n = st.sidebar.slider(
            "Show Top N by Priority",
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

def render_map(df: pd.DataFrame, confidence_threshold: float = 0.5) -> None:
    """Render the Folium map with colour-coded kiln markers."""
    import folium
    from streamlit_folium import st_folium

    if df.empty:
        st.warning("No kilns match the current filters.")
        return

    # Centre map on mean location
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles=None,
    )

    # Priority-based colour scale
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

        # Build popup
        breached = parse_breached_rules(row.get("breached_rules", []))

        needs_verification = row["confidence"] < confidence_threshold

        popup_html = f"""
        <div style="min-width: 250px; font-family: sans-serif;">
            <h4 style="margin: 0 0 8px 0; color: {color};">
                {'🔴' if rank <= total * 0.33 else '🟡' if rank <= total * 0.66 else '🟢'}
                Kiln {row.get('kiln_id', 'N/A')[:8]}...
            </h4>
            <table style="width: 100%; font-size: 0.9em;">
                <tr><td><b>Class</b></td><td>{row['class']}</td></tr>
                <tr><td><b>Confidence</b></td><td>{row['confidence']:.2%}</td></tr>
                <tr><td><b>Priority Rank</b></td><td>#{rank}</td></tr>
                <tr><td><b>Breach Score</b></td><td>{row.get('breach_score', 'N/A')}</td></tr>
                <tr><td><b>Breached Rules</b></td><td>{', '.join(breached) if breached else 'None'}</td></tr>
            </table>
        """

        # Distance details
        dist_cols = [c for c in row.index if c.startswith("dist_") and c.endswith("_m")]
        if dist_cols:
            popup_html += "<hr style='margin: 4px 0;'><table style='width: 100%; font-size: 0.85em;'>"
            for dc in dist_cols:
                feature = dc.replace("dist_", "").replace("_m", "")
                val = row[dc]
                display = f"{val:.0f} m" if val != float("inf") else "N/A"
                popup_html += f"<tr><td>↔ {feature}</td><td>{display}</td></tr>"
            popup_html += "</table>"

        if needs_verification:
            popup_html += """
            <div style="background: #f39c12; color: white; padding: 4px 8px;
                        border-radius: 4px; margin-top: 8px; text-align: center;
                        font-size: 0.85em; font-weight: 600;">
                ⚠️ NEEDS VERIFICATION (low confidence)
            </div>
            """

        popup_html += "</div>"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"#{rank} | {row['class']} | {row['confidence']:.0%}",
        ).add_to(m)

    st_folium(m, width=None, height=600, returned_objects=[])


# ---------------------------------------------------------------------------
# Stats panel
# ---------------------------------------------------------------------------

def render_stats(df: pd.DataFrame) -> None:
    """Render summary statistics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Kilns", len(df))
    with col2:
        breaching = (df.get("breach_count", pd.Series([0])) > 0).sum()
        st.metric("Breaching Rules", int(breaching))
    with col3:
        flagged = df.get("technology_flagged", pd.Series([False])).sum()
        st.metric("Tech Flagged", int(flagged))
    with col4:
        if "priority" in df.columns:
            st.metric("Max Priority Score", f"{df['priority'].max():.1f}")


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def csv_export(df: pd.DataFrame) -> None:
    """Provide a CSV download button for the filtered data."""
    # Drop geometry for CSV
    export_cols = [c for c in df.columns if c != "geometry"]
    csv = df[export_cols].to_csv(index=False)
    st.download_button(
        label="📥 Export filtered list as CSV",
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
        """
        <h1 style="text-align: center; margin-bottom: 0;">
            🏭 KilnWatch BD
        </h1>
        <p style="text-align: center; color: #888; margin-top: 4px; margin-bottom: 20px;">
            Satellite-Based Brick Kiln Compliance Triage Dashboard
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
    st.subheader("🗺️ Kiln Map")
    render_map(filtered)

    st.markdown("---")

    # Data table
    st.subheader("📋 Kiln Details")
    display_cols = [
        "kiln_id", "class", "confidence", "district",
        "breach_count", "breach_score", "priority_rank",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

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
