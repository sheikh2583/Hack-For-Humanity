"""Tests for normalized exposure priority scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.score import priority
from src.score.priority import (
    _assign_priority_bands,
    _rule_signal_summary,
    _score_priority_components,
)


def test_priority_bands_use_top_twenty_middle_forty_bottom_forty() -> None:
    """Ten distinct score values yield the requested 2/4/4 split."""
    bands = _assign_priority_bands(pd.Series(np.arange(10, 0, -1), name="priority"))
    assert bands.value_counts().to_dict() == {"Low": 4, "Medium": 4, "High": 2}
    assert bands.iloc[:2].eq("High").all()
    assert bands.iloc[2:6].eq("Medium").all()
    assert bands.iloc[6:].eq("Low").all()


def test_priority_bands_break_ties_to_keep_quantile_sizes() -> None:
    """Tied scores are ranked stably before qcut creates the percentile bands."""
    bands = _assign_priority_bands(pd.Series([0.0] * 10, name="priority"))
    assert bands.value_counts().to_dict() == {"Low": 4, "Medium": 4, "High": 2}


def test_rule_signal_summary_sums_severity_and_chooses_strongest() -> None:
    """Configured signal severities determine sum and top display label."""
    frame = pd.DataFrame({
        "breached_rules": [["near_school", "near_settlement"], [], ["technology_flagged"]],
        "dist_schools_m": [340.0, np.nan, np.nan],
    })
    rules = {
        "technology": {"severity": 2},
        "siting_rules": [
            {"id": "near_school", "feature": "schools", "severity": 3},
            {"id": "near_settlement", "feature": "settlements", "severity": 2},
        ],
    }
    scores, top_signals = _rule_signal_summary(frame, rules)
    assert scores.tolist() == [5.0, 0.0, 2.0]
    assert top_signals.tolist() == ["Near school (340 m)", "None", "FCBK technology"]


def test_zero_exposure_preserves_signal_score_order() -> None:
    """With no exposure, the higher screening-signal score retains higher priority."""
    kilns = pd.DataFrame({"breach_score": [5.0, 1.0], "confidence": [0.8, 1.0]})
    scored = _score_priority_components(
        kilns, np.zeros(2), np.zeros(2), np.zeros(2),
        {"n_schools": 1, "n_hospitals": 1, "settlement_area": 1},
    )
    assert scored.loc[0, "exposure"] == 0
    assert scored.loc[0, "priority"] > scored.loc[1, "priority"]


def test_exposure_weights_can_change_rank() -> None:
    """Changing component weights can change relative priority."""
    kilns = pd.DataFrame({"breach_score": [1.0, 1.0], "confidence": [1.0, 1.0]})
    components = (np.array([10, 0]), np.array([0, 10]), np.zeros(2))
    school_weighted = _score_priority_components(
        kilns, *components, {"n_schools": 2, "n_hospitals": 0, "settlement_area": 0}
    )
    hospital_weighted = _score_priority_components(
        kilns, *components, {"n_schools": 0, "n_hospitals": 2, "settlement_area": 0}
    )
    assert school_weighted.loc[0, "priority"] > school_weighted.loc[1, "priority"]
    assert hospital_weighted.loc[1, "priority"] > hospital_weighted.loc[0, "priority"]


def test_sensitivity_reuses_spatial_features_per_radius(monkeypatch, tmp_path) -> None:
    """Spatial priority calculation runs once for each radius, not each weight set."""
    base = pd.DataFrame({
        "kiln_id": ["a", "b", "c"],
        "breach_score": [1.0, 1.0, 1.0],
        "confidence": [1.0, 1.0, 1.0],
        "n_schools": [1.0, 2.0, 3.0],
        "n_hospitals": [3.0, 2.0, 1.0],
        "settlement_area": [1.0, 1.0, 1.0],
    })
    calls: list[float] = []

    def fake_compute_priority(_path, output, radius_m, osm_dir):
        calls.append(radius_m)
        return base.copy()

    monkeypatch.setattr(priority, "compute_priority", fake_compute_priority)
    monkeypatch.setattr(priority, "_load_scoring_config", lambda: {"normalization": "percentile_rank"})
    result = priority.sensitivity_analysis(
        tmp_path / "unused.parquet",
        weight_sets=[{"n_schools": 1}, {"n_hospitals": 1}],
        radii=[500, 1000],
    )

    assert calls == [500, 1000]
    assert len(result) == 4
