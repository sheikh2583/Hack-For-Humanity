"""Export bounding-box Sentinel-2 composites for inference.

Input schema: AOI YAML with district ``name`` values matching geoBoundaries
ADM2 ``shapeName`` and preprocessing YAML. Output: Earth Engine GeoTIFF
exports containing raw B4/B3/B2 reflectance at EPSG:4326 degree resolution.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_MARGIN_DEGREES = 0.05
EXPORT_SCALE_METERS = 10


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
    """Submit Earth Engine exports using configured pilot dates.

    Input schema: AOI YAML ``districts`` list and preprocessing YAML ``pilot``
    dates. Output: Drive GeoTIFF tasks; this function makes Earth Engine calls.
    """
    preprocessing_config = preprocessing_config or PROJECT_ROOT / "config" / "preprocessing.yaml"
    boundaries_path = boundaries_path or PROJECT_ROOT / "data/raw/boundaries/geoBoundaries_BGD_ADM2.geojson"
    prep = _read_yaml(preprocessing_config)
    pilot = prep.get("pilot", {})
    start_date, end_date = pilot.get("start_date"), pilot.get("end_date")
    if not start_date or not end_date:
        raise RuntimeError("Set both pilot.start_date and pilot.end_date in config/preprocessing.yaml")
    aoi = _read_yaml(aoi_config)
    if not boundaries_path.exists():
        raise FileNotFoundError(f"ADM2 boundaries not found: {boundaries_path}")

    earthengine_project = os.environ.get("KILNWATCH_EE_PROJECT")
    if not earthengine_project:
        raise RuntimeError("KILNWATCH_EE_PROJECT is missing; set it to your Google Cloud project ID")
    import ee  # type: ignore[import-untyped]
    from rich import print as rprint

    ee.Initialize(project=os.environ.get("KILNWATCH_EE_PROJECT"))
    rgb_bands = prep["rgb_bands"]
    if rgb_bands != ["B4", "B3", "B2"]:
        raise ValueError("Earth Engine export is defined for raw B4, B3, B2 bands")
    collection_id = prep["collection"]
    cloud_property = str(prep["cloud_filter"]["property"])
    cloud_limit = float(prep["cloud_filter"]["property_less_than"])
    boundaries = gpd.read_file(boundaries_path)
    if "shapeName" not in boundaries:
        raise ValueError("ADM2 GeoJSON must contain the geoBoundaries shapeName field")
    for district in aoi["districts"]:
        name = district["name"]
        boundary_name = district.get("boundary_name", name)
        geometry, _ = _district_geometry(
            boundaries_path, boundary_name, prep["output"]["district_crs"]
        )
        from shapely.geometry import shape

        bounds = shape(geometry).bounds
        bbox_coords = [
            bounds[0] - EXPORT_MARGIN_DEGREES,
            bounds[1] - EXPORT_MARGIN_DEGREES,
            bounds[2] + EXPORT_MARGIN_DEGREES,
            bounds[3] + EXPORT_MARGIN_DEGREES,
        ]
        bbox = ee.Geometry.BBox(*bbox_coords, proj="EPSG:4326")
        collection = (
            ee.ImageCollection(collection_id)
            .filterBounds(bbox)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt(cloud_property, cloud_limit))
            .select(rgb_bands)
            .sort(cloud_property)
        )
        scene_count = int(collection.size().getInfo())
        rprint(f"{name}: compositing {scene_count} Sentinel-2 scene(s) with cloud cover < {cloud_limit}%")
        composite = collection.median().select(rgb_bands)

        # Keep exported values raw; the recorded training recipe applies per-patch min/max later.
        task = ee.batch.Export.image.toDrive(
            image=composite,
            description=f"kilnwatch_{name}_{start_date}_{end_date}",
            folder="kilnwatch_exports",
            region=bbox,
            crs="EPSG:4326",
            scale=EXPORT_SCALE_METERS,
            maxPixels=1e13,
            fileFormat="GeoTIFF",
        )
        task.start()
        rprint(f"Export task started for {name} (EPSG:4326): {task.status()}")


def main() -> None:
    """CLI: configure the AOI and submit district exports to Earth Engine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aoi", type=Path, default=PROJECT_ROOT / "config/aoi.yaml")
    args = parser.parse_args()
    export_composites(args.aoi)


if __name__ == "__main__":
    main()
