"""Explore SentinelKilnDB Parquet files via streaming batches.

Usage:
    python explore_parquet.py [dataset_dir]

Default dataset_dir is data/raw/sentinelkilndb.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq

from src.data.convert_sentinelkilndb import SPLITS, _parquet_path


def main(dataset_dir: Path) -> None:
    """Print schema, row counts, and sample rows for each split Parquet file."""
    print(f"Dataset directory: {dataset_dir}\n")

    total_all = 0
    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.is_file():
            print(f"[MISSING] {pq_path}")
            continue

        pf = pq.ParquetFile(pq_path)
        n_rows = pf.metadata.num_rows
        n_groups = pf.num_row_groups
        print(f"== {pq_path} | {n_rows} rows | {n_groups} row group(s)")
        print(pf.schema_arrow)
        print()
        total_all += n_rows

    print(f"Total chips across all splits: {total_all}\n")

    # Sample first 5 rows from train
    train_pq = _parquet_path(dataset_dir, "train")
    if train_pq.is_file():
        print("Sample rows (first 5 from train):")
        pf = pq.ParquetFile(train_pq)
        count = 0
        for batch in pf.iter_batches(batch_size=5):
            for row in batch.to_pylist():
                print({k: repr(v)[:300] for k, v in row.items()})
                count += 1
                if count >= 5:
                    break
            if count >= 5:
                break
        print()


if __name__ == "__main__":
    ds = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/sentinelkilndb")
    main(ds)
