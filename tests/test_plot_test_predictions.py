"""Synthetic geometry and label-sampling checks for prediction plots."""

from pathlib import Path

from src.eval.plot_test_predictions import polygon_iou, read_labels, resolve_weights


def test_polygon_iou_identical_synthetic_boxes() -> None:
    """Identical four-corner polygons have IoU one."""
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert polygon_iou(polygon, polygon) == 1.0


def test_read_labels_accepts_normalized_obb_row(tmp_path: Path) -> None:
    """A tiny normalized OBB row converts to pixel vertices."""
    label = tmp_path / "chip.txt"
    label.write_text("1 0.1 0.1 0.9 0.1 0.9 0.9 0.1 0.9\n", encoding="utf-8")
    assert read_labels(label, 100) == [(1, [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)])]


def test_weights_auto_search_uses_results_final_checkpoint(tmp_path: Path) -> None:
    """Missing explicit checkpoint falls back to a full-training checkpoint."""
    candidate = tmp_path / "results" / "run-a" / "checkpoints" / "final" / "best.pt"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    assert resolve_weights(tmp_path / "missing.pt", root=tmp_path) == candidate.resolve()
