"""src.geo.crs — CRS utilities for distance/area math.

Provides a helper to get the best projected CRS for Bangladesh,
with the EPSG:9680 → UTM fallback chain described in AGENTS.md.
"""

from __future__ import annotations

import pyproj
from pyproj.exceptions import CRSError, ProjError


def get_projected_crs() -> pyproj.CRS:
    """Return the best projected CRS for distance/area math in Bangladesh.

    Preference order:
    1. EPSG:9680 (WGS 84 / TM 90 NE)
    2. EPSG:32645 (UTM 45N) — for centroids west of 90°E
    3. EPSG:32646 (UTM 46N) — fallback

    Returns
    -------
    pyproj.CRS
        A projected CRS suitable for metre-based calculations.
    """
    for code in [9680, 32645, 32646]:
        try:
            crs = pyproj.CRS.from_epsg(code)
            # Quick sanity check: can we build a transformer?
            pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
            return crs
        except (CRSError, ProjError):
            continue
    raise RuntimeError("Cannot build any projected CRS for Bangladesh. Check pyproj/PROJ installation.")

