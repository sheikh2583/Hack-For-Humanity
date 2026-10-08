"""Tests for src.geo.osm_layers — error handling.

Verifies that network/timeout errors propagate while
InsufficientResponseError returns an empty GeoDataFrame.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pytest
import yaml
from shapely.geometry import Point, box

from src.geo.osm_layers import (
    LAYER_TAGS,
    PBF_DOWNLOAD_ERROR,
    _annotate_source_provenance,
    _clip_features_to_district,
    _district_bbox,
    _fetch_layer,
    _pbf_reader,
    fetch_all_layers,
)


def test_district_bbox_resolves_named_adm2_polygon(tmp_path: Path) -> None:
    """A name entry resolves to that feature's polygon extent."""
    path = tmp_path / "adm2.geojson"
    gpd.GeoDataFrame(
        {"shapeName": ["Test District"], "geometry": [box(88, 24, 89, 25)]},
        crs="EPSG:4326",
    ).to_file(path, driver="GeoJSON")
    assert _district_bbox("test district", path) == (88.0, 24.0, 89.0, 25.0)


def test_osm_features_are_clipped_to_district_polygon() -> None:
    """A feature inside the bbox but outside the polygon is removed."""
    features = gpd.GeoDataFrame(
        {"name": ["inside", "outside"], "geometry": [box(0.2, 0.2, 0.3, 0.3), box(0.8, 0.8, 0.9, 0.9)]},
        crs="EPSG:4326",
    )
    clipped = _clip_features_to_district(features, box(0, 0, 0.5, 0.5))
    assert clipped["name"].tolist() == ["inside"]


def test_fetched_osm_layer_retains_source_and_feature_provenance() -> None:
    """A fetched feature carries its source identity and access metadata."""
    import pandas as pd

    features = gpd.GeoDataFrame(
        {"name": ["school"], "amenity": ["school"], "geometry": [Point(88.5, 24.5)]},
        index=pd.MultiIndex.from_tuples([("way", 123)], names=["element", "id"]),
        crs="EPSG:4326",
    )
    result = _annotate_source_provenance(
        features, "schools", "https://overpass.example/api/interpreter"
    )

    assert result.loc[result.index[0], "feature_id"] == "('way', 123)"
    assert result.loc[result.index[0], "source_layer_id"] == "openstreetmap:schools"
    assert result.loc[result.index[0], "source_authority"] == "OpenStreetMap contributors"
    assert result.loc[result.index[0], "source_url"] == "https://overpass.example/api/interpreter"
    assert result.loc[result.index[0], "source_accessed_at"]
    assert result.loc[result.index[0], "source_version_date"] is None
    assert "not a legally controlling boundary" in result.loc[result.index[0], "geometry_provenance"]


def test_fetch_all_layers_reuses_cache_unless_refreshed(tmp_path: Path) -> None:
    """A complete local cache avoids Overpass calls unless refresh is requested."""
    aoi_path = tmp_path / "aoi.yaml"
    aoi_path.write_text(yaml.safe_dump({"districts": [{"name": "Test District"}]}))
    features = gpd.GeoDataFrame(
        {"name": ["test"], "geometry": [Point(88.5, 24.5)]},
        crs="EPSG:4326",
    )
    with (
        patch("src.geo.osm_layers._district_geometry", return_value=box(88, 24, 89, 25)),
        patch("src.geo.osm_layers._fetch_layer", return_value=features) as fetch,
        patch("src.geo.osm_layers.render_layer_maps"),
    ):
        fetch_all_layers(aoi_path, tmp_path / "cache")
        assert fetch.call_count == len(LAYER_TAGS)
        fetch_all_layers(aoi_path, tmp_path / "cache")
        assert fetch.call_count == len(LAYER_TAGS)
        fetch_all_layers(aoi_path, tmp_path / "cache", refresh=True)
        assert fetch.call_count == len(LAYER_TAGS) * 2


def test_pbf_fallback_extracts_and_annotates_features(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed Overpass request falls back to a synthetic Pyrosm reader."""
    pbf = tmp_path / "bangladesh-latest.osm.pbf"
    pbf.touch()
    monkeypatch.setattr("src.geo.osm_layers.DEFAULT_PBF", pbf)
    features = gpd.GeoDataFrame(
        {"name": ["school"], "amenity": ["school"], "geometry": [Point(88.2, 24.2)]},
        index=[123], crs="EPSG:4326",
    )

    class FakeReader:
        def get_data_by_custom_criteria(self, **kwargs):
            assert kwargs["custom_filter"] == {"amenity": ["school"]}
            assert kwargs["keep_other_tags"] is False
            return features

    fake_pyrosm = types.ModuleType("pyrosm")
    fake_pyrosm.OSM = lambda *_args, **_kwargs: FakeReader()
    monkeypatch.setitem(sys.modules, "pyrosm", fake_pyrosm)
    _pbf_reader.cache_clear()
    with patch("osmnx.features_from_bbox", side_effect=ConnectionError("blocked")) as overpass:
        result = _fetch_layer("schools", {"amenity": "school"}, (88, 24, 89, 25))
        overpass.assert_not_called()
    assert result["name"].tolist() == ["school"]
    assert "local Geofabrik Bangladesh PBF snapshot" in result.iloc[0]["geometry_provenance"]


def test_railways_layer_is_configured() -> None:
    """The OSM cache schema includes the requested railway layer."""
    assert LAYER_TAGS["railways"] == {"railway": True}


class TestFetchLayerErrors:
    """Tests for error handling in _fetch_layer."""

    def test_network_error_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A network error without local PBF produces the actionable message."""
        monkeypatch.setattr("src.geo.osm_layers.DEFAULT_PBF", tmp_path / "missing.osm.pbf")
        with patch(
            "osmnx.features_from_bbox",
            side_effect=ConnectionError("Simulated network failure"),
        ), pytest.raises(RuntimeError, match=PBF_DOWNLOAD_ERROR):
            _fetch_layer(
                "schools",
                {"amenity": "school"},
                (88.0, 24.0, 88.5, 24.5),
            )

    def test_timeout_error_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A timeout without local PBF produces the actionable message."""
        monkeypatch.setattr("src.geo.osm_layers.DEFAULT_PBF", tmp_path / "missing.osm.pbf")
        with patch(
            "osmnx.features_from_bbox",
            side_effect=TimeoutError("Overpass timeout"),
        ), pytest.raises(RuntimeError, match=PBF_DOWNLOAD_ERROR):
            _fetch_layer(
                "hospitals",
                {"amenity": "hospital"},
                (88.0, 24.0, 88.5, 24.5),
            )

    def test_insufficient_response_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """InsufficientResponseError should return an empty GeoDataFrame."""
        from osmnx._errors import InsufficientResponseError  # type: ignore[import-untyped]

        # Ensure the real user PBF does not change this test's Overpass-only path.
        monkeypatch.setattr("src.geo.osm_layers.DEFAULT_PBF", Path("missing-test.osm.pbf"))
        with patch(
            "osmnx.features_from_bbox",
            side_effect=InsufficientResponseError("No data"),
        ):
            gdf = _fetch_layer(
                "schools",
                {"amenity": "school"},
                (88.0, 24.0, 88.5, 24.5),
            )
            assert gdf.empty
            assert gdf.crs.to_epsg() == 4326
