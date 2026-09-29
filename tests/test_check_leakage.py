"""Tiny synthetic checks for cross-split chip-centre leakage filtering (Chebyshev, EPSG:9680)."""

from __future__ import annotations

import pytest
from pyproj import Transformer

from src.eval.check_leakage import (
    DEFAULT_THRESHOLD_M,
    dropped_counts_by_split,
    filter_cross_split_leakage,
)

_TO_WGS84 = Transformer.from_crs("EPSG:9680", "EPSG:4326", always_xy=True)
_BASE_X, _BASE_Y = 500_000.0, 2_650_000.0  # arbitrary point inside Bangladesh in EPSG:9680


def _rec(name: str, split: str, dx: float = 0.0, dy: float = 0.0) -> dict[str, object]:
    """Build a record whose centre is (dx, dy) metres from the base point in EPSG:9680."""
    lon, lat = _TO_WGS84.transform(_BASE_X + dx, _BASE_Y + dy)
    return {"image_name": name, "latitude": lat, "longitude": lon, "split": split}


def test_default_threshold_is_1300_m() -> None:
    """Default threshold covers the 1280 m chip footprint plus a margin."""
    assert DEFAULT_THRESHOLD_M == 1300.0


def test_adjacent_chips_across_cell_edge_are_filtered() -> None:
    """Chips across a 0.25-degree cell edge ~22 m apart lose their val copy."""
    records = [
        {"image_name": "train.png", "latitude": 24.1249, "longitude": 88.1, "split": "train"},
        {"image_name": "val.png", "latitude": 24.1251, "longitude": 88.1, "split": "val"},
        {"image_name": "far.png", "latitude": 24.2, "longitude": 88.1, "split": "test"},
    ]
    kept, dropped, minimum = filter_cross_split_leakage(records)
    assert "val.png" in dropped
    assert "train.png" in kept
    assert "far.png" in kept
    assert minimum is not None and minimum > DEFAULT_THRESHOLD_M


@pytest.mark.parametrize("held_out", ["val", "test"])
def test_900_m_apart_drops_val_or_test_but_keeps_train(held_out: str) -> None:
    """Two chips 900 m apart in different splits: the val/test one is dropped."""
    records = [_rec("train.png", "train"), _rec("held.png", held_out, dx=900.0)]
    kept, dropped, minimum = filter_cross_split_leakage(records)
    assert dropped == {"held.png"}
    assert kept == {"train.png"}
    assert minimum is None  # only one split left


@pytest.mark.parametrize("held_out", ["val", "test"])
def test_1500_m_apart_keeps_both(held_out: str) -> None:
    """Two chips 1500 m apart in different splits: both are kept."""
    records = [_rec("train.png", "train"), _rec("held.png", held_out, dx=1500.0)]
    kept, dropped, minimum = filter_cross_split_leakage(records)
    assert dropped == set()
    assert kept == {"train.png", "held.png"}
    assert minimum == pytest.approx(1500.0, abs=1.0)


def test_distance_is_chebyshev_not_euclidean() -> None:
    """dx=dy=1000 m: Euclidean 1414 m (would keep) but Chebyshev 1000 m (must drop)."""
    records = [_rec("train.png", "train"), _rec("val.png", "val", dx=1000.0, dy=1000.0)]
    _, dropped, _ = filter_cross_split_leakage(records)
    assert dropped == {"val.png"}


def test_diagonal_beyond_threshold_on_one_axis_is_kept() -> None:
    """dx=1500, dy=200: Chebyshev 1500 m > threshold, so no overlap and no drop."""
    records = [_rec("train.png", "train"), _rec("val.png", "val", dx=1500.0, dy=200.0)]
    _, dropped, minimum = filter_cross_split_leakage(records)
    assert dropped == set()
    assert minimum == pytest.approx(1500.0, abs=1.0)


def test_train_chips_are_never_dropped_and_val_test_pair_loses_both() -> None:
    """A close val/test pair drops both; a train chip near them survives."""
    records = [
        _rec("train.png", "train", dx=-5000.0),
        _rec("val.png", "val"),
        _rec("test.png", "test", dx=500.0),
    ]
    kept, dropped, _ = filter_cross_split_leakage(records)
    assert dropped == {"val.png", "test.png"}
    assert kept == {"train.png"}
    assert dropped_counts_by_split(records, dropped) == {"train": 0, "val": 1, "test": 1}


def test_same_split_neighbours_are_not_dropped() -> None:
    """Overlap within one split is not cross-split leakage."""
    records = [_rec("a.png", "val"), _rec("b.png", "val", dx=100.0)]
    kept, dropped, minimum = filter_cross_split_leakage(records)
    assert dropped == set() and kept == {"a.png", "b.png"} and minimum is None


def test_custom_threshold_and_validation() -> None:
    """A smaller threshold keeps a 900 m pair; a negative threshold is rejected."""
    records = [_rec("train.png", "train"), _rec("val.png", "val", dx=900.0)]
    _, dropped, _ = filter_cross_split_leakage(records, threshold_m=800.0)
    assert dropped == set()
    with pytest.raises(ValueError):
        filter_cross_split_leakage(records, threshold_m=-1.0)
    assert filter_cross_split_leakage([]) == (set(), set(), None)
