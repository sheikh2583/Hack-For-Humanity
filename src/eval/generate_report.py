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


def _load_siting_rules() -> list[dict[str, Any]]:
    """Return the configured siting rules (id, feature, buffer_m) from config/rules.yaml."""
    rules_path = Path(__file__).resolve().parents[2] / "config" / "rules.yaml"
    with rules_path.open(encoding="utf-8") as stream:
        configured = yaml.safe_load(stream) or {}
    return [
        rule for rule in configured.get("siting_rules", [])
        if rule.get("id") is not None and rule.get("buffer_m") is not None
    ]


def _clean(row: dict[str, Any], key: str) -> str:
    """Return a stripped string field, empty when missing or NaN."""
    value = row.get(key)
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _breached_ids(row: dict[str, Any]) -> set[str]:
    """Parse the ``breached_rules`` field (list, array, JSON or comma text) into a set."""
    raw = row.get("breached_rules", [])
    if hasattr(raw, "tolist") and not isinstance(raw, str):
        raw = raw.tolist()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = [item.strip() for item in raw.split(",") if item.strip()]
    if not isinstance(raw, (list, tuple)):
        return set()
    return {str(item) for item in raw if item is not None}


def _distance(row: dict[str, Any], columns: tuple[str, ...]) -> float | None:
    """First numeric distance found in ``columns``, or ``None``."""
    for column in columns:
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if not pd.isna(value):
            return float(value)
    return None


def _area_text(row: dict[str, Any], table: dict[str, str]) -> str:
    """Compose "upazila, district" in the report language."""
    from src.eval.pdf_kit import name_text

    parts = [_clean(row, "upazila"), _clean(row, "district")]
    parts[1] = name_text(table, parts[1]) if parts[1] else ""
    return ", ".join(part for part in parts if part) or table["unknown"]


def generate_kiln_report(
    row: dict[str, Any], lang: str = "bn", submission: dict[str, Any] | None = None,
) -> bytes | None:
    """Generate an A4 kiln PDF, optionally with its linked complaint submission.

    Input schema: candidate row fields plus optional report metadata (id, time,
    reason, note, contact, status, and kind). Output: PDF bytes or ``None``.
    """
    try:
        from fpdf import FPDF

        from src.eval import pdf_kit as kit

        table = kit.labels(lang)
        today = datetime.now(UTC).date().isoformat()
        lat, lon = float(row["lat"]), float(row["lon"])
        kiln_id = _clean(row, "kiln_id") or table["not_recorded"]
        directions = f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lon:.6f}"
        view = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
        earth = f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},500a,500d,35y,0h,0t,0r"

        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=False)
        kit.register_fonts(pdf)
        pdf.set_title(f"{table['brand']} - {table['kiln_title']}")
        pdf.add_page()
        margin = pdf.l_margin = pdf.r_margin = 15
        width = pdf.w - 2 * margin
        y = kit.header_band(pdf, table, table["kiln_title"], today)

        # Candidate details
        y = kit.section_title(pdf, margin, y, width, table["sec_candidate"])
        kind = _clean(row, "class") or _clean(row, "class_name")
        place = _clean(row, "nearest_place")
        fields = [
            (table["candidate_id"], kiln_id),
            (table["area"], _area_text(row, table)),
            (table["nearest_place"], place or table["not_recorded"]),
            (table["kiln_type"], kit.name_text(table, kind)),
            (table["priority"], kit.name_text(table, _clean(row, "priority_band"))),
            (table["detection"], kit.detection_text(table, _clean(row, "detection_status"))),
        ]
        label_w = 46.0
        for label, value in fields:
            lines = kit.wrap_text(pdf, value, width - label_w - 4, 9.5)
            height = max(7.0, 5.2 * len(lines) + 2.4)
            pdf.set_fill_color(*kit.BAND)
            pdf.rect(margin, y, label_w, height, style="F")
            kit.put(pdf, margin + 2, y + 1.6, label, 9, True, kit.MUTED)
            for offset, line in enumerate(lines):
                kit.put(pdf, margin + label_w + 3, y + 1.6 + 5.2 * offset, line, 9.5)
            pdf.set_draw_color(*kit.RULE)
            pdf.line(margin, y + height, margin + width, y + height)
            y += height
        y += 6

        # Location
        y = kit.section_title(pdf, margin, y, width, table["sec_location"])
        kit.put(pdf, margin, y, table["coordinates"], 9, True, kit.MUTED)
        kit.put(pdf, margin + label_w + 1, y - 0.8, f"{lat:.6f}, {lon:.6f}", 12, True)
        y += 8
        for text, url in ((table["directions"], directions), (table["map"], view), (table["earth"], earth)):
            used = kit.put(pdf, margin, y, text, 9, False, (29, 78, 216), link=url)
            pdf.set_draw_color(29, 78, 216)
            pdf.line(margin, y + 5.2, margin + used, y + 5.2)
            y += 6.5
        y += 4

        # Distance table over configured siting rules
        y = kit.section_title(pdf, margin, y, width, table["sec_distances"])
        columns = (margin, margin + 70, margin + 108, margin + 138)
        for x, key in zip(columns, ("feature", "distance", "threshold", "status")):
            kit.put(pdf, x, y, table[key], 8.5, True, kit.MUTED)
        y += 6.5
        pdf.set_draw_color(*kit.RULE)
        pdf.line(margin, y - 0.8, margin + width, y - 0.8)
        breached = _breached_ids(row)
        any_signal = False
        for rule in _load_siting_rules():
            feature = str(rule.get("feature"))
            if feature not in kit.FEATURE_LABELS:
                continue
            label_key, distance_columns = kit.FEATURE_LABELS[feature]
            distance = _distance(row, distance_columns)
            threshold = float(rule["buffer_m"])
            if distance is None:
                kind_key, dist_text = "nodata", "-"
            else:
                kind_key = "within" if distance < threshold else "outside"
                dist_text = f"{distance:,.0f} m"
            any_signal = any_signal or kind_key == "within"
            kit.put(pdf, columns[0], y, table[label_key], 9)
            kit.put(pdf, columns[1], y, dist_text, 9)
            kit.put(pdf, columns[2], y, f"{threshold:,.0f} m", 9, False, kit.MUTED)
            kit.status_dot(pdf, columns[3], y + 2.1, kind_key)
            kit.put(pdf, columns[3] + 5, y, table[kind_key], 9)
            y += 6.5
            pdf.set_draw_color(*kit.RULE)
            pdf.line(margin, y - 0.8, margin + width, y - 0.8)
        y += 5

        # Rule signals
        y = kit.section_title(pdf, margin, y, width, table["sec_signals"])
        signals = []
        for rule in _load_siting_rules():
            feature = str(rule.get("feature"))
            if feature in kit.FEATURE_LABELS:
                distance = _distance(row, kit.FEATURE_LABELS[feature][1])
                if distance is not None and distance < float(rule["buffer_m"]):
                    signals.append(f"{table[kit.FEATURE_LABELS[feature][0]]}: {distance:,.0f} m")
        if "technology_flagged" in breached:
            signals.append(table["technology"])
        if not signals:
            signals = [table["no_signals"]]
        for signal in signals:
            y = kit.paragraph(pdf, margin + 4, y, width - 4, signal, 9.5)

        if submission is not None:
            pdf.add_page()
            y = kit.header_band(pdf, table, table["sec_complaint"], today)
            y = kit.section_title(pdf, margin, y, width, table["sec_complaint"])
            linked = bool(_clean(row, "kiln_id")) and not bool(submission.get("not_linked"))
            complaint_fields = [
                (table["report_id"], submission.get("id")),
                (table["submitted"], submission.get("created_at")),
                (table["report_kind"], submission.get("kind")),
                (table["reason"], submission.get("reason")),
                (table["report_status"], submission.get("status")),
                (table["report_contact"], submission.get("contact")),
                (table["report_note"], submission.get("note")),
            ]
            if not linked:
                y = kit.paragraph(pdf, margin, y, width, table["not_linked"], 10, True)
                y += 5
            label_width = 42.0
            for label, raw_value in complaint_fields:
                value = str(raw_value or "").strip() or table["not_recorded"]
                lines = kit.wrap_text(pdf, value, width - label_width - 5, 9.5)
                height = max(8.0, 5.8 * len(lines) + 3)
                if y + height > pdf.h - 22:
                    pdf.add_page()
                    y = kit.header_band(pdf, table, table["sec_complaint"], today)
                    y = kit.section_title(pdf, margin, y, width, table["sec_complaint"])
                pdf.set_fill_color(*kit.BAND)
                pdf.rect(margin, y, label_width, height, style="F")
                kit.put(pdf, margin + 2, y + 1.7, label, 8.5, True, kit.MUTED)
                for offset, line in enumerate(lines):
                    kit.put(pdf, margin + label_width + 4, y + 1.7 + 5.8 * offset, line, 9.5)
                pdf.set_draw_color(*kit.RULE)
                pdf.line(margin, y + height, margin + width, y + height)
                y += height

        page_count = len(pdf.pages)
        for page_number in range(1, page_count + 1):
            pdf.page = page_number
            kit.footer(pdf, table, page_number, page_count)
        return bytes(pdf.output())
    except Exception:
        logger.exception("Could not generate kiln candidate PDF")
        return None
