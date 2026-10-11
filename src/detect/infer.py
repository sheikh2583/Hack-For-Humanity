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
  detector_model str       Checkpoint model identity (training argument or filename)
  detector_version str|None Ultralytics package/checkpoint version
  imagery_date  str|None   Acquisition date when present; null otherwise
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

import re
import unicodedata
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
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


def read_as_windows(
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
                if src.count != 3:
                    raise ValueError(f"Expected 3-band RGB raster, found {src.count}: {raster_path}")
                data = src.read(window=window, out_dtype="float64")  # all bands, (C, H, W)
                chip_transform = src.window_transform(window)
                yield {
                    "array": np.transpose(data, (1, 2, 0)),  # (H, W, C)
                    "row_off": row_off,
                    "col_off": col_off,
                    "transform": chip_transform,
                }


def _tile_raster(
    raster_path: Path,
    chip_size: int = 128,
    overlap: int = 30,
) -> Iterator[dict[str, Any]]:
    """Backward-compatible alias for the streaming window reader."""
    return read_as_windows(raster_path, chip_size=chip_size, overlap=overlap)


def _tile_starts(length: int, chip_size: int, stride: int) -> list[int]:
    """Return chip origins including a final window aligned to the far edge."""
    if length <= chip_size:
        return [0]
    starts = list(range(0, length - chip_size + 1, stride))
    far_edge = length - chip_size
    if starts[-1] != far_edge:
        starts.append(far_edge)
    return starts


def _count_tiles(width: int, height: int, chip_size: int = 128, overlap: int = 30) -> int:
    """Count non-tiny raster windows for the configured tile size and overlap."""
    stride = chip_size - overlap
    rows = sum(min(chip_size, height - start) >= chip_size // 2 for start in _tile_starts(height, chip_size, stride))
    cols = sum(min(chip_size, width - start) >= chip_size // 2 for start in _tile_starts(width, chip_size, stride))
    return rows * cols


def _predict_tile(
    model: Any, tile: dict[str, Any], imgsz: int, conf_threshold: float, device: str = "cpu"
) -> Any:
    """Predict one RGB tile using Ultralytics' expected BGR array input.

    Input schema: tile contains an HxWx3 RGB uint8 array. Output: Ultralytics
    prediction result for that tile, at the requested inference image size.
    """
    rgb_uint8 = minmax_uint8(tile["array"])
    return model.predict(
        rgb_uint8[..., ::-1], imgsz=imgsz, conf=conf_threshold, verbose=False, device=device
    )


def _point_output_records(
    detections: list[dict[str, Any]], district_name: str
) -> list[dict[str, Any]]:
    """Convert kept polygon detections to the requested WGS84 point schema.

    Input schema: records with ``kiln_id``, Polygon ``geometry``, ``class`` and
    ``confidence``. Output: Point GeoParquet rows with class_name and lat/lon.
    """
    rows = []
    for detection in detections:
        point = detection["geometry"].centroid
        rows.append({
            "kiln_id": detection["kiln_id"],
            "geometry": Point(point.x, point.y),
            "class_name": detection["class"],
            "confidence": float(detection["confidence"]),
            "district": district_name,
            "lat": float(point.y),
            "lon": float(point.x),
        })
    return rows


def _normalize_district_name(name: str) -> str:
    """Normalize a district label for boundary matching.

    Input schema: one district-name string. Output: lowercase, unaccented
    text with whitespace removed.
    """
    unaccented = "".join(
        char for char in unicodedata.normalize("NFD", name)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", "", unaccented).lower()


def _load_district_polygon(
    boundary_path: Path, district_name: str, warning: Any
) -> tuple[BaseGeometry, str, str] | None:
    """Load one district boundary by normalized name from GeoJSON properties.

    Input schema: GeoJSON properties containing ``shapeName`` plus polygon
    geometry. Output: WGS84 geometry, matched shapeName, and canonical display
    name, or ``None`` when no matching boundary is available.
    """
    DISTRICT_ALIASES = {
        "chapainawabganj": "Nawabganj",
        "chapai nawabganj": "Nawabganj",
        "nawabganj": "Nawabganj",
        "gazipur": "Gazipur",
        "rajshahi": "Rajshahi",
        "dhaka": "Dhaka",
        "chittagong": "Chittagong",
    }
    DISTRICT_DISPLAY_NAMES = {
        "Nawabganj": "Chapainawabganj",
        "Gazipur": "Gazipur",
        "Rajshahi": "Rajshahi",
        "Dhaka": "Dhaka",
        "Chittagong": "Chittagong",
    }

    if not boundary_path.is_file():
        warning(f"District boundary file not found: {boundary_path}; continuing without clipping.")
        return None
    print(f"Using district boundary file: {boundary_path}")
    try:
        boundaries = gpd.read_file(boundary_path)
    except Exception as exc:  # noqa: BLE001 - unreadable optional boundary must not stop inference
        warning(f"Could not read district boundary file {boundary_path}: {exc}; continuing without clipping.")
        return None
    if "shapeName" not in boundaries.columns:
        warning(f"No shapeName column in {boundary_path}; continuing without clipping.")
        return None
    available_names = sorted(boundaries["shapeName"].dropna().astype(str).unique().tolist())
    normalized_aliases = {
        _normalize_district_name(alias): shape_name
        for alias, shape_name in DISTRICT_ALIASES.items()
    }
    matched_shapename = normalized_aliases.get(_normalize_district_name(district_name))
    if matched_shapename is None:
        warning(
            f"Unknown district '{district_name}'. Available shapeName values: "
            f"{available_names}; continuing without clipping."
        )
        return None
    matched = boundaries["shapeName"].astype("string").str.casefold().eq(
        matched_shapename.casefold()
    )
    selected = boundaries.loc[matched]
    if selected.empty:
        warning(
            f"Mapped shapeName '{matched_shapename}' for district '{district_name}' "
            f"was not found. Available shapeName values: {available_names}; "
            "continuing without clipping."
        )
        return None
    if selected.crs is None:
        warning(f"District boundary CRS is missing in {boundary_path}; continuing without clipping.")
        return None
    selected = selected.to_crs("EPSG:4326")
    from shapely import union_all

    return (
        union_all(selected.geometry.values),
        str(selected["shapeName"].iloc[0]),
        DISTRICT_DISPLAY_NAMES[matched_shapename],
    )


def _clip_detections_to_polygon(
    detections: list[dict[str, Any]], district_polygon: BaseGeometry
) -> list[dict[str, Any]]:
    """Keep detection records whose WGS84 centroid is within the district.

    Input schema: detection mappings with Polygon ``geometry`` in EPSG:4326.
    Output schema: the same records filtered by centroid inclusion.
    """
    return [
        detection for detection in detections
        if detection["geometry"].centroid.within(district_polygon)
    ]


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
    point_output: bool = False,
    district_name: str | None = None,
    device: str = "cpu",
    append: bool = False,
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
    point_output : bool
        Write WGS84 centroid points with the demo inference output columns.
    district_name : str | None
        Required district metadata when ``point_output`` is true.
    append : bool
        If True and ``output`` already exists, load the existing GeoParquet
        and concatenate new detections before writing.  Allows incremental
        multi-district inference into a single output file.

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
    if point_output and not district_name:
        raise ValueError("district_name is required for point_output")

    model = YOLO(str(weights))
    checkpoint = getattr(model, "ckpt", None) or {}
    train_args = checkpoint.get("train_args", {}) if isinstance(checkpoint, dict) else {}
    import ultralytics

    detector_model = str(train_args.get("model") or weights.name)
    detector_version = str(checkpoint.get("version") or ultralytics.__version__)
    trained_imgsz = train_args.get("imgsz")
    if trained_imgsz is None:
        raise ValueError("Checkpoint does not record training imgsz; cannot verify inference size")
    if int(trained_imgsz) != imgsz:
        rprint(
            f"[yellow]Inference imgsz={imgsz} differs from checkpoint training imgsz="
            f"{trained_imgsz}.[/yellow]"
        )

    # Convert each detection as it is created; avoid retaining per-CRS
    # GeoDataFrames and a second concatenated copy of all detections.
    all_records: list[dict[str, Any]] = []

    if raster_dir.is_file():
        raster_files = [raster_dir]
    elif raster_dir.is_dir():
        raster_files = sorted(raster_dir.glob("*.tif")) + sorted(raster_dir.glob("*.tiff"))
    else:
        raise FileNotFoundError(f"Raster directory or file not found: {raster_dir}")
    rprint(f"[cyan]Found {len(raster_files)} raster file(s) in {raster_dir}[/cyan]")

    for raster_path in raster_files:
        district = raster_path.stem.replace("kilnwatch_", "").split("_")[0]
        rprint(f"[cyan]Processing {raster_path.name} (district={district})...[/cyan]")

        with rasterio.open(raster_path) as src:
            raster_crs = CRS.from_user_input(src.crs).to_string()
            raster_width, raster_height = src.width, src.height
        transformer = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True)

        rprint(
            f"Processing raster {raster_width}x{raster_height} px in "
            f"{_count_tiles(raster_width, raster_height, chip_size, overlap)} tiles"
        )
        tiles = read_as_windows(raster_path, chip_size=chip_size, overlap=overlap)
        tile_count = 0
        masked_tile_count = 0
        for tile in tiles:
            tile_count += 1
            masked_tile_count += int(bool(np.any(np.all(tile["array"] == 0, axis=2))))
            results = _predict_tile(model, tile, imgsz, conf_threshold, device=device)
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
                            "detector_model": detector_model,
                            "detector_version": detector_version,
                            # Exported composite acquisition dates are not
                            # retained in the current raster/export contract.
                            "imagery_date": None,
                        }
                    )
        masked_tile_fraction = masked_tile_count / tile_count if tile_count else 0.0
        rprint(f"  -> {tile_count} tiles processed one at a time")
        rprint(f"  Tiles containing masked zero pixels: {masked_tile_fraction:.3%}")

    rprint(f"[cyan]{len(all_records)} raw detections before NMS.[/cyan]")

    # Cross-tile NMS (in EPSG:4326 - acceptable for small OBBs)
    kept = _nms_polygons(all_records, iou_threshold=iou_threshold)
    rprint(f"[green]{len(kept)} detections after NMS.[/green]")

    project_root = Path(__file__).resolve().parents[2]
    boundary_candidates = [
        project_root / "data" / "raw" / "boundaries" / "geoBoundaries_BGD_ADM2.geojson",
        project_root / "geoBoundaries_BGD_ADM2.geojson",
    ]
    boundary_path = next((path for path in boundary_candidates if path.is_file()), boundary_candidates[0])
    if district_name:
        district_match = _load_district_polygon(boundary_path, district_name, rprint)
    else:
        district_match = None
        rprint("[yellow]No --district-name provided; continuing without district polygon clipping.[/yellow]")
    district_display_name = str(district_name) if district_name else ""
    if district_match is not None:
        district_polygon, _matched_shapename, district_display_name = district_match
        count_before_clip = len(kept)
        kept = _clip_detections_to_polygon(kept, district_polygon)
        for detection in kept:
            detection["district"] = district_display_name
        rprint(f"Clipped {count_before_clip} -> {len(kept)} detections to district polygon.")

    # Build final GeoDataFrame, preserving the legacy polygon contract by default.
    if point_output:
        point_records = _point_output_records(kept, district_display_name)
        gdf = gpd.GeoDataFrame(
            point_records,
            columns=["kiln_id", "geometry", "class_name", "confidence", "district", "lat", "lon"],
            geometry="geometry",
            crs="EPSG:4326",
        )
    elif kept:
        gdf = gpd.GeoDataFrame(kept, crs="EPSG:4326")
    else:
        gdf = gpd.GeoDataFrame(
            columns=[
                "kiln_id", "geometry", "class", "confidence", "district",
                "detector_model", "detector_version", "imagery_date",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    if append and output.is_file():
        import pandas as pd

        existing = gpd.read_parquet(output)
        rprint(f"[cyan]Appending {len(gdf)} new detections to {len(existing)} existing rows.[/cyan]")
        gdf = gpd.GeoDataFrame(
            pd.concat([existing, gdf], ignore_index=True),
            geometry="geometry",
            crs=gdf.crs or existing.crs,
        )
    gdf.to_parquet(output)
    rprint(f"[green]Kilns written to {output} ({len(gdf)} total rows)[/green]")
    if point_output:
        fcbk_count = int((gdf["class_name"] == "FCBK").sum())
        zigzag_count = int((gdf["class_name"] == "Zigzag").sum())
        rprint(f"Total detections: {len(gdf)}")
        rprint(f"FCBK count: {fcbk_count}")
        rprint(f"Zigzag count: {zigzag_count}")
    return gdf
