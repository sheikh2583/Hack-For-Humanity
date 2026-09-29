"""Ultralytics training, metrics, plots, and Git-visible log archives.

Input schema: pretrained OBB weights plus a host-local YOLO dataset YAML.
Output schema: Ultralytics checkpoints/results under each numbered run's
``checkpoints/`` folder and ten-epoch metrics under its ``logs/`` folder.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from src.training.run_store import ROOT


def _row_count(results_csv: Path) -> int:
    """Count completed epochs in an Ultralytics metrics CSV."""
    if not results_csv.is_file():
        return 0
    with results_csv.open(newline="", encoding="utf-8-sig") as source:
        return sum(1 for row in csv.DictReader(source) if row.get("epoch"))


def _stage_log_paths(paths: list[Path]) -> None:
    """Stage newly written metric chunks without staging checkpoints or committing."""
    if not paths:
        return
    relative_paths = [path.resolve().relative_to(ROOT).as_posix() for path in paths]
    try:
        subprocess.run(["git", "add", "--", *relative_paths], cwd=ROOT,
                       check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Warning: could not stage metric archives: {error}", file=sys.stderr)


def _archive_callbacks(
    results_csv: Path, logs_dir: Path, interval: int
) -> tuple[Callable[[Any], None], Callable[[Any], None]]:
    """Build callbacks that archive complete windows and a final partial window."""
    from src.training.log_archive import archive_completed_epochs

    def on_epoch_end(trainer: Any) -> None:
        completed = _row_count(results_csv)
        if completed and completed % interval == 0:
            paths = archive_completed_epochs(results_csv, logs_dir, completed, interval)
            _stage_log_paths(paths)

    def on_train_end(trainer: Any) -> None:
        completed = _row_count(results_csv)
        if completed:
            paths = archive_completed_epochs(
                results_csv, logs_dir, completed, interval, include_partial=True
            )
            _stage_log_paths(paths)

    return on_epoch_end, on_train_end


def train_stage(
    *, weights: Path, data_yaml: Path, checkpoints_dir: Path, logs_dir: Path,
    stage_name: str, imgsz: int, epochs: int, config: dict[str, Any],
    device: str, resume: bool = False,
) -> Path:
    """Train or resume one named YOLO OBB stage and return its output folder."""
    from ultralytics import YOLO

    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    result_dir = checkpoints_dir / stage_name
    on_epoch_end, on_train_end = _archive_callbacks(
        result_dir / "results.csv", logs_dir / stage_name, config["archive_interval"]
    )
    model = YOLO(str(weights))
    model.add_callback("on_fit_epoch_end", on_epoch_end)
    model.add_callback("on_train_end", on_train_end)
    model.train(
        data=str(data_yaml.resolve()), imgsz=imgsz, epochs=epochs,
        batch=config["batch"], workers=config["workers"], patience=config["patience"],
        seed=config["seed"], flipud=config["augmentation"]["flipud"],
        degrees=config["augmentation"]["degrees"], device=device,
        project=checkpoints_dir.resolve().relative_to(ROOT).as_posix(),
        name=stage_name, exist_ok=True, plots=True, resume=resume,
    )
    return result_dir


def validation_map50(result_dir: Path, preferred_column: str) -> float:
    """Read a stage's last validation mAP50 from its results.csv."""
    path = result_dir / "results.csv"
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fields = {field.strip(): field for field in (reader.fieldnames or [])}
        column = fields.get(preferred_column)
        if column is None:
            column = next((field for name, field in fields.items() if "mAP50" in name), None)
        rows = list(reader)
    if column is None or not rows:
        raise ValueError(f"No validation mAP50 row found in {path}")
    return float(rows[-1][column])


def copy_review_plots(source: Path, destination: Path) -> None:
    """Copy confusion-matrix and precision-recall plots into the final folder."""
    destination.mkdir(parents=True, exist_ok=True)
    for plot in source.glob("*.png"):
        if "confusion_matrix" in plot.name or "PR_curve" in plot.name:
            shutil.copy2(plot, destination / plot.name)


def evaluate_test(
    checkpoint: Path, *, data_yaml: Path, checkpoints_dir: Path,
    imgsz: int, device: str, test_split: str,
) -> tuple[dict[str, float], Path]:
    """Evaluate a selected model on the held-out split and return metrics/path."""
    from ultralytics import YOLO

    metrics = YOLO(str(checkpoint)).val(
        data=str(data_yaml.resolve()), split=test_split, imgsz=imgsz,
        device=device, plots=True,
        project=checkpoints_dir.resolve().relative_to(ROOT).as_posix(),
        name="heldout_test", exist_ok=True,
    )
    values = {
        "map50": float(metrics.box.map50), "map50_95": float(metrics.box.map),
        "precision": float(metrics.box.mp), "recall": float(metrics.box.mr),
    }
    return values, Path(getattr(metrics, "save_dir", checkpoints_dir / "heldout_test"))
