"""Tests for src.eval.audit_sample — Wilson interval and sampling."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from src.cli import app
from src.eval.audit_sample import _wilson_interval, compute_audit_results


def test_audit_results_cli_reports_known_synthetic_precision(tmp_path: Path) -> None:
    """The CLI summarizes ten known labels overall and in confidence terciles."""
    labels = [
        ("low", "kiln"), ("low", "not_kiln"), ("low", "kiln"),
        ("mid", "not_kiln"), ("mid", "not_kiln"), ("mid", "kiln"),
        ("high", "kiln"), ("high", "kiln"), ("high", "not_kiln"), ("high", "kiln"),
    ]
    audit_csv = tmp_path / "audit.csv"
    pd.DataFrame(
        {"tercile": [tercile for tercile, _ in labels], "label": [label for _, label in labels]}
    ).to_csv(audit_csv, index=False)

    results = compute_audit_results(audit_csv, tmp_path / "direct-results.json")
    assert results["overall"]["n"] == 10
    assert results["overall"]["true_positives"] == 6
    assert results["overall"]["precision"] == 0.6
    for summary in [results["overall"], *results["by_tercile"].values()]:
        assert summary["ci_95_lower"] < summary["precision"] < summary["ci_95_upper"]

    command_result = CliRunner().invoke(app, ["audit-results", str(audit_csv)])
    assert command_result.exit_code == 0, command_result.output
    assert "by_tercile" in command_result.output
    assert "ci_95_lower" in command_result.output
    assert (tmp_path / "audit_results.json").is_file()


class TestWilsonInterval:
    """Tests for the Wilson score confidence interval."""

    def test_perfect_precision(self) -> None:
        lo, hi = _wilson_interval(10, 10)
        assert lo > 0.6  # should be well above 0.5
        assert hi <= 1.0

    def test_zero_precision(self) -> None:
        lo, hi = _wilson_interval(0, 10)
        assert lo >= 0.0
        assert hi < 0.4  # should be well below 0.5

    def test_empty(self) -> None:
        lo, hi = _wilson_interval(0, 0)
        assert lo == 0.0
        assert hi == 0.0

    def test_half(self) -> None:
        lo, hi = _wilson_interval(50, 100)
        assert 0.35 < lo < 0.5
        assert 0.5 < hi < 0.65
