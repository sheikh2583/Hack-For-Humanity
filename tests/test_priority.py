"""Tests for normalized exposure priority scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.score import priority
from src.score.priority import _score_priority_components


def test_zero_exposure_preserves_breach_order() -> None:
    """With no exposure, the higher breach score retains higher priority."""
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
