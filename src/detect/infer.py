"""YOLO-OBB inference on Sentinel-2 GeoTIFFs.

Input
-----
- ``weights``:    Path to a trained ``best.pt`` (YOLOv8 OBB).
- ``raster_dir``: Directory of GeoTIFF composites exported by
  ``src.data.export_s2``.

Output
------
- ``data/processed/kilns.parquet`` - GeoParquet with columns:

  ============  =========  =============================================
  Column        Dtype      Description
  ============  =========  =============================================
    kiln_id       str        Unique identifier (UUID4)
    geometry      Polygon    OBB polygon in EPSG:4326
    class         str        Kiln class name (FCBK / Zigzag)
    confidence    float64    Detection confidence ∈ [0, 1]
    district      str        District name from filename / AOI config
  ============  =========  =============================================

Processing
----------
1. Tile each GeoTIFF into 128×128 chips with 30 px overlap.
2. Run OBB inference per chip.
3. Convert pixel-space OBB polygons to geographic coords using the
   raster's affine transform.
4. Polygon-IoU NMS across overlapping tiles to merge duplicates.
5. Write GeoParquet.

Contract
--------
>>> from src.detect.infer import run_inference
>>> run_inference(weights=Path("best.pt"), raster_dir=..., output=...)
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.ops import transform as transform_geometry
from shapely.strtree import STRtree

from src.data.convert_sentinelkilndb import OUTPUT_CLASSES
from src.data.normalize import minmax_uint8

# ---------------------------------------------------------------------------
# Coordinate transform helpers
# ---------------------------------------------------------------------------


def _pixel_to_geo(
    pixel_coords: np.ndarray,
    transform: Any,
) -> np.ndarray:
    """Convert pixel (col, row) coordinates to geographic (x, y) using an affine transform.

    Parameters
    ----------
    pixel_coords : np.ndarray
        Array of shape (N, 2) with (col, row) in pixel space.
    transform : affine.Affine or rasterio.transform.Affine
        The raster's affine transformation.

    Returns
    -------
    np.ndarray
        Array of shape (N, 2) with (lon, lat) in the raster's CRS.
    """
    cols = pixel_coords[:, 0]
    rows = pixel_coords[:, 1]
    xs = transform.c + cols * transform.a + rows * transform.b
    ys = transform.f + cols * transform.d + rows * transform.e
    return np.column_stack([xs, ys])


def _polygon_iou(poly_a: Polygon, poly_b: Polygon) -> float:
    """Compute Intersection-over-Union for two shapely Polygons."""
    if not poly_a.is_valid or not poly_b.is_valid:
        return 0.0
    intersection = poly_a.intersection(poly_b).area
    union = poly_a.union(poly_b).area
    return intersection / union if union > 0 else 0.0


def _nms_polygons(
    detections: list[dict[str, Any]],
    iou_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Non-maximum suppression using polygon IoU.

    Parameters
    ----------
    detections : list[dict]
        Each dict has keys ``geometry`` (Polygon), ``confidence`` (float),
        and any other metadata columns.
    iou_threshold : float
        IoU above which a lower-confidence detection is suppressed.

    Returns
    -------
    list[dict]
        Filtered detections.
    """
    # Sort by confidence descending
    dets = sorted(detections, key=lambda d: d["confidence"], reverse=True)
    keep: list[dict[str, Any]] = []

    geometries = [d["geometry"] for d in dets]
    tree = STRtree(geometries)
    suppressed_indices: set[int] = set()
    for idx, det in enumerate(dets):
        if idx in suppressed_indices:
            continue
        suppressed = False
        for candidate in tree.query(det["geometry"]):
            other_idx = int(candidate)
            if other_idx >= idx:
                continue
            if _polygon_iou(det["geometry"], geometries[other_idx]) > iou_threshold:
                suppressed = True
                break
        if not suppressed:
            keep.append(det)
            for candidate in tree.query(det["geometry"]):
                other_idx = int(candidate)
                if other_idx > idx and _polygon_iou(det["geometry"], geometries[other_idx]) > iou_threshold:
                    suppressed_indices.add(other_idx)
    return keep


# ---------------------------------------------------------------------------
# Tiling
# ---------------------------------------------------------------------------


def _tile_raster(
    raster_path: Path,
    chip_size: int = 128,
    overlap: int = 30,
) -> Iterator[dict[str, Any]]:
    """Yield GeoTIFF chips and metadata one at a time.

    Parameters
    ----------
    raster_path : Path
        Path to a GeoTIFF file.
    chip_size : int
        Chip size in pixels.
    overlap : int
        Overlap between adjacent chips in pixels.

    Returns
    -------
    Iterator[dict]
        Each dict has ``array`` (H×W×C), ``row_off``, ``col_off``, and
        ``transform`` (chip-local affine).
    """
    import rasterio  # type: ignore[import-untyped]
    from rasterio.windows import Window  # type: ignore[import-untyped]

    with rasterio.open(raster_path) as src:
        height, width = src.height, src.width
        step = chip_size - overlap
        row_starts = _tile_starts(height, chip_size, step)
        col_starts = _tile_starts(width, chip_size, step)
        for row_off in row_starts:
            for col_off in col_starts:
                win_h = min(chip_size, height - row_off)
                win_w = min(chip_size, width - col_off)
                if win_h < chip_size // 2 or win_w < chip_size // 2:
                    continue  # skip tiny edge tiles
                window = Window(col_off, row_off, win_w, win_h)
                data = src.read(window=window)  # (C, H, W)
                chip_transform = src.window_transform(window)
                yield {
                    "array": np.transpose(data, (1, 2, 0)),  # (H, W, C)
                    "row_off": row_off,
                    "col_off": col_off,
                    "transform": chip_transform,
                }


def _tile_starts(length: int, chip_size: int, stride: int) -> list[int]:
    """Return chip origins including a final window aligned to the far edge."""
    if length <= chip_size:
        return [0]
    starts = list(range(0, length - chip_size + 1, stride))
    far_edge = length - chip_size
    if starts[-1] != far_edge:
        starts.append(far_edge)
    return starts


def _predict_tile(model: Any, tile: dict[str, Any], imgsz: int, conf_threshold: float) -> Any:
    """Predict one RGB tile using Ultralytics' expected BGR array input.

    Input schema: tile contains an HxWx3 RGB uint8 array. Output: Ultralytics
    prediction result for that tile, at the requested inference image size.
    """
    rgb_uint8 = minmax_uint8(tile["array"])
    return model.predict(rgb_uint8[..., ::-1], imgsz=imgsz, conf=conf_threshold, verbose=False)


# ---------------------------------------------------------------------------
# Main inference
# ---------------------------------------------------------------------------


def run_inference(
    weights: Path,
    raster_dir: Path,
    output: Path,
    chip_size: int | None = None,
    overlap: int | None = None,
    imgsz: int = 512,
    conf_threshold: float = 0.1,
    iou_threshold: float = 0.5,
) -> gpd.GeoDataFrame:
    """Run YOLO-OBB inference on all GeoTIFFs in a directory.

    Parameters
    ----------
    weights : Path
        Path to ``best.pt`` (YOLOv8 OBB weights).
    raster_dir : Path
        Directory containing GeoTIFF composites.
    output : Path
        Output GeoParquet file path.
    chip_size, overlap : int
        Tiling parameters matching training setup.
    conf_threshold : float
        Minimum detection confidence.
    iou_threshold : float
        IoU threshold for cross-tile NMS.

    Returns
    -------
    gpd.GeoDataFrame
        Detected kilns with schema matching module docstring.
    """
    import rasterio  # type: ignore[import-untyped]
    import yaml
    from rich import print as rprint
    from ultralytics import YOLO  # type: ignore[import-untyped]

    preprocessing_path = Path(__file__).resolve().parents[2] / "config" / "preprocessing.yaml"
    with preprocessing_path.open(encoding="utf-8") as stream:
        preprocessing = yaml.safe_load(stream)
    patch_config = preprocessing["patches"]
    chip_size = int(chip_size if chip_size is not None else patch_config["size_px"])
    overlap = int(overlap if overlap is not None else patch_config["overlap_px"])
    if int(patch_config["stride_px"]) != chip_size - overlap:
        raise ValueError("Configured patch stride must equal chip size minus overlap")
    if patch_config["origin_px"] != [0, 0] or not patch_config["align_last_patch_to_far_edge"]:
        raise ValueError("Inference tiling supports the configured (0, 0) origin and far-edge alignment")
    if preprocessing["reflectance_conversion"]["method"] != "per_patch_per_band_minmax_uint8":
        raise ValueError("Unsupported preprocessing conversion for inference")

    model = YOLO(str(weights))
    checkpoint = getattr(model, "ckpt", None) or {}
    train_args = checkpoint.get("train_args", {}) if isinstance(checkpoint, dict) else {}
    trained_imgsz = train_args.get("imgsz")
    if trained_imgsz is None:
        raise ValueError("Checkpoint does not record training imgsz; cannot verify inference size")
    if int(trained_imgsz) != imgsz:
        raise ValueError(f"imgsz={imgsz} does not match training imgsz={trained_imgsz}")

    # Convert each detection as it is created; avoid retaining per-CRS
    # GeoDataFrames and a second concatenated copy of all detections.
    all_records: list[dict[str, Any]] = []

    raster_files = sorted(raster_dir.glob("*.tif")) + sorted(raster_dir.glob("*.tiff"))
    rprint(f"[cyan]Found {len(raster_files)} raster file(s) in {raster_dir}[/cyan]")

    for raster_path in raster_files:
        district = raster_path.stem.replace("kilnwatch_", "").split("_")[0]
        rprint(f"[cyan]Processing {raster_path.name} (district={district})...[/cyan]")

        with rasterio.open(raster_path) as src:
            raster_crs = CRS.from_user_input(src.crs).to_string()
        transformer = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True)

        tiles = _tile_raster(raster_path, chip_size=chip_size, overlap=overlap)
        tile_count = 0
        masked_tile_count = 0
        for tile in tiles:
            tile_count += 1
            masked_tile_count += int(bool(np.any(np.all(tile["array"] == 0, axis=2))))
            results = _predict_tile(model, tile, imgsz, conf_threshold)
            for result in results:
                if result.obb is None:
                    continue
                for obb, conf, cls_id in zip(
                    result.obb.xyxyxyxy.cpu().numpy(),
                    result.obb.conf.cpu().numpy(),
                    result.obb.cls.cpu().numpy().astype(int),
                ):
                    # obb shape: (4, 2) - pixel coords (col, row)
                    geo_coords = _pixel_to_geo(obb, tile["transform"])
                    polygon = Polygon(geo_coords)
                    if not polygon.is_valid:
                        polygon = polygon.buffer(0)
                    polygon_wgs84 = transform_geometry(transformer.transform, polygon)

                    all_records.append(
                        {
                            "kiln_id": str(uuid.uuid4()),
                            "geometry": polygon_wgs84,
                            "class": OUTPUT_CLASSES.get(int(cls_id), f"unknown_{cls_id}"),
                            "confidence": float(conf),
                            "district": district,
                        }
                    )
        masked_tile_fraction = masked_tile_count / tile_count if tile_count else 0.0
        rprint(f"  -> {tile_count} tiles processed one at a time")
        rprint(f"  Tiles containing masked zero pixels: {masked_tile_fraction:.3%}")

    rprint(f"[cyan]{len(all_records)} raw detections before NMS.[/cyan]")

    # Cross-tile NMS (in EPSG:4326 - acceptable for small OBBs)
    kept = _nms_polygons(all_records, iou_threshold=iou_threshold)
    rprint(f"[green]{len(kept)} detections after NMS.[/green]")

    # Build final GeoDataFrame
    if kept:
        gdf = gpd.GeoDataFrame(kept, crs="EPSG:4326")
    else:
        gdf = gpd.GeoDataFrame(
            columns=["kiln_id", "geometry", "class", "confidence", "district"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(output)
    rprint(f"[green]Kilns written to {output}[/green]")
    return gdf

