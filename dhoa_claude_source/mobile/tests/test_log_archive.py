"""Tiny synthetic coverage for training metric log archiving."""

import csv
from pathlib import Path

from src.training.log_archive import archive_completed_epochs


def test_archives_ten_epoch_windows_and_final_partial(tmp_path: Path) -> None:
    """Archive a complete ten-epoch block and the remaining two rows."""
    results = tmp_path / "results.csv"
    with results.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["epoch", "train/loss", "metrics/mAP50"])
        writer.writeheader()
        writer.writerows(
            {"epoch": index, "train/loss": index / 10, "metrics/mAP50": index / 100}
            for index in range(1, 13)
        )

    archive_dir = tmp_path / "results" / "run_0001" / "logs" / "yolov8n-obb-256"
    completed = archive_completed_epochs(results, archive_dir, completed_epochs=10)
    assert [path.name for path in completed] == ["epochs_0001-0010.csv"]
    assert archive_completed_epochs(results, archive_dir, completed_epochs=10) == []

    tail = archive_completed_epochs(
        results, archive_dir, completed_epochs=12, include_partial=True
    )
    assert [path.name for path in tail] == ["epochs_0011-0012.csv"]
    with tail[0].open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["epoch"] for row in rows] == ["11", "12"]
