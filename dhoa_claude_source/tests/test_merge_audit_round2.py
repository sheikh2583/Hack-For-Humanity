"""Tests for independent Round 2 audit merging and precision summaries."""

from __future__ import annotations

import pandas as pd
from typer.testing import CliRunner

from src.cli import app
from src.eval.merge_audit_round2 import merge_audit_round2


def test_merge_round2_joins_and_computes_tercile_precision(tmp_path) -> None:
    """Synthetic Round 2 CSVs merge by kiln_id and write Wilson summaries."""
    labels_path = tmp_path / "labels.csv"
    key_path = tmp_path / "key.csv"
    pd.DataFrame({"kiln_id": ["k1", "k2", "k3"], "label": ["TP", "FP", "SKIP"]}).to_csv(
        labels_path, index=False
    )
    pd.DataFrame(
        {"kiln_id": ["k1", "k2", "k3"], "confidence": [0.1, 0.5, 0.9], "tercile": ["low", "mid", "high"]}
    ).to_csv(key_path, index=False)

    output_csv = tmp_path / "merged.csv"
    summary_path = tmp_path / "summary.md"
    result = merge_audit_round2(labels_path, key_path, output_csv, summary_path)

    merged = pd.read_csv(output_csv)
    assert list(merged.columns) == ["kiln_id", "confidence", "label"]
    assert merged["kiln_id"].tolist() == ["k1", "k2", "k3"]
    assert result["overall"]["true_positives"] == 1
    assert result["overall"]["n"] == 2
    assert result["overall"]["skips"] == 1
    assert result["by_tercile"]["low"]["precision"] == 1
    assert result["by_tercile"]["mid"]["precision"] == 0
    assert "95% Wilson" in summary_path.read_text(encoding="utf-8")


def test_round2_cli_accepts_labels_and_key_paths(tmp_path) -> None:
    """The audit-results-r2 command writes both requested output artifacts."""
    labels_path = tmp_path / "labels.csv"
    key_path = tmp_path / "key.csv"
    pd.DataFrame({"kiln_id": ["k1", "k2", "k3"], "label": ["TP", "FP", "TP"]}).to_csv(
        labels_path, index=False
    )
    pd.DataFrame(
        {"kiln_id": ["k1", "k2", "k3"], "confidence": [0.1, 0.5, 0.9]}
    ).to_csv(key_path, index=False)
    output_csv = tmp_path / "merged.csv"
    summary_path = tmp_path / "summary.md"

    result = CliRunner().invoke(
        app,
        [
            "audit-results-r2", "--labels", str(labels_path), "--key", str(key_path),
            "--output", str(output_csv), "--summary", str(summary_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Overall | 2 / 3" in result.output
    assert output_csv.is_file()
    assert summary_path.is_file()
