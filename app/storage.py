"""Storage boundary for public reports and staff visit workflows.

Input schema: report values, visit/note status values, named Inspector filter
snapshots, activity events and optional image bytes. Output schema:
``ReportRecord``, ``VisitRecord``, ``NoteRecord``, ``SavedFilterRecord``,
``ActivityRecord`` and ``VisitPhotoRecord`` values persisted in SQLite.
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Iterator
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class DataExtent:
    """Latitude/longitude bounds derived from the existing public kiln data."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


@dataclass(frozen=True)
class NewReport:
    """One public report before its generated id and stored timestamp."""

    kind: str
    kiln_id: str | None
    lat: float
    lon: float
    reason: str
    note: str
    contact: str | None = None
    photo: bytes | None = None
    photo_content_type: str | None = None


@dataclass(frozen=True)
class ReportRecord:
    """One stored report using the S4/S5 reports table schema."""

    id: str
    kind: str
    kiln_id: str | None
    lat: float
    lon: float
    reason: str
    note: str
    contact: str | None
    photo_ref: str | None
    created_at: str
    status: str
    handled_by: str | None
    handled_at: str | None


VISIT_STATUSES = ("not_visited", "assigned", "visited", "confirmed_active", "not_a_kiln")
REPORT_STATUSES = ("new", "reviewed", "resolved")


@dataclass(frozen=True)
class VisitRecord:
    """Current visit assignment for one kiln; mirrors the visits table columns."""

    kiln_id: str
    status: str
    assignee: str | None
    updated_by: str
    updated_at: str


@dataclass(frozen=True)
class NoteRecord:
    """One appended staff note; rowid provides history order without extra fields."""

    kiln_id: str
    text: str
    author: str
    created_at: str


@dataclass(frozen=True)
class SavedFilterRecord:
    """One display-name-scoped Inspector filter snapshot."""

    display_name: str
    name: str
    filters: dict[str, object]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ActivityRecord:
    """One append-only staff activity entry with JSON details."""

    id: int
    actor: str
    action: str
    entity_id: str
    details: dict[str, object]
    created_at: str


@dataclass(frozen=True)
class VisitPhotoRecord:
    """One image attached to a kiln visit with a database-relative path."""

    id: str
    kiln_id: str
    photo_ref: str
    author: str
    created_at: str


class ReportStore(Protocol):
    """Replaceable interface used by public submission and the future inbox."""

    def create_report(self, report: NewReport) -> str:
        """Persist one report and return its generated id."""

    def list_reports(self) -> list[ReportRecord]:
        """Return stored reports ordered by creation time, oldest first."""

    def open_report_count(self) -> int:
        """Return the number of new or reviewed reports awaiting resolution."""

    def set_report_status(self, report_id: str, status: str, handled_by: str) -> None:
        """Update an inbox status and record its handler and handling time."""


class WorkStore(Protocol):
    """Persistence interface for staff-only kiln visits and notes."""

    def get_visit(self, kiln_id: str) -> VisitRecord | None: ...
    def list_visits(self, assignee: str | None = None, status: str | None = None) -> list[VisitRecord]: ...
    def set_visit(self, kiln_id: str, status: str, assignee: str | None, updated_by: str) -> None: ...
    def add_note(self, kiln_id: str, text: str, author: str) -> None: ...
    def list_notes(self, kiln_id: str) -> list[NoteRecord]: ...
    def save_filter(self, display_name: str, name: str, filters: dict[str, object]) -> None: ...
    def list_saved_filters(self, display_name: str) -> list[SavedFilterRecord]: ...
    def delete_saved_filter(self, display_name: str, name: str) -> None: ...
    def list_activity(self, limit: int = 100) -> list[ActivityRecord]: ...
    def add_visit_photo(self, kiln_id: str, photo: bytes, content_type: str, author: str) -> str: ...
    def list_visit_photos(self, kiln_id: str) -> list[VisitPhotoRecord]: ...


def extent_from_frame(frame: pd.DataFrame) -> DataExtent | None:
    """Derive inclusive coordinate bounds from a frame with numeric ``lat``/``lon``.

    Input: a pandas/GeoPandas-like frame containing latitude and longitude
    columns. Output: EPSG:4326 coordinate extent, or ``None`` if no finite pair
    exists. No country bounds or coordinates are supplied by this module.
    """
    if not {"lat", "lon"}.issubset(frame.columns):
        return None
    lat = frame["lat"]
    lon = frame["lon"]
    pairs = [
        (float(latitude), float(longitude))
        for latitude, longitude in zip(lat, lon)
        if _finite(latitude) and _finite(longitude)
    ]
    if not pairs:
        return None
    return DataExtent(
        min_lat=min(pair[0] for pair in pairs), max_lat=max(pair[0] for pair in pairs),
        min_lon=min(pair[1] for pair in pairs), max_lon=max(pair[1] for pair in pairs),
    )


def _finite(value: object) -> bool:
    """True when a value can be converted to a finite float."""
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def coordinates_in_extent(lat: float, lon: float, extent: DataExtent | None) -> bool:
    """Check finite WGS84 coordinates against the existing data extent."""
    return bool(
        extent is not None and _finite(lat) and _finite(lon)
        and extent.min_lat <= float(lat) <= extent.max_lat
        and extent.min_lon <= float(lon) <= extent.max_lon
    )


class SQLiteReportStore:
    """SQLite implementation of ``ReportStore`` for local persistence.

    Input: a database path (normally ``data/app.db``) and report, visit, filter,
    activity, and photo values. Output: local SQLite records and optional photo
    files in sibling ``reports/`` and ``visit_photos/`` directories; no sample
    records are inserted.
    """

    _PHOTO_TYPES = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    }

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a row-aware SQLite connection and ensure the storage tables exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    kiln_id TEXT,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    reason TEXT NOT NULL,
                    note TEXT NOT NULL,
                    contact TEXT,
                    photo_ref TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    handled_by TEXT,
                    handled_at TEXT
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS saved_filters (
                    display_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    filters_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (display_name, name)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS visit_photos (
                    id TEXT PRIMARY KEY,
                    kiln_id TEXT NOT NULL,
                    photo_ref TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS visits (
                    kiln_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    assignee TEXT,
                    updated_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS notes (
                    kiln_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_report(self, report: NewReport) -> str:
        """Insert a report, save an optional supported image, and return its id."""
        if not (_finite(report.lat) and _finite(report.lon)):
            raise ValueError("report coordinates must be finite")
        if not report.kind.strip() or not report.reason.strip():
            raise ValueError("report kind and reason are required")

        report_id = str(uuid.uuid4())
        photo_ref: str | None = None
        photo_path: Path | None = None
        if report.photo is not None:
            suffix = self._PHOTO_TYPES.get(report.photo_content_type or "")
            if suffix is None:
                raise ValueError("unsupported photo content type")
            photo_dir = self.database_path.parent / "reports"
            photo_dir.mkdir(parents=True, exist_ok=True)
            photo_path = photo_dir / f"{report_id}{suffix}"
            photo_path.write_bytes(report.photo)
            photo_ref = photo_path.relative_to(self.database_path.parent).as_posix()

        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO reports (
                        id, kind, kiln_id, lat, lon, reason, note, contact,
                        photo_ref, created_at, status, handled_by, handled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', NULL, NULL)""",
                    (
                        report_id, report.kind, report.kiln_id, float(report.lat), float(report.lon),
                        report.reason, report.note, report.contact or None, photo_ref,
                        datetime.now(UTC).isoformat(),
                    ),
                )
        except Exception:
            if photo_path is not None:
                photo_path.unlink(missing_ok=True)
            raise
        return report_id

    def list_reports(self) -> list[ReportRecord]:
        """Return saved reports oldest first for the future inspector inbox."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reports ORDER BY created_at, id"
            ).fetchall()
        return [ReportRecord(**dict(row)) for row in rows]

    def open_report_count(self) -> int:
        """Count new and reviewed reports for the Inspector Portal notification badge.

        Input: the reports table in this store's SQLite database. Output: one
        integer count; report content is not loaded into application memory.
        """
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM reports WHERE status IN ('new', 'reviewed')"
            ).fetchone()
        return int(row["count"])

    def set_report_status(self, report_id: str, status: str, handled_by: str) -> None:
        """Set an inbox status and record who handled it and when."""
        if status not in REPORT_STATUSES:
            raise ValueError("unsupported report status")
        with self._connect() as connection:
            previous = connection.execute("SELECT status FROM reports WHERE id=?", (report_id,)).fetchone()
            result = connection.execute(
                "UPDATE reports SET status=?, handled_by=?, handled_at=? WHERE id=?",
                (status, handled_by.strip(), datetime.now(UTC).isoformat(), report_id),
            )
            if result.rowcount != 1:
                raise KeyError(report_id)
            if previous is not None and previous["status"] != status:
                self._record_activity(
                    connection, handled_by, "report_status_changed", report_id,
                    {"from": previous["status"], "to": status},
                )

    def get_visit(self, kiln_id: str) -> VisitRecord | None:
        """Return one kiln's latest assignment, or None when not yet tracked."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM visits WHERE kiln_id=?", (str(kiln_id),)).fetchone()
        return VisitRecord(**dict(row)) if row else None

    def list_visits(self, assignee: str | None = None, status: str | None = None) -> list[VisitRecord]:
        """List current assignments, optionally filtered by assignee and status."""
        if status is not None and status not in VISIT_STATUSES:
            raise ValueError("unsupported visit status")
        clauses: list[str] = []
        values: list[str] = []
        if assignee is not None:
            clauses.append("assignee=?")
            values.append(assignee)
        if status is not None:
            clauses.append("status=?")
            values.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM visits" + where + " ORDER BY updated_at DESC, kiln_id", values).fetchall()
        return [VisitRecord(**dict(row)) for row in rows]

    def set_visit(self, kiln_id: str, status: str, assignee: str | None, updated_by: str) -> None:
        """Create or update the current visit status/assignee for a kiln."""
        if status not in VISIT_STATUSES:
            raise ValueError("unsupported visit status")
        if not str(kiln_id).strip() or not updated_by.strip():
            raise ValueError("kiln id and updater are required")
        with self._connect() as connection:
            previous = connection.execute("SELECT status,assignee FROM visits WHERE kiln_id=?", (str(kiln_id),)).fetchone()
            connection.execute(
                """INSERT INTO visits (kiln_id,status,assignee,updated_by,updated_at)
                   VALUES (?,?,?,?,?) ON CONFLICT(kiln_id) DO UPDATE SET
                   status=excluded.status, assignee=excluded.assignee,
                   updated_by=excluded.updated_by, updated_at=excluded.updated_at""",
                (str(kiln_id), status, assignee or None, updated_by.strip(), datetime.now(UTC).isoformat()),
            )
            new_state = {"status": status, "assignee": assignee or None}
            old_state = dict(previous) if previous else None
            if old_state != new_state:
                self._record_activity(connection, updated_by.strip(), "visit_updated", str(kiln_id),
                                      {"from": old_state, "to": new_state})

    def add_note(self, kiln_id: str, text: str, author: str) -> None:
        """Append a non-empty staff note to a kiln's history."""
        if not str(kiln_id).strip() or not text.strip() or not author.strip():
            raise ValueError("kiln id, note text and author are required")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO notes (kiln_id,text,author,created_at) VALUES (?,?,?,?)",
                (str(kiln_id), text.strip(), author.strip(), datetime.now(UTC).isoformat()),
            )
            self._record_activity(connection, author.strip(), "note_added", str(kiln_id), {})

    def list_notes(self, kiln_id: str) -> list[NoteRecord]:
        """Return a kiln's notes in append order."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT kiln_id,text,author,created_at FROM notes WHERE kiln_id=? ORDER BY rowid", (str(kiln_id),)
            ).fetchall()
        return [NoteRecord(**dict(row)) for row in rows]

    @staticmethod
    def _record_activity(
        connection: sqlite3.Connection, actor: str, action: str,
        entity_id: str, details: dict[str, object],
    ) -> None:
        """Append one activity entry inside the caller's transaction."""
        connection.execute(
            "INSERT INTO activity_log (actor,action,entity_id,details_json,created_at) VALUES (?,?,?,?,?)",
            (actor.strip(), action, entity_id, json.dumps(details, ensure_ascii=False, sort_keys=True), datetime.now(UTC).isoformat()),
        )

    def save_filter(self, display_name: str, name: str, filters: dict[str, object]) -> None:
        """Create or update one named filter snapshot scoped to a staff display name."""
        owner, label = display_name.strip(), name.strip()
        allowed = {"district", "upazila", "priorities", "kiln_type"}
        if not owner or not label or set(filters) - allowed:
            raise ValueError("display name, filter name and supported filter fields are required")
        serialized = json.dumps(filters, ensure_ascii=False, sort_keys=True)
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO saved_filters (display_name,name,filters_json,created_at,updated_at)
                   VALUES (?,?,?,?,?) ON CONFLICT(display_name,name) DO UPDATE SET
                   filters_json=excluded.filters_json, updated_at=excluded.updated_at""",
                (owner, label, serialized, now, now),
            )
            self._record_activity(connection, owner, "saved_filter_saved", label, {})

    def list_saved_filters(self, display_name: str) -> list[SavedFilterRecord]:
        """Return saved filters only for the exact signed-in display name."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM saved_filters WHERE display_name=? ORDER BY name COLLATE NOCASE", (display_name.strip(),)
            ).fetchall()
        return [SavedFilterRecord(
            row["display_name"], row["name"], json.loads(row["filters_json"]), row["created_at"], row["updated_at"]
        ) for row in rows]

    def delete_saved_filter(self, display_name: str, name: str) -> None:
        """Delete one filter only from the owner's saved-filter collection."""
        owner, label = display_name.strip(), name.strip()
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM saved_filters WHERE display_name=? AND name=?", (owner, label)
            )
            if result.rowcount:
                self._record_activity(connection, owner, "saved_filter_deleted", label, {})

    def list_activity(self, limit: int = 100) -> list[ActivityRecord]:
        """Return newest activity entries first with a bounded requested limit."""
        if not 1 <= int(limit) <= 500:
            raise ValueError("activity limit must be between 1 and 500")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [ActivityRecord(
            row["id"], row["actor"], row["action"], row["entity_id"],
            json.loads(row["details_json"]), row["created_at"],
        ) for row in rows]

    def add_visit_photo(self, kiln_id: str, photo: bytes, content_type: str, author: str) -> str:
        """Store an allowed image beside the database and link it to a kiln visit."""
        suffix = self._PHOTO_TYPES.get(content_type)
        if not suffix or not kiln_id.strip() or not author.strip() or not photo:
            raise ValueError("a supported image, kiln id and author are required")
        photo_id = str(uuid.uuid4())
        photo_dir = self.database_path.parent / "visit_photos"
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_path = photo_dir / f"{photo_id}{suffix}"
        photo_path.write_bytes(photo)
        photo_ref = photo_path.relative_to(self.database_path.parent).as_posix()
        try:
            with self._connect() as connection:
                created = datetime.now(UTC).isoformat()
                connection.execute(
                    "INSERT INTO visit_photos (id,kiln_id,photo_ref,author,created_at) VALUES (?,?,?,?,?)",
                    (photo_id, kiln_id, photo_ref, author.strip(), created),
                )
                self._record_activity(connection, author.strip(), "visit_photo_added", kiln_id,
                                      {"photo_id": photo_id})
        except Exception:
            photo_path.unlink(missing_ok=True)
            raise
        return photo_id

    def list_visit_photos(self, kiln_id: str) -> list[VisitPhotoRecord]:
        """Return a kiln's stored visit images in append order."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM visit_photos WHERE kiln_id=? ORDER BY created_at,id", (str(kiln_id),)
            ).fetchall()
        return [VisitPhotoRecord(**dict(row)) for row in rows]
