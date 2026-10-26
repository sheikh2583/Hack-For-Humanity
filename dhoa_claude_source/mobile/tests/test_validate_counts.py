"""Tests for src.eval.validate_counts — district comparison and closure proximity."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.eval.validate_counts import check_closure_proximity, compare_district_counts


def _write_detections(path: Path) -> None:
    """Create a tiny synthetic detection GeoParquet."""
    gdf = gpd.GeoDataFrame(
        {
            "kiln_id": ["k1", "k2", "k3"],
            "district": ["Gazipur", "Gazipur", "Nawabganj"],
            "class": ["FCBK", "Zigzag", "FCBK"],
            "confidence": [0.9, 0.7, 0.85],
        },
        geometry=[Point(90.4, 24.0), Point(90.401, 24.001), Point(88.3, 24.6)],
        crs="EPSG:4326",
    )
    gdf.to_parquet(path)


class TestCompareDistrictCounts:
    """Synthetic tests for district-level detection count comparison."""

    def test_matching_districts(self, tmp_path: Path) -> None:
        """Counts and ratio are computed correctly for matching districts."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        ref_csv = tmp_path / "ref.csv"
        ref_csv.write_text("district,reported_count\nGazipur,4\nNawabganj,2\n", encoding="utf-8")

        result = compare_district_counts(det_path, ref_csv)
        assert result["Gazipur"]["detected"] == 2
        assert result["Gazipur"]["reported"] == 4
        assert result["Gazipur"]["ratio"] == 0.5
        assert result["Nawabganj"]["detected"] == 1
        assert result["Nawabganj"]["reported"] == 2
        assert result["Nawabganj"]["ratio"] == 0.5

    def test_extra_district_in_reference(self, tmp_path: Path) -> None:
        """A district in the reference but not in detections gets detected=0."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        ref_csv = tmp_path / "ref.csv"
        ref_csv.write_text("district,reported_count\nGazipur,2\nBogra,10\n", encoding="utf-8")

        result = compare_district_counts(det_path, ref_csv)
        assert result["Bogra"]["detected"] == 0
        assert result["Bogra"]["reported"] == 10

    def test_zero_reported_gives_null_ratio(self, tmp_path: Path) -> None:
        """Zero reported count results in ratio=None."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        ref_csv = tmp_path / "ref.csv"
        ref_csv.write_text("district,reported_count\nGazipur,0\n", encoding="utf-8")

        result = compare_district_counts(det_path, ref_csv)
        assert result["Gazipur"]["ratio"] is None

    def test_bad_csv_raises(self, tmp_path: Path) -> None:
        """Reference CSV without required columns raises ValueError."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        ref_csv = tmp_path / "bad.csv"
        ref_csv.write_text("name,count\nGazipur,5\n", encoding="utf-8")
        with pytest.raises(ValueError, match="reported_count"):
            compare_district_counts(det_path, ref_csv)


class TestCheckClosureProximity:
    """Synthetic tests for closure proximity check."""

    def test_nearby_detection_found(self, tmp_path: Path) -> None:
        """A closure location near a detection returns its distance."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        closure_csv = tmp_path / "closures.csv"
        # Very close to k1 at (90.4, 24.0)
        closure_csv.write_text(
            "latitude,longitude,closure_year\n24.001,90.401,2022\n",
            encoding="utf-8",
        )

        result = check_closure_proximity(det_path, closure_csv)
        assert len(result) == 1
        assert result[0]["nearest_detection_m"] is not None
        assert result[0]["nearest_detection_m"] < 500  # should be ~100-200 m
        assert result[0]["nearest_class"] in {"FCBK", "Zigzag"}

    def test_far_closure_returns_none(self, tmp_path: Path) -> None:
        """A closure far from any detection returns None distance."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        closure_csv = tmp_path / "closures.csv"
        # Very far away
        closure_csv.write_text(
            "latitude,longitude\n22.0,89.0\n",
            encoding="utf-8",
        )

        result = check_closure_proximity(det_path, closure_csv, max_distance_m=1000.0)
        assert len(result) == 1
        assert result[0]["nearest_detection_m"] is None

    def test_empty_detections(self, tmp_path: Path) -> None:
        """No detections returns None distance for all closures."""
        empty_gdf = gpd.GeoDataFrame(
            {"kiln_id": [], "class": [], "confidence": []},
            geometry=[],
            crs="EPSG:4326",
        )
        det_path = tmp_path / "empty.parquet"
        empty_gdf.to_parquet(det_path)
        closure_csv = tmp_path / "closures.csv"
        closure_csv.write_text("latitude,longitude\n24.0,90.4\n", encoding="utf-8")

        result = check_closure_proximity(det_path, closure_csv)
        assert len(result) == 1
        assert result[0]["nearest_detection_m"] is None

    def test_bad_closure_csv_raises(self, tmp_path: Path) -> None:
        """Closure CSV without required columns raises ValueError."""
        det_path = tmp_path / "kilns.parquet"
        _write_detections(det_path)
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("lat,lon\n24.0,90.4\n", encoding="utf-8")
        with pytest.raises(ValueError, match="latitude"):
            check_closure_proximity(det_path, bad_csv)
