"""Storage boundary for public reports.

Input schema: ``NewReport`` values using the agreed reports fields and optional
image bytes. Output schema: ``ReportRecord`` values persisted by a replaceable
``ReportStore`` implementation; the initial implementation uses SQLite.
"""

from __future__ import annotations

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


class ReportStore(Protocol):
    """Replaceable interface used by public submission and the future inbox."""

    def create_report(self, report: NewReport) -> str:
        """Persist one report and return its generated id."""

    def list_reports(self) -> list[ReportRecord]:
        """Return stored reports ordered by creation time, oldest first."""


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

    Input: a database path (normally ``data/app.db``) and report values.
    Output: the agreed ``reports`` table and uploaded image files under a
    sibling ``reports/`` directory; no sample records are inserted.
    """

    _PHOTO_TYPES = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    }

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a row-aware SQLite connection and ensure the agreed table exists."""
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
