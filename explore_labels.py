"""Explore SentinelKilnDB labels via streaming batches + boundary polygon.

Streams all three Parquet files without loading them fully into memory,
filters chips to the Bangladesh boundary polygon (not a bbox), and prints
label statistics.

Usage:
    python explore_labels.py [dataset_dir] [boundary_path]

Defaults:
    dataset_dir  = data/raw/sentinelkilndb
    boundary_path = data/raw/bangladesh_boundary.geojson
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pyarrow.parquet as pq
from shapely.geometry import Point
from shapely.prepared import prep

from src.data.convert_sentinelkilndb import (
    COL_IMAGE_NAME,
    COL_OBB,
    ORIGINAL_CLASSES,
    SPLITS,
    _parquet_path,
    parse_latlon,
)


def main(dataset_dir: Path, boundary_path: Path) -> None:
    """Stream all Parquet files, filter to boundary, print label statistics."""
    print(f"Dataset directory: {dataset_dir}")
    print(f"Boundary: {boundary_path}\n")

    gdf = gpd.read_file(boundary_path)
    boundary_prep = prep(gdf.unary_union)

    class_counter: Counter[int] = Counter()
    total_all = 0
    total_bd = 0
    n_positive = 0
    n_negative = 0
    unparseable = 0
    sample_lines: list[str] = []

    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.is_file():
            print(f"[MISSING] {pq_path}")
            continue

        pf = pq.ParquetFile(pq_path)
        for batch in pf.iter_batches(batch_size=4096, columns=[COL_IMAGE_NAME, COL_OBB]):
            d = batch.to_pydict()
            for name, obb in zip(d[COL_IMAGE_NAME], d[COL_OBB]):
                total_all += 1

                parsed = parse_latlon(name)
                if parsed is None:
                    unparseable += 1
                    continue
                lat, lon = parsed

                if not boundary_prep.contains(Point(lon, lat)):
                    continue
                total_bd += 1

                if obb:
                    n_positive += 1
                    for line in obb:
                        cls = int(line.split()[0])
                        class_counter[cls] += 1
                        if len(sample_lines) < 5:
                            sample_lines.append(f"  [{split}] {name}: {line}")
                else:
                    n_negative += 1

    print(f"Total chips:           {total_all}")
    print(f"Parseable names:       {total_all - unparseable}")
    print(f"Unparseable names:     {unparseable}")
    print(f"Chips inside boundary: {total_bd}")
    print(f"Positive chips:        {n_positive}")
    print(f"Negative chips:        {n_negative}")
    print()

    print("Class distribution (inside boundary):")
    for cls_id in sorted(class_counter):
        name = ORIGINAL_CLASSES.get(cls_id, f"unknown({cls_id})")
        print(f"  {cls_id} ({name}): {class_counter[cls_id]} bbox labels")
    print()

    if sample_lines:
        print("Sample label lines:")
        for line in sample_lines:
            print(line)


if __name__ == "__main__":
    ds = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/sentinelkilndb")
    bd = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/raw/bangladesh_boundary.geojson")
    main(ds, bd)
