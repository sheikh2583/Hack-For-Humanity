"""Merge district candidate GeoParquet files into one canonical GeoParquet.

Input schema: EPSG:4326 GeoParquet files with a non-empty ``district`` column.
Output schema: one EPSG:4326 GeoParquet with the same candidate columns.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def merge_district_candidates(inputs: list[Path], output: Path) -> gpd.GeoDataFrame:
    """Merge current district outputs after validating their district metadata."""
    if not inputs:
        raise ValueError("At least one district candidate file is required")
    frames: list[gpd.GeoDataFrame] = []
    for path in inputs:
        frame = gpd.read_parquet(path)
        if "district" not in frame.columns:
            raise ValueError(f"{path} does not contain a district column")
        districts = frame["district"].astype("string").str.strip()
        if districts.isna().any() or districts.eq("").any():
            raise ValueError(f"{path} contains candidates without a district")
        frames.append(frame)
    merged = gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), geometry="geometry", crs=frames[0].crs
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(output)
    return merged


def main() -> None:
    """Parse paths, merge district candidates, and print the resulting row count."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = merge_district_candidates(args.inputs, args.output)
    print(f"Merged {len(result)} candidates into {args.output}")


if __name__ == "__main__":
    main()
