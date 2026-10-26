"""Compare kiln candidates with YOLO training chip centres.

Input schema: EPSG:4326 kiln GeoParquet and PNG filenames in
``data/interim/yolo_obb/train/images`` using ``latitude_longitude.png``.
Output schema: the same GeoDataFrame with ``detection_status`` and an
overwritten GeoParquet at the requested path.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

from src.geo.crs import centroid_longitude, get_projected_crs

ROOT = Path(__file__).resolve().parents[2]
TRAIN_IMAGES = ROOT / "data" / "interim" / "yolo_obb" / "train" / "images"
UNKNOWN_STATUS = "Unknown (training data not available)"


def load_training_centres(images_dir: Path = TRAIN_IMAGES) -> gpd.GeoDataFrame:
    """Read valid ``lat_lon.png`` chip centres as EPSG:4326 points."""
    if not images_dir.is_dir():
        raise FileNotFoundError(images_dir)
    points: list[Point] = []
    for image_path in images_dir.glob("*.png"):
        stem = image_path.stem
        try:
            lat_text, lon_text = stem.split("_", maxsplit=1)
            lat, lon = float(lat_text), float(lon_text)
        except ValueError:
            continue
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            points.append(Point(lon, lat))
    return gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")


def compare_frames(
    kilns: gpd.GeoDataFrame, centres: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Return kilns labeled by nearest training chip centre distance.

    Input schema: EPSG:4326 kiln geometries and EPSG:4326 point centres.
    Output: copied kiln rows with ``detection_status``; geometry and CRS stay
    as supplied. Candidates under 200 metres are known survey locations.
    """
    if kilns.crs is None or centres.crs is None:
        raise ValueError("Kiln and training centre layers must declare a CRS")
    if centres.empty:
        result = kilns.copy()
        result["detection_status"] = "New candidate (2025-26)"
        return result
    projected = get_projected_crs(centroid_longitude(kilns))
    kiln_points = kilns.to_crs(projected).geometry
    centre_points = centres.to_crs(projected).geometry
    nearest_m = kiln_points.apply(lambda geom: float(centre_points.distance(geom).min()))
    result = kilns.copy()
    result["detection_status"] = nearest_m.lt(200).map(
        {True: "Known (2023-24 survey)", False: "New candidate (2025-26)"}
    )
    return result


def compare_with_training(
    parquet_path: Path = ROOT / "data" / "processed" / "kilns_prioritised.parquet",
    images_dir: Path = TRAIN_IMAGES,
) -> tuple[int, int, int]:
    """Update candidate GeoParquet and return known, new, and total counts.

    A missing or unreadable training image directory marks every row unknown
    and emits a warning; the candidate data remains a GeoParquet.
    """
    kilns = gpd.read_parquet(parquet_path)
    try:
        centres = load_training_centres(images_dir)
        compared = compare_frames(kilns, centres)
    except Exception as error:  # noqa: BLE001 - required unavailable-data fallback
        warnings.warn(f"Training chip centres unavailable: {error}", stacklevel=2)
        compared = kilns.copy()
        compared["detection_status"] = UNKNOWN_STATUS
    compared.to_parquet(parquet_path, index=False)
    known = int(compared["detection_status"].eq("Known (2023-24 survey)").sum())
    new = int(compared["detection_status"].eq("New candidate (2025-26)").sum())
    total = len(compared)
    print(f"Known count: {known}\nNew candidate count: {new}\nTotal: {total}")
    return known, new, total
