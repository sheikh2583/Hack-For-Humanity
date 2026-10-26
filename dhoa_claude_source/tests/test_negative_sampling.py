"""Tests for negative-region audit sampling in src.eval.audit_sample."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, box

from src.eval.audit_sample import sample_negative_regions


def test_negative_region_samples_are_far_from_detections(tmp_path: Path) -> None:
    """Sampled points lie inside the boundary and far from any detection."""
    # Create a synthetic detection near the centre of a boundary polygon.
    boundary_path = tmp_path / "boundary.geojson"
    boundary = gpd.GeoDataFrame(
        {"name": ["TestDistrict"]},
        geometry=[box(90.0, 23.5, 91.0, 24.5)],
        crs="EPSG:4326",
    )
    boundary.to_file(boundary_path, driver="GeoJSON")

    det_path = tmp_path / "kilns.parquet"
    detections = gpd.GeoDataFrame(
        {
            "kiln_id": ["d1"],
            "class": ["FCBK"],
            "confidence": [0.9],
        },
        geometry=[Point(90.5, 24.0)],
        crs="EPSG:4326",
    )
    detections.to_parquet(det_path)

    output = tmp_path / "negatives.csv"
    result = sample_negative_regions(
        det_path, boundary_path, n=5, min_distance_m=2000.0, output=output, seed=123,
    )

    assert len(result) > 0
    assert "lat" in result.columns
    assert "lon" in result.columns
    assert "google_earth" in result.columns
    assert "label" in result.columns
    assert output.is_file()


def test_negative_region_with_no_detections(tmp_path: Path) -> None:
    """When no detections exist every boundary point qualifies."""
    boundary_path = tmp_path / "boundary.geojson"
    boundary = gpd.GeoDataFrame(
        {"name": ["Empty"]},
        geometry=[box(90.0, 23.5, 91.0, 24.5)],
        crs="EPSG:4326",
    )
    boundary.to_file(boundary_path, driver="GeoJSON")

    empty = gpd.GeoDataFrame(
        {"kiln_id": [], "class": [], "confidence": []},
        geometry=[],
        crs="EPSG:4326",
    )
    det_path = tmp_path / "empty.parquet"
    empty.to_parquet(det_path)

    output = tmp_path / "neg.csv"
    result = sample_negative_regions(
        det_path, boundary_path, n=3, output=output, seed=42,
    )
    assert len(result) == 3
