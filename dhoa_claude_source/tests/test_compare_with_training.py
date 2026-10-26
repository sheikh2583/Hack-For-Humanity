"""Synthetic checks for training chip proximity classification."""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point

from src.eval.compare_with_training import compare_frames


def test_compare_frames_marks_near_known_and_far_new() -> None:
    """A close synthetic point is known while a distant one is new."""
    kilns = gpd.GeoDataFrame(
        {"kiln_id": ["near", "far"]},
        geometry=[Point(90.0, 23.0), Point(90.02, 23.0)],
        crs="EPSG:4326",
    )
    centres = gpd.GeoDataFrame(geometry=[Point(90.0, 23.0)], crs="EPSG:4326")
    compared = compare_frames(kilns, centres)
    assert compared["detection_status"].tolist() == [
        "Known (2023-24 survey)", "New candidate (2025-26)"
    ]
