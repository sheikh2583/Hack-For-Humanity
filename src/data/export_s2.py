"""Export district-clipped Sentinel-2 composites for inference.

Input schema: AOI YAML with district ``name`` values matching geoBoundaries
ADM2 ``shapeName`` and preprocessing YAML. Output: Earth Engine GeoTIFF
exports containing raw B4/B3/B2 reflectance in a district-specific UTM CRS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML mapping used by the exporter."""
    with path.open(encoding="utf-8") as stream:
        result = yaml.safe_load(stream)
    if not isinstance(result, dict):
        raise TypeError(f"Expected a YAML mapping in {path}")
    return result


def district_epsg(
    longitude: float,
    threshold: float = 90,
    west_epsg: str = "EPSG:32645",
    east_epsg: str = "EPSG:32646",
) -> str:
    """Return the prescribed Bangladesh UTM CRS for a district centroid."""
    return west_epsg if longitude < threshold else east_epsg


def _district_geometry(
    boundaries_path: Path, district_name: str, crs_config: dict[str, Any]
) -> tuple[Any, str]:
    """Read a named ADM2 polygon and return its EE geometry coordinates and CRS."""
    boundaries = gpd.read_file(boundaries_path)
    if "shapeName" not in boundaries.columns:
        raise ValueError("ADM2 GeoJSON must contain the geoBoundaries shapeName field")
    match = boundaries[boundaries["shapeName"].str.casefold() == district_name.casefold()]
    if len(match) != 1:
        raise ValueError(f"Expected one ADM2 polygon named {district_name!r}; found {len(match)}")
    polygon = match.to_crs("EPSG:4326").geometry.iloc[0]
    return polygon.__geo_interface__, district_epsg(
        float(polygon.centroid.x),
        float(crs_config["centroid_longitude_threshold"]),
        str(crs_config["west_of_threshold"]),
        str(crs_config["at_or_east_of_threshold"]),
    )


def export_composites(
    aoi_config: Path,
    preprocessing_config: Path | None = None,
    boundaries_path: Path | None = None,
) -> None:
    """Submit Earth Engine exports, refusing unverified preprocessing settings."""
    preprocessing_config = preprocessing_config or PROJECT_ROOT / "config" / "preprocessing.yaml"
    boundaries_path = boundaries_path or PROJECT_ROOT / "data/raw/boundaries/geoBoundaries_BGD_ADM2.geojson"
    prep = _read_yaml(preprocessing_config)
    if prep.get("preprocessing_verified") is not True:
        raise RuntimeError("Set preprocessing_verified: true after reviewing config/preprocessing.yaml")
    aoi = _read_yaml(aoi_config)
    if not boundaries_path.exists():
        raise FileNotFoundError(f"ADM2 boundaries not found: {boundaries_path}")

    import ee  # type: ignore[import-untyped]
    from rich import print as rprint

    ee.Initialize()
    bands = prep["bands"]
    rgb_bands = prep["rgb_bands"]
    cloud_mask_band = str(prep["cloud_mask"]["band"])
    cloud_bit = int(prep["cloud_mask"]["qa60_bit"])
    collection_id = prep["collection"]
    start_date, end_date = prep["date_range"]
    cloud_property = str(prep["cloud_filter"]["property"])
    cloud_limit = float(prep["cloud_filter"]["property_less_than"])
    scale = int(prep["output"]["scale_m"])
    count_scale = int(prep["valid_pixel_count"]["scale_m"])
    count_band = str(prep["valid_pixel_count"]["band"])
    if prep["valid_pixel_count"]["reducer"] != "count":
        raise ValueError("Only the recorded ee.Reducer.count valid-pixel rule is supported")
    method = prep["compositing_method"]

    boundaries = gpd.read_file(boundaries_path)
    if "shapeName" not in boundaries:
        raise ValueError("ADM2 GeoJSON must contain the geoBoundaries shapeName field")
    for district in aoi["districts"]:
        name = district["name"]
        boundary_name = district.get("boundary_name", name)
        geometry, epsg = _district_geometry(
            boundaries_path, boundary_name, prep["output"]["district_crs"]
        )
        region = ee.Geometry(geometry, proj="EPSG:4326", geodesic=False)
        projection = ee.Projection(epsg)
        collection = (
            ee.ImageCollection(collection_id)
            .filterBounds(region)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt(cloud_property, cloud_limit))
            .select(bands)
            .sort(cloud_property)
        )

        def mask_clouds(image: Any) -> Any:
            qa = image.select(cloud_mask_band).uint16()
            return image.updateMask(qa.bitwiseAnd(1 << cloud_bit).eq(0))

        if method == "median":
            composite = mask_clouds(collection.median()).select(rgb_bands)
        elif method == "best_or_median":
            best = mask_clouds(ee.Image(collection.first()))
            median = mask_clouds(collection.median())
            best_count = best.select(count_band).reduceRegion(
                reducer=ee.Reducer.count(), geometry=region, scale=count_scale, maxPixels=1e10
            ).get(count_band)
            median_count = median.select(count_band).reduceRegion(
                reducer=ee.Reducer.count(), geometry=region, scale=count_scale, maxPixels=1e10
            ).get(count_band)
            choose_best = ee.Number(best_count).gt(ee.Number(median_count))
            composite = ee.Image(ee.Algorithms.If(choose_best, best, median)).select(rgb_bands)
        else:
            raise ValueError(f"Unsupported compositing_method: {method}")

        # Keep exported values raw; the recorded training recipe applies per-patch min/max later.
        task = ee.batch.Export.image.toDrive(
            image=composite.clip(region).reproject(crs=projection, scale=scale),
            description=f"kilnwatch_{name}_{start_date}_{end_date}",
            folder="kilnwatch_exports",
            region=region,
            crs=epsg,
            scale=scale,
            maxPixels=1e13,
            fileFormat="GeoTIFF",
        )
        task.start()
        rprint(f"Export task started for {name} ({epsg}): {task.status()}")
