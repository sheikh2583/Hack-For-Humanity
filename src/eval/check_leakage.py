"""Remove nearby validation/test chips that cross assigned split boundaries.

Input schema: records are mappings with ``image_name`` (unique filename),
``latitude`` and ``longitude`` (EPSG:4326 chip centre), and ``split``
(``train``, ``val`` or ``test``). Output schema: kept filenames, dropped
validation/test filenames, and the minimum cross-split Chebyshev distance in
metres (``None`` if fewer than two splits remain).

Chips are 128 px at 10 m, i.e. 1.28 km square, so two axis-aligned chips overlap
when ``|dx| < 1280 m`` AND ``|dy| < 1280 m``. That is exactly a Chebyshev (L-inf)
distance below 1280 m, so distances are Chebyshev, measured between chip centres
in EPSG:9680 (WGS 84 / TM 90 NE). The default threshold adds a 20 m margin.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import geopandas as gpd
import numpy as np
import pyproj
from scipy.spatial import cKDTree

from src.geo.crs import get_projected_crs

CHEBYSHEV_P = np.inf
DEFAULT_THRESHOLD_M = 1300.0
LEAKAGE_CRS_EPSG = 9680
FILTERED_SPLITS = ("val", "test")  # train chips are never dropped


def _leakage_crs() -> pyproj.CRS:
    """Return EPSG:9680, raising if the projected-CRS helper fell back to UTM.

    The threshold is defined in EPSG:9680 metres, so a silent UTM fallback would
    change what 1300 m means.
    """
    crs = get_projected_crs()
    if crs.to_epsg() != LEAKAGE_CRS_EPSG:
        raise RuntimeError(
            f"Leakage filter requires EPSG:{LEAKAGE_CRS_EPSG}, got {crs.to_string()}. "
            "Check the pyproj/PROJ installation."
        )
    return crs


def filter_cross_split_leakage(
    records: Sequence[Mapping[str, Any]], threshold_m: float = DEFAULT_THRESHOLD_M
) -> tuple[set[str], set[str], float | None]:
    """Drop val/test chips within ``threshold_m`` (Chebyshev) of another split.

    Records carry a unique ``image_name``, numeric ``latitude``/``longitude``
    in EPSG:4326 and ``split``. A val or test chip is dropped when any chip in a
    different split (train, or the other of val/test) lies within ``threshold_m``
    in Chebyshev distance, computed in EPSG:9680. Train chips are never dropped.
    Distances are evaluated against the original records, so a close val/test
    pair loses both members. Returns kept names, dropped names, and the minimum
    cross-split Chebyshev distance among kept chips, or ``None`` if fewer than
    two splits remain.
    """
    if threshold_m < 0:
        raise ValueError("threshold_m must be non-negative")
    if not records:
        return set(), set(), None

    frame = gpd.GeoDataFrame(
        records,
        geometry=gpd.points_from_xy(
            [float(r["longitude"]) for r in records],
            [float(r["latitude"]) for r in records],
        ),
        crs="EPSG:4326",
    ).to_crs(_leakage_crs())
    coords = np.array([(geom.x, geom.y) for geom in frame.geometry], dtype=float)
    splits = np.array([str(r["split"]) for r in records])
    names = [str(r["image_name"]) for r in records]

    dropped: set[str] = set()
    for split in FILTERED_SPLITS:
        own = np.flatnonzero(splits == split)
        other = np.flatnonzero(splits != split)
        if own.size == 0 or other.size == 0:
            continue
        distances, _ = cKDTree(coords[other]).query(coords[own], k=1, p=CHEBYSHEV_P)
        dropped.update(names[i] for i, d in zip(own, distances, strict=True) if d <= threshold_m)

    kept_idx = np.array([i for i, n in enumerate(names) if n not in dropped], dtype=int)
    min_distance: float | None = None
    kept_splits = sorted({str(s) for s in splits[kept_idx]})
    for pos, a in enumerate(kept_splits):
        for b in kept_splits[pos + 1 :]:
            ia = kept_idx[splits[kept_idx] == a]
            ib = kept_idx[splits[kept_idx] == b]
            dist, _ = cKDTree(coords[ib]).query(coords[ia], k=1, p=CHEBYSHEV_P)
            candidate = float(dist.min())
            min_distance = candidate if min_distance is None else min(min_distance, candidate)
    return set(names) - dropped, dropped, min_distance


def dropped_counts_by_split(
    records: Sequence[Mapping[str, Any]], dropped: set[str]
) -> dict[str, int]:
    """Count dropped chips per split.

    Input: the same ``records`` given to :func:`filter_cross_split_leakage` and
    its ``dropped`` name set. Output: ``{"train": 0, "val": n, "test": m}``;
    ``train`` is always 0 by construction.
    """
    counts = Counter(str(r["split"]) for r in records if str(r["image_name"]) in dropped)
    return {split: counts.get(split, 0) for split in ("train", "val", "test")}
