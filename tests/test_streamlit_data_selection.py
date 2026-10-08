"""Synthetic tests for choosing the latest processed detection GeoParquet."""

import os
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

from app.streamlit_app import class_counts, latest_kilns_file, load_data


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


@pytest.mark.parametrize(
    ("class_column", "geometries", "coordinates"),
    [
        (
            "class",
            [box(90.0, 24.0, 90.01, 24.01), box(90.02, 24.0, 90.03, 24.01)],
            None,
        ),
        (
            "class_name",
            [Point(90.005, 24.005), Point(90.025, 24.005)],
            [(24.005, 90.005), (24.005, 90.025)],
        ),
    ],
)
def test_dashboard_loads_both_class_schemas_and_counts(
    tmp_path: Path,
    class_column: str,
    geometries: list,
    coordinates: list[tuple[float, float]] | None,
) -> None:
    """Polygon and point pipeline schemas normalize to the same class counts."""
    data: dict[str, object] = {
        "kiln_id": ["fcbk", "zigzag"],
        class_column: ["FCBK", "Zigzag"],
        "confidence": [0.8, 0.9],
        "district": ["Synthetic", "Synthetic"],
    }
    if coordinates is not None:
        data["lat"] = [value[0] for value in coordinates]
        data["lon"] = [value[1] for value in coordinates]
    path = tmp_path / "kilns_schema.parquet"
    gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326").to_parquet(path)

    loaded = load_data(path)

    assert class_counts(loaded) == (1, 1)
    assert {"class", "lat", "lon"}.issubset(loaded.columns)
    assert loaded["lat"].notna().all()
    assert loaded["lon"].notna().all()
