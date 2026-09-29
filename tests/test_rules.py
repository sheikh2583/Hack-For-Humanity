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
            {"name": ["Test School"], "geometry": [school_point]},
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
