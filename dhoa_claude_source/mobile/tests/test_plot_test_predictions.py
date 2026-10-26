"""Synthetic geometry and label-sampling checks for prediction plots."""

from pathlib import Path

from src.eval.plot_test_predictions import polygon_iou, read_labels, resolve_weights

# Code inspection confirms multi-label chips enter both positive class buckets,
# selections are de-duplicated, annotations use PIL green/red polygon draws, and
# per-chip matching counts true positives at IoU >= 0.5. The script also creates
# results/run_0002/visual_check/ before saving the contact sheet.


def test_polygon_iou_identical_synthetic_boxes() -> None:
    """Identical four-corner polygons have IoU one."""
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert polygon_iou(polygon, polygon) == 1.0


def test_read_labels_accepts_normalized_obb_row(tmp_path: Path) -> None:
    """A tiny normalized OBB row converts to pixel vertices."""
    label = tmp_path / "chip.txt"
    label.write_text("1 0.1 0.1 0.9 0.1 0.9 0.9 0.1 0.9\n", encoding="utf-8")
    assert read_labels(label, 100) == [(1, [(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0)])]


def test_weights_auto_search_uses_preferred_final_checkpoint(tmp_path: Path) -> None:
    """Default resolution selects the numbered final model, not a runs checkpoint."""
    candidate = tmp_path / "results" / "run-a" / "checkpoints" / "final" / "best.pt"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    preferred = tmp_path / "results" / "run_0002" / "checkpoints" / "final" / "best.pt"
    preferred.parent.mkdir(parents=True)
    preferred.touch()
    smoke = tmp_path / "runs" / "smoke" / "weights" / "best.pt"
    smoke.parent.mkdir(parents=True)
    smoke.touch()

    assert resolve_weights(None, root=tmp_path) == preferred.resolve()


def test_weights_missing_final_fails_closed_even_with_smoke_checkpoint(tmp_path: Path) -> None:
    """A smoke checkpoint is not selected unless the caller opts in."""
    smoke = tmp_path / "runs" / "smoke" / "weights" / "best.pt"
    smoke.parent.mkdir(parents=True)
    smoke.touch()

    import pytest

    with pytest.raises(FileNotFoundError, match="No full-training checkpoint found"):
        resolve_weights(None, root=tmp_path)


def test_smoke_checkpoint_requires_explicit_opt_in(
    tmp_path: Path, capsys
) -> None:
    """Opting into a smoke-path checkpoint prints a prominent warning."""
    smoke = tmp_path / "runs" / "smoke" / "weights" / "best.pt"
    smoke.parent.mkdir(parents=True)
    smoke.touch()

    assert resolve_weights(None, root=tmp_path, allow_smoke_weights=True) == smoke.resolve()
    assert "WARNING" in capsys.readouterr().out

    import pytest

    with pytest.raises(FileNotFoundError, match="Pass --allow-smoke-weights"):
        resolve_weights(smoke, root=tmp_path)
    assert resolve_weights(smoke, root=tmp_path, allow_smoke_weights=True) == smoke.resolve()


def test_explicit_missing_weights_does_not_fall_back(tmp_path: Path) -> None:
    """An explicit invalid path is an error even if a final model exists."""
    import pytest

    final = tmp_path / "results" / "run_0002" / "checkpoints" / "final" / "best.pt"
    final.parent.mkdir(parents=True)
    final.touch()
    with pytest.raises(FileNotFoundError, match="Explicit weights file not found"):
        resolve_weights(tmp_path / "missing.pt", root=tmp_path)
