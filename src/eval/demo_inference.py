"""Run CPU-friendly demo inference on the prepared YOLO OBB test chips.

Input schema: 128x128 RGB PNG chips named ``lat_lon.png`` in
``data/interim/yolo_obb/test/images``. Output schema: EPSG:4326 GeoParquet
points with kiln_id, geometry, class_name, confidence, district, lat, lon.
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

from src.data.convert_sentinelkilndb import OUTPUT_CLASSES, parse_latlon

ROOT = Path(__file__).resolve().parents[2]
PIXEL_DEGREES = 8.983e-5


def resolve_weights(path: Path | None, root: Path = ROOT) -> Path:
    """Prefer full-training checkpoints; use runs only as a warned last resort."""
    if path is not None and path.is_file():
        return path.resolve()
    preferred = root / "results/run_0002/checkpoints/final/best.pt"
    if preferred.is_file():
        return preferred.resolve()
    for match in sorted((root / "results").glob("*/checkpoints/final/best.pt")):
        if match.is_file():
            return match.resolve()
    for match in sorted((root / "runs").glob("*/weights/best.pt")):
        if match.is_file():
            print(f"WARNING: using {match}; this may be a smoke-test checkpoint.")
            return match.resolve()
    raise FileNotFoundError(
        f"Weights not found at {path or 'an unspecified path'}; searched results/run_0002/checkpoints/final, "
        "results/*/checkpoints/final, and runs/*/weights"
    )


def detection_point(lat: float, lon: float, corners: Any) -> Point:
    """Convert pixel OBB corners to EPSG:4326 centroid.

    Input: chip centre (lat, lon) and four pixel (x, y) corners; output Point.
    """
    left = lon - 64 * PIXEL_DEGREES
    top = lat + 64 * PIXEL_DEGREES
    xs = [left + float(x) * PIXEL_DEGREES for x, _ in corners]
    ys = [top - float(y) * PIXEL_DEGREES for _, y in corners]
    return Point(sum(xs) / len(xs), sum(ys) / len(ys))


def run(weights: Path | None = None) -> gpd.GeoDataFrame:
    """Infer all test images and write the requested point GeoParquet."""
    from ultralytics import YOLO

    images = ROOT / "data/interim/yolo_obb/test/images"
    weights = resolve_weights(weights)
    print(f"Using weights: {weights}")
    output = ROOT / "data/processed/kilns.parquet"
    model = YOLO(str(weights))
    records: list[dict[str, Any]] = []
    chip_count = 0
    for image in sorted(images.glob("*.png")):
        center = parse_latlon(image.name)
        if center is None:
            raise ValueError(f"Unexpected chip filename: {image.name}")
        chip_count += 1
        for result in model.predict(str(image), conf=0.1, imgsz=512, save=False, verbose=False, device="cpu"):
            if result.obb is None:
                continue
            for corners, confidence, class_id in zip(
                result.obb.xyxyxyxy.cpu().numpy(), result.obb.conf.cpu().numpy(),
                result.obb.cls.cpu().numpy().astype(int),
            ):
                point = detection_point(*center, corners)
                records.append({
                    "kiln_id": str(uuid.uuid4()), "geometry": point,
                    "class_name": OUTPUT_CLASSES.get(class_id, f"unknown_{class_id}"),
                    "confidence": float(confidence), "district": "",
                    "lat": point.y, "lon": point.x,
                })
    frame = gpd.GeoDataFrame(records, columns=["kiln_id", "geometry", "class_name", "confidence", "district", "lat", "lon"], geometry="geometry", crs="EPSG:4326")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output)
    fcbk = int((frame.class_name == "FCBK").sum())
    zigzag = int((frame.class_name == "Zigzag").sum())
    print(f"Total detections: {len(frame)}\nFCBK count: {fcbk}\nZigzag count: {zigzag}\nChips processed: {chip_count}")
    return frame


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=None)
    args = parser.parse_args()
    # Assert requested projected CRS availability at startup, with established fallback.
    from src.geo.crs import get_projected_crs
    get_projected_crs(90.0)
    run(args.weights)


if __name__ == "__main__":
    main()
