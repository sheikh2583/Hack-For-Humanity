"""Error analysis: save crops of false positives and missed kilns.

Input
-----
- Inference results and ground-truth labels from the spatial test split.

Output
------
- ``data/processed/error_analysis/false_positives/`` — top-50 highest-confidence FPs.
- ``data/processed/error_analysis/missed_kilns/`` — top-50 missed ground-truth kilns.

Contract
--------
>>> from src.eval.error_analysis import run_error_analysis
>>> run_error_analysis(predictions_dir, ground_truth_dir, images_dir, output_dir)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_error_analysis(
    predictions_dir: Path,
    ground_truth_dir: Path,
    images_dir: Path,
    output_dir: Path,
    top_n: int = 50,
    iou_threshold: float = 0.5,
) -> dict[str, int]:
    """Identify false positives and missed kilns from the test split.

    Parameters
    ----------
    predictions_dir : Path
        Directory with YOLO-format prediction label files.
    ground_truth_dir : Path
        Directory with ground-truth label files.
    images_dir : Path
        Directory with the corresponding image chips.
    output_dir : Path
        Where to save the cropped error images.
    top_n : int
        Number of worst errors to save (default 50).
    iou_threshold : float
        IoU threshold for matching predictions to ground truth.

    Returns
    -------
    dict[str, int]
        Counts: ``{false_positives, missed_kilns}``.
    """
    from PIL import Image  # type: ignore[import-untyped]
    from rich import print as rprint

    fp_dir = output_dir / "false_positives"
    miss_dir = output_dir / "missed_kilns"
    fp_dir.mkdir(parents=True, exist_ok=True)
    miss_dir.mkdir(parents=True, exist_ok=True)

    # Collect predictions sorted by confidence
    pred_files = sorted(predictions_dir.glob("*.txt"))
    gt_files = {p.stem: p for p in ground_truth_dir.glob("*.txt")}

    false_positives: list[dict[str, Any]] = []
    missed_kilns: list[dict[str, Any]] = []

    for pred_file in pred_files:
        stem = pred_file.stem
        gt_file = gt_files.get(stem)
        img_file = images_dir / f"{stem}.png"

        # Parse predictions (YOLO-OBB format: class x1 y1 ... x4 y4 conf)
        pred_lines = pred_file.read_text().strip().splitlines() if pred_file.exists() else []
        gt_lines = gt_file.read_text().strip().splitlines() if gt_file and gt_file.exists() else []

        # Simple matching: if no GT exists, all predictions are FP
        if not gt_lines:
            for line in pred_lines:
                parts = line.split()
                conf = float(parts[-1]) if len(parts) > 9 else 0.5
                false_positives.append({"stem": stem, "conf": conf, "img": img_file})
        elif not pred_lines:
            for line in gt_lines:
                missed_kilns.append({"stem": stem, "img": img_file})

    # Save top-N false positives by confidence
    false_positives.sort(key=lambda x: x["conf"], reverse=True)
    saved_fp = 0
    for fp in false_positives[:top_n]:
        if fp["img"].exists():
            img = Image.open(fp["img"])
            img.save(fp_dir / f"fp_{saved_fp:03d}_{fp['stem']}.png")
            saved_fp += 1

    # Save top-N missed kilns
    saved_miss = 0
    for miss in missed_kilns[:top_n]:
        if miss["img"].exists():
            img = Image.open(miss["img"])
            img.save(miss_dir / f"miss_{saved_miss:03d}_{miss['stem']}.png")
            saved_miss += 1

    result = {"false_positives": saved_fp, "missed_kilns": saved_miss}
    rprint(f"[green]Error analysis complete: {result}[/green]")
    return result
