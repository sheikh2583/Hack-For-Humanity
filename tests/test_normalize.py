"""Synthetic tests for the recorded SentinelKilnDB min/max transform."""

from __future__ import annotations

import numpy as np

from src.data.normalize import minmax_uint8


def test_minmax_uint8_each_band_has_zero_and_max_254() -> None:
    """Per-band min/max normalization produces zero and the epsilon-limited 254."""
    patch = np.array(
        [[[10, 20, 30], [20, 40, 60]], [[30, 60, 90], [40, 80, 120]]],
        dtype=np.uint16,
    )
    normalized = minmax_uint8(patch)
    assert normalized.dtype == np.uint8
    assert np.all(normalized.min(axis=(0, 1)) == 0)
    assert np.all(normalized.max(axis=(0, 1)) == 254)
