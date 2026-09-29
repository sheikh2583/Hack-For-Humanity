"""Archive completed Ultralytics metric rows into Git-trackable CSV chunks.

Input schema: Ultralytics ``results.csv`` with an ``epoch`` column and metric
columns. Output schema: header-preserving CSV files named by inclusive epoch
ranges, suitable for inspection and version control.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def archive_completed_epochs(
    results_csv: Path,
    archive_dir: Path,
    completed_epochs: int,
    interval: int = 10,
    include_partial: bool = False,
) -> list[Path]:
    """Write any new complete metric windows and an optional final partial window.

    Args:
        results_csv: Ultralytics CSV written after validation for each epoch.
        archive_dir: Version-controlled destination, such as
            ``results/run_0001/logs/yolov8n-obb-256``.
        completed_epochs: Number of completed epochs currently in the CSV.
        interval: Number of rows per regular archive chunk.
        include_partial: Also archive rows after the last full interval. Use at
            training end to preserve early-stopped runs.

    Returns:
        Paths newly created. Existing chunks are left unchanged, so callbacks
        and resumed runs do not silently rewrite already archived evidence.
    """
    if interval <= 0:
        raise ValueError("interval must be positive")
    if completed_epochs < 0:
        raise ValueError("completed_epochs cannot be negative")

    with Path(results_csv).open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "epoch" not in reader.fieldnames:
            raise ValueError(f"{results_csv} must contain an 'epoch' column")
        fieldnames = [field.strip() for field in reader.fieldnames]
        rows: list[dict[str, Any]] = []
        for row in reader:
            normalized = {str(key).strip(): value for key, value in row.items() if key}
            if normalized.get("epoch"):
                rows.append(normalized)

    if len(rows) < completed_epochs:
        raise ValueError(
            f"{results_csv} has {len(rows)} epoch rows, fewer than the "
            f"{completed_epochs} completed epochs"
        )

    archive_dir = Path(archive_dir)
    created: list[Path] = []
    last_full_end = (completed_epochs // interval) * interval
    windows = [
        (start, start + interval - 1)
        for start in range(1, last_full_end + 1, interval)
    ]
    if include_partial and completed_epochs > last_full_end:
        windows.append((last_full_end + 1, completed_epochs))

    for start, end in windows:
        destination = archive_dir / f"epochs_{start:04d}-{end:04d}.csv"
        if destination.exists():
            continue
        chunk = rows[start - 1 : end]
        if len(chunk) != end - start + 1:
            raise ValueError(f"{results_csv} is missing rows for epochs {start}-{end}")
        archive_dir.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".csv.tmp")
        with temporary.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(chunk)
        temporary.replace(destination)
        created.append(destination)

    return created
