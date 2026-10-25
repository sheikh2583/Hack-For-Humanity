"""Shared drawing helpers and bilingual labels for the Dhoa PDF reports.

Input schema: an ``fpdf.FPDF`` page plus plain text; ``lang`` is ``"bn"`` or ``"en"``.
Output schema: drawn cells/paragraphs and ``LABELS``/data-name lookups. The Noto Sans
Bengali font has no Latin letters and Helvetica has no Bangla, so every string is split
into runs and each run is drawn with the right font (Bangla runs are shaped with
HarfBuzz so conjuncts render correctly). All PDF wording lives in ``LABELS`` in both
languages (``tests/test_pdf_p6.py`` checks the two stay in step); it needs
native-speaker review.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FONT_PATH = Path(__file__).resolve().parent / "fonts" / "NotoSansBengali-Regular.ttf"
BN_FONT = "NotoBengali"
LATIN_FONT = "Helvetica"
LANGUAGES = ("bn", "en")

# Palette (RGB). Print-friendly: dark text on white, one accent.
INK = (17, 24, 39)
MUTED = (75, 85, 99)
RULE = (209, 213, 219)
ACCENT = (197, 48, 48)
BAND = (243, 244, 246)
STATUS_COLOURS = {"within": (197, 48, 48), "outside": (22, 128, 61), "nodata": (156, 163, 175)}

_BN_CHAR = re.compile("[ঀ-৿‌‍]+")

LABELS: dict[str, dict[str, str]] = {
    "bn": {
        "brand": "ধোঁয়া",
        "kiln_title": "ইটভাটা প্রার্থী প্রতিবেদন",
        "community_title": "কমিউনিটি প্রতিবেদন",
        "generated": "প্রতিবেদনের তারিখ",
        "sec_candidate": "প্রার্থীর তথ্য",
        "sec_location": "অবস্থান",
        "sec_distances": "মানচিত্রে চিহ্নিত স্থান থেকে দূরত্ব",
        "sec_signals": "নিয়মের সংকেত",
        "sec_navigation": "দিকনির্দেশনা",
        "candidate_id": "প্রার্থীর আইডি",
        "area": "এলাকা",
        "nearest_place": "নিকটতম স্থান",
        "kiln_type": "ভাটার ধরন",
        "priority": "অগ্রাধিকার",
        "detection": "শনাক্তকরণের অবস্থা",
        "coordinates": "স্থানাঙ্ক",
        "feature": "স্থান",
        "distance": "দূরত্ব",
        "threshold": "সীমা",
        "status": "অবস্থা",
        "within": "সীমার মধ্যে",
        "outside": "সীমার বাইরে",
        "nodata": "তথ্য নেই",
        "no_signals": "কোনো নিয়ম-সংকেত নথিভুক্ত নেই।",
        "directions": "গুগল ম্যাপে দিকনির্দেশনা",
        "map": "গুগল ম্যাপে অবস্থান",
        "earth": "গুগল আর্থ",
        "footer": "ধোঁয়া দ্বারা স্যাটেলাইট ছবির বিশ্লেষণ থেকে তৈরি। নিয়মের সংকেত মানচিত্রে চিহ্নিত স্থানের দূরত্বকে নির্ধারিত সীমার সাথে তুলনা করে।",
        "page": "পৃষ্ঠা",
        "near_in": "{count}টি ইটভাটার প্রার্থী {place} থেকে {radius:g} কিমির মধ্যে চিহ্নিত হয়েছে।",
        "in_area": "{count}টি ইটভাটার প্রার্থী {place} এলাকায় চিহ্নিত হয়েছে।",
        "basis": "ভিত্তি: ২০২৫–২৬ শুষ্ক মৌসুমের স্যাটেলাইট ছবির বিশ্লেষণ।",
        "col_no": "ক্রম",
        "col_distance": "দূরত্ব",
        "col_area": "এলাকা",
        "col_type": "ধরন",
        "col_priority": "অগ্রাধিকার",
        "col_coords": "স্থানাঙ্ক",
        "no_rows": "এই এলাকায় কোনো ভাটার তথ্য পাওয়া যায়নি।",
        "can_do": "আপনি যা করতে পারেন",
        "do_1": "অভিযোগ জানান: পরিবেশ অধিদপ্তরের হটলাইন ১৬১৩১ অথবা doe.gov.bd",
        "do_2": "আপনার উপজেলার পরিবেশ কর্মকর্তার সাথে যোগাযোগ করুন",
        "do_3": "এই প্রতিবেদন স্থানীয় এনজিও বা গণমাধ্যমের সাথে ভাগ করুন",
        "do_4": "স্থানীয় প্রশাসনের মাধ্যমে সরকারি পরিদর্শনের অনুরোধ করুন",
        "community_note": "এই প্রতিবেদনটি কমিউনিটি সচেতনতার জন্য — শুধুমাত্র তথ্যের উদ্দেশ্যে।",
        "school": "স্কুল", "hospital": "হাসপাতাল", "settlement": "বসতি", "railway": "রেলপথ",
        "wetland": "জলাভূমি", "forest": "সরকারি বন", "technology": "ফিক্সড চিমনি প্রযুক্তি",
        "new": "নতুন প্রার্থী (২০২৫–২৬)", "known": "আগে চিহ্নিত (২০২৩–২৪ জরিপ)",
        "High": "উচ্চ", "Medium": "মাঝারি", "Low": "নিম্ন",
        "FCBK": "ফিক্সড চিমনি ইটভাটা", "Zigzag": "জিগজ্যাগ ইটভাটা",
        "unknown": "অজানা", "not_recorded": "নথিভুক্ত নেই",
        "Chapainawabganj": "চাঁপাইনবাবগঞ্জ", "Gazipur": "গাজীপুর", "Rajshahi": "রাজশাহী",
        "Dhaka": "ঢাকা", "Chittagong": "চট্টগ্রাম",
    },
    "en": {
        "brand": "ধোঁয়া",
        "kiln_title": "Kiln Candidate Report",
        "community_title": "Community Report",
        "generated": "Date generated",
        "sec_candidate": "Candidate",
        "sec_location": "Location",
        "sec_distances": "Distances to mapped features",
        "sec_signals": "Rule signals",
        "sec_navigation": "Navigation",
        "candidate_id": "Candidate ID",
        "area": "Area",
        "nearest_place": "Nearest place",
        "kiln_type": "Kiln type",
        "priority": "Priority",
        "detection": "Detection status",
        "coordinates": "Coordinates",
        "feature": "Feature",
        "distance": "Distance",
        "threshold": "Threshold",
        "status": "Status",
        "within": "Within threshold",
        "outside": "Outside threshold",
        "nodata": "No data",
        "no_signals": "No rule signals recorded.",
        "directions": "Directions in Google Maps",
        "map": "Location in Google Maps",
        "earth": "Google Earth",
        "footer": "Generated by Dhoa from satellite imagery analysis. Rule signals compare mapped distances with the configured thresholds.",
        "page": "Page",
        "near_in": "{count} kiln candidates were identified within {radius:g} km of {place}.",
        "in_area": "{count} kiln candidates were identified in {place}.",
        "basis": "Basis: satellite imagery analysis of the 2025-26 dry season.",
        "col_no": "No.",
        "col_distance": "Distance",
        "col_area": "Area",
        "col_type": "Type",
        "col_priority": "Priority",
        "col_coords": "Coordinates",
        "no_rows": "No kiln data was found for this area.",
        "can_do": "What you can do",
        "do_1": "File a complaint: DoE hotline 16131 or doe.gov.bd",
        "do_2": "Contact your Upazila Environment Officer",
        "do_3": "Share this report with local NGOs or media",
        "do_4": "Request an official inspection through your local administration",
        "community_note": "This report is for community awareness only and is provided for information purposes.",
        "school": "School", "hospital": "Hospital", "settlement": "Settlement", "railway": "Railway",
        "wetland": "Wetland", "forest": "Government forest", "technology": "Fixed chimney technology",
        "new": "New candidate (2025-26)", "known": "Previously detected (2023-24 survey)",
        "High": "High", "Medium": "Medium", "Low": "Low",
        "FCBK": "Fixed chimney kiln", "Zigzag": "Zigzag kiln",
        "unknown": "Unknown", "not_recorded": "Not recorded",
        "Chapainawabganj": "Chapainawabganj", "Gazipur": "Gazipur", "Rajshahi": "Rajshahi",
        "Dhaka": "Dhaka", "Chittagong": "Chittagong",
    },
}

# rule feature (config/rules.yaml) -> (label key, candidate distance columns in priority order)
FEATURE_LABELS: dict[str, tuple[str, tuple[str, ...]]] = {
    "schools": ("school", ("dist_schools_m", "dist_school_m")),
    "hospitals": ("hospital", ("dist_hospitals_m", "dist_hospital_m")),
    "settlements": ("settlement", ("dist_settlements_m", "dist_settlement_m")),
    "railways": ("railway", ("dist_railways_m", "dist_railway_m")),
    "water": ("wetland", ("dist_water_m", "dist_wetland_m")),
    "government_forest": ("forest", ("dist_government_forest_m", "dist_forests_m")),
}


def labels(lang: str | None) -> dict[str, str]:
    """Return the label set for ``lang`` (Bangla for anything unknown)."""
    return LABELS[lang if lang in LABELS else "bn"]


def name_text(table: dict[str, str], value: object, fallback_key: str = "unknown") -> str:
    """Translate a data value (district, class, priority); unknown values pass through."""
    text = "" if value is None else str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return table[fallback_key]
    return table.get(text, text)


def detection_text(table: dict[str, str], value: object) -> str:
    """Translate the detection status; unrecognised text is shown as-is."""
    text = "" if value is None else str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return table["not_recorded"]
    if text.lower().startswith("new"):
        return table["new"]
    if text.lower().startswith(("known", "previous")):
        return table["known"]
    return text


# ----------------------------------------------------------------------------- fonts


def has_bangla_font() -> bool:
    """Whether the bundled Bangla font file exists."""
    return FONT_PATH.is_file()


def register_fonts(pdf: Any) -> None:
    """Register the Bangla font on ``pdf`` (Helvetica is built in)."""
    if has_bangla_font():
        pdf.add_font(BN_FONT, fname=str(FONT_PATH))
    pdf.core_fonts_encoding = "cp1252"


def split_runs(text: str) -> list[tuple[bool, str]]:
    """Split ``text`` into ``(is_bangla, run)`` pieces; Latin and Bangla alternate."""
    runs: list[tuple[bool, str]] = []
    position = 0
    for match in _BN_CHAR.finditer(text):
        if match.start() > position:
            runs.append((False, text[position:match.start()]))
        runs.append((True, match.group()))
        position = match.end()
    if position < len(text):
        runs.append((False, text[position:]))
    return runs


def _latin_safe(text: str) -> str:
    """Make ``text`` encodable by the core font (cp1252); other characters become ``?``."""
    return text.encode("cp1252", "replace").decode("cp1252")


def _use_font(pdf: Any, bangla: bool, size: float, bold: bool) -> None:
    if bangla and has_bangla_font():
        pdf.set_font(BN_FONT, "", size)
        pdf.set_text_shaping(use_shaping_engine=True, direction="ltr", script="beng", language="ben")
    else:
        pdf.set_text_shaping(use_shaping_engine=False)
        pdf.set_font(LATIN_FONT, "B" if bold else "", size)


def _run_text(run: str, bangla: bool) -> str:
    return run if bangla and has_bangla_font() else _latin_safe(run)


def text_width(pdf: Any, text: str, size: float = 9, bold: bool = False) -> float:
    """Width of ``text`` in the document unit when drawn with mixed fonts."""
    total = 0.0
    for bangla, run in split_runs(text):
        _use_font(pdf, bangla, size, bold)
        total += pdf.get_string_width(_run_text(run, bangla))
    _use_font(pdf, False, size, bold)
    return total


def fit_text(pdf: Any, text: str, max_width: float, size: float = 9, bold: bool = False) -> str:
    """Shorten ``text`` with ``...`` until it is at most ``max_width`` wide."""
    if text_width(pdf, text, size, bold) <= max_width:
        return text
    while text and text_width(pdf, text + "...", size, bold) > max_width:
        text = text[:-1]
    return text + "..."


def wrap_text(pdf: Any, text: str, max_width: float, size: float = 9, bold: bool = False) -> list[str]:
    """Wrap ``text`` into lines no wider than ``max_width`` (breaks inside a word only if needed)."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = word if not current else f"{current} {word}"
        if text_width(pdf, candidate, size, bold) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        while text_width(pdf, current, size, bold) > max_width and len(current) > 1:
            cut = len(current) - 1
            while cut > 1 and text_width(pdf, current[:cut], size, bold) > max_width:
                cut -= 1
            lines.append(current[:cut])
            current = current[cut:]
    if current or not lines:
        lines.append(current)
    return lines


def put(
    pdf: Any, x: float, y: float, text: str, size: float = 9, bold: bool = False,
    colour: tuple[int, int, int] = INK, link: str | None = None,
) -> float:
    """Draw one line of mixed-script text at ``(x, y)`` (top-left); return its width."""
    pdf.set_text_color(*colour)
    cursor = x
    line_height = size * 0.5
    for bangla, run in split_runs(text):
        _use_font(pdf, bangla, size, bold)
        piece = _run_text(run, bangla)
        width = pdf.get_string_width(piece)
        pdf.set_xy(cursor, y)
        pdf.cell(width, line_height + 1.5, piece, link=link or "")
        cursor += width
    _use_font(pdf, False, size, bold)
    pdf.set_text_color(*INK)
    return cursor - x


def put_right(
    pdf: Any, right: float, y: float, text: str, size: float = 9, bold: bool = False,
    colour: tuple[int, int, int] = INK,
) -> None:
    """Draw ``text`` so that it ends at ``right``."""
    put(pdf, right - text_width(pdf, text, size, bold), y, text, size, bold, colour)


def paragraph(
    pdf: Any, x: float, y: float, width: float, text: str, size: float = 9,
    bold: bool = False, colour: tuple[int, int, int] = INK, line: float | None = None,
) -> float:
    """Draw wrapped text; return the y coordinate below it."""
    step = line if line is not None else size * 0.5 + 2.2
    for row in wrap_text(pdf, text, width, size, bold):
        put(pdf, x, y, row, size, bold, colour)
        y += step
    return y


def section_title(pdf: Any, x: float, y: float, width: float, text: str) -> float:
    """Draw a section heading with an accent rule; return the y below it."""
    put(pdf, x, y, text, size=11, bold=True, colour=INK)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(x, y + 7, x + width, y + 7)
    pdf.set_line_width(0.2)
    return y + 10


def status_dot(pdf: Any, x: float, y: float, kind: str) -> None:
    """Draw the status marker: filled circle (within), ring (outside), dash (no data)."""
    colour = STATUS_COLOURS.get(kind, STATUS_COLOURS["nodata"])
    pdf.set_fill_color(*colour)
    pdf.set_draw_color(*colour)
    if kind == "within":
        pdf.ellipse(x, y, 2.6, 2.6, style="F")
    elif kind == "outside":
        pdf.set_line_width(0.5)
        pdf.ellipse(x, y, 2.6, 2.6, style="D")
        pdf.set_line_width(0.2)
    else:
        pdf.line(x, y + 1.3, x + 2.6, y + 1.3)
    pdf.set_draw_color(*RULE)


def header_band(pdf: Any, table: dict[str, str], title: str, day: str) -> float:
    """Draw the branded page header; return the y where content may start."""
    margin = pdf.l_margin
    width = pdf.w - 2 * margin
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 0, pdf.w, 4, style="F")
    put(pdf, margin, 10, table["brand"], size=22, bold=True)
    put(pdf, margin + text_width(pdf, table["brand"], 22, True) + 4, 13.5, title, size=14, bold=True, colour=MUTED)
    put_right(pdf, margin + width, 11, f"{table['generated']}: {day}", size=8, colour=MUTED)
    pdf.set_draw_color(*RULE)
    pdf.line(margin, 25, margin + width, 25)
    return 31.0


def footer(pdf: Any, table: dict[str, str], page: int, pages: int | None = None) -> None:
    """Draw the footer note and page number at the bottom of the current page."""
    margin = pdf.l_margin
    width = pdf.w - 2 * margin
    pdf.set_draw_color(*RULE)
    pdf.line(margin, pdf.h - 18, margin + width, pdf.h - 18)
    paragraph(pdf, margin, pdf.h - 16.5, width - 22, table["footer"], size=7, colour=MUTED, line=3.6)
    label = f"{table['page']} {page}" + (f" / {pages}" if pages else "")
    put_right(pdf, margin + width, pdf.h - 16.5, label, size=7, colour=MUTED)
