"""Tiny synthetic kiln data for tests (never the real dataset).

Input: a row count and seed. Output: ``make_kilns`` -> DataFrame with the
dashboard columns; ``write_parquet`` -> a GeoParquet file the app can load via
``DHOA_DATA_DIR``. Geography is made up: two districts around (23.8, 90.3) and
(24.0, 90.4); one named place whose two kilns are ~12 km apart so its centre is
~6 km from both (used for the empty-state test).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REMOTE_PLACE = "Remote Bazar"


def make_kilns(count: int = 60, seed: int = 7) -> pd.DataFrame:
    """Return ``count`` synthetic kilns plus two far-apart ``REMOTE_PLACE`` kilns."""
    rng = np.random.default_rng(seed)
    half = count // 2
    district = np.array(["Dhaka"] * half + ["Gazipur"] * (count - half))
    base_lat = np.where(district == "Dhaka", 23.80, 24.00)
    base_lon = np.where(district == "Dhaka", 90.30, 90.40)
    frame = pd.DataFrame(
        {
            "kiln_id": [f"s{i}" for i in range(count)],
            "lat": base_lat + rng.random(count) * 0.10,
            "lon": base_lon + rng.random(count) * 0.10,
            "district": district,
            "upazila": np.where(rng.random(count) < 0.5, "Savar", "Dhamrai"),
            "class": rng.choice(["Zigzag", "FCBK"], count),
            "priority": rng.random(count),
            "nearest_place": [None] * count,
        }
    )
    frame.loc[frame["district"] == "Gazipur", "upazila"] = "Tongi"
    remote = pd.DataFrame(
        {
            "kiln_id": ["r1", "r2"], "lat": [24.50, 24.50], "lon": [88.30, 88.4075],
            "district": ["Rajshahi"] * 2, "upazila": ["Paba"] * 2, "class": ["Zigzag"] * 2,
            "priority": [0.5, 0.4], "nearest_place": [REMOTE_PLACE] * 2,
        }
    )
    return pd.concat([frame, remote], ignore_index=True)


def write_parquet(directory: Path, count: int = 60) -> Path:
    """Write ``kilns_prioritised.parquet`` (EPSG:4326 points) into ``directory``."""
    import geopandas as gpd

    frame = make_kilns(count)
    gdf = gpd.GeoDataFrame(
        frame, geometry=gpd.points_from_xy(frame["lon"], frame["lat"]), crs="EPSG:4326"
    )
    path = directory / "kilns_prioritised.parquet"
    gdf.to_parquet(path)
    return path
