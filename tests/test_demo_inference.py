"""Synthetic checks for demo inference coordinate conversion and rules display."""

from pathlib import Path

from app.streamlit_app import rules_are_verified
from src.eval.demo_inference import detection_point, resolve_weights


def test_detection_point_maps_chip_center_to_wgs84() -> None:
    """A centred synthetic OBB maps to the encoded chip centre."""
    point = detection_point(24.0, 90.0, [(60, 60), (68, 60), (68, 68), (60, 68)])
    assert abs(point.x - 90.0) < 1e-9
    assert abs(point.y - 24.0) < 1e-9


def test_rules_verified_uses_all_configured_rule_flags() -> None:
    """Any false technology or siting verification flag makes status false."""
    assert rules_are_verified({"technology": {"verified": True}, "siting_rules": [{"verified": True}]})
    assert not rules_are_verified({"technology": {"verified": True}, "siting_rules": [{"verified": False}]})


def test_weights_search_prefers_run_0002_full_checkpoint(tmp_path: Path) -> None:
    """The designated full-training checkpoint wins over smoke outputs."""
    candidate = tmp_path / "results" / "run_0002" / "checkpoints" / "final" / "best.pt"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    smoke = tmp_path / "runs" / "smoke-yolov8n-obb-256" / "weights" / "best.pt"
    smoke.parent.mkdir(parents=True)
    smoke.touch()
    assert resolve_weights(tmp_path / "missing.pt", root=tmp_path) == candidate.resolve()


def test_weights_search_uses_other_results_before_runs(tmp_path: Path) -> None:
    """Other final checkpoints take precedence over run-folder checkpoints."""
    candidate = tmp_path / "results" / "run_0003" / "checkpoints" / "final" / "best.pt"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    smoke = tmp_path / "runs" / "smoke" / "weights" / "best.pt"
    smoke.parent.mkdir(parents=True)
    smoke.touch()
    assert resolve_weights(None, root=tmp_path) == candidate.resolve()


def test_weights_warns_when_only_runs_checkpoint_exists(tmp_path: Path, capsys) -> None:
    """A last-resort runs checkpoint prints the smoke-test warning."""
    candidate = tmp_path / "runs" / "smoke" / "weights" / "best.pt"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    assert resolve_weights(None, root=tmp_path) == candidate.resolve()
    assert "may be a smoke-test checkpoint" in capsys.readouterr().out
