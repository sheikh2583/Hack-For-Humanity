"""CPU-only tests for the mobile API using tiny synthetic candidate rows."""

from __future__ import annotations

import pandas as pd

from backend import main


def test_candidate_serialization_keeps_mobile_fields() -> None:
    """Candidate cards include district, map coordinates, and advisory text."""
    row = pd.Series(
        {
            "kiln_id": "demo-1",
            "district": "Dhaka",
            "lat": 23.7,
            "lon": 90.4,
            "class": "FCBK",
            "confidence": 0.8,
            "priority": 5,
            "priority_rank": 1,
            "breached_rules": ["near_school"],
            "breach_count": 1,
        }
    )
    item = main._candidate(row, fallback=True)
    assert item["district"] == "Dhaka"
    assert item["candidate_rule_signals"] == ["near_school"]
    assert item["advisory"] == main.ADVISORY


def test_projected_distance_is_zero_for_same_point() -> None:
    """Nearby distance uses the projected CRS path and is stable for identity."""
    assert main._distance_m(23.7, 90.4, 23.7, 90.4) == 0
