"""Extract OSM named places and enrich kiln GeoParquet rows.

Input schema: Bangladesh OSM PBF plus EPSG:4326 kiln point GeoParquet.
Output schemas: EPSG:4326 place-point GeoParquet and enriched kiln GeoParquet.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.geo.crs import get_projected_crs

PLACE_TYPES = ("village", "town", "hamlet", "suburb", "neighbourhood", "city")
NEW_PLACE_COLUMNS = ("nearest_place", "nearest_place_dist_m", "nearest_place_type")


def _first_name(row: pd.Series) -> object:
    """Choose English name when present, otherwise the OSM name/local name."""
    for key in ("name:en", "name", "name:bn"):
        value = row.get(key)
        if value is not None and pd.notna(value) and str(value).strip():
            return str(value).strip()
    return None


def extract_osm_places(pbf_path: Path, output_path: Path) -> gpd.GeoDataFrame:
    """Extract named place tags and save centroid points as GeoParquet.

    Input schema: OSM PBF path. Output schema: ``name``, ``place_type``,
    ``lat``, ``lon``, and centroid ``geometry`` in EPSG:4326.
    """
    from pyrosm import OSM

    osm = OSM(str(pbf_path), engine="out_of_core", workers=1, keep_metadata=False)
    source = osm.get_pois(
        custom_filter={"place": list(PLACE_TYPES)},
        tags_to_keep=["place", "name", "name:en", "name:bn"],
    )
    if source is None or source.empty:
        raise ValueError("No place features were extracted from the OSM PBF")
    if source.crs is None or "geometry" not in source:
        raise ValueError("OSM place features must include geometry and a declared CRS")

    names = source.apply(_first_name, axis=1)
    source = source.loc[names.notna()].copy()
    source["name"] = names.loc[source.index]
    source["place_type"] = source["place"].astype("string")
    source = source.to_crs("EPSG:4326")
    projected = source.to_crs(get_projected_crs(float(source.geometry.union_all().centroid.x)))
    centroids = projected.geometry.centroid.to_crs("EPSG:4326")
    places = gpd.GeoDataFrame(
        {
            "name": source["name"].astype("string"),
            "place_type": source["place_type"].astype("string"),
            "lon": centroids.x,
            "lat": centroids.y,
        },
        geometry=centroids,
        crs="EPSG:4326",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    places.to_parquet(output_path, index=False)
    return places


def match_nearest_places(
    kilns: gpd.GeoDataFrame,
    places: gpd.GeoDataFrame,
    max_distance_m: float = 2000.0,
) -> gpd.GeoDataFrame:
    """Add nearest OSM place fields without changing kiln coordinates/columns.

    Input schemas: kiln GeoDataFrame with numeric ``lat``/``lon`` in WGS84;
    place GeoDataFrame with ``name``/``place_type`` and WGS84 Point geometry.
    Output schema: copied kiln frame plus nearest place name, distance metres,
    and place type; unmatched values are null.
    """
    conflicts = set(NEW_PLACE_COLUMNS).intersection(kilns.columns)
    if conflicts:
        raise ValueError(f"Refusing to overwrite existing kiln columns: {sorted(conflicts)}")
    required_kiln = {"lat", "lon"}
    required_places = {"name", "place_type", "geometry"}
    if not required_kiln.issubset(kilns.columns) or not required_places.issubset(places.columns):
        raise ValueError("Kilns require lat/lon; places require name/place_type/geometry")
    if places.crs is None or kilns.crs is None:
        raise ValueError("Both GeoDataFrames must declare a CRS")

    result = kilns.copy()
    result["nearest_place"] = pd.Series([None] * len(result), index=result.index, dtype="object")
    result["nearest_place_dist_m"] = pd.Series(float("nan"), index=result.index, dtype="float64")
    result["nearest_place_type"] = pd.Series([None] * len(result), index=result.index, dtype="object")
    if result.empty or places.empty:
        return result

    longitude = pd.to_numeric(result["lon"], errors="coerce")
    latitude = pd.to_numeric(result["lat"], errors="coerce")
    valid = longitude.notna() & latitude.notna()
    kiln_points = gpd.GeoDataFrame(
        {"_kiln_index": result.index[valid]},
        geometry=gpd.points_from_xy(longitude.loc[valid], latitude.loc[valid]),
        crs="EPSG:4326",
    )
    projected_crs = get_projected_crs(float(longitude.loc[valid].mean()) if valid.any() else 90.0)
    kiln_points = kiln_points.to_crs(projected_crs)
    place_points = places[["name", "place_type", "geometry"]].to_crs(projected_crs)
    nearest = gpd.sjoin_nearest(
        kiln_points,
        place_points,
        how="left",
        max_distance=max_distance_m,
        distance_col="nearest_place_dist_m",
    )
    for _, match in nearest.dropna(subset=["name"]).iterrows():
        index = match["_kiln_index"]
        result.at[index, "nearest_place"] = match["name"]
        result.at[index, "nearest_place_dist_m"] = float(match["nearest_place_dist_m"])
        result.at[index, "nearest_place_type"] = match["place_type"]
    return result


def join_upazilas(kilns: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame, name_column: str) -> gpd.GeoDataFrame:
    """Spatially join kiln points to supplied upazila polygons.

    Input schemas: WGS84 kiln GeoDataFrame with ``lat``/``lon`` and polygon
    boundary GeoDataFrame containing ``name_column``. Output: copied kiln frame
    with ``upazila`` populated only for matched point-in-polygon rows.
    """
    if "upazila" in kilns.columns:
        raise ValueError("Refusing to overwrite existing kiln upazila column")
    if name_column not in boundaries.columns:
        raise ValueError(f"Upazila name field {name_column!r} is absent")
    result = kilns.copy()
    result["upazila"] = pd.Series([None] * len(result), index=result.index, dtype="object")
    points = gpd.GeoDataFrame(
        {"_kiln_index": result.index},
        geometry=gpd.points_from_xy(result["lon"], result["lat"]),
        crs="EPSG:4326",
    )
    polygons = boundaries[[name_column, "geometry"]].to_crs("EPSG:4326")
    joined = gpd.sjoin(points, polygons, how="left", predicate="within")
    for _, match in joined.dropna(subset=[name_column]).iterrows():
        result.at[match["_kiln_index"], "upazila"] = match[name_column]
    return result
