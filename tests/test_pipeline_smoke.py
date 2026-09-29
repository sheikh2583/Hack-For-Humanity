"""Synthetic integration smoke test from detections through dashboard loader."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import yaml
from shapely.geometry import Point


def test_synthetic_rules_priority_dashboard_pipeline(tmp_path: Path) -> None:
    """Run synthetic GeoParquet through rules, priority and app data loading."""
    from app.data_loader import load_kilns
    from src.rules.engine import evaluate_rules
    from src.score.priority import compute_priority

    detected_path = tmp_path / "kilns.parquet"
    detected = gpd.GeoDataFrame(
        {
            "kiln_id": ["high", "low"],
            "class": ["FCBK", "Zigzag"],
            "confidence": [0.8, 0.9],
            "district": ["Synthetic", "Synthetic"],
        },
        geometry=[Point(90.4, 24.0), Point(90.5, 24.0)],
        crs="EPSG:4326",
    )
    detected.to_parquet(detected_path)
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(yaml.safe_dump({
        "version": "smoke-v1",
        "technology": {"flagged_classes": ["FCBK"], "severity": 3, "verified": True},
        "siting_rules": [],
    }), encoding="utf-8")
    osm_dir = tmp_path / "interim"
    (osm_dir / "osm").mkdir(parents=True)
    scored_path = tmp_path / "scored.parquet"
    evaluate_rules(detected_path, rules_path, osm_dir, scored_path)
    ranked_path = tmp_path / "processed" / "kilns_prioritised.parquet"
    prioritised = compute_priority(scored_path, ranked_path, osm_dir=tmp_path / "empty_interim")
    assert prioritised.loc[prioritised.kiln_id == "high", "priority"].iloc[0] > 0

    loaded = load_kilns(ranked_path)
    assert set(loaded["kiln_id"]) == {"high", "low"}
    assert {"lat", "lon", "priority", "exposure"}.issubset(loaded.columns)
