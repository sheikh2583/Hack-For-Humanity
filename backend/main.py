"""Small FastAPI service for the KilnWatch BD mobile demo.

Input schema: prioritized GeoParquet rows with kiln identity, WGS84
coordinates, class, confidence, priority, and rule-signal fields. Output
schema: advisory candidate JSON, nearby candidate JSON, and in-memory field
note acknowledgements. This service does not run inference or alter pipeline
outputs.
"""

from __future__ import annotations

import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = Path(os.getenv("KILNWATCH_DATA", ROOT / "data" / "processed" / "kilns_prioritised.parquet"))
ADVISORY = "Advisory only: unverified screening candidates"

app = FastAPI(title="KilnWatch BD Mobile API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FieldNote(BaseModel):
    """Input schema for a demo field observation."""

    candidate_id: str
    note: str = Field(default="", max_length=2000)
    latitude: float | None = None
    longitude: float | None = None
    photo_uri: str | None = None


class FieldNoteReceipt(BaseModel):
    """Output schema for a saved in-memory field observation."""

    saved: bool
    candidate_id: str
    saved_at: str


def _fallback_rows() -> pd.DataFrame:
    """Return one real candidate-shaped row when local data is unavailable."""
    return pd.DataFrame(
        [
            {
                "kiln_id": "4541f65c-ac90-4dea-a90c-8c6a998625d6",
                "district": "Dhaka",
                "lat": 23.76923656463623,
                "lon": 90.41157913208008,
                "class": "FCBK",
                "confidence": 0.46941086649894714,
                "priority": 20.39470133088356,
                "priority_rank": 1,
                "breached_rules": [
                    "technology_flagged",
                    "near_school",
                    "near_hospital",
                    "near_settlement",
                ],
                "breach_count": 4,
                "rules_version": "draft-1",
            }
        ]
    )


def _load_rows() -> tuple[pd.DataFrame, bool]:
    """Load candidates or return the demo fallback."""
    if not DATA_PATH.is_file():
        return _fallback_rows(), True
    frame = gpd.read_parquet(DATA_PATH).drop(columns=["geometry"], errors="ignore")
    return frame, False


def _signals(value: object) -> list[str]:
    """Normalize a Parquet list, JSON string, or array into signal IDs."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [value]
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []


def _band(rank: object, total: int) -> str:
    """Return a display-only priority band from the stored rank."""
    try:
        rank_number = int(float(rank))
    except (TypeError, ValueError):
        return "Unknown"
    high_cutoff = max(1, math.ceil(total / 3))
    medium_cutoff = max(high_cutoff, math.ceil(total * 2 / 3))
    return "High" if rank_number <= high_cutoff else "Medium" if rank_number <= medium_cutoff else "Low"


def _candidate(row: pd.Series, fallback: bool, total: int = 1) -> dict[str, Any]:
    """Serialize one candidate without geometry or internal verification flags."""
    return {
        "id": str(row.get("kiln_id", "")),
        "district": str(row.get("district", "Not recorded")),
        "latitude": float(row.get("lat")),
        "longitude": float(row.get("lon")),
        "class": str(row.get("class", row.get("class_name", "Not recorded"))),
        "confidence": float(row.get("confidence")),
        "screening_priority": float(row.get("priority", 0)),
        "priority_rank": int(float(row.get("priority_rank"))) if pd.notna(row.get("priority_rank")) else None,
        "priority_band": _band(row.get("priority_rank"), total),
        "candidate_rule_signals": _signals(row.get("breached_rules")),
        "signal_count": int(row.get("breach_count", 0) or 0),
        "rules_version": str(row.get("rules_version", "Not recorded")),
        "advisory": ADVISORY,
        "fallback": fallback,
    }


def _projector(longitude: float) -> Transformer:
    """Build the configured Bangladesh projected CRS with the documented fallback."""
    try:
        return Transformer.from_crs("EPSG:4326", "EPSG:9680", always_xy=True)
    except Exception:
        epsg = "EPSG:32645" if longitude < 90 else "EPSG:32646"
        return Transformer.from_crs("EPSG:4326", epsg, always_xy=True)


def _distance_m(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    """Measure candidate proximity in the configured projected CRS."""
    transformer = _projector((lon_a + lon_b) / 2)
    x_a, y_a = transformer.transform(lon_a, lat_a)
    x_b, y_b = transformer.transform(lon_b, lat_b)
    return math.hypot(x_a - x_b, y_a - y_b)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small service health response."""
    return {"status": "ok"}


@app.get("/api/candidates")
def candidates(
    district: str | None = None,
    kiln_class: str | None = Query(default=None, alias="class"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Return filtered candidate cards for the mobile list."""
    frame, fallback = _load_rows()
    if district:
        frame = frame[frame["district"].astype(str).eq(district)]
    if kiln_class:
        frame = frame[frame["class"].astype(str).eq(kiln_class)]
    frame = frame[pd.to_numeric(frame["confidence"], errors="coerce").ge(min_confidence)]
    frame = frame.sort_values("priority_rank", na_position="last").head(limit)
    return {
        "items": [_candidate(row, fallback, len(frame)) for _, row in frame.iterrows()],
        "count": int(len(frame)),
        "source": DATA_PATH.name if not fallback else "demo fallback",
        "modified": datetime.fromtimestamp(DATA_PATH.stat().st_mtime, tz=UTC).isoformat() if not fallback else None,
        "advisory": ADVISORY,
    }


@app.get("/api/candidates/{candidate_id}")
def candidate_detail(candidate_id: str) -> dict[str, Any]:
    """Return one candidate for the map/detail screen."""
    frame, fallback = _load_rows()
    matches = frame[frame["kiln_id"].astype(str).eq(candidate_id)]
    if matches.empty:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate(matches.iloc[0], fallback, len(frame))


@app.get("/api/nearby")
def nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(default=50000, gt=0, le=200000),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Return nearby candidates ordered by projected distance."""
    frame, fallback = _load_rows()
    result: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        distance = _distance_m(latitude, longitude, float(row.lat), float(row.lon))
        if distance <= radius_m:
            item = _candidate(row, fallback, len(frame))
            item["distance_m"] = round(distance, 1)
            result.append(item)
    result.sort(key=lambda item: (item["distance_m"], item["priority_rank"] or 10**9))
    return {"items": result[:limit], "count": min(len(result), limit), "advisory": ADVISORY}


@app.post("/api/field-notes", response_model=FieldNoteReceipt)
def save_field_note(note: FieldNote) -> FieldNoteReceipt:
    """Acknowledge one demo observation without persistent storage."""
    return FieldNoteReceipt(
        saved=True,
        candidate_id=note.candidate_id,
        saved_at=datetime.now(UTC).isoformat(),
    )
