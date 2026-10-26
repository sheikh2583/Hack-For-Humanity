"""Tests for src.eval.error_analysis — synthetic false-positive and missed-kiln detection."""

from __future__ import annotations

from pathlib import Path

from src.eval.error_analysis import run_error_analysis


def _write_chips(images_dir: Path, stems: list[str]) -> None:
    """Create minimal 2×2 white PNG files for testing."""
    from PIL import Image

    images_dir.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        img = Image.new("RGB", (2, 2), (255, 255, 255))
        img.save(images_dir / f"{stem}.png")


def test_false_positive_and_missed_kiln_counts(tmp_path: Path) -> None:
    """Predictions without GT are FP; empty predictions with GT are missed."""
    pred_dir = tmp_path / "predictions"
    gt_dir = tmp_path / "ground_truth"
    img_dir = tmp_path / "images"
    out_dir = tmp_path / "errors"

    pred_dir.mkdir()
    gt_dir.mkdir()

    # chip_a: prediction exists, no GT → false positive
    (pred_dir / "chip_a.txt").write_text("0 0.1 0.1 0.9 0.1 0.9 0.9 0.1 0.9 0.95\n")
    # chip_b: GT exists AND an empty prediction file → missed kiln
    # (the code iterates prediction files, so a GT-only chip needs
    #  a prediction file to be visited)
    (pred_dir / "chip_b.txt").write_text("")
    (gt_dir / "chip_b.txt").write_text("0 0.2 0.2 0.8 0.2 0.8 0.8 0.2 0.8\n")

    _write_chips(img_dir, ["chip_a", "chip_b"])

    result = run_error_analysis(pred_dir, gt_dir, img_dir, out_dir, top_n=10)

    assert result["false_positives"] == 1
    assert result["missed_kilns"] == 1
    assert (out_dir / "false_positives" / "fp_000_chip_a.png").is_file()
    assert (out_dir / "missed_kilns" / "miss_000_chip_b.png").is_file()


def test_empty_inputs_produce_zero_counts(tmp_path: Path) -> None:
    """No predictions and no GT files produce zero errors."""
    pred_dir = tmp_path / "predictions"
    gt_dir = tmp_path / "ground_truth"
    img_dir = tmp_path / "images"
    out_dir = tmp_path / "errors"

    pred_dir.mkdir()
    gt_dir.mkdir()
    img_dir.mkdir()

    result = run_error_analysis(pred_dir, gt_dir, img_dir, out_dir)
    assert result["false_positives"] == 0
    assert result["missed_kilns"] == 0


def test_partial_errors_are_box_matched_and_gt_only_chip_is_visited(tmp_path: Path) -> None:
    """Matching catches partial misses, extra boxes, and labels with no pred file."""
    pred_dir = tmp_path / "predictions"
    gt_dir = tmp_path / "ground_truth"
    img_dir = tmp_path / "images"
    out_dir = tmp_path / "errors"

    pred_dir.mkdir()
    gt_dir.mkdir()

    # First box matches; the shifted prediction is a false positive and the
    # second ground truth is missed. A separate GT-only chip is also detected.
    (pred_dir / "chip_c.txt").write_text(
        "0 0.1 0.1 0.4 0.1 0.4 0.4 0.1 0.4 0.9\n"
        "0 0.6 0.6 0.9 0.6 0.9 0.9 0.6 0.9 0.8\n"
    )
    (gt_dir / "chip_c.txt").write_text(
        "0 0.1 0.1 0.4 0.1 0.4 0.4 0.1 0.4\n"
        "0 0.1 0.6 0.4 0.6 0.4 0.9 0.1 0.9\n"
    )
    (gt_dir / "chip_d.txt").write_text("0 0.2 0.2 0.8 0.2 0.8 0.8 0.2 0.8\n")

    _write_chips(img_dir, ["chip_c", "chip_d"])

    result = run_error_analysis(pred_dir, gt_dir, img_dir, out_dir)
    assert result["false_positives"] == 1
    assert result["missed_kilns"] == 2
