"""Tests for district GeoParquet merge validation."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point

from scripts.merge_candidates import merge_district_candidates


def _write_candidates(path, district: str) -> None:
    """Write one synthetic candidate with a declared district."""
    gpd.GeoDataFrame(
        {"kiln_id": [district], "district": [district], "confidence": [0.8]},
        geometry=[Point(90, 24)], crs="EPSG:4326",
    ).to_parquet(path)


def test_merge_rejects_missing_district_and_keeps_valid_rows(tmp_path) -> None:
    """Canonical output contains only candidates with explicit district metadata."""
    chapai = tmp_path / "chapai.parquet"
    gazipur = tmp_path / "gazipur.parquet"
    output = tmp_path / "kilns.parquet"
    _write_candidates(chapai, "Chapainawabganj")
    _write_candidates(gazipur, "Gazipur")
    result = merge_district_candidates([chapai, gazipur], output)
    assert set(result["district"]) == {"Chapainawabganj", "Gazipur"}

    blank = tmp_path / "blank.parquet"
    _write_candidates(blank, "")
    with pytest.raises(ValueError, match="without a district"):
        merge_district_candidates([blank], output)
