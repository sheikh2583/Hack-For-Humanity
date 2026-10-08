"""CPU-only synthetic coverage for dashboard filters and review bands."""

from __future__ import annotations

from io import StringIO

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from app.dashboard_filters import (
    SIGNAL_ABSENT,
    SIGNAL_PRESENT,
    UNKNOWN_SIGNAL,
    add_priority_bands,
    add_signal_status_columns,
    apply_candidate_filters,
    signal_status,
)
from app.popup import ADVISORY_NOTICE
from app.presentation import screening_csv

RULES = {
    "technology": {"flagged_classes": ["FCBK"]},
    "siting_rules": [
        {"id": "near_school", "feature": "schools", "buffer_m": 1000},
    ],
}


@pytest.mark.parametrize(
    ("class_column", "geometry"),
    [("class", box(90, 24, 90.01, 24.01)), ("class_name", Point(90.0, 24.0))],
)
def test_class_filter_supports_polygon_and_point_schemas(class_column: str, geometry: object) -> None:
    """Both supported geometry types and class-column schemas filter correctly."""
    frame = gpd.GeoDataFrame(
        {class_column: ["FCBK", "Zigzag"], "confidence": [0.8, 0.9]},
        geometry=[geometry, geometry],
        crs="EPSG:4326",
    )

    filtered = apply_candidate_filters(frame, {}, classes={"FCBK"})

    assert len(filtered) == 1
    assert filtered.iloc[0][class_column] == "FCBK"
    assert filtered.geometry.iloc[0].geom_type == ("Polygon" if class_column == "class" else "Point")


def test_composed_filters_keep_expected_candidate_and_csv_counts() -> None:
    """Area, class, confidence, rank-band, and signal filters intersect."""
    frame = gpd.GeoDataFrame(
        {
            "kiln_id": ["a", "b", "c"],
            "district": ["D1", "D1", "D2"],
            "class": ["FCBK", "Zigzag", "FCBK"],
            "confidence": [0.91, 0.61, 0.88],
            "priority": [4.0, 1.5, 3.0],
            "priority_rank": [1, 3, 2],
            "breached_rules": [["near_school"], [], []],
            "dist_schools_m": [100.0, 5000.0, float("inf")],
            "technology_flagged": [True, False, True],
        },
        geometry=[Point(90.0, 24.0), Point(90.1, 24.1), Point(90.2, 24.2)],
        crs="EPSG:4326",
    )

    filtered = apply_candidate_filters(
        frame,
        RULES,
        districts={"D1"},
        classes={"FCBK"},
        confidence_range=(0.8, 1.0),
        priority_bands={"High"},
        signal_filters={"near_school": SIGNAL_PRESENT},
    )
    csv_result = screening_csv(filtered)
    exported = pd.read_csv(StringIO(csv_result), comment="#")

    assert filtered["kiln_id"].tolist() == ["a"]
    assert len(exported) == len(filtered) == 1
    assert "advisory_use_notice" in exported.columns
    assert "inspection_priority_band" in exported.columns
    assert "geometry" not in exported.columns


def test_missing_signal_fields_are_unknown_and_can_be_filtered_as_unknown() -> None:
    """Missing distance/layer data stays unknown rather than becoming absence."""
    row = {"kiln_id": "unknown", "class_name": "Zigzag", "confidence": 0.7}
    assert signal_status(row, RULES["siting_rules"][0]) == UNKNOWN_SIGNAL

    frame = gpd.GeoDataFrame([row], geometry=[Point(90, 24)], crs="EPSG:4326")
    filtered = apply_candidate_filters(
        frame,
        RULES,
        signal_filters={"near_school": UNKNOWN_SIGNAL},
    )

    assert len(filtered) == 1
    assert "priority_band" not in filtered.columns
    annotated = add_signal_status_columns(frame, RULES)
    assert annotated.loc[0, "screening_signal_status_near_school"] == UNKNOWN_SIGNAL
    assert "Unknown / not available" in screening_csv(annotated)


def test_finite_distance_can_show_only_no_signal_in_available_mapped_data() -> None:
    """A known distant mapped feature is distinct from unavailable coverage."""
    rule = RULES["siting_rules"][0]
    assert signal_status({"dist_schools_m": 1200.0}, rule) == SIGNAL_ABSENT
    assert signal_status({"dist_schools_m": float("inf")}, rule) == UNKNOWN_SIGNAL


def test_priority_bands_are_relative_deterministic_and_leave_scores_unchanged() -> None:
    """Ranks split into relative thirds without changing stored score/rank."""
    frame = pd.DataFrame(
        {"priority": [6.0, 5.0, 4.0, 3.0, 2.0, 1.0], "priority_rank": [1, 2, 3, 4, 5, 6]}
    )

    first = add_priority_bands(frame)
    second = add_priority_bands(frame)

    assert first["priority_band"].tolist() == ["High", "High", "Medium", "Medium", "Low", "Low"]
    assert first["priority_band"].tolist() == second["priority_band"].tolist()
    pd.testing.assert_series_equal(first["priority"], frame["priority"])
    pd.testing.assert_series_equal(first["priority_rank"], frame["priority_rank"])
    reordered = apply_candidate_filters(
        frame.iloc[::-1], {}, priority_order="High to Low"
    )
    assert reordered["priority_rank"].tolist() == [1, 2, 3, 4, 5, 6]

    score_only = apply_candidate_filters(
        pd.DataFrame({"priority": [1.0, 3.0, 2.0]}), {}, priority_order="High to Low"
    )
    assert score_only["priority"].tolist() == [3.0, 2.0, 1.0]
    assert score_only["priority_band"].tolist() == ["High", "Medium", "Low"]


def test_advisory_notice_remains_explicit() -> None:
    """Candidate review language still rejects legal or administrative findings."""
    assert "Screening candidates only" in ADVISORY_NOTICE
    assert "not legal or administrative findings" in ADVISORY_NOTICE
