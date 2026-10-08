"""Synthetic tests for choosing the latest processed detection GeoParquet."""

import os
from pathlib import Path

from app.streamlit_app import latest_kilns_file


def test_latest_kilns_file_selects_by_modification_time(tmp_path: Path) -> None:
    """The newest kilns parquet is selected regardless of district suffix."""
    older = tmp_path / "kilns_chapai_real.parquet"
    newer = tmp_path / "kilns_gazipur.parquet"
    older.touch()
    newer.touch()
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))
    assert latest_kilns_file(tmp_path) == newer


def test_latest_kilns_file_returns_none_for_empty_directory(tmp_path: Path) -> None:
    """No processed detections returns no path."""
    assert latest_kilns_file(tmp_path) is None
