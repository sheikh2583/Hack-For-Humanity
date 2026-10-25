"""M6 header and wording tests (no Streamlit run needed)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import app.streamlit_app as dashboard
import app.strings as T

ROOT = Path(__file__).resolve().parents[1]
BANNED = ("লঙ্ঘন", "বিপজ্জনক", "violation", "hazardous", "illegal", "non-compliant")


def test_data_date_is_file_mtime_not_today(tmp_path: Path) -> None:
    path = tmp_path / "kilns.parquet"
    path.write_bytes(b"x")
    stamp = datetime(2026, 3, 5, 12, tzinfo=UTC).timestamp()
    os.utime(path, (stamp, stamp))
    assert dashboard._data_date_label(path) == "2026-03-05"
    assert dashboard._data_date_label(None) == T.NO_DATA
    assert dashboard._data_date_label(tmp_path / "missing.parquet") == T.NO_DATA


def test_header_wording_is_advisory() -> None:
    for name in ("METRIC_HIGH_PRIORITY_KILNS", "METRIC_RULE_VIOLATIONS", "COL_BREACH_COUNT"):
        for language in T.LANGUAGES:  # both Bangla and English wording
            text = T.text(name, language).casefold()
            assert not any(word in text for word in BANNED), (name, language)


def test_no_legal_distances_or_law_expander_in_ui_strings() -> None:
    assert not hasattr(T, "LAW_TEXT") and not hasattr(T, "RELEVANT_LAW_BRICK_MANUFACTURING_AND_KIL")
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "LAW_TEXT" not in source and "datetime.now(UTC).date().isoformat()" not in source
