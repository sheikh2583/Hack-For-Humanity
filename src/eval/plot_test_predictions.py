"""Plot a balanced sample of YOLO OBB test predictions.

Input schema: RGB PNG chips and normalized YOLO OBB label rows
``class_id x1 y1 ... x4 y4``. Output: an 8x6 annotated contact sheet.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

from src.data.convert_sentinelkilndb import OUTPUT_CLASSES

ROOT = Path(__file__).resolve().parents[2]


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


def read_labels(path: Path, size: int) -> list[tuple[int, list[tuple[float, float]]]]:
    """Read YOLO OBB rows; input normalized vertices, output pixel polygons."""
    parsed = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            values = [float(value) for value in line.split()]
            if len(values) != 9:
                raise ValueError(f"Expected OBB row with 9 values in {path}")
            parsed.append((int(values[0]), [(values[i] * size, values[i + 1] * size) for i in (1, 3, 5, 7)]))
    return parsed


def polygon_iou(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    """Calculate polygon IoU using Shapely; inputs are pixel polygon vertices."""
    from shapely.geometry import Polygon
    pa, pb = Polygon(a), Polygon(b)
    union = pa.union(pb).area
    return pa.intersection(pb).area / union if union else 0.0


def select_sample(images: list[Path], labels_dir: Path, n: int, seed: int) -> list[Path]:
    """Choose balanced FCBK-positive, Zigzag-positive, and negative chips."""
    buckets: dict[int, list[Path]] = {0: [], 1: [], 2: []}
    for image in images:
        labels = read_labels(labels_dir / f"{image.stem}.txt", 128)
        if not labels:
            buckets[2].append(image)
        else:
            for class_id in {item[0] for item in labels}:
                if class_id in (0, 1):
                    buckets[class_id].append(image)
    per = n // 3
    rng = random.Random(seed)
    chosen: list[Path] = []
    for bucket in buckets.values():
        rng.shuffle(bucket)
        chosen.extend(path for path in bucket if path not in chosen and len([p for p in chosen if p in bucket]) < per)
    if len(chosen) < n:
        remaining = [path for path in images if path not in chosen]
        rng.shuffle(remaining)
        chosen.extend(remaining[:n-len(chosen)])
    if len(chosen) < n:
        raise ValueError(f"Need {n} test chips, found only {len(chosen)}")
    return chosen[:n]


def run(n: int = 48, seed: int = 0, weights: Path | None = None) -> Path:
    """Predict, annotate and save contact sheet; prints per-chip IoU counts."""
    from ultralytics import YOLO
    image_dir = ROOT / "data/interim/yolo_obb/test/images"
    labels_dir = ROOT / "data/interim/yolo_obb/test/labels"
    selected = select_sample(sorted(image_dir.glob("*.png")), labels_dir, n, seed)
    weights_path = resolve_weights(weights)
    print(f"Using weights: {weights_path}")
    model = YOLO(str(weights_path))
    tiles: list[Image.Image] = []
    for path in selected:
        image = Image.open(path).convert("RGB")
        truth = read_labels(labels_dir / f"{path.stem}.txt", image.width)
        result = model.predict(str(path), conf=0.1, imgsz=512, save=False, verbose=False, device="cpu")[0]
        predictions: list[tuple[int, list[tuple[float, float]], float]] = []
        if result.obb is not None:
            for box, confidence, cls in zip(result.obb.xyxyxyxy.cpu().numpy(), result.obb.conf.cpu().numpy(), result.obb.cls.cpu().numpy().astype(int)):
                predictions.append((cls, [(float(x), float(y)) for x, y in box], float(confidence)))
        matched: set[int] = set()
        tp = 0
        for cls, poly, confidence in predictions:
            candidates = [(polygon_iou(poly, gt_poly), idx) for idx, (gt_cls, gt_poly) in enumerate(truth) if gt_cls == cls and idx not in matched]
            best_iou, best_idx = max(candidates, default=(0.0, -1))
            if best_iou >= 0.5:
                tp += 1
                matched.add(best_idx)
        fp, fn = len(predictions)-tp, len(truth)-tp
        print(f"{path.name}: TP={tp} FP={fp} FN={fn}")
        draw = ImageDraw.Draw(image)
        for cls, poly in truth:
            draw.polygon(poly, outline="lime", width=1)
        for cls, poly, confidence in predictions:
            draw.polygon(poly, outline="red", width=1)
            draw.text(poly[0], f"{OUTPUT_CLASSES.get(cls, cls)} {confidence:.2f}", fill="red")
        image = image.resize((512, 512))
        tiles.append(image)
    sheet = Image.new("RGB", (8*512, max(6, (len(tiles)+7)//8)*512), "white")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 8)*512, (index // 8)*512))
    output = ROOT / "results/run_0002/visual_check/contact_sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return output


def main() -> None:
    """Parse command line options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=48)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--weights", type=Path, default=None)
    args = parser.parse_args()
    if args.n <= 0 or args.n % 3:
        parser.error("--n must be a positive multiple of 3")
    from src.geo.crs import get_projected_crs
    get_projected_crs(90.0)
    print(run(args.n, args.seed, args.weights))


if __name__ == "__main__":
    main()
