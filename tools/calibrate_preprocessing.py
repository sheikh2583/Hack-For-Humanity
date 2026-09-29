"""Compare exported and training SentinelKilnDB PNG chips.

Input schema: two directories of RGB PNGs with identical ``lat_lon.png``
filenames. Output: per-pair/channel training-minus-exported mean and percentile
differences, aggregate statistics, and a measured scalar ratio suggestion.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

CHANNELS = ("R", "G", "B")


def compare_chip(exported_path: Path, training_path: Path) -> dict[str, object]:
    """Compute channel distribution differences and a ratio from a paired chip."""
    exported = np.asarray(Image.open(exported_path).convert("RGB"), dtype=np.float64)
    training = np.asarray(Image.open(training_path).convert("RGB"), dtype=np.float64)
    if exported.shape != training.shape:
        raise ValueError(f"Chip shape mismatch: {exported_path.name}: {exported.shape} vs {training.shape}")
    result: dict[str, object] = {"filename": exported_path.name}
    ratios: list[float] = []
    for index, channel in enumerate(CHANNELS):
        export_values = exported[..., index].ravel()
        train_values = training[..., index].ravel()
        for label, percentile in (("mean", None), ("p1", 1), ("p50", 50), ("p99", 99)):
            export_stat = export_values.mean() if percentile is None else np.percentile(export_values, percentile)
            train_stat = train_values.mean() if percentile is None else np.percentile(train_values, percentile)
            result[f"{channel}_{label}_difference"] = float(train_stat - export_stat)
        nonzero = train_values > 0
        if nonzero.any():
            ratios.extend((export_values[nonzero] / train_values[nonzero]).tolist())
    result["suggested_divisor"] = float(np.median(ratios)) if ratios else float("nan")
    return result


def calibrate(exported_dir: Path, training_dir: Path) -> list[dict[str, object]]:
    """Compare same-named PNGs and print per-chip plus aggregate diagnostics."""
    exported = {path.name: path for path in exported_dir.glob("*.png")}
    training = {path.name: path for path in training_dir.glob("*.png")}
    common = sorted(exported.keys() & training.keys())
    if not common:
        raise ValueError("No matching lat_lon.png filenames found in the two directories")
    rows = [compare_chip(exported[name], training[name]) for name in common]
    for row in rows:
        print(row)
    print(f"Matched chips: {len(rows)}; unmatched exported: {len(exported.keys() - training.keys())}; "
          f"unmatched training: {len(training.keys() - exported.keys())}")
    ratios = [float(row["suggested_divisor"]) for row in rows if np.isfinite(row["suggested_divisor"])]
    print(f"Measured scalar divisor suggestion (exported / training): {np.median(ratios) if ratios else float('nan')}")
    return rows


def main() -> None:
    """Parse directories and run PNG calibration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exported_dir", type=Path)
    parser.add_argument("training_dir", type=Path)
    args = parser.parse_args()
    calibrate(args.exported_dir, args.training_dir)


if __name__ == "__main__":
    main()
