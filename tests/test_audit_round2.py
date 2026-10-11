"""Synthetic tests for blinded Round 2 sampling and analysis."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from scripts.make_audit_sample import _components_within_50m
from src.cli import app
from src.eval.audit_round2 import (
    analyze_round2,
    cohen_kappa,
    normalize_labels,
    precision_summary,
    weighted_precision,
    wilson_interval,
)


def test_sampling_duplicate_components_use_projected_centroid_distance() -> None:
    """Candidates within 50 m share a group in synthetic WGS84 points."""
    points = gpd.GeoDataFrame(
        geometry=[Point(90, 24), Point(90.0001, 24), Point(90.01, 24)],
        crs="EPSG:4326",
    )
    groups = _components_within_50m(points, "EPSG:9680")
    assert sorted(sorted(group) for group in groups) == [[0, 1], [2]]


@pytest.mark.parametrize("successes, total", [(0, 10), (10, 10)])
def test_wilson_interval_edge_cases(successes: int, total: int) -> None:
    """Wilson bounds are valid at zero and perfect success rates."""
    lower, upper = wilson_interval(successes, total)
    assert 0 <= lower <= upper <= 1
    if successes == 0:
        assert lower == 0 and upper < 0.4
    else:
        assert upper == 1 and lower > 0.6


def test_skip_is_counted_but_excluded_from_precision() -> None:
    """SKIP responses are reported separately and excluded from the denominator."""
    summary = precision_summary(pd.Series(["TP", "SKIP", "FP"]))
    assert summary["n"] == 2
    assert summary["tp"] == 1
    assert summary["fp"] == 1
    assert summary["skip"] == 1
    assert summary["precision"] == 0.5


def test_population_weighting_uses_population_share() -> None:
    """Population weights, rather than sample sizes, determine the estimate."""
    result = weighted_precision(
        {
            "low": pd.Series(["TP"]),
            "mid": pd.Series(["FP"]),
            "high": pd.Series(["TP"]),
        },
        {"low": 1, "mid": 1, "high": 2},
        bootstrap_reps=200,
    )
    assert result["precision"] == 0.75
    assert result["ci_95_lower"] == 0.75
    assert result["ci_95_upper"] == 0.75


def test_kappa_counts_skip_mismatch_as_disagreement() -> None:
    """A SKIP against a non-SKIP response is an exact-label disagreement."""
    agreement, kappa = cohen_kappa(
        pd.Series(["TP", "FP", "SKIP"]),
        pd.Series(["TP", "SKIP", "FP"]),
    )
    assert agreement == pytest.approx(1 / 3)
    assert kappa == pytest.approx(0.0)


def test_blank_labels_raise_clear_error(tmp_path) -> None:
    """Blank human responses stop analysis with a location-specific message."""
    with pytest.raises(ValueError, match="Blank label"):
        normalize_labels(pd.Series(["TP", ""]), str(tmp_path / "sheet.csv"))


def test_analysis_writes_weighted_and_agreement_summaries(tmp_path) -> None:
    """Tiny synthetic sheets produce summaries and retain overlap disagreements."""
    required = {
        "kiln_id": ["c1", "g1"], "district": ["Chapainawabganj", "Gazipur"],
        "label": ["TP", "SKIP"], "kiln_class": ["FCBK", "n/a"],
    }
    sheet_a = tmp_path / "audit_blind_A.csv"
    sheet_b = tmp_path / "audit_blind_B.csv"
    pd.DataFrame(required).to_csv(sheet_a, index=False)
    pd.DataFrame({**required, "label": ["FP", "TP"]}).to_csv(sheet_b, index=False)
    key_path = tmp_path / "audit_key.csv"
    pd.DataFrame({
        "kiln_id": ["c1", "g1"], "district": ["Chapainawabganj", "Gazipur"],
        "model_confidence": [0.3, 0.5], "band": ["low", "high"],
        "tercile_within_district": ["mid", "high"],
        "predicted_class": ["FCBK", "Zigzag"], "is_overlap": [True, True],
        "assigned_sheet": ["A+B", "A+B"],
    }).to_csv(key_path, index=False)
    report_path = tmp_path / "audit_sampling_report.md"
    report_path.write_text(
        "| District | Band | Eligible population after exclusions/dedup | Requested | Sampled | Shortfall |\n"
        "|---|---|---:|---:|---:|---:|\n" +
        "".join(f"| {district} | {band} | 1 | 1 | 1 | 0 |\n"
                for district in ("Chapainawabganj", "Gazipur")
                for band in ("low", "mid", "high")),
        encoding="utf-8",
    )
    result = analyze_round2(
        sheet_a, sheet_b, key_path, report_path,
        report_path=tmp_path / "results.md", csv_path=tmp_path / "results.csv",
    )
    assert result["agreement"] == 0.0
    assert len(result["disagreements"]) == 2
    assert result["districts"]["Chapainawabganj"]["by_band"]["low"]["skip"] == 0
    assert (tmp_path / "results.md").is_file()
    assert (tmp_path / "results.csv").is_file()
    old_labels = tmp_path / "old.csv"
    pd.DataFrame({"label": ["TP", "FP"]}).to_csv(old_labels, index=False)
    from typer.testing import CliRunner

    cli = CliRunner().invoke(
        app,
        [
            "audit-round2-results", "--sheet-a", str(sheet_a), "--sheet-b", str(sheet_b),
            "--key", str(key_path), "--sampling-report", str(report_path),
            "--old-labels", str(old_labels),
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert (tmp_path / "audit_round2_results.md").is_file()
