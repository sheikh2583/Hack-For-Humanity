"""Match YOLO OBB predictions to labels and save unmatched chip images.

Input schema: YOLO OBB text files (class, eight normalized vertices, optional
prediction confidence) and matching PNG chips. Output schema: counts of saved
false-positive and missed-kiln chip images under the requested output folder.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon


def _read_boxes(path: Path, *, predictions: bool) -> list[dict[str, Any]]:
    """Read YOLO OBB rows into class, polygon, and confidence records."""
    boxes: list[dict[str, Any]] = []
    if not path.exists():
        return boxes
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) not in ({9, 10} if predictions else {9}):
            raise ValueError(f"{path}:{line_number}: expected 9 OBB fields and optional confidence")
        try:
            class_id = int(parts[0])
            coords = [float(value) for value in parts[1:9]]
            confidence = float(parts[9]) if len(parts) == 10 else 1.0
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: invalid OBB value") from error
        if not all(math.isfinite(value) for value in [*coords, confidence]):
            raise ValueError(f"{path}:{line_number}: OBB values must be finite")
        polygon = Polygon(list(zip(coords[::2], coords[1::2])))
        if not polygon.is_valid or polygon.area <= 0:
            raise ValueError(f"{path}:{line_number}: OBB polygon must be valid and non-empty")
        boxes.append({"class_id": class_id, "polygon": polygon, "conf": confidence})
    return boxes


def run_error_analysis(
    predictions_dir: Path,
    ground_truth_dir: Path,
    images_dir: Path,
    output_dir: Path,
    top_n: int = 50,
    iou_threshold: float = 0.5,
) -> dict[str, int]:
    """Save chips containing unmatched predictions or labels.

    Matching is class-aware and greedy by descending confidence, with each
    prediction and ground-truth polygon used at most once. A chip is listed
    once per unmatched object.
    """
    from PIL import Image
    from rich import print as rprint

    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be between 0 and 1")
    if top_n < 0:
        raise ValueError("top_n must be non-negative")

    fp_dir, miss_dir = output_dir / "false_positives", output_dir / "missed_kilns"
    fp_dir.mkdir(parents=True, exist_ok=True)
    miss_dir.mkdir(parents=True, exist_ok=True)
    pred_files = {path.stem: path for path in predictions_dir.glob("*.txt")}
    gt_files = {path.stem: path for path in ground_truth_dir.glob("*.txt")}
    false_positives: list[dict[str, Any]] = []
    missed_kilns: list[dict[str, Any]] = []

    for stem in sorted(pred_files.keys() | gt_files.keys()):
        preds = _read_boxes(pred_files[stem], predictions=True) if stem in pred_files else []
        truths = _read_boxes(gt_files[stem], predictions=False) if stem in gt_files else []
        matched_preds: set[int] = set()
        matched_truths: set[int] = set()
        for pi in sorted(range(len(preds)), key=lambda index: preds[index]["conf"], reverse=True):
            pred = preds[pi]
            options = [
                (
                    pred["polygon"].intersection(truth["polygon"]).area
                    / pred["polygon"].union(truth["polygon"]).area,
                    gi,
                )
                for gi, truth in enumerate(truths)
                if gi not in matched_truths and pred["class_id"] == truth["class_id"]
            ]
            if options:
                best_iou, gi = max(options)
                if best_iou >= iou_threshold:
                    matched_preds.add(pi)
                    matched_truths.add(gi)
        image_path = images_dir / f"{stem}.png"
        false_positives.extend(
            {"stem": stem, "conf": pred["conf"], "img": image_path, "index": index}
            for index, pred in enumerate(preds) if index not in matched_preds
        )
        missed_kilns.extend(
            {"stem": stem, "img": image_path, "index": index}
            for index in range(len(truths)) if index not in matched_truths
        )

    false_positives.sort(key=lambda item: item["conf"], reverse=True)
    saved_fp = 0
    for fp in false_positives[:top_n]:
        if fp["img"].exists():
            with Image.open(fp["img"]) as image:
                image.save(fp_dir / f"fp_{saved_fp:03d}_{fp['stem']}.png")
            saved_fp += 1
    saved_miss = 0
    for miss in missed_kilns[:top_n]:
        if miss["img"].exists():
            with Image.open(miss["img"]) as image:
                image.save(miss_dir / f"miss_{saved_miss:03d}_{miss['stem']}.png")
            saved_miss += 1
    result = {"false_positives": saved_fp, "missed_kilns": saved_miss}
    rprint(f"[green]Error analysis complete: {result}[/green]")
    return result
