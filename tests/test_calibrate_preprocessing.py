"""Synthetic tests for exported/training RGB chip comparison."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from tools.calibrate_preprocessing import compare_chip


def test_pair_reports_channel_differences(tmp_path: Path) -> None:
    """Per-channel differences and scalar ratio are computed from tiny PNGs."""
    exported_path = tmp_path / "24.0_90.0.png"
    training_path = tmp_path / "24.0_90.0-train.png"
    exported = np.full((2, 2, 3), [20, 40, 60], dtype=np.uint8)
    training = np.full((2, 2, 3), [10, 20, 30], dtype=np.uint8)
    Image.fromarray(exported).save(exported_path)
    Image.fromarray(training).save(training_path)
    result = compare_chip(exported_path, training_path)
    assert result["R_mean_difference"] == -10.0
    assert result["G_p50_difference"] == -20.0
    assert result["B_p99_difference"] == -30.0
    assert result["suggested_divisor"] == 2.0
