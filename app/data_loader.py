"""Load prioritised kiln GeoParquet for the dashboard.

Input schema: GeoParquet with kiln geometries in EPSG:4326 and pipeline
attributes. Output: GeoDataFrame with centroid ``lat`` and ``lon`` columns.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from src.geo.crs import centroid_longitude, get_projected_crs


def load_kilns(path: Path) -> gpd.GeoDataFrame:
    """Load dashboard rows from a prioritised kiln GeoParquet."""
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_parquet(path)
    if gdf.crs is None:
        raise ValueError("Dashboard GeoParquet must declare a CRS")
    projected = get_projected_crs(centroid_longitude(gdf))
    centroids = gdf.to_crs(projected).geometry.centroid.to_crs("EPSG:4326")
    gdf["lat"] = centroids.y.to_numpy()
    gdf["lon"] = centroids.x.to_numpy()
    return gdf
