"""Create the multi-page community "Near me" PDF without writing files.

Input schema: a place label, a DataFrame with optional ``distance_m``, ``class``,
``priority_band``, ``lat``, ``lon``, ``upazila``, ``district`` columns, and a radius in
metres (``0`` = the whole named area). Output schema: A4 PDF bytes in ``lang``
("bn" or "en"), or ``None`` when generation fails. The table repeats its header on every
page and every page shows "page x / y".
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pandas as pd

logger = logging.getLogger(__name__)

_COLUMN_WIDTHS = (11.0, 20.0, 52.0, 32.0, 22.0, 43.0)  # no, distance, area, type, priority, coords
_ROW_LINE = 4.6


def _text(value: object) -> str:
    """Stripped string; empty for missing/NaN values."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _row_cells(row: pd.Series, number: int, radius_m: int, table: dict[str, str]) -> list[str]:
    """Format one table row (no, distance, area, type, priority, coordinates)."""
    from src.eval import pdf_kit as kit

    distance = pd.to_numeric(pd.Series([row.get("distance_m")]), errors="coerce").iloc[0]
    distance_text = f"{distance:,.0f} m" if radius_m and pd.notna(distance) else "-"
    district = _text(row.get("district"))
    area = ", ".join(
        part for part in (_text(row.get("upazila")), kit.name_text(table, district) if district else "") if part
    ) or "-"
    try:
        coords = f"{float(row['lat']):.5f}, {float(row['lon']):.5f}"
    except (KeyError, TypeError, ValueError):
        coords = "-"
    return [
        str(number), distance_text, area,
        kit.name_text(table, _text(row.get("class"))),
        kit.name_text(table, _text(row.get("priority_band"))),
        coords,
    ]


def _build(
    location: str, rows: pd.DataFrame, radius_m: int, lang: str, total_pages: int | None, hotline: str | None = None
) -> tuple[bytes, int]:
    """Lay the report out once; return ``(pdf bytes, page count)``."""
    from fpdf import FPDF

    from src.eval import pdf_kit as kit

    table = kit.labels(lang)
    today = datetime.now(UTC).date().isoformat()
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    kit.register_fonts(pdf)
    pdf.set_title(f"{table['brand']} - {table['community_title']}")
    margin = pdf.l_margin = pdf.r_margin = 15
    width = pdf.w - 2 * margin
    bottom = pdf.h - 22

    def new_page() -> float:
        pdf.add_page()
        kit.footer(pdf, table, pdf.page, total_pages)
        return kit.header_band(pdf, table, table["community_title"], today)

    def header_row(y: float) -> float:
        pdf.set_fill_color(*kit.BAND)
        pdf.rect(margin, y - 1.2, width, 7.4, style="F")
        x = margin
        for w, key in zip(_COLUMN_WIDTHS, ("col_no", "col_distance", "col_area", "col_type", "col_priority", "col_coords")):
            kit.put(pdf, x + 1.5, y, kit.fit_text(pdf, table[key], w - 3, 8.5, True), 8.5, True, kit.MUTED)
            x += w
        return y + 8

    y = new_page()
    place = location.strip() or table["unknown"]
    key = "near_in" if radius_m else "in_area"
    summary = table[key].format(count=len(rows), place=place, radius=radius_m / 1000)
    y = kit.paragraph(pdf, margin, y, width, summary, 11, True, kit.INK, line=6.4) + 1
    y = kit.paragraph(pdf, margin, y, width, table["basis"], 8.5, False, kit.MUTED) + 4

    if rows.empty:
        y = kit.paragraph(pdf, margin, y, width, table["no_rows"], 10)
    else:
        y = header_row(y)
        for number, (_, row) in enumerate(rows.iterrows(), start=1):
            cells = _row_cells(row, number, radius_m, table)
            wrapped = [
                kit.wrap_text(pdf, cell, w - 3, 8.5) for cell, w in zip(cells, _COLUMN_WIDTHS)
            ]
            height = max(len(lines) for lines in wrapped) * _ROW_LINE + 2.6
            if y + height > bottom:
                y = header_row(new_page())
            x = margin
            for lines, w in zip(wrapped, _COLUMN_WIDTHS):
                for offset, line in enumerate(lines):
                    kit.put(pdf, x + 1.5, y + offset * _ROW_LINE, line, 8.5)
                x += w
            y += height
            pdf.set_draw_color(*kit.RULE)
            pdf.line(margin, y - 0.8, margin + width, y - 0.8)

    # "What you can do" block: keep together, move to a new page when it does not fit
    first = (
        table["do_1"].format(hotline=hotline.translate(kit.BN_DIGITS) if lang == "bn" else hotline)
        if hotline else table["do_1_web"]
    )
    actions = [first, *(table[f"do_{index}"] for index in range(2, 5))]
    block = 12 + sum(len(kit.wrap_text(pdf, a, width - 8, 9.5)) * 5.2 + 1.2 for a in actions) + 10
    y += 6
    if y + block > bottom:
        y = new_page()
    y = kit.section_title(pdf, margin, y, width, table["can_do"])
    for action in actions:
        pdf.set_fill_color(*kit.ACCENT)
        pdf.ellipse(margin + 1, y + 1.9, 1.6, 1.6, style="F")
        y = kit.paragraph(pdf, margin + 6, y, width - 6, action, 9.5, line=5.2) + 1.2
    y += 3
    kit.paragraph(pdf, margin, y, width, table["community_note"], 8.5, False, kit.MUTED)
    return bytes(pdf.output()), pdf.page


def generate_community_report(
    location: str, rows: pd.DataFrame, radius_m: int, lang: str = "bn", hotline: str | None = None
) -> bytes | None:
    """Generate the community PDF in ``lang``; ``None`` on failure (logged).

    ``hotline`` is the verified hotline number from ``config/dashboard.yaml`` or ``None``
    (then the PDF names only the Department of Environment website).
    """
    try:
        _, pages = _build(location, rows, int(radius_m or 0), lang, None, hotline)
        data, _ = _build(location, rows, int(radius_m or 0), lang, pages, hotline)
        return data
    except Exception:
        logger.exception("Could not generate community PDF")
        return None
