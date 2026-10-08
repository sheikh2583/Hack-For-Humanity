"""Load pipeline kiln GeoParquet for the dashboard.

Input schema: point or polygon GeoParquet in EPSG:4326 with pipeline attributes
and optional coordinate columns. Output: GeoDataFrame with centroid ``lat``
and ``lon`` columns.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from src.geo.crs import centroid_longitude, get_projected_crs


def load_kilns(path: Path) -> gpd.GeoDataFrame:
    """Load dashboard rows and ensure centroid coordinates are available.

    Input schema: EPSG:4326 GeoParquet containing point or polygon kiln
    geometries, with optional ``lat``/``lon`` columns. Output: the same rows
    with WGS84 ``lat`` and ``lon`` centroid columns.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_parquet(path)
    if gdf.crs is None:
        raise ValueError("Dashboard GeoParquet must declare a CRS")
    if gdf.empty:
        if "lat" not in gdf.columns:
            gdf["lat"] = []
        if "lon" not in gdf.columns:
            gdf["lon"] = []
        return gdf
    if {"lat", "lon"}.issubset(gdf.columns):
        return gdf
    projected = get_projected_crs(centroid_longitude(gdf))
    centroids = gdf.to_crs(projected).geometry.centroid.to_crs("EPSG:4326")
    gdf["lat"] = centroids.y.to_numpy()
    gdf["lon"] = centroids.x.to_numpy()
    return gdf
