"""Dhoa dashboard with shared Bangla labels and two public-facing views."""

from __future__ import annotations

import html
import json
import logging
import sys
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

DASHBOARD_TITLE = unicodedata.normalize("NFC", "\u09a7\u09cb\u0981\u09af\u09bc\u09be")
assert "\u0981" in DASHBOARD_TITLE, repr(DASHBOARD_TITLE)

st.set_page_config(page_title=DASHBOARD_TITLE, layout="wide", initial_sidebar_state="expanded")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_ROOT / "app"))

import folium
import geopandas as gpd
import pandas as pd
import yaml
from branca.element import Element
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

# isort: off
from dashboard_filters import ( 
    SIGNAL_PRESENT,
    add_priority_bands,
    apply_candidate_filters,
)
from data_loader import load_kilns 
from src.rules.engine import _ensure_class_column 
# isort: on

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_PATH = DATA_DIR / "kilns_prioritised.parquet"
_priority_candidate_list = components.declare_component(
    "dhoa_priority_candidate_list",
    path=str(_ROOT / "app" / "components" / "priority_candidate_list"),
)
DESIGN_COLORS = {
    "high": "#e53e3e",
    "medium": "#dd6b20",
    "low": "#38a169",
    "new": "#3182ce",
    "advisory": "#d69e2e",
    "background": "#0e1117",
    "card": "#1e2329",
    "text": "#fafafa",
}
PRIORITY_COLORS = {
    "High": DESIGN_COLORS["high"],
    "Medium": DESIGN_COLORS["medium"],
    "Low": DESIGN_COLORS["low"],
}
DISTRICTS = ["All Districts", "Chapainawabganj", "Gazipur", "Rajshahi", "Dhaka", "Chittagong"]
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
    return """
<style>
@import url("https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap");
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100%; padding: 0.75rem 1.25rem 1.5rem;
}
[data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding-top: 0.75rem !important;
}
/* Hide heading permalinks only; keep map, navigation, and export links usable. */
[data-testid="stHeaderActionElements"],
h1 a, h2 a, h3 a, h4 a,
[role="heading"] a, [role="heading"] button,
h1 [data-testid="stHeaderActionElements"],
h2 [data-testid="stHeaderActionElements"],
h3 [data-testid="stHeaderActionElements"],
h4 [data-testid="stHeaderActionElements"],
[role="heading"] [data-testid="stHeaderActionElements"] { display: none !important; }
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] { margin-top: 0.2rem; }
[data-testid="stMetric"] { min-width: 0; }
/* Replace Streamlit's developer-oriented status icon with a Bengali loading cue. */
[data-testid="stStatusWidget"],
[data-testid^="stStatusWidget"],
[data-testid="stStatusWidgetRunningIcon"] {
    width: auto !important;
    height: auto !important;
    min-width: 0;
    margin-right: 0.4rem !important;
    overflow: visible !important;
}
[data-testid="stStatusWidget"] > *,
[data-testid^="stStatusWidget"] > *,
[data-testid="stStatusWidgetRunningIcon"] svg,
[data-testid="stStatusWidgetRunningIcon"] img { display: none !important; }
[data-testid="stStatusWidget"]::after,
[data-testid^="stStatusWidget"]::after,
[data-testid="stStatusWidgetRunningIcon"]::after {
    content: "";
    display: block;
    max-width: 220px;
    color: #dbe3ec;
    font-family: "Noto Sans Bengali", "Nirmala UI", "Vrinda", sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.35;
    white-space: nowrap;
}
.dhoa-metrics {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: clamp(0.5rem, 1.2vw, 1rem);
    width: 100%;
    margin: 0.5rem 0 1rem;
}
.dhoa-metric { min-width: 0; padding: 0.35rem 0.65rem; border-left: 2px solid #475569; }
.dhoa-metric strong { display: block; font-size: 1.15rem; line-height: 1.3; }
.dhoa-metric span { display: block; color: #aab4c0; font-size: 0.82rem; line-height: 1.35; }
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button,
[data-baseweb="select"] > div,
[data-testid="stSlider"] [role="slider"] { min-height: 44px; }
.dhoa-mobile-map-hint {
    display: none;
    margin: 0.25rem 0 0.65rem;
    color: #cbd5e1;
    font-size: 0.9rem;
}
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding: 0.65rem 0.75rem 1.5rem;
    }
    [data-testid="stMainBlockContainer"] { padding-top: 1.35rem !important; }
    [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.75rem; }
    [data-testid="stMetricContainer"] { min-width: 0; }
    [data-testid="stStatusWidgetRunningIcon"]::after {
        max-width: 115px;
        font-size: 0.7rem;
        line-height: 1.3;
        white-space: normal;
        text-align: right;
    }
    [data-testid="stIFrame"] iframe {
        width: 100% !important; height: 52vh !important;
        min-height: 280px !important; max-height: 500px !important;
    }
    .st-key-dhoa_map_frame iframe {
        width: 100% !important;
        height: 52vh !important;
        min-height: 300px !important;
        max-height: 500px !important;
    }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    .dhoa-metrics { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem !important; }
    .dhoa-mobile-map-hint { display: block !important; }
}
@media (max-width: 480px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-left: 0.5rem; padding-right: 0.5rem;
    }
    body, p, label, [data-testid="stCaptionContainer"] { font-size: 14px; }
}
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
    display: block !important;
    box-sizing: border-box !important;
    width: 100% !important;
    padding: 0.38em 0 0.12em !important;
    margin-top: 0.35rem !important;
    line-height: 1.8 !important;
    overflow: visible !important;
    font-family: "Noto Sans Bengali", sans-serif !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
}
[data-testid="stMainBlockContainer"] h1.dhoa-brand-title span {
    font-family: "Noto Sans Bengali", sans-serif !important;
    font-feature-settings: "kern", "liga", "mark", "mkmk" !important;
    font-kerning: normal !important;
    font-variant-ligatures: contextual common-ligatures !important;
    line-height: inherit !important;
    overflow: visible !important;
}
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] h1.dhoa-brand-title {
        font-size: 1.9rem !important;
        line-height: 1.8 !important;
        padding-top: 0.38em !important;
        padding-bottom: 0.12em !important;
    }
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


def _type_label(value: object) -> str:
    """Return a concise Bengali label for the kiln type."""
    return "\u09ab\u09bf\u0995\u09cd\u09b8\u09a1 \u099a\u09bf\u09ae\u09a8\u09bf \u0987\u099f\u09ad\u09be\u099f\u09be" if str(value) == "FCBK" else "\u099c\u09bf\u0997\u099c\u09cd\u09af\u09be\u0997 \u0987\u099f\u09ad\u09be\u099f\u09be"


def _priority_label(value: object) -> str:
    """Translate an internal priority band for display."""
    return {"High": "উচ্চ", "Medium": "মাঝারি", "Low": "নিম্ন"}.get(str(value), "নির্ধারিত নয়")


def _district_label(value: object) -> str:
    """Translate district options while preserving unknown district names."""
    return {
        "All Districts": "সব জেলা",
        "Chapainawabganj": "চাঁপাইনবাবগঞ্জ",
        "Gazipur": "গাজীপুর",
        "Rajshahi": "রাজশাহী",
        "Dhaka": "ঢাকা",
        "Chittagong": "চট্টগ্রাম",
    }.get(str(value), str(value))


def _signal_label(value: object) -> str:
    """Translate known rule identifiers for dashboard display."""
    translated = {
        "near_school": "স্কুলের কাছে",
        "near_hospital": "হাসপাতালের কাছে",
        "near_settlement": "বসতির কাছে",
        "near_railway": "রেলপথের কাছে",
        "near_wetland": "জলাভূমির কাছে",
        "near_government_forest": "সরকারি বনের কাছে",
        "technology_flagged": "ফিক্সড চিমনি প্রযুক্তি",
    }.get(str(value))
    if translated:
        return translated
    label = str(value)
    for english, bangla in (("Near school", "স্কুলের কাছে"), ("Near hospital", "হাসপাতালের কাছে"), ("Near settlement", "বসতির কাছে"), ("Near railway", "রেলপথের কাছে"), ("Near wetland", "জলাভূমির কাছে"), ("Near government forest", "সরকারি বনের কাছে")):
        label = label.replace(english, bangla)
    return label


def _signals(row: pd.Series) -> list[str]:
    value = row.get("breached_rules", [])
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(signal) for signal in value if signal is not None and pd.notna(signal) and str(signal).strip().casefold() not in {"", "nan", "none"}]


def _area_label(row: Mapping[str, object], fallback: str = "district") -> str:
    """Format stored OSM place enrichment or a district/coordinate fallback.

    Input schema: candidate mapping with optional nearest_place, distance,
    place type, district, lat, and lon. Output schema: display string.
    """
    name = row.get("nearest_place")
    if name is not None and pd.notna(name) and str(name).strip():
        distance = pd.to_numeric(pd.Series([row.get("nearest_place_dist_m")]), errors="coerce").iloc[0]
        district = row.get("district")
        district_text = _district_label(district) if district is not None and pd.notna(district) else ""
        area = f"{name}, {district_text}" if district_text else str(name)
        if pd.notna(distance):
            return f"{area} \u09a5\u09c7\u0995\u09c7 {distance:.0f} \u09ae\u09bf\u099f\u09be\u09b0 \u09a6\u09c2\u09b0\u09c7"
        return area
    if fallback == "coordinates":
        latitude = pd.to_numeric(pd.Series([row.get("lat")]), errors="coerce").iloc[0]
        longitude = pd.to_numeric(pd.Series([row.get("lon")]), errors="coerce").iloc[0]
        return f"{latitude:.4f}° উত্তর, {longitude:.4f}° পূর্ব" if pd.notna(latitude) and pd.notna(longitude) else "অবস্থান পাওয়া যায়নি"
    district = row.get("district")
    return f"জেলা: {_district_label(district)}" if district is not None and pd.notna(district) else "জেলার তথ্য নেই"


def _place_type_label(value: str) -> str:
    """Translate OSM place types for consistent Bangla area labels."""
    return {
        "village": "গ্রাম", "town": "শহর", "hamlet": "ছোট বসতি",
        "suburb": "শহরতলি", "neighbourhood": "মহল্লা", "city": "নগর",
    }.get(value.casefold(), value)


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
        translated = {"school": "স্কুল", "hospital": "হাসপাতাল", "settlement": "বসতি", "railway": "রেলপথ", "wetland": "জলাভূমি", "government forest": "সরকারি বন"}.get(label, label)
        return f"{translated} থেকে {distance:,.0f} মিটার" if pd.notna(distance) else f"{translated}-সংক্রান্ত সংকেত"
    return "কোনো নিয়ম-সংকেত নথিভুক্ত নেই"


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
    """Calculate kiln distances from a searched WGS84 point.

    Input schema: kiln GeoDataFrame with numeric ``lat``/``lon`` columns in
    EPSG:4326 and a WGS84 search coordinate. Output: distances in metres,
    indexed like the input frame, measured in the selected local projected CRS.
    """
    from src.geo.crs import get_projected_crs

    projected_crs = get_projected_crs(longitude)
    search_point = gpd.GeoSeries(
        gpd.points_from_xy([longitude], [latitude]), crs="EPSG:4326"
    ).to_crs(projected_crs).iloc[0]
    kiln_points = gpd.GeoSeries(
        gpd.points_from_xy(gdf["lon"], gdf["lat"], crs="EPSG:4326"), index=gdf.index
    ).to_crs(projected_crs)
    return kiln_points.distance(search_point)


def community_alert_pdf(location: str, rows: pd.DataFrame, radius_m: int) -> bytes:
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
        pdf.multi_cell(0, 6, "এই প্রতিবেদনটি কমিউনিটি সচেতনতার জন্য — শুধুমাত্র তথ্যের উদ্দেশ্যে।", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 16)
    title_separator = "—" if has_bengali_font else "-"
    pdf.multi_cell(0, 9, f"Dhoa {title_separator} Community Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf_location = location if has_bengali_font else location.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 7, f"Kiln Candidates Near {pdf_location}", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 7, f"Generated: {datetime.now(UTC):%Y-%m-%d}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.multi_cell(
        0, 6,
        f"{len(rows)} kiln candidates were identified within {radius_m / 1000:g} km of {pdf_location} using satellite imagery analysis of the 2025-26 dry season.",
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
            f"{row['distance_m']:.0f} m", str(row.get("class", "Unknown")),
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


def render_community_view(gdf: gpd.GeoDataFrame) -> None:
    """Render the shared community search, result map/table, and alert PDF.

    Input schema: prioritized kiln GeoDataFrame with lat/lon, class,
    priority, and optional OSM place fields. Output schema: a
    community search form, adjustable-radius result summary, map, and result table.
    """
    st.markdown("<div class='dhoa-section-title'>\u0986\u09aa\u09a8\u09be\u09b0 \u098f\u09b2\u09be\u0995\u09be\u09b0 \u0995\u09be\u099b\u09be\u0995\u09be\u099b\u09bf \u0996\u09c1\u0981\u099c\u09c1\u09a8</div>", unsafe_allow_html=True)
    with st.container(border=True), st.form("community_search_form", border=False):
            name = st.text_input('\u09a8\u09be\u09ae \u09b2\u09bf\u0996\u09c1\u09a8', placeholder='\u09af\u09c7\u09ae\u09a8: Chapainawabganj Government Primary School')
            coordinate_columns = st.columns(2, gap="small")
            latitude = coordinate_columns[0].number_input("\u0985\u0995\u09cd\u09b7\u09be\u0982\u09b6 (Latitude)", value=0.0, min_value=-90.0, max_value=90.0, format="%.6f", help="\u09af\u09c7\u09ae\u09a8: 23.8103")
            longitude = coordinate_columns[1].number_input("\u09a6\u09cd\u09b0\u09be\u0998\u09bf\u09ae\u09be\u0982\u09b6 (Longitude)", value=0.0, min_value=-180.0, max_value=180.0, format="%.6f", help="\u09af\u09c7\u09ae\u09a8: 90.4125")
            submitted = st.form_submit_button('\U0001f50d \u0996\u09c1\u0981\u099c\u09c1\u09a8', width="stretch")
            st.caption("\u09a8\u09be\u09ae \u09a6\u09bf\u09df\u09c7 \u0996\u09cb\u0981\u099c\u09c1\u09a8, \u09a8\u09be \u09b8\u09cd\u09a5\u09be\u09a8\u09be\u0999\u09cd\u0995 \u09a6\u09bf\u09df\u09c7 \u0996\u09c1\u0981\u099c\u09c1\u09a8; \u09a8\u09be\u09ae \u09a6\u09bf\u09b2\u09c7 \u09b8\u09cd\u09a5\u09be\u09a8\u09be\u0999\u09cd\u0995 \u0997\u09a3\u09cd\u09af \u0995\u09b0\u09be \u09b9\u09ac\u09c7 \u09a8\u09be\u0964")
    if submitted:
        st.session_state.pop("community_search", None)
        st.session_state.pop("community_report", None)
        location_name = name.strip()
        if location_name:
            try:
                from geopy.geocoders import Nominatim
                loc = Nominatim(user_agent="dhoa-bd").geocode(f"{location_name}, Bangladesh", timeout=10)
            except Exception:  # noqa: BLE001 - geocoding/import are an external service boundary
                st.warning('\u26a0\ufe0f \u09a8\u09be\u09ae\u09c7\u09b0 \u0996\u09cb\u0981\u099c\u09be\u09af\u09bc \u09ac\u09cd\u09af\u09b0\u09cd\u09a5\u0964 \u09ac\u09be\u09a8\u09be\u09a8 \u09b2\u09bf\u0996\u09c1\u09a8 \u0985\u09a5\u09ac\u09be \u099c\u09c7\u09b2\u09be\u09b0 \u09a8\u09be\u09ae \u09af\u09cb\u0997 \u0995\u09b0\u09c1\u09a8\u0964')
                return
            if loc is None:
                st.warning("\u26a0\ufe0f \u09b8\u09cd\u09a5\u09be\u09a8\u09c7\u09b0 \u09a8\u09be\u09ae \u09aa\u09be\u0993\u09af\u09bc\u09be\u09af\u09a8\u09bf\u0964 \u09b8\u09cd\u09aa\u09c7\u09b2\u09bf\u0982\u09af\u09bc\u09be\u099f\u09bf\u0982\u09af\u09bc\u09c7\u09b0 \u09b8\u09be\u09a5\u09c7 \u099c\u09c7\u09b2\u09be\u09b0 \u09a8\u09be\u09ae \u09af\u09cb\u0997 \u0995\u09b0\u09c1\u09a8\u0964")
                return
            point = (float(loc.latitude), float(loc.longitude))
        else:
            location_name = f"{latitude:.5f}, {longitude:.5f}"
            point = (float(latitude), float(longitude))
        st.session_state["community_search"] = (location_name, point)

    search = st.session_state.get("community_search")
    if search is None:
        return
    location_name, (search_lat, search_lon) = search
    radius_m = int(st.slider("\u0985\u09a8\u09c1\u09b8\u09a8\u09cd\u09a7\u09be\u09a8\u09c7\u09b0 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7 (\u09ae\u09bf\u099f\u09be\u09b0)", min_value=250, max_value=5000, value=1000, step=250, key="community_radius_m"))
    distances = community_distances(gdf, search_lat, search_lon)
    nearby = gdf.loc[distances.le(radius_m)].copy()
    nearby["distance_m"] = distances.loc[nearby.index]
    nearby = nearby.sort_values("distance_m")

    result_column, map_column = st.columns([2, 3], gap="medium")
    with result_column:
        st.subheader("\u0995\u09be\u099b\u09be\u0995\u09be\u099b\u09bf\u09b0 \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0")
        with st.container(border=True):
            st.metric(f"Candidates within {radius_m / 1000:g} km radius", f"{len(nearby):,}")
            try:
                report = community_alert_pdf(location_name, nearby, radius_m)
                st.session_state["community_report"] = report
                st.download_button(
                    "Download community report", report,
                    "dhoa_community_report.pdf", "application/pdf",
                    width="stretch", key="community_alert_download",
                )
            except Exception:  # noqa: BLE001 - report generation boundary
                logging.exception("Community PDF generation failed")
                st.error("Could not create the community report. Please try again.")
            if nearby.empty:
                st.success(f"No kiln candidates found within {radius_m / 1000:g} km of this location.")
            else:
                table = pd.DataFrame({
                    "Distance (m)": nearby["distance_m"].round(0).astype("Int64").astype("string").fillna("No data").to_numpy(),
                    "Area": [_area_label(row, fallback="district") for _, row in nearby.iterrows()],
                    "Kiln type": [_type_label(row.get("class")) for _, row in nearby.iterrows()],
                    "Priority": [_priority_label(row.get("priority_band")) for _, row in nearby.iterrows()],
                    "Directions": [
                        f"https://www.google.com/maps/dir/?api=1&destination={float(row['lat']):.6f}%2C{float(row['lon']):.6f}"
                        for _, row in nearby.iterrows()
                    ],
                })
                st.dataframe(
                    table, hide_index=True, width="stretch",
                    column_config={"Directions": st.column_config.LinkColumn(display_text="Open map")},
                )
    with map_column:
        st.subheader("\u098f\u09b2\u09be\u0995\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0")
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:.5rem;margin:.4rem 0'>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{DESIGN_COLORS['new']}'>&#9679;</b> \u0996\u09cb\u0981\u099c\u09be\u09b0 \u09b8\u09cd\u09a5\u09be\u09a8</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['High']}'>&#9679;</b> \u0989\u099a\u09cd\u099a \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['Medium']}'>&#9679;</b> \u09ae\u09be\u099d\u09be\u09b0\u09bf</span>"
            f"<span style='background:#1e2329;padding:.35rem .6rem;border-radius:999px'><b style='color:{PRIORITY_COLORS['Low']}'>&#9679;</b> \u09a8\u09bf\u09ae\u09cd\u09a8</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"\u09a8\u09c0\u09b2 \u09ac\u09c3\u09a4\u09cd\u09a4\u09c7\u09b0 \u09b8\u09c0\u09ae\u09be\u09a8\u09be \u0996\u09cb\u0981\u099c\u09be\u09b0 \u09b8\u09cd\u09a5\u09be\u09a8 \u09a5\u09c7\u0995\u09c7 {radius_m / 1000:g} km \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac \u09a6\u09c7\u0996\u09be\u09df\u0964 \u09b2\u09be\u09b2, \u0995\u09ae\u09b2\u09be \u0993 \u09b8\u09ac\u09c1\u099c \u09ac\u09bf\u09a8\u09cd\u09a6\u09c1 \u09ad\u09be\u099f\u09be\u09b0 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u09a6\u09c7\u0996\u09be\u09df; \u09ac\u09bf\u09a8\u09cd\u09a6\u09c1\u09a4\u09c7 \u099a\u09be\u09aa\u09b2\u09c7 \u09ac\u09bf\u09b8\u09cd\u09a4\u09be\u09b0\u09bf\u09a4 \u09a6\u09c7\u0996\u09c1\u09a8\u0964")
        with st.container(border=True):
            map_view = folium.Map(location=[search_lat, search_lon], zoom_start=13, control_scale=True, tiles="OpenStreetMap")
            map_view.get_root().html.add_child(Element(_popup_styles()))
            folium.CircleMarker(
                [search_lat, search_lon], radius=8, color=DESIGN_COLORS["new"],
                fill=True, fill_color=DESIGN_COLORS["new"], fill_opacity=1,
                tooltip=location_name,
            ).add_to(map_view)
            folium.Circle([search_lat, search_lon], radius=radius_m, color=DESIGN_COLORS["new"], fill=False).add_to(map_view)
            for _, row in nearby.iterrows():
                color = PRIORITY_COLORS.get(str(row.get("priority_band")), DESIGN_COLORS["advisory"])
                popup = folium.Popup(_popup_html(row), min_width=320, max_width=320)
                folium.CircleMarker(
                    location=[float(row["lat"]), float(row["lon"])], radius=7,
                    color=color, fill=True, fill_color=color, fill_opacity=0.88,
                    popup=popup,
                ).add_to(map_view)
            st_folium(map_view, height=580, width=None, key="dhoa_community_map")
            # Mobile users should rotate their device for a wider map.

def _popup_content(row: Mapping[str, object]) -> dict[str, Any]:
    """Build sanitized Bangla display fields shared by all kiln popups.

    Input schema: one kiln row with optional type, place, priority, rule,
    coordinate, and detection fields. Output schema: sanitized display values.
    """
    def present(value: object, fallback: str = "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987") -> str:
        return fallback if value is None or pd.isna(value) or not str(value).strip() else str(value)

    area = _area_label(row)
    priority = _priority_label(row.get("priority_band"))
    latitude = pd.to_numeric(pd.Series([row.get("lat")]), errors="coerce").iloc[0]
    longitude = pd.to_numeric(pd.Series([row.get("lon")]), errors="coerce").iloc[0]
    coordinates = f"{latitude:.5f}\u00b0 \u0989\u09a4\u09cd\u09a4\u09b0, {longitude:.5f}\u00b0 \u09aa\u09c2\u09b0\u09cd\u09ac" if pd.notna(latitude) and pd.notna(longitude) else "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    district_value = row.get("district")
    district = _district_label(district_value) if district_value is not None and pd.notna(district_value) else "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    signals: list[str] = []
    rules = load_config()["rules"].get("siting_rules", [])
    breaches = set(_signals(pd.Series(dict(row))))
    labels = {"schools": "\u09b8\u09cd\u0995\u09c1\u09b2", "hospitals": "\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2", "settlements": "\u09ac\u09b8\u09a4\u09bf", "railways": "\u09b0\u09c7\u09b2\u09aa\u09a5", "water": "\u099c\u09b2\u09be\u09ad\u09c2\u09ae\u09bf", "government_forest": "\u09ac\u09a8"}
    for rule in sorted(rules, key=lambda item: float(item.get("severity", 0)), reverse=True):
        rule_id = str(rule.get("id", ""))
        feature = str(rule.get("feature", ""))
        label = labels.get(feature, feature.replace("_", " "))
        distance = pd.to_numeric(pd.Series([row.get(f"dist_{feature}_m")]), errors="coerce").iloc[0]
        if pd.isna(distance) and feature == "government_forest":
            distance = pd.to_numeric(pd.Series([row.get("dist_forests_m")]), errors="coerce").iloc[0]
        if pd.isna(distance):
            signals.append("\U0001f332 \u09ac\u09a8\u09c7\u09b0 \u09a4\u09a5\u09cd\u09af \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7 \u09a8\u09c7\u0987" if feature == "government_forest" else f"\u26aa {label}: \u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987")
            continue
        threshold = float(rule.get("buffer_m", 0))
        inside = rule_id in breaches or float(distance) < threshold
        icon = "\U0001f534" if inside and int(rule.get("severity", 1)) >= 3 else "\U0001f7e1" if inside else "\U0001f7e2"
        description = f"{float(distance):,.0f} \u09ae\u09bf." if inside else "\u09b8\u09c0\u09ae\u09be\u09b0 \u09ac\u09be\u0987\u09b0\u09c7"
        signals.append(f"{icon} {label}: {description}")
    if not signals:
        signals.append("\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987")
    is_new = str(row.get("detection_status", "")) == "New candidate (2025-26)"
    return {"type": _type_label(row.get("class", row.get("class_name"))), "is_new": is_new,
            "area": area, "priority": priority, "coordinates": coordinates,
            "district": district, "signals": signals, "kiln_id": present(row.get("kiln_id")),
            "latitude": float(latitude) if pd.notna(latitude) else None,
            "longitude": float(longitude) if pd.notna(longitude) else None}


def build_popup(row: pd.Series) -> str:
    """Build ordered plain-text popup content for a kiln candidate."""
    content = _popup_content(row)
    badges = f"[{content['type']}]" + (" [\u09a8\u09a4\u09c1\u09a8]" if content["is_new"] else "")
    separator = "\u2500" * 32
    return "\n".join([badges, f"\u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u00b7 {content['area']}", separator,
        f"\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0: {content['priority']}",
        f"\U0001f4cd \u098f\u09b2\u09be\u0995\u09be: {content['area']}",
        f"{content['coordinates']} \u00b7 {content['district']}", separator,
        "\u09a8\u09bf\u09af\u09bc\u09ae\u09c7\u09b0 \u09b8\u0982\u0995\u09c7\u09a4:", *content["signals"], separator,
        "[\U0001f5fa\ufe0f \u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be] [\U0001f4cd \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0] [\U0001f30d Earth]",
        f"[\U0001f4c4 \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a8\u09ae\u09cd\u09ac\u09b0: {content['kiln_id']}]", separator])


def _popup_html(row: pd.Series) -> str:
    """Render each map popup through the shared escaped 320px template."""
    content = _popup_content(row)
    latitude, longitude = content["latitude"], content["longitude"]
    directions = f"https://www.google.com/maps/dir/?api=1&destination={latitude:.6f}%2C{longitude:.6f}" if latitude is not None else "#"
    maps = f"https://www.google.com/maps?q={latitude:.6f}%2C{longitude:.6f}" if latitude is not None else "#"
    earth = f"https://earth.google.com/web/@{latitude:.6f},{longitude:.6f},500a,500d,35y" if latitude is not None else "#"
    escaped = html.escape
    new_badge = "<span class='badge new-badge'>\u09a8\u09a4\u09c1\u09a8 (\u09e8\u09e6\u09e8\u09eb\u2013\u09e8\u09e8)</span>" if content["is_new"] else ""
    signal_lines = "".join(f"<div>{escaped(signal)}</div>" for signal in content["signals"])
    return ("<div class='dhoa-popup'><div class='badges'>"
        f"<span class='badge'>{escaped(content['type'])}</span>{new_badge}</div>"
        f"<strong>\u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u00b7 {escaped(content['area'])}</strong><hr>"
        f"\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0: {escaped(content['priority'])}<br>"
        f"\U0001f4cd \u098f\u09b2\u09be\u0995\u09be: {escaped(content['area'])}<br>"
        f"{escaped(content['coordinates'])} \u00b7 {escaped(content['district'])}<hr>"
        f"<strong>\u09a8\u09bf\u09af\u09bc\u09ae\u09c7\u09b0 \u09b8\u0982\u0995\u09c7\u09a4:</strong>{signal_lines}<hr>"
        "<div class='popup-actions'>"
        f"<a href='{escaped(directions, quote=True)}' target='_blank' rel='noopener'>\U0001f5fa\ufe0f \u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be</a>"
        f"<a href='{escaped(maps, quote=True)}' target='_blank' rel='noopener'>\U0001f4cd \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0</a>"
        f"<a href='{escaped(earth, quote=True)}' target='_blank' rel='noopener'>\U0001f30d \u0986\u09b0\u09cd\u09a5</a></div>"
        f"<div>\U0001f4c4 \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a8\u09ae\u09cd\u09ac\u09b0: {escaped(content['kiln_id'])}</div><hr></div>")


def _popup_styles() -> str:
    """Return popup CSS using the shared design-system palette."""
    return (
        "<style>"
        f".dhoa-popup{{width:290px;color:{DESIGN_COLORS['text']};line-height:1.45}}"
        f".dhoa-popup hr{{border:0;border-top:1px solid {DESIGN_COLORS['text']};opacity:.35;margin:.45rem 0}}"
        f".dhoa-popup .badge{{background:{DESIGN_COLORS['card']};padding:.1rem .35rem;border-radius:.25rem;font-weight:700}}"
        f".dhoa-popup .new-badge{{background:{DESIGN_COLORS['new']}}}"
        ".dhoa-popup .badges,.dhoa-popup .popup-actions{display:flex;gap:.4rem;flex-wrap:wrap}"
        "</style>"
    )


def _format_distance_cell(row: pd.Series, rule: Mapping[str, Any]) -> str:
    """Format one configured rule distance, marking only in-buffer values.

    Input schema: one candidate row and a siting-rule mapping from rules.yaml.
    Output schema: localized distance text, warning marker, or missing-data text.
    """
    feature = str(rule.get("feature", ""))
    value = pd.to_numeric(
        pd.Series([row.get(f"dist_{feature}_m")]), errors="coerce"
    ).iloc[0]
    if pd.isna(value):
        return "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    rendered = (
        f"{value / 1000:.1f} \u0995\u09bf\u09ae\u09bf"
        if value >= 1000
        else f"{value:,.0f} \u09ae\u09bf"
    )
    threshold = pd.to_numeric(
        pd.Series([rule.get("buffer_m")]), errors="coerce"
    ).iloc[0]
    if pd.notna(threshold) and value < threshold:
        return f"{rendered} \u26a0\ufe0f"
    return rendered

def _kiln_list_frame(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Build a selectable distance table without repeating rule labels per row.

    Input schema: filtered candidate GeoDataFrame with district, coordinates,
    priority, and configured distance fields. Output schema: visible location,
    priority, and one distance column per active siting rule.
    """
    rules = load_config()["rules"].get("siting_rules", [])
    feature_labels = {
        "schools": "\u09b8\u09cd\u0995\u09c1\u09b2",
        "hospitals": "\u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2",
        "railways": "\u09b0\u09c7\u09b2\u09aa\u09a5",
        "settlements": "\u09ac\u09b8\u09a4\u09bf",
        "government_forest": "\u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09ac\u09a8",
        "water": "\u099c\u09b2\u09be\u09ad\u09c2\u09ae\u09bf",
    }
    select_label = "\u09ad\u09be\u099f\u09be\u099f\u09bf \u09a6\u09c7\u0996\u09c1\u09a8"
    location_label = "\u098f\u09b2\u09be\u0995\u09be"
    priority_label = "\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0"
    columns = [select_label, location_label, priority_label]
    columns.extend(
        f"{feature_labels.get(str(rule.get('feature')), str(rule.get('feature')))} \u09a5\u09c7\u0995\u09c7 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac"
        for rule in rules
    )
    icons = {
        "High": "\U0001f534 \u0989\u099a\u09cd\u099a",
        "Medium": "\U0001f7e0 \u09ae\u09be\u099d\u09be\u09b0\u09bf",
        "Low": "\U0001f7e2 \u09a8\u09bf\u09ae\u09cd\u09a8",
    }
    records: list[dict[str, object]] = []
    for _, row in gdf.iterrows():
        location = f"\U0001f4cd {_area_label(row, fallback='coordinates')}"
        record: dict[str, object] = {
            select_label: select_label,
            location_label: location,
            priority_label: icons.get(
                str(row.get("priority_band", "")),
                _priority_label(row.get("priority_band")),
            ),
        }
        for rule, column in zip(rules, columns[3:], strict=True):
            record[column] = _format_distance_cell(row, rule)
        records.append(record)
    return pd.DataFrame(records, columns=columns)


def _priority_table_style(value: object) -> str:
    """Return the centralized design-system style for a priority cell."""
    color = PRIORITY_COLORS.get(str(value), DESIGN_COLORS["advisory"])
    return f"color: {color}; font-weight: 700"


def _filtered(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> gpd.GeoDataFrame:
    """Apply the sidebar filter state without rendering UI."""
    result = apply_candidate_filters(
        gdf,
        load_config()["rules"],
        districts=None if filters["district"] == "All Districts" else {filters["district"]},
        classes=None if filters["kiln_type"] == "All types" else {"FCBK" if "FCBK" in filters["kiln_type"] else "Zigzag"},
        priority_bands=filters["priorities"] or {"__none__"},
        signal_filters=filters.get("signal_filters", {}),
    )
    if filters.get("new_only") and "detection_status" in result.columns:
        result = result[result["detection_status"].eq("New candidate (2025-26)")].copy()
    return result


def _export_csv(gdf: pd.DataFrame) -> str:
    """Create the fixed candidate CSV with configured rule distances."""
    from src.eval.generate_report import generate_candidate_csv

    exported = pd.read_csv(StringIO(generate_candidate_csv(gdf)))
    return exported.drop(columns=["Confidence_Pct"], errors="ignore").to_csv(index=False, na_rep="")


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


def render_header(gdf: gpd.GeoDataFrame) -> str:
    """Render the Dhoa header, mode navigation, and candidate summary metrics."""
    identity, _ = st.columns([5, 2], gap="small", vertical_alignment="center")
    with identity:
        st.markdown(f"<h1 class='dhoa-brand-title'>{html.escape(DASHBOARD_TITLE)}</h1>", unsafe_allow_html=True)
        loaded = dashboard_kilns_file()
        subtitle = "\u09ac\u09be\u0982\u09b2\u09be\u09a6\u09c7\u09b6\u09c7\u09b0 \u0987\u099f\u09ad\u09be\u099f\u09be \u09aa\u09b0\u09cd\u09af\u09ac\u09c7\u0995\u09cd\u09b7\u09a3 \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1"
        if loaded is not None:
            updated = datetime.fromtimestamp(loaded.stat().st_mtime, tz=UTC).date().isoformat()
            subtitle += f" \u00b7 \u09a4\u09a5\u09cd\u09af \u09b9\u09be\u09b2\u09a8\u09be\u0997\u09be\u09a6 {updated}"
        st.caption(subtitle)
    mode = st.segmented_control(
        "\u09ad\u09bf\u0989 \u09ac\u09be\u099b\u09be\u0987 \u0995\u09b0\u09c1\u09a8",
        ["\U0001f3db \u09aa\u09b0\u09bf\u09a6\u09b0\u09cd\u09b6\u0995 \u09ad\u09bf\u0989", "\U0001f3d8 \u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf \u09ad\u09bf\u0989"],
        default="\U0001f3db \u09aa\u09b0\u09bf\u09a6\u09b0\u09cd\u09b6\u0995 \u09ad\u09bf\u0989",
        key="dhoa_view_mode", width="stretch",
    )
    is_community = mode == "\U0001f3d8 \u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf \u09ad\u09bf\u0989"
    with st.popover("\u2754 \u0995\u09c0\u09ad\u09be\u09ac\u09c7 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09ac\u09c7\u09a8?", icon=":material/help:", width="stretch"):
        if is_community:
            st.markdown("""
**\u0995\u09ae\u09bf\u0989\u09a8\u09bf\u099f\u09bf \u09ad\u09bf\u0989 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0**

1. \u09b8\u09cd\u0995\u09c1\u09b2, \u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2 \u09ac\u09be \u098f\u09b2\u09be\u0995\u09be\u09b0 \u09a8\u09be\u09ae \u09b2\u09bf\u0996\u09c1\u09a8 \u0985\u09a5\u09ac\u09be \u0985\u0995\u09cd\u09b7\u09be\u0982\u09b6-\u09a6\u09cd\u09b0\u09be\u0998\u09bf\u09ae\u09be\u0982\u09b6 \u09a6\u09bf\u09a8\u0964 \u09a8\u09be\u09ae \u09a6\u09bf\u09b2\u09c7 \u09b8\u09cd\u09a5\u09be\u09a8\u09be\u0999\u09cd\u0995 \u0997\u09a3\u09cd\u09af \u0995\u09b0\u09be \u09b9\u09ac\u09c7 \u09a8\u09be\u0964

2. **\u0996\u09c1\u0981\u099c\u09c1\u09a8** \u099a\u09be\u09aa\u09c1\u09a8\u0964 \u09ab\u09b2\u09be\u09ab\u09b2 \u0986\u09b8\u09be\u09b0 \u09aa\u09b0 **\u0985\u09a8\u09c1\u09b8\u09a8\u09cd\u09a7\u09be\u09a8\u09c7\u09b0 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7** \u09b8\u09cd\u09b2\u09be\u0987\u09a1\u09be\u09b0 \u09a6\u09bf\u09df\u09c7 250 \u09ae\u09bf\u099f\u09be\u09b0 \u09a5\u09c7\u0995\u09c7 5 \u0995\u09bf\u09ae\u09bf \u09ac\u09be\u099b\u09c1\u09a8\u0964 \u09aa\u09cd\u09b0\u09a4\u09bf \u09a7\u09be\u09aa 250 \u09ae\u09bf\u099f\u09be\u09b0; \u09b6\u09c1\u09b0\u09c1\u09a4\u09c7 1 \u0995\u09bf\u09ae\u09bf \u09a5\u09be\u0995\u09c7\u0964 \u09b8\u0982\u0996\u09cd\u09af\u09be, \u09a4\u09be\u09b2\u09bf\u0995\u09be, \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u0993 PDF \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7 \u0985\u09a8\u09c1\u09af\u09be\u09df\u09c0 \u09b9\u09be\u09b2\u09a8\u09be\u0997 \u09b9\u09ac\u09c7\u0964

3. \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7 \u09a8\u09c0\u09b2 \u09aa\u09bf\u09a8 \u0996\u09cb\u0981\u099c\u09be \u09b8\u09cd\u09a5\u09be\u09a8, \u098f\u09ac\u0982 \u09a8\u09c0\u09b2 \u09ac\u09c3\u09a4\u09cd\u09a4\u09c7\u09b0 \u09b8\u09c0\u09ae\u09be\u09a8\u09be \u09ac\u09be\u099b\u09be \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7 \u09a6\u09c7\u0996\u09be\u09df\u0964 \u09b2\u09be\u09b2, \u0995\u09ae\u09b2\u09be \u0993 \u09b8\u09ac\u09c1\u099c \u09ac\u09bf\u09a8\u09cd\u09a6\u09c1 \u09af\u09a5\u09be\u0995\u09cd\u09b0\u09ae\u09c7 \u0989\u099a\u09cd\u099a, \u09ae\u09be\u099d\u09be\u09b0\u09bf \u0993 \u09a8\u09bf\u09ae\u09cd\u09a8 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0\u09c7\u09b0 \u09ad\u09be\u099f\u09be \u09a6\u09c7\u0996\u09be\u09df\u0964 \u09ac\u09bf\u09b8\u09cd\u09a4\u09be\u09b0\u09bf\u09a4 \u09a6\u09c7\u0996\u09a4\u09c7 \u09ad\u09be\u099f\u09be\u09b0 \u099a\u09bf\u09b9\u09cd\u09a8\u09c7 \u099a\u09be\u09aa \u09a6\u09bf\u09a8\u0964

4. **Download community report** \u09ac\u09be\u099f\u09a8\u099f\u09bf \u09ab\u09b2\u09be\u09ab\u09b2\u09c7\u09b0 \u09aa\u09be\u09b6\u09c7, \u09a4\u09be\u09b2\u09bf\u0995\u09be\u09b0 \u0989\u09aa\u09b0\u09c7 \u09a5\u09be\u0995\u09c7\u0964 \u098f\u099f\u09bf\u09a4\u09c7 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u09ac\u09cd\u09af\u09be\u09b8\u09be\u09b0\u09cd\u09a7 \u0993 \u09ab\u09b2\u09be\u09ab\u09b2 \u09a5\u09be\u0995\u09c7\u0964

""")
        else:
            st.markdown("""
**\u09aa\u09b0\u09bf\u09a6\u09b0\u09cd\u09b6\u0995 \u09ad\u09bf\u0989 \u0995\u09c0\u09ad\u09be\u09ac\u09c7 \u09ac\u09cd\u09af\u09ac\u09b9\u09be\u09b0 \u0995\u09b0\u09ac\u09c7\u09a8**

\u09e7. \u09ac\u09be\u09ae\u09c7\u09b0 **\u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0** \u0996\u09c1\u09b2\u09c7 \u099c\u09c7\u09b2\u09be, \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09a7\u09b0\u09a8, \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u0985\u09a5\u09ac\u09be \u09a8\u09bf\u09df\u09ae\u09c7\u09b0 \u09b8\u0982\u0995\u09c7\u09a4 \u09ac\u09be\u099b\u09c1\u09a8\u0964

\u09e8. **\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0\u09c7\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be** \u09a5\u09c7\u0995\u09c7 \u0987\u099f\u09ad\u09be\u099f\u09be \u09ac\u09be\u099b\u09c1\u09a8, \u0985\u09a5\u09ac\u09be \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7\u09b0 \u099a\u09bf\u09b9\u09cd\u09a8\u09c7 \u099a\u09be\u09aa \u09a6\u09bf\u09df\u09c7 \u09a4\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u0995\u09b0\u09c1\u09a8\u0964 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 \u09a4\u09a5\u09cd\u09af \u09a6\u09c7\u0996\u09a4\u09c7 \u09aa\u09be\u09ac\u09c7\u09a8\u0964

\u09e9. \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0\u09c7 **\u09b0\u09be\u09b8\u09cd\u09a4\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0** \u0985\u09a5\u09ac\u09be **\u09b8\u09cd\u09af\u09be\u099f\u09c7\u09b2\u09be\u0987\u099f \u099b\u09ac\u09bf** \u09ac\u09be\u099b\u09c1\u09a8\u0964 \u09aa\u09cd\u09b0\u09df\u09cb\u099c\u09a8\u09c7 CSV \u09a4\u09be\u09b2\u09bf\u0995\u09be \u0985\u09a5\u09ac\u09be \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u0987\u099f\u09ad\u09be\u099f\u09be\u09b0 PDF \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1 \u0995\u09b0\u09c1\u09a8\u0964
""")
    if is_community:
        st.caption("\u09b8\u09cd\u0995\u09c1\u09b2, \u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2 \u09ac\u09be \u098f\u09b2\u09be\u0995\u09be\u09b0 \u09a8\u09be\u09ae \u09a6\u09bf\u09af\u09bc\u09c7 \u0996\u09c1\u0981\u099c\u09c1\u09a8, \u0985\u09a5\u09ac\u09be \u09ae\u09be\u09a8\u09c1\u09b7\u09bf\u0995 \u09b8\u09cd\u09a5\u09be\u09a8\u09be\u0999\u09cd\u0995 \u09a6\u09bf\u09af\u09bc\u09c7 \u09aa\u09bf\u09a8 \u09a6\u09bf\u09a8।")
        selected_mode = "community"
    else:
        st.caption("\u09b8\u09c1\u09b8\u099c\u09cd\u099c\u09bf\u09a4 \u09ad\u09be\u099f\u09be\u099f\u09bf\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be \u0993 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u09a6\u09c7\u0996\u09c1\u09a8, \u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0 \u09a6\u09bf\u09af\u09bc\u09c7 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u0996\u09c1\u0981\u099c\u09c1\u09a8।")
        selected_mode = "inspector"
    high = int(gdf["priority_band"].eq("High").sum())
    new_count = int(gdf.get("detection_status", pd.Series("Known", index=gdf.index)).eq("New candidate (2025-26)").sum())
    flagged = _flagged_count(gdf, load_config()["rules"])
    items = (
        (f"{len(gdf):,}", "\u09ae\u09cb\u099f \u09ad\u09be\u099f\u09be"),
        (f"{high:,}", "\u099c\u09b0\u09c1\u09b0\u09bf \u09ad\u09be\u099f\u09be"),
        (f"{new_count:,}", "\u09a8\u09a4\u09c1\u09a8 \u0986\u09ac\u09bf\u09b7\u09cd\u0995\u09be\u09b0"),
        (f"{flagged:,}", "\u0986\u0987\u09a8 \u09b2\u0999\u09cd\u0998\u09a8"),
        (datetime.now(UTC).date().isoformat(), "\u09b8\u09b0\u09cd\u09ac\u09b6\u09c7\u09b7 \u09b9\u09be\u09b2\u09a8\u09be\u0997\u09be\u09a6"),
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
    if district == "All Districts":
        return
    selected = gdf[gdf["district"].astype(str).eq(district)]
    high_count = int(selected["priority_band"].astype(str).eq("High").sum())
    signal_values = [signal for _, row in selected.iterrows() for signal in _signals(row)]
    signal_counts = pd.Series(signal_values, dtype="string").value_counts()
    rule_names = {
        str(rule.get("id")): _signal_label(rule.get("id", ""))
        for rule in load_config()["rules"].get("siting_rules", [])
    }
    rule_names["technology_flagged"] = "ফিক্সড চিমনি প্রযুক্তি"
    top_rule_signal = (
        rule_names.get(str(signal_counts.index[0]), _signal_label(signal_counts.index[0]))
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
        ("মোট প্রার্থী", "উচ্চ অগ্রাধিকার", "আনুমানিক এলাকা (বর্গ কিমি)", "প্রধান নিয়ম-সংকেত"),
        (len(selected), high_count, f"{coverage_km2:,.2f}", top_rule_signal),
    ):
        column.metric(label, value)
    risk_count = len(high_risk_rows) if near else len(high_rows)
    bangla_risk_scope = "স্কুল ও হাসপাতালের কাছে" if risk_scope == "schools and hospitals" else "স্কুলের কাছে" if risk_scope == "schools" else "হাসপাতালের কাছে" if risk_scope == "hospitals" else "নিয়ম-সংকেতযুক্ত"
    st.info(f"{_district_label(district)} জেলায় {bangla_risk_scope} {risk_count}টি উচ্চ অগ্রাধিকারপ্রাপ্ত প্রার্থী পাওয়া গেছে।")


def render_sidebar(gdf: gpd.GeoDataFrame, mode: str) -> dict[str, Any]:
    """Render Inspector filters and the persistent export/contact actions."""
    with st.sidebar:
        st.markdown(f"## {DASHBOARD_TITLE}")
        st.divider()
        filters: dict[str, Any] = {
            "district": "All Districts", "kiln_type": "All types",
            "priorities": {"High", "Medium", "Low"}, "new_only": False,
            "signal_filters": {}, "map_style": "Road map",
        }
        if mode == "inspector":
            with st.expander("\u098f\u09b2\u09be\u0995\u09be \u09a6\u09bf\u09df\u09c7 \u0996\u09c1\u0981\u099c\u09c1\u09a8", expanded=False):
                with st.form("inspector_area_search_form", border=False):
                    area_name = st.text_input("\u09b8\u09cd\u0995\u09c1\u09b2, \u09b9\u09be\u09b8\u09aa\u09be\u09a4\u09be\u09b2 \u09ac\u09be \u098f\u09b2\u09be\u0995\u09be\u09b0 \u09a8\u09be\u09ae", key="inspector_area_name", placeholder="\u09af\u09c7\u09ae\u09a8: Chapainawabganj")
                    area_coords = st.columns(2, gap="small")
                    area_lat = area_coords[0].number_input("Latitude", value=24.0, min_value=-90.0, max_value=90.0, format="%.6f", key="inspector_area_lat")
                    area_lon = area_coords[1].number_input("Longitude", value=90.0, min_value=-180.0, max_value=180.0, format="%.6f", key="inspector_area_lon")
                    area_submitted = st.form_submit_button("\U0001f50d \u098f\u09b2\u09be\u0995\u09be \u0996\u09c1\u0981\u099c\u09c1\u09a8", width="stretch")
                if area_submitted:
                    if area_name.strip():
                        try:
                            from geopy.geocoders import Nominatim
                            location = Nominatim(user_agent="dhoa-bd").geocode(f"{area_name.strip()}, Bangladesh", timeout=10)
                        except Exception:  # noqa: BLE001 - external geocoding boundary
                            location = None
                        if location is None:
                            st.warning("\u09b8\u09cd\u09a5\u09be\u09a8\u099f\u09bf \u0996\u09c1\u0981\u099c\u09c7 \u09aa\u09be\u0993\u09df\u09be \u09af\u09be\u09df\u09a8\u09bf; \u09a8\u09be\u09ae \u09ac\u09be \u099c\u09c7\u09b2\u09be\u09b0 \u09a8\u09be\u09ae \u09af\u09cb\u0997 \u0995\u09b0\u09c1\u09a8\u0964")
                        else:
                            st.session_state["inspector_area_search"] = (area_name.strip(), float(location.latitude), float(location.longitude))
                    else:
                        st.session_state["inspector_area_search"] = (f"{area_lat:.5f}, {area_lon:.5f}", float(area_lat), float(area_lon))
                area_search = st.session_state.get("inspector_area_search")
                if area_search:
                    area_label, search_lat, search_lon = area_search
                    nearby_count = int(community_distances(gdf, search_lat, search_lon).le(1000).sum())
                    st.caption(f"{area_label}: 1 km \u098f\u09b0 \u09ae\u09a7\u09cd\u09af\u09c7 {nearby_count:,} \u099f\u09bf \u09ad\u09be\u099f\u09be\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0. \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0 \u098f\u0987 \u098f\u09b2\u09be\u0995\u09be\u09df \u0995\u09c7\u09a8\u09cd\u09a6\u09cd\u09b0\u09bf\u09a4 \u09b9\u09ac\u09c7\u0964")
            with st.expander("\u09ab\u09bf\u09b2\u09cd\u099f\u09be\u09b0", expanded=False):
                districts = ["All Districts", *sorted(gdf["district"].dropna().astype(str).unique())] if "district" in gdf else ["All Districts"]
                filters["district"] = st.selectbox("\u099c\u09c7\u09b2\u09be", districts, format_func=lambda value: "\u09b8\u09ac \u099c\u09c7\u09b2\u09be" if value == "All Districts" else _district_label(value), key="dhoa_district_filter")
                filters["kiln_type"] = st.selectbox("\u09ad\u09be\u099f\u09be\u09b0 \u09a7\u09b0\u09a8", ["All types", "FCBK", "Zigzag"], format_func=lambda value: "\u09b8\u09ac \u09a7\u09b0\u09a8" if value == "All types" else _type_label(value), key="dhoa_kiln_type_filter")
                filters["map_style"] = st.selectbox("\u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0", ["Road map", "Satellite imagery"], format_func=lambda value: "\u09b0\u09be\u09b8\u09cd\u09a4\u09be\u09b0 \u09ae\u09be\u09a8\u099a\u09bf\u09a4\u09cd\u09b0" if value == "Road map" else "\u09b8\u09cd\u09af\u09be\u099f\u09c7\u09b2\u09be\u0987\u099f \u099b\u09ac\u09bf", key="dhoa_map_style")
                filters["priorities"] = set(st.multiselect("\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0", ["High", "Medium", "Low"], default=["High", "Medium", "Low"], format_func=_priority_label, key="dhoa_priority_filter")) or {"__none__"}
                filters["new_only"] = st.checkbox("\U0001f195 \u09b6\u09c1\u09a7\u09c1 \u09a8\u09a4\u09c1\u09a8 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0", value=False, key="dhoa_new_only")
                rules = load_config()["rules"]
                signal_ids = [str(rule.get("id")) for rule in [rules.get("technology", {}), *rules.get("siting_rules", [])] if rule.get("id")]
                selected_signals = st.multiselect("\u09a8\u09bf\u09df\u09ae-\u09b8\u0982\u0995\u09c7\u09a4", signal_ids, format_func=_signal_label, placeholder="\u09b8\u09ac", key="dhoa_signal_filter")
                filters["signal_filters"] = {signal: SIGNAL_PRESENT for signal in selected_signals}
        st.divider()
        visible = _filtered(gdf, filters) if mode == "inspector" else gdf
        if mode == "inspector":
            slug = str(filters["district"]).lower().replace(" ", "_")
            st.download_button("\u2b07 \u09ac\u09be\u099b\u09be\u0987\u0995\u09c3\u09a4 \u09a4\u09be\u09b2\u09bf\u0995\u09be CSV \u09a1\u09be\u0989\u09a8\u09b2\u09cb\u09a1", _export_csv(visible), f"dhoa_{slug}_{datetime.now(UTC):%Y%m%d}.csv", "text/csv", width="stretch", key="sidebar_export_list")
        st.markdown("\u09aa\u09b0\u09bf\u09ac\u09c7\u09b6 \u0985\u09a7\u09bf\u09a6\u09aa\u09cd\u09a4\u09b0\u09c7\u09b0 \u09b9\u099f\u09b2\u09be\u0987\u09a8: \u09e7\u09ec\u09e7\u09e9\u09e7 | [doe.gov.bd](https://doe.gov.bd)")
    return filters

def _render_selected_candidate(row: pd.Series) -> None:
    """Render selected kiln details and navigation without confidence scores."""
    lat, lon = float(row.lat), float(row.lon)
    candidate_id = str(row.get("kiln_id", "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"))
    forest_distance = pd.to_numeric(pd.Series([row.get("dist_government_forest_m")]), errors="coerce").iloc[0]
    if pd.isna(forest_distance):
        forest_distance = pd.to_numeric(pd.Series([row.get("dist_forests_m")]), errors="coerce").iloc[0]
    st.subheader(f"\u2705 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09bf\u09a4 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 \u00b7 \u0987\u099f\u09ad\u09be\u099f\u09be #{candidate_id}")
    forest_distance_label = (
        f"{float(forest_distance):,.0f} \u09ae\u09bf\u099f\u09be\u09b0"
        if pd.notna(forest_distance)
        else "\u09a4\u09a5\u09cd\u09af \u09a8\u09c7\u0987"
    )
    st.markdown(f"**\u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09ac\u09a8 \u09a5\u09c7\u0995\u09c7 \u09a6\u09c2\u09b0\u09a4\u09cd\u09ac:** {forest_distance_label}")
    st.markdown(f"**\u09a7\u09b0\u09a8:** {_type_label(row.get('class'))}")
    st.markdown(f"**\u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0:** {_priority_label(row.get('priority_band'))} \u2014 {_priority_reason(row)}")
    st.markdown(f"**\u098f\u09b2\u09be\u0995\u09be:** {_area_label(row)}")
    detection = "\u09a8\u09a4\u09c1\u09a8 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0 (\u09e8\u09e6\u09e8\u09eb\u2013\u09e8\u09e8)" if row.get("detection_status") == "New candidate (2025-26)" else "\u0986\u0997\u09c7 \u099a\u09bf\u09b9\u09cd\u09a8\u09bf\u09a4 (\u09e8\u09e6\u09e8\u09e9\u2013\u09e8\u09ea \u099c\u09b0\u09bf\u09aa)"
    st.markdown(f"**\u09b6\u09a8\u09be\u0995\u09cd\u09a4\u0995\u09b0\u09a3\u09c7\u09b0 \u0985\u09ac\u09b8\u09cd\u09a5\u09be:** {detection}")
    st.markdown(f"**\u09b8\u09cd\u09a5\u09be\u09a8\u09be\u0999\u09cd\u0995:** {lat:.5f}, {lon:.5f}")
    columns = st.columns(3)
    columns[0].link_button("\U0001f5fa\ufe0f \u09a6\u09bf\u0995\u09a8\u09bf\u09b0\u09cd\u09a6\u09c7\u09b6\u09a8\u09be", f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}&travelmode=driving", width="stretch")
    columns[1].link_button("\U0001f4cd \u09b0\u09be\u09b8\u09cd\u09a4\u09be\u09b0 \u09a6\u09c3\u09b6\u09cd\u09af", f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},3a,90y,0h,90t/data=!3m1!1e3", width="stretch")
    columns[2].link_button("\U0001f30d Earth", f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y", width="stretch")


def _render_report_download(row: pd.Series) -> None:
    """Render the one selected-candidate PDF download control."""
    candidate_id = str(row.get("kiln_id", "unknown"))
    try:
        report = _report_from_json(json.dumps(row.to_dict(), default=_json_default, sort_keys=True))
        if report is None:
            st.error("\u274c \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a4\u09c8\u09b0\u09bf \u0995\u09b0\u09be \u09af\u09be\u09df\u09a8\u09bf\u0964 \u0986\u09ac\u09be\u09b0 \u099a\u09c7\u09b7\u09cd\u099f\u09be \u0995\u09b0\u09c1\u09a8\u0964")
            return
        safe_id = "".join(char if char.isalnum() or char in "-_" else "_" for char in candidate_id)
        filename = f"dhoa_report_{safe_id}_{datetime.now(UTC):%Y%m%d}.pdf"
        st.download_button(
            "📄 নির্বাচিত প্রার্থীর PDF ডাউনলোড",
            report,
            filename,
            "application/pdf",
            width="stretch",
            key=f"kiln_report_{safe_id}",
        )
    except Exception:  # noqa: BLE001 - report generation boundary
        st.error("\u274c \u09aa\u09cd\u09b0\u09a4\u09bf\u09ac\u09c7\u09a6\u09a8 \u09a4\u09c8\u09b0\u09bf \u0995\u09b0\u09be \u09af\u09be\u09df\u09a8\u09bf\u0964 \u0986\u09ac\u09be\u09b0 \u099a\u09c7\u09b7\u09cd\u099f\u09be \u0995\u09b0\u09c1\u09a8\u0964")


def build_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> folium.Map:
    """Build a Folium map with all filtered candidates and priority layers.

    Input schema: candidate GeoDataFrame containing ``lat``, ``lon``,
    ``priority_band`` and optional screening fields, plus the sidebar filter
    mapping. Output schema: Folium map with visible priority marker layers and
    a hidden-by-default weighted heatmap.
    """
    filtered = _filtered(gdf, filters)
    selected_id = st.session_state.get("selected_kiln_id")
    area_search = st.session_state.get("inspector_area_search")
    if area_search:
        center = (float(area_search[1]), float(area_search[2]))
        zoom = 13
    elif selected_id is not None and "kiln_id" in filtered.columns:
        selected = filtered[filtered["kiln_id"].astype(str).eq(str(selected_id))]
        if not selected.empty:
            center = (float(selected.iloc[0]["lat"]), float(selected.iloc[0]["lon"]))
            zoom = 18
        else:
            st.session_state["selected_kiln_id"] = None
            center = DISTRICT_CENTERS.get(
                str(filters.get("district", "All Districts")), DISTRICT_CENTERS["All Districts"]
            )
            zoom = 7 if filters.get("district") == "All Districts" else 10
    elif filters.get("district") == "All Districts" and not filtered.empty:
        center = (float(filtered["lat"].mean()), float(filtered["lon"].mean()))
        zoom = 7
    else:
        center = DISTRICT_CENTERS.get(
            str(filters.get("district", "All Districts")), DISTRICT_CENTERS["All Districts"]
        )
        zoom = 7 if filters.get("district") == "All Districts" else 10

    satellite = filters.get("map_style") == "Satellite imagery"
    map_view = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles=None)
    if area_search:
        folium.CircleMarker(
            location=center, radius=8, color=DESIGN_COLORS["new"],
            fill=True, fill_color=DESIGN_COLORS["new"], fill_opacity=1,
            tooltip=str(area_search[0]),
        ).add_to(map_view)
        folium.Circle(center, radius=1000, color=DESIGN_COLORS["new"], fill=False).add_to(map_view)
    map_view.get_root().html.add_child(
        Element(
            """<style>
            .leaflet-popup-content-wrapper { max-width: min(320px, 76vw); }
            .leaflet-popup-content {
                width: min(280px, 68vw) !important; max-height: 240px;
                overflow-y: auto; overflow-x: hidden; overflow-wrap: anywhere;
            }
            .dhoa-popup { max-width: 280px; overflow-wrap: anywhere; word-break: break-word; }
            @media (max-width: 768px) {
                .leaflet-control-zoom a {
                    width: 40px; height: 40px; line-height: 40px; font-size: 20px;
                }
                .leaflet-control-layers-toggle { width: 40px; height: 40px; }
                .leaflet-control-layers-expanded {
                    max-height: 42vh; overflow-y: auto; font-size: 16px;
                }
                .leaflet-popup-content {
                    width: min(260px, 70vw) !important; max-height: 40vh;
                }
            }
            </style>"""
        )
    )
    folium.TileLayer("OpenStreetMap", name="রাস্তার মানচিত্র", show=not satellite).add_to(map_view)
    folium.TileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="স্যাটেলাইট চিত্র",
        show=satellite,
    ).add_to(map_view)

    heat_points: list[list[float]] = []
    for band, color in PRIORITY_COLORS.items():
        group = MarkerCluster(
        name=f"{_priority_label(band)} অগ্রাধিকার", show=True,
            options={"disableClusteringAtZoom": 12},
        ).add_to(map_view)
        candidates = filtered[filtered["priority_band"].astype(str).eq(band)]
        for _, row in candidates.iterrows():
            latitude, longitude = float(row["lat"]), float(row["lon"])
            marker_label = (
                f"{_priority_label(band)} অগ্রাধিকার | {_type_label(row.get('class'))} | "
                f"{_district_label(row.get('district', 'জেলা নথিভুক্ত নয়'))}"
            )
            popup_html = _popup_html(row)
            is_selected = str(row.get("kiln_id")) == str(selected_id)
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=12 if is_selected else 8,
                color="#111827" if is_selected else color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                weight=4 if is_selected else 2,
                tooltip=f"✓ নির্বাচিত · {marker_label}" if is_selected else marker_label,
                popup=folium.Popup(popup_html, min_width=320, max_width=320),
            ).add_to(group)
            if band == "High":
                raw_weight = pd.to_numeric(pd.Series([row.get("priority")]), errors="coerce").iloc[0]
                weight = float(raw_weight) if pd.notna(raw_weight) else 1.0
                heat_points.append([latitude, longitude, max(0.0, weight)])

    other_candidates = filtered[~filtered["priority_band"].astype(str).isin(PRIORITY_COLORS)]
    if not other_candidates.empty:
        group = folium.FeatureGroup(name="অন্যান্য অগ্রাধিকার", show=True).add_to(map_view)
        for _, row in other_candidates.iterrows():
            popup_html = _popup_html(row)
            is_selected = str(row.get("kiln_id")) == str(selected_id)
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=12 if is_selected else 8,
                color="#111827" if is_selected else "gray",
                fill=True,
                fill_color="gray",
                fill_opacity=0.85,
                weight=4 if is_selected else 2,
                tooltip="✓ নির্বাচিত" if is_selected else None,
                popup=folium.Popup(popup_html, min_width=320, max_width=320),
            ).add_to(group)

    if heat_points:
        HeatMap(
            heat_points,
            name="উচ্চ অগ্রাধিকারের হিটম্যাপ",
            show=False,
            radius=15,
            blur=18,
        ).add_to(map_view)
    folium.LayerControl(collapsed=False).add_to(map_view)
    return map_view


def render_map(gdf: gpd.GeoDataFrame, filters: Mapping[str, Any]) -> None:
    """Render the Folium map and show details/report for a clicked candidate.

    Input schema: candidate GeoDataFrame and sidebar filter mapping. Output:
    an interactive Folium map plus the selected candidate's detail/report panel.
    """
    visible = _filtered(gdf, filters)
    high_candidates = visible[visible["priority_band"].astype(str).eq("High")]
    list_panel, map_panel = st.columns([2, 3], gap="medium")
    with list_panel:
        st.subheader("\U0001f525 \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be")
        st.caption(f"{len(high_candidates):,}\u099f\u09bf \u0989\u099a\u09cd\u099a \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0\u09c7\u09b0 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0")
        if high_candidates.empty:
            st.info("এই ফিল্টারে উচ্চ অগ্রাধিকারের কোনো প্রার্থী নেই।")
        else:
            list_frame = _kiln_list_frame(high_candidates)
            list_choice = _priority_candidate_list(
                columns=list_frame.columns.tolist(),
                rows=list_frame.astype(str).values.tolist(),
                kiln_ids=high_candidates["kiln_id"].astype(str).tolist(),
                selected_id=(
                    str(st.session_state.get("selected_kiln_id"))
                    if st.session_state.get("selected_kiln_id") is not None
                    else None
                ),
                height=640,
                key="dhoa_high_priority_list",
                default=None,
            )
            if isinstance(list_choice, dict):
                click_token = list_choice.get("selection_token")
                if click_token and click_token != st.session_state.get("dhoa_list_selection_token"):
                    chosen_id = list_choice.get("kiln_id")
                    st.session_state["selected_kiln_id"] = str(chosen_id) if chosen_id else None
                    st.session_state["dhoa_list_selection_token"] = click_token
    with map_panel:
        st.caption("চিহ্নের রং অগ্রাধিকার বোঝায়; গাঢ় সীমানা নির্বাচিত প্রার্থীকে দেখায়।")
        selected_id_for_report = st.session_state.get("selected_kiln_id")
        selected_for_report = (
            visible[visible["kiln_id"].astype(str).eq(str(selected_id_for_report))]
            if selected_id_for_report is not None
            else visible.iloc[0:0]
        )
        if selected_for_report.empty:
            st.caption("PDF পেতে তালিকা বা মানচিত্র থেকে একটি প্রার্থী নির্বাচন করুন।")
        else:
            _render_report_download(selected_for_report.iloc[0])
        map_selection_id = st.session_state.get("selected_kiln_id")
        map_key = f"dhoa_folium_map_{map_selection_id or 'all'}"
        if st.session_state.get("dhoa_map_component_key") != map_key:
            st.session_state["dhoa_last_map_click_count"] = None
            st.session_state["dhoa_map_component_key"] = map_key
        with st.container(key="dhoa_map_frame"):
            map_result = st_folium(
                build_map(gdf, filters),
                key=map_key,
                height=580,
                width=None,
                use_container_width=True,
                returned_objects=["last_object_clicked", "last_object_clicked_count"],
            )
    clicked = map_result.get("last_object_clicked") if isinstance(map_result, dict) else None
    click_count = map_result.get("last_object_clicked_count") if isinstance(map_result, dict) else None
    previous_count = st.session_state.get("dhoa_last_map_click_count")
    if clicked and click_count != previous_count and not visible.empty:
        click_lat = pd.to_numeric(pd.Series([clicked.get("lat")]), errors="coerce").iloc[0]
        click_lon = pd.to_numeric(pd.Series([clicked.get("lng")]), errors="coerce").iloc[0]
        if pd.notna(click_lat) and pd.notna(click_lon):
            from pyproj import Geod

            geod = Geod(ellps="WGS84")
            distances = visible.apply(
                lambda row: abs(
                    geod.inv(
                        float(click_lon),
                        float(click_lat),
                        float(row["lon"]),
                        float(row["lat"]),
                    )[2]
                ),
                axis=1,
            )
            clicked_kiln_id = str(visible.loc[distances.idxmin(), "kiln_id"])
            current_kiln_id = st.session_state.get("selected_kiln_id")
            selection_changed = True
            if clicked_kiln_id == current_kiln_id:
                st.session_state["selected_kiln_id"] = None
                st.session_state["dhoa_list_selection_token"] = None
            else:
                st.session_state["selected_kiln_id"] = clicked_kiln_id
        st.session_state["dhoa_last_map_click_count"] = click_count
        if pd.notna(click_lat) and pd.notna(click_lon) and selection_changed:
            st.rerun()

    selected_id = st.session_state.get("selected_kiln_id")
    selected = visible[visible["kiln_id"].astype(str).eq(str(selected_id))] if selected_id is not None else visible.iloc[0:0]
    if selected.empty:
        st.info("বিস্তারিত ও প্রতিবেদন দেখতে মানচিত্রের কোনো ইটভাটার চিহ্নে চাপ দিন।")
    else:
        if st.button("\u09ad\u09be\u099f\u09be\u09b0 \u09a8\u09bf\u09b0\u09cd\u09ac\u09be\u099a\u09a8 \u09ac\u09be\u09a4\u09bf\u09b2 \u0995\u09b0\u09c1\u09a8 \u00b7 \u09b8\u09ac \u09ad\u09be\u099f\u09be \u09a6\u09c7\u0996\u09c1\u09a8", key="dhoa_clear_kiln_selection"):
            st.session_state["selected_kiln_id"] = None
            st.session_state["dhoa_list_selection_token"] = None
            st.session_state["dhoa_last_map_click_count"] = None
            st.rerun()
        _render_selected_candidate(selected.iloc[0])


def render_footer() -> None:
    """Render the shared hotline footer at the end of either view."""
    st.markdown(
        "<div class='dhoa-footer'>\u09a7\u09cb\u0981\u09af\u09bc\u09be \u00b7 DoE \u09b9\u099f\u09b2\u09be\u0987\u09a8: 16131 | doe.gov.bd</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Run the shared Dhoa header, sidebar, and selected mode flow.

    Input schema: local configuration and prioritized GeoParquet.
    Output schema: one Inspector or Community dashboard view.
    """
    st.markdown(responsive_css(), unsafe_allow_html=True)
    with st.empty() as loading_msg:
        loading_msg.info("\u09aa\u09c3\u09b7\u09cd\u09a0\u09be \u09b2\u09cb\u09a1 \u09b9\u099a\u09cd\u099b\u09c7...")
    try:
        load_config()
        gdf = load_data()
    except Exception:
        logging.getLogger(__name__).exception("Dashboard data/configuration load failed")
        loading_msg.empty()
        st.error("\u274c \u09a4\u09a5\u09cd\u09af \u09ac\u09be \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1 \u09b2\u09cb\u09a1 \u0995\u09b0\u09be \u09af\u09be\u09df\u09a8\u09bf\u0964 \u09a6\u09df\u09be \u0995\u09b0\u09c7 \u09aa\u09b0\u09c7 \u099a\u09c7\u09b7\u09cd\u099f\u09be \u0995\u09b0\u09c1\u09a8\u0964")
        return
    if gdf is None:
        st.error("\u274c \u09a1\u09cd\u09af\u09be\u09b6\u09ac\u09cb\u09b0\u09cd\u09a1\u09c7\u09b0 \u09a4\u09a5\u09cd\u09af \u09aa\u09be\u0993\u09df\u09be \u09af\u09be\u099a\u09cd\u099b\u09c7 \u09a8\u09be\u0964 \u09aa\u09cd\u09b0\u09a5\u09ae\u09c7 \u09a1\u09c7\u099f\u09be \u09aa\u09cd\u09b0\u09b8\u09c7\u09b8 \u0995\u09b0\u09c7 \u09a8\u09bf\u09a8\u0964")
        loading_msg.empty()

        return
    from src.geo.crs import get_projected_crs

    centroid_longitude = float(gdf["lon"].mean()) if not gdf.empty else 90.0
    try:
        get_projected_crs(centroid_longitude)
        gdf = add_priority_bands(gdf)
        if "detection_status" not in gdf.columns:
            gdf["detection_status"] = "Known"
        mode = render_header(gdf)
        with st.expander("⚖️ প্রাসঙ্গিক আইন — ইট প্রস্তুত ও ভাটা স্থাপন (নিয়ন্ত্রণ) আইন, ২০১৩"):
            st.markdown("""
**ধারা ৮(১)** — নিষিদ্ধ এলাকায় ইটভাটা স্থাপন করা যাবে না:
- আবাসিক এলাকা (কমপক্ষে ৫০টি পরিবার)
- সিটি কর্পোরেশন, পৌরসভা বা উপজেলা সদর
- সরকারি বা ব্যক্তিমালিকানাধীন বন, অভয়ারণ্য, জলাভূমি
- কৃষি জমি
- প্রতিবেশগত সংকটাপন্ন এলাকা
- ডিগ্রেডেড এয়ার শেড

**ধারা ৮(৩)** — নিম্নবর্ণিত দূরত্বের মধ্যে ইটভাটা নিষিদ্ধ:
- নিষিদ্ধ এলাকার সীমা থেকে **১ কিলোমিটার**
- সরকারি বনাঞ্চল থেকে **২ কিলোমিটার**
- পাহাড়ের পাদদেশ থেকে **০.৫ কিলোমিটার**
- শিক্ষা প্রতিষ্ঠান, হাসপাতাল, রেলপথ থেকে **১ কিলোমিটার**

*সূত্র: ইট প্রস্তুত ও ভাটা স্থাপন (নিয়ন্ত্রণ) আইন, ২০১৩ (সংশোধিত ২০১৯)*
    """)
        filters = render_sidebar(gdf, mode)
        if mode == "community":
            render_community_view(gdf)
            render_footer()
            loading_msg.empty()
            return
        visible = _filtered(gdf, filters)
        render_map(gdf, filters)
        high_count = int(visible.get("priority_band", pd.Series(index=visible.index, dtype="string")).astype(str).eq("High").sum())
        flagged_count = _flagged_count(visible, load_config()["rules"])
        new_status = visible.get("detection_status", pd.Series("Known", index=visible.index))
        new_count = int(new_status.eq("New candidate (2025-26)").sum())
        st.markdown(f"**{high_count:,} \u0989\u099a\u09cd\u099a \u0985\u0997\u09cd\u09b0\u09be\u09a7\u09bf\u0995\u09be\u09b0 | {flagged_count:,} \u09a8\u09bf\u09df\u09ae \u09b8\u0982\u0995\u09c7\u09a4 | {new_count:,} \u09a8\u09a4\u09c1\u09a8 \u09aa\u09cd\u09b0\u09be\u09b0\u09cd\u09a5\u09c0**")
        render_footer()
        loading_msg.empty()
    except Exception:
        logging.getLogger(__name__).exception("Dashboard view rendering failed")
        st.error("\u274c \u098f\u0987 \u09aa\u09be\u09a4\u09be\u099f\u09bf \u09a6\u09c7\u0996\u09be\u09a8\u09cb \u09af\u09be\u099a\u09cd\u099b\u09c7 \u09a8\u09be\u0964 \u09aa\u09c3\u09b7\u09cd\u09a0\u09be\u099f\u09bf \u09b0\u09bf\u09ab\u09cd\u09b0\u09c7\u09b6 \u0995\u09b0\u09c1\u09a8\u0964")
        loading_msg.empty()


if __name__ == "__main__":
    main()
