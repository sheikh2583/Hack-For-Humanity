"""Tests for config-driven Sentinel-2 preprocessing setup."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import yaml

from src.data.export_s2 import district_epsg, export_composites


def test_recipe_config_and_district_crs() -> None:
    """Recipe matches the documented authors' code and district CRS rule."""
    recipe = yaml.safe_load(Path("config/preprocessing.yaml").read_text(encoding="utf-8"))
    assert recipe["preprocessing_verified"] is False
    assert recipe["collection"] == "COPERNICUS/S2_SR_HARMONIZED"
    assert recipe["cloud_mask"]["qa60_bit"] == 10
    assert recipe["patches"]["stride_px"] == 98
    assert recipe["reflectance_conversion"]["method"] == "per_patch_per_band_minmax_uint8"
    crs_rule = recipe["output"]["district_crs"]
    assert district_epsg(89.99, threshold=crs_rule["centroid_longitude_threshold"], west_epsg=crs_rule["west_of_threshold"], east_epsg=crs_rule["at_or_east_of_threshold"]) == "EPSG:32645"
    assert district_epsg(
        90.0,
        threshold=crs_rule["centroid_longitude_threshold"],
        west_epsg=crs_rule["west_of_threshold"],
        east_epsg=crs_rule["at_or_east_of_threshold"],
    ) == "EPSG:32646"


def test_export_stops_while_recipe_unverified(tmp_path: Path) -> None:
    """Missing pilot dates stop before any Earth Engine authentication attempt."""
    prep = tmp_path / "preprocessing.yaml"
    prep.write_text("pilot: {start_date: '', end_date: null}\n", encoding="utf-8")
    aoi = tmp_path / "aoi.yaml"
    aoi.write_text("districts: []\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="pilot.start_date"):
        export_composites(aoi, preprocessing_config=prep, boundaries_path=tmp_path / "missing.geojson")


def test_export_stops_when_pilot_date_range_is_missing(tmp_path: Path) -> None:
    """A verified recipe still requires a human-supplied pilot date range."""
    prep = tmp_path / "preprocessing.yaml"
    prep.write_text("pilot: {start_date: '2025-11-01', end_date: ''}\n", encoding="utf-8")
    aoi = tmp_path / "aoi.yaml"
    aoi.write_text("districts: []\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="pilot.start_date"):
        export_composites(aoi, preprocessing_config=prep, boundaries_path=tmp_path / "missing.geojson")


def test_export_requires_earth_engine_project_before_initialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing project configuration is rejected before calling ``ee.Initialize``."""
    prep = tmp_path / "preprocessing.yaml"
    prep.write_text(
        "pilot: {start_date: '2024-01-01', end_date: '2024-02-01'}\n",
        encoding="utf-8",
    )
    aoi = tmp_path / "aoi.yaml"
    aoi.write_text("districts: []\n", encoding="utf-8")
    boundaries = tmp_path / "boundaries.geojson"
    boundaries.write_text("{}", encoding="utf-8")
    initialize_called = False

    def initialize(**_: object) -> None:
        nonlocal initialize_called
        initialize_called = True

    monkeypatch.setitem(sys.modules, "ee", types.SimpleNamespace(Initialize=initialize))
    monkeypatch.delenv("EARTHENGINE_PROJECT", raising=False)
    monkeypatch.delenv("KILNWATCH_EE_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="KILNWATCH_EE_PROJECT"):
        export_composites(aoi, preprocessing_config=prep, boundaries_path=boundaries)
    assert initialize_called is False


def test_configured_districts_resolve_in_real_adm2_file() -> None:
    """Configured boundary names resolve uniquely against the supplied ADM2 file."""
    from src.data.export_s2 import _district_geometry

    aoi = yaml.safe_load(Path("config/aoi.yaml").read_text(encoding="utf-8"))
    recipe = yaml.safe_load(Path("config/preprocessing.yaml").read_text(encoding="utf-8"))
    boundaries = Path("data/raw/boundaries/geoBoundaries_BGD_ADM2.geojson")
    if not boundaries.is_file():  # the boundary file is not shipped in share/review archives
        pytest.skip(f"{boundaries} not present on this machine")
    for district in aoi["districts"]:
        geometry, epsg = _district_geometry(
            boundaries,
            district.get("boundary_name", district["name"]),
            recipe["output"]["district_crs"],
        )
        assert geometry["type"] in {"Polygon", "MultiPolygon"}
        assert epsg in {"EPSG:32645", "EPSG:32646"}
