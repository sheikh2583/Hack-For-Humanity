"""Create one-page inspection candidate PDFs without writing files.

Input schema: mapping-like candidate row with kiln ID, district, class,
confidence, priority band, WGS84 coordinates, rule IDs, and distance fields.
Output schema: an A4 PDF as bytes, or ``None`` when PDF generation fails.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

EXPORT_COLUMNS = [
    "ID", "District", "Type", "Confidence_Pct", "Priority_Score",
    "Priority_Band", "Detection_Status", "Latitude", "Longitude",
    "Dist_School_m", "Dist_Hospital_m", "Dist_Railway_m",
    "Dist_Settlement_m", "Dist_Forest_m", "Dist_Water_m",
    "Rule_Signals_Count", "Flagged_For_Review", "Rule_Data_Notes",
    "Breach_Severity_Score", "Top_Rule_Signal",
]
FEATURE_EXPORT_COLUMNS = {
    "schools": "Dist_School_m", "hospitals": "Dist_Hospital_m",
    "railways": "Dist_Railway_m", "settlements": "Dist_Settlement_m",
    "forests": "Dist_Forest_m", "water": "Dist_Water_m",
}
SIGNAL_FIELDS = (
    ("near_school", "Near school", "dist_schools_m"),
    ("near_hospital", "Near hospital", "dist_hospitals_m"),
    ("near_railway", "Near railway", "dist_railways_m"),
    ("near_government_forest", "Near government forest", "dist_forests_m"),
    ("near_settlement", "Near settlement", "dist_settlements_m"),
    ("near_wetland", "Near wetland", "dist_water_m"),
)


def generate_candidate_csv(rows: pd.DataFrame) -> str:
    """Create the dashboard CSV schema from rows and configured siting rules.

    Input: candidate DataFrame with kiln attributes and configured distance
    columns. Output: CSV text with the fixed candidate and mapped-distance
    columns; absent values are empty CSV fields.
    """
    rules_path = Path(__file__).resolve().parents[2] / "config" / "rules.yaml"
    with rules_path.open(encoding="utf-8") as stream:
        rules = yaml.safe_load(stream) or {}
    def get_column(name: str, default: object = "") -> pd.Series:
        return rows[name] if name in rows else pd.Series(default, index=rows.index)

    output = pd.DataFrame(index=rows.index)
    output["ID"] = get_column("kiln_id")
    output["District"] = get_column("district")
    classes = get_column("class", "")
    output["Type"] = classes.map(
        lambda value: "Fixed-chimney kiln (flagged for review)" if str(value) == "FCBK" else "Zigzag kiln"
    )
    output["Confidence_Pct"] = pd.to_numeric(get_column("confidence"), errors="coerce").mul(100).round(1)
    output["Priority_Score"] = get_column("priority", float("nan"))
    output["Priority_Band"] = get_column("priority_band")
    output["Detection_Status"] = get_column("detection_status", "Known").fillna("Known")
    output["Latitude"] = get_column("lat")
    output["Longitude"] = get_column("lon")
    for feature, export_name in FEATURE_EXPORT_COLUMNS.items():
        output[export_name] = pd.to_numeric(
            get_column(f"dist_{feature}_m", float("nan")), errors="coerce"
        ).replace([float("inf"), -float("inf")], float("nan"))
    count_col = "rule_signals_count" if "rule_signals_count" in rows else "breach_count"
    if count_col in rows:
        signal_count = pd.to_numeric(rows[count_col], errors="coerce").fillna(0).astype(int)
    else:
        signals = get_column("breached_rules", []).map(
            lambda value: len(value) if isinstance(value, (list, tuple)) else 0
        )
        signal_count = signals
    output["Rule_Signals_Count"] = signal_count
    flags = pd.to_numeric(signal_count, errors="coerce").fillna(0).gt(0)
    for rule in rules.get("siting_rules", []):
        feature = rule.get("feature")
        buffer_m = rule.get("buffer_m")
        distance_column = f"dist_{feature}_m"
        if buffer_m is not None and distance_column in rows:
            flags |= pd.to_numeric(rows[distance_column], errors="coerce").lt(float(buffer_m))
    output["Flagged_For_Review"] = flags
    output["Rule_Data_Notes"] = get_column("rule_data_notes", float("nan"))
    output["Breach_Severity_Score"] = pd.to_numeric(
        get_column("breach_severity_score", get_column("breach_score", float("nan"))),
        errors="coerce",
    )
    output["Top_Rule_Signal"] = get_column("top_rule_signal", "None")
    return output.reindex(columns=EXPORT_COLUMNS).to_csv(index=False, na_rep="NaN")


def _value(row: dict[str, Any], key: str, default: str = "Not recorded") -> str:
    """Format a candidate field as concise PDF text."""
    value = row.get(key, default)
    return default if value is None else str(value)


def generate_kiln_report(row: dict[str, Any]) -> bytes | None:
    """Generate a single-page A4 report PDF from one candidate row."""
    try:
        from fpdf import FPDF

        today = datetime.now(UTC).date().isoformat()
        lat, lon = float(row["lat"]), float(row["lon"])
        kiln_id = _value(row, "kiln_id")
        directions = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}"
        view = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
        earth = f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y,0h,0t,0r"
        pdf = FPDF(format="A4")
        pdf.core_fonts_encoding = "cp1252"
        pdf.set_auto_page_break(auto=False, margin=12)
        pdf.add_page()
        bengali_font = Path(__file__).resolve().parent / "fonts" / "NotoSansBengali-Regular.ttf"
        pdf.add_font("NotoBengali", fname=str(bengali_font))
        pdf.set_font("NotoBengali", size=16)
        pdf.set_text_shaping(
            use_shaping_engine=True,
            direction="ltr",
            script="beng",
            language="ben",
        )
        pdf.cell(40, 10, "ধোঁয়া")
        pdf.set_text_shaping(use_shaping_engine=False)
        pdf.set_font("Helvetica", "B", 17)
        pdf.cell(0, 10, "- Inspection Candidate Report", new_x="LMARGIN", new_y="NEXT")
        pdf.set_title("ধোঁয়া - Inspection Candidate Report")
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 6, f"Date generated: {today}", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        fields = [
            ("Candidate ID", kiln_id), ("District", _value(row, "district")),
            ("Type", _value(row, "class", _value(row, "class_name"))),
            ("Priority", _value(row, "priority_band")),
            ("Coordinates", f"{lat:.6f}, {lon:.6f}"),
            ("Detection Status", _value(row, "detection_status", "Known")),
        ]
        for label, value in fields:
            pdf.cell(42, 7, label, border=1)
            pdf.set_font("Helvetica", size=9)
            pdf.cell(0, 7, str(value)[:105], border=1, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "B", 10)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Rule Signals", new_x="LMARGIN", new_y="NEXT")
        breached_rules = row.get("breached_rules", [])
        if hasattr(breached_rules, "tolist") and not isinstance(breached_rules, str):
            breached_rules = breached_rules.tolist()
        if isinstance(breached_rules, str):
            try:
                breached_rules = json.loads(breached_rules)
            except json.JSONDecodeError:
                breached_rules = [
                    item.strip() for item in breached_rules.split(",") if item.strip()
                ]
        if not isinstance(breached_rules, (list, tuple)):
            breached_rules = []
        breached_ids = {
            str(signal)
            for signal in breached_rules
            if signal is not None
        }
        rules_path = Path(__file__).resolve().parents[2] / "config" / "rules.yaml"
        with rules_path.open(encoding="utf-8") as stream:
            configured_rules = yaml.safe_load(stream) or {}
        thresholds = {
            str(rule["id"]): float(rule["buffer_m"])
            for rule in configured_rules.get("siting_rules", [])
            if rule.get("id") is not None and rule.get("buffer_m") is not None
        }
        pdf.set_font("Helvetica", size=9)
        added_signal = False
        for signal_id, signal_label, distance_column in SIGNAL_FIELDS:
            threshold = thresholds.get(signal_id)
            distance = pd.to_numeric(
                pd.Series([row.get(distance_column)]), errors="coerce"
            ).iloc[0]
            if (
                threshold is None
                or pd.isna(distance)
                or (signal_id not in breached_ids and float(distance) > threshold)
            ):
                continue
            added_signal = True
            pdf.multi_cell(
                0,
                5,
                f"- {signal_label}: {float(distance):,.0f} m",
                new_x="LMARGIN",
                new_y="NEXT",
            )
        if "technology_flagged" in breached_ids:
            added_signal = True
            pdf.multi_cell(
                0,
                5,
                "- Fixed chimney technology",
                new_x="LMARGIN",
                new_y="NEXT",
            )
        if not added_signal:
            pdf.cell(0, 5, "No triggered rule signals recorded.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Navigation", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=8)
        for link in (f"Google Maps Directions: {directions}", f"Google Maps View: {view}", f"Google Earth: {earth}"):
            for offset in range(0, len(link), 62):
                pdf.cell(0, 4, link[offset : offset + 62], new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(-19)
        pdf.set_font("Helvetica", size=8)
        pdf.multi_cell(0, 4, f"Advisory only \u2014 generated {today}. This is a screening candidate. Field verification required before any inspection action.")
        return bytes(pdf.output())
    except Exception:
        logger.exception("Could not generate kiln candidate PDF")
        return None

