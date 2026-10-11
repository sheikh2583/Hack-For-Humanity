"""Tests for configured Earth Engine export boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.data.export_s2 import _require_preprocessing_verification, configured_bbox
from tools.export_district import configured_district_names


def test_configured_bbox_reads_gazipur_coordinates() -> None:
    """Gazipur's configured AOI is returned in west/south/east/north order."""
    district = {
        "name": "Gazipur",
        "bbox": {"west": 89.85, "south": 23.85, "east": 90.55, "north": 24.35},
    }
    assert configured_bbox(district) == (89.85, 23.85, 90.55, 24.35)


def test_configured_bbox_rejects_invalid_coordinate_order() -> None:
    """Configured AOIs fail before an export when their coordinate order is invalid."""
    with pytest.raises(ValueError, match="west < east"):
        configured_bbox(
            {"name": "Test", "bbox": {"west": 2, "south": 1, "east": 1, "north": 3}}
        )


def test_false_preprocessing_flag_logs_warning_and_blocks_export(caplog, tmp_path: Path) -> None:
    """An unreviewed preprocessing configuration cannot reach Earth Engine."""
    with pytest.raises(RuntimeError, match="Preprocessing review is required"):
        _require_preprocessing_verification(
            {"preprocessing_verified": False}, tmp_path / "preprocessing.yaml"
        )
    assert "preprocessing_verified=false" in caplog.text


def test_new_district_aoi_names_bboxes_and_export_choices() -> None:
    """New configured districts use the supplied bbox and CLI names."""
    project_root = Path(__file__).resolve().parents[1]
    aoi_path = project_root / "config/aoi.yaml"
    config = yaml.safe_load(aoi_path.read_text(encoding="utf-8"))
    expected = {
        "Rajshahi": ("Rajshahi", (88.1, 24.0, 88.8, 24.6)),
        "Dhaka": ("Dhaka", (89.9, 23.5, 90.7, 24.1)),
        "Chittagong": ("Chittagong", (91.6, 22.1, 92.4, 22.9)),
    }
    districts = {district["name"]: district for district in config["districts"]}
    choices = configured_district_names(aoi_path)
    for name, (boundary_name, bbox) in expected.items():
        assert name in choices
        assert districts[name]["boundary_name"] == boundary_name
        assert configured_bbox(districts[name]) == bbox
