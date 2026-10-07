"""src.geo.crs — CRS utilities for distance/area math.

Provides a helper to get the best projected CRS for Bangladesh,
with the EPSG:9680 → UTM fallback chain described in AGENTS.md.
"""

from __future__ import annotations

from typing import Any

import pyproj
from pyproj.exceptions import CRSError, ProjError


def centroid_longitude(frame: Any) -> float:
    """Return a GeoDataFrame's union centroid longitude in EPSG:4326.

    Input schema: a non-empty GeoDataFrame with geometry and a declared CRS.
    Output: centroid longitude in decimal degrees, used only to select a UTM
    fallback when EPSG:9680 is unavailable.
    """
    if frame.crs is None:
        raise ValueError("A CRS is required to determine the geometry centroid")
    if frame.empty:
        raise ValueError("Cannot determine a centroid longitude from an empty GeoDataFrame")
    centroid = frame.to_crs("EPSG:4326").geometry.union_all().centroid
    if centroid.is_empty:
        raise ValueError("Cannot determine a centroid longitude from empty geometries")
    longitude = float(centroid.x)
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"Centroid longitude is outside EPSG:4326: {longitude}")
    return longitude


def get_projected_crs(centroid_lon: float | None = None) -> pyproj.CRS:
    """Return the best projected CRS for distance/area math in Bangladesh.

    Preference order:
    1. EPSG:9680 (WGS 84 / TM 90 NE)
    2. EPSG:32645 (UTM 45N) — when the data centroid is west of 90°E
    3. EPSG:32646 (UTM 46N) — when the data centroid is at/east of 90°E

    ``centroid_lon`` is required only when EPSG:9680 cannot be constructed.

    Returns
    -------
    pyproj.CRS
        A projected CRS suitable for metre-based calculations.
    """
    try:
        crs = pyproj.CRS.from_epsg(9680)
        pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        return crs
    except (CRSError, ProjError):
        if centroid_lon is None:
            raise RuntimeError(
                "EPSG:9680 is unavailable; pass the data centroid longitude to select UTM 45N or 46N"
            )

    if not -180.0 <= centroid_lon <= 180.0:
        raise ValueError(f"Centroid longitude must be in [-180, 180], got {centroid_lon}")
    code = 32645 if centroid_lon < 90.0 else 32646
    try:
        crs = pyproj.CRS.from_epsg(code)
        pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        return crs
    except (CRSError, ProjError) as error:
        raise RuntimeError(f"Cannot build EPSG:{code}; check pyproj/PROJ installation") from error
