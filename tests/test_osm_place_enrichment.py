"""Synthetic tests for OSM place and upazila enrichment."""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point, box

from src.data.osm_place_enrichment import join_upazilas, match_nearest_places


def test_nearest_place_and_upazila_match_preserve_kiln_coordinates() -> None:
    """Nearby synthetic features match while distant features stay null."""
    kilns = gpd.GeoDataFrame(
        {"lat": [24.0, 25.0], "lon": [90.0, 90.0], "district": ["A", "B"]},
        geometry=[Point(90.0, 24.0), Point(90.0, 25.0)],
        crs="EPSG:4326",
    )
    places = gpd.GeoDataFrame(
        {"name": ["Sample village"], "place_type": ["village"]},
        geometry=[Point(90.001, 24.0)], crs="EPSG:4326",
    )
    enriched = match_nearest_places(kilns, places)
    assert enriched.loc[0, "nearest_place"] == "Sample village"
    assert 0 < enriched.loc[0, "nearest_place_dist_m"] < 2000
    assert enriched.loc[1, "nearest_place"] is None
    assert enriched["lat"].tolist() == kilns["lat"].tolist()
    boundaries = gpd.GeoDataFrame(
        {"shapeName": ["Sample Upazila"]},
        geometry=[box(89.9, 23.9, 90.1, 24.1)], crs="EPSG:4326",
    )
    with_upazila = join_upazilas(enriched, boundaries, "shapeName")
    assert with_upazila.loc[0, "upazila"] == "Sample Upazila"
    assert with_upazila.loc[1, "upazila"] is None
