"""S4/S5 storage and coordinate validation tests.

Input schema: tiny synthetic latitude/longitude frames and report values.
Output schema: coordinates bounded by the source frame and report rows that
survive a new SQLite storage instance, including synthetic staff visit records.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

from app.storage import (
    NewReport,
    SQLiteReportStore,
    coordinates_in_extent,
    extent_from_frame,
)


def test_report_coordinates_use_only_the_synthetic_data_extent() -> None:
    """Bounds are derived from finite coordinates and include their edges."""
    frame = pd.DataFrame({"lat": [23.5, 24.0, None], "lon": [90.0, 91.0, 90.5]})
    extent = extent_from_frame(frame)
    assert extent is not None
    assert coordinates_in_extent(23.5, 90.0, extent)
    assert coordinates_in_extent(24.0, 91.0, extent)
    assert not coordinates_in_extent(24.1, 91.0, extent)
    assert not coordinates_in_extent(float("nan"), 90.5, extent)


def test_reports_persist_across_store_instances_without_seed_rows(tmp_path: Path) -> None:
    """A fresh SQLite store sees only the submitted synthetic report."""
    database = tmp_path / "app.db"
    assert SQLiteReportStore(database).list_reports() == []
    report = NewReport(
        kind="existing_candidate", kiln_id="synthetic-1", lat=23.7, lon=90.3,
        reason="wrong_location", note="Synthetic note", contact=None,
    )
    report_id = SQLiteReportStore(database).create_report(report)
    records = SQLiteReportStore(database).list_reports()

    assert len(records) == 1
    assert records[0].id == report_id
    assert records[0].kind == "existing_candidate"
    assert records[0].status == "new"
    assert records[0].handled_by is None and records[0].handled_at is None
    assert records[0].contact is None and records[0].photo_ref is None


def test_optional_photo_keeps_its_bytes_and_a_relative_reference(tmp_path: Path) -> None:
    """An optional PNG upload is stored as a sibling asset, referenced relatively."""
    database = tmp_path / "app.db"
    report = NewReport(
        kind="not_on_map", kiln_id=None, lat=23.7, lon=90.3,
        reason="not_on_map", note="Synthetic image", photo=b"tiny-png-fixture",
        photo_content_type="image/png",
    )
    record_id = SQLiteReportStore(database).create_report(report)
    record = SQLiteReportStore(database).list_reports()[0]

    assert record.id == record_id
    assert record.photo_ref is not None and record.photo_ref.startswith("reports/")
    assert (tmp_path / record.photo_ref).read_bytes() == b"tiny-png-fixture"


def test_staff_visits_notes_and_report_handling_persist(tmp_path: Path) -> None:
    """Tiny synthetic staff records persist and use only the defined status values."""
    database = tmp_path / "app.db"
    store = SQLiteReportStore(database)
    assert store.list_visits() == []
    store.set_visit("synthetic-1", "assigned", "Inspector A", "Inspector A")
    store.set_visit("synthetic-2", "visited", "Inspector A", "Inspector A")
    store.add_note("synthetic-1", "Gate was closed", "Inspector A")
    assert [visit.kiln_id for visit in store.list_visits(assignee="Inspector A", status="assigned")] == ["synthetic-1"]
    assert store.get_visit("synthetic-1").updated_by == "Inspector A"
    assert store.list_notes("synthetic-1")[0].text == "Gate was closed"
    report_id = store.create_report(NewReport(
        kind="not_on_map", kiln_id=None, lat=23.7, lon=90.3,
        reason="not_on_map", note="Synthetic inbox row",
    ))
    store.set_report_status(report_id, "reviewed", "Inspector A")
    reopened = SQLiteReportStore(database)
    assert reopened.list_reports()[0].status == "reviewed"
    assert reopened.list_reports()[0].handled_by == "Inspector A"
