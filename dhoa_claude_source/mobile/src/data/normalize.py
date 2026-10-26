"""SentinelKilnDB per-patch RGB normalization.

Input schema: a non-empty HxWx3 numeric array ordered R, G, B from raw
Sentinel-2 B4, B3, B2. Output: HxWx3 uint8 using the authors' per-band,
per-patch min/max stretch.
"""

from __future__ import annotations

import numpy as np


def minmax_uint8(patch: np.ndarray) -> np.ndarray:
    """Apply the recorded per-band min/max stretch independently per patch."""
    array = np.asarray(patch)
    if array.ndim != 3 or array.shape[2] != 3 or array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError("patch must be a non-empty HxWx3 RGB array")
    result = np.empty(array.shape, dtype=np.uint8)
    for channel in range(3):
        band = array[..., channel].astype(np.float64)
        scaled = (band - band.min()) / (band.max() - band.min() + 1e-5) * 255
        result[..., channel] = scaled.astype(np.uint8)
    return result
