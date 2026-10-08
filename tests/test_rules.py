"""Tests for src.rules.engine — rule evaluation with synthetic data.

Uses tiny synthetic kilns and features at known distances to verify
that breach detection and distance calculations are correct.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pytest
import yaml
from shapely.geometry import Point

from src.rules.engine import _ensure_class_column


def test_demo_class_name_is_accepted_by_rule_engine() -> None:
    """The requested demo schema maps class_name for screening compatibility."""
    kilns = gpd.GeoDataFrame(
        {"class_name": ["FCBK"], "geometry": [Point(90, 24)]}, crs="EPSG:4326"
    )
    compatible = _ensure_class_column(kilns)
    assert compatible["class"].tolist() == ["FCBK"]


class TestRuleEngine:
    """Integration tests for the compliance rule engine."""

    @pytest.fixture
    def setup_data(self, tmp_path: Path):
        """Create synthetic kilns, OSM layers, and rules config."""
        # Rules config
        rules = {
            "version": "test-v1",
            "technology": {
                "flagged_classes": ["FCBK"],
                "severity": 3,
                "verified": False,
            },
            "siting_rules": [
                {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3, "verified": False},
                {"id": "near_hospital", "feature": "hospitals", "buffer_m": 1000, "severity": 3, "verified": False},
            ],
        }
        rules_path = tmp_path / "rules.yaml"
        rules_path.write_text(yaml.dump(rules))

        # Synthetic kilns — one near a school (500m), one far (5km)
        # Using approximate degree-to-metre conversion at ~24°N:
        # 1° lat ≈ 110,574 m, 1° lon ≈ 101,300 m
        kiln_near = Point(88.5, 24.0)           # near school
        kiln_far = Point(88.55, 24.05)          # ~5 km from school

        kilns_gdf = gpd.GeoDataFrame(
            {
                "kiln_id": ["kiln_near", "kiln_far"],
                "geometry": [kiln_near, kiln_far],
                "class": ["FCBK", "Zigzag"],
                "confidence": [0.9, 0.8],
                "district": ["TestDistrict", "TestDistrict"],
                "detector_model": ["synthetic-model", "synthetic-model"],
                "detector_version": ["test-version", "test-version"],
                "imagery_date": [None, None],
            },
            crs="EPSG:4326",
        )
        kilns_path = tmp_path / "kilns.parquet"
        kilns_gdf.to_parquet(kilns_path)

        # Synthetic school at ~500m from kiln_near
        school_point = Point(88.5 + 500 / 101300, 24.0)

        osm_dir = tmp_path / "osm" / "TestDistrict"
        osm_dir.mkdir(parents=True)

        schools_gdf = gpd.GeoDataFrame(
            {
                "name": ["Test School"],
                "feature_id": ["way/123"],
                "source_layer_id": ["openstreetmap:schools"],
                "source_authority": ["OpenStreetMap contributors"],
                "source_url": ["https://www.openstreetmap.org/"],
                "source_version_date": [None],
                "source_accessed_at": ["2026-10-08T00:00:00+00:00"],
                "geometry_provenance": ["synthetic test geometry"],
                "geometry": [school_point],
            },
            crs="EPSG:4326",
        )
        schools_gdf.to_parquet(osm_dir / "schools.parquet")

        # Empty hospitals
        hospitals_gdf = gpd.GeoDataFrame(
            {"name": [], "geometry": []},
            geometry="geometry",
            crs="EPSG:4326",
        )
        hospitals_gdf.to_parquet(osm_dir / "hospitals.parquet")

        return {
            "kilns_path": kilns_path,
            "rules_path": rules_path,
            "osm_dir": tmp_path,
            "output": tmp_path / "scored.parquet",
        }

    def test_breach_detection(self, setup_data: dict) -> None:
        """Verify that a kiln within buffer distance triggers a breach."""
        from src.rules.engine import evaluate_rules

        result = evaluate_rules(
            kilns_path=setup_data["kilns_path"],
            rules_config=setup_data["rules_path"],
            osm_dir=setup_data["osm_dir"],
            output=setup_data["output"],
        )

        near_kiln = result[result["kiln_id"] == "kiln_near"].iloc[0]
        far_kiln = result[result["kiln_id"] == "kiln_far"].iloc[0]

        # Near kiln: FCBK (technology flagged) + near school → 2 breaches
        assert "technology_flagged" in near_kiln["breached_rules"]
        assert "near_school" in near_kiln["breached_rules"]
        assert near_kiln["breach_count"] >= 2

        # Far kiln: Zigzag (not flagged) + far from school
        assert not far_kiln["technology_flagged"]
        assert "near_school" not in far_kiln["breached_rules"]

    def test_rules_verified_flag(self, setup_data: dict) -> None:
        """All kilns should have rules_verified=false when rules are unverified."""
        from src.rules.engine import evaluate_rules

        result = evaluate_rules(
            kilns_path=setup_data["kilns_path"],
            rules_config=setup_data["rules_path"],
            osm_dir=setup_data["osm_dir"],
            output=setup_data["output"],
        )

        assert not result["rules_verified"].any()

    def test_distance_column_exists(self, setup_data: dict) -> None:
        """Distance columns should be present in output."""
        from src.rules.engine import evaluate_rules

        result = evaluate_rules(
            kilns_path=setup_data["kilns_path"],
            rules_config=setup_data["rules_path"],
            osm_dir=setup_data["osm_dir"],
            output=setup_data["output"],
        )

        assert "dist_schools_m" in result.columns
        assert "dist_hospitals_m" in result.columns

    def test_candidate_signals_have_unverified_provenance(self, setup_data: dict) -> None:
        """Matched mapped features retain source, method, confidence, and review state."""
        import json

        from src.rules.engine import evaluate_rules

        result = evaluate_rules(
            kilns_path=setup_data["kilns_path"],
            rules_config=setup_data["rules_path"],
            osm_dir=setup_data["osm_dir"],
            output=setup_data["output"],
        )
        near_kiln = result[result["kiln_id"] == "kiln_near"].iloc[0]
        records = json.loads(near_kiln["signal_provenance_json"])
        school_signal = next(item for item in records if item["signal_id"] == "near_school")

        assert school_signal["review_state"] == "unverified_candidate"
        assert school_signal["rule_config_version"] == "test-v1"
        assert school_signal["source_layer_id"] == "openstreetmap:schools"
        assert school_signal["source_authority"] == "OpenStreetMap contributors"
        assert school_signal["source_url"].startswith("https://")
        assert school_signal["feature_id"] == "way/123"
        assert school_signal["distance_m"] == pytest.approx(500, abs=3)
        assert "Shapely nearest geometry distance" in school_signal["measurement_method"]
        assert school_signal["detector_model_version"] == "synthetic-model / test-version"
        assert school_signal["detector_confidence"] == pytest.approx(0.9)
        assert school_signal["imagery_date"] is None
        assert school_signal["instrument_id"] is None
        assert school_signal["effective_dates"] is None
