"""Convert SentinelKilnDB Parquet files to a spatial-block-split YOLO-OBB dataset.

Input
-----
- ``dataset_dir``:  Root of the raw SentinelKilnDB download.  Expected layout::

      <dataset_dir>/
        train/train.parquet
        val/val.parquet
        test/test.parquet

  Each Parquet file is a single row group with columns:

  ==================  ==========  ===============================================
  Column              Arrow type  Description
  ==================  ==========  ===============================================
  ``image_name``      string      ``lat_lon.png`` — lat/lon joined by underscore
  ``image``           binary      Raw PNG bytes, 128×128 px, 8-bit RGB
  ``dota_label``      list<string>  DOTA-format label lines (empty = negative)
  ``yolo_aa_label``   list<string>  YOLO-AABB label lines (empty = negative)
  ``yolo_obb_label``  list<string>  YOLO-OBB label lines (empty = negative)
  ==================  ==========  ===============================================

  Each string in ``yolo_obb_label`` is one label line::

      <class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>

  where ``class_id`` is an integer (0=rare merged type, 1=FCBK, 2=Zigzag) and the four
  corner coordinates are normalised to [0, 1].

- ``boundary_path``:  GeoJSON polygon(s) of Bangladesh (e.g. GADM level-0).

Output
------
- A YOLO-OBB directory tree at ``output_dir/``:

      output_dir/
        train/{images,labels}/
        val/{images,labels}/
        test/{images,labels}/
        dataset.yaml
        split_report.json

- Each positive chip produces ``<image_name>`` (PNG bytes copied verbatim) and
  a ``.txt`` label file containing the remapped YOLO-OBB lines.  Negative chips
  produce an empty ``.txt`` label file.
- ``dataset.yaml`` — Ultralytics YOLO-OBB config (path, split dirs, class names).
- ``split_report.json`` — per-class-per-split counts, leakage analysis for the
  shipped split, and metadata.

Processing
----------
- Parquet files are read with ``pyarrow.parquet.ParquetFile.iter_batches``;
  full files are never loaded into memory.
- Chips are filtered to Bangladesh using the boundary polygon (not a bbox).
- The shipped split is **ignored**; chips are re-split by 0.25° spatial grid
  cells randomly assigned to train/val/test at 70/15/15.
- The rare source class 0 is merged into FCBK, yielding two output classes:
  FCBK (0) and Zigzag (1).

Contract
--------
>>> from src.data.convert_sentinelkilndb import convert_dataset
>>> counts = convert_dataset(dataset_dir, boundary_path, output_dir)
>>> # Writes files; returns {split: {class_name: count}}.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pyarrow.parquet as pq
from shapely.geometry import Point
from shapely.prepared import prep

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Columns we always read from the Parquet files (never the image column in
#: pass 1; added in pass 2 only).
COL_IMAGE_NAME: str = "image_name"
COL_IMAGE: str = "image"
COL_OBB: str = "yolo_obb_label"

#: Original class IDs in the Parquet data (verified against DOTA labels).
ORIGINAL_CLASSES: dict[int, str] = {0: "CFCBK", 1: "FCBK", 2: "Zigzag"}

#: Remap source class 0 and FCBK (1) → FCBK (0), Zigzag (2) → Zigzag (1).
CLASS_REMAP: dict[int, int] = {0: 0, 1: 0, 2: 1}

#: Output class names after merging the rare source type into FCBK.
OUTPUT_CLASSES: dict[int, str] = {0: "FCBK", 1: "Zigzag"}

#: The three shipped split names (also the directory names in dataset_dir).
SPLITS: tuple[str, ...] = ("train", "val", "test")

#: Filename pattern: lat_lon.png (underscore, NOT comma).
_LAT_LON_RE = re.compile(r"^(-?\d+\.\d+)_(-?\d+\.\d+)\.png$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_latlon(image_name: str) -> tuple[float, float] | None:
    """Extract ``(lat, lon)`` from a chip filename like ``'20.1249_72.7295.png'``.

    Parameters
    ----------
    image_name : str
        The ``image_name`` value from a Parquet row (basename only, though a
        full path is also accepted).

    Returns
    -------
    tuple[float, float] | None
        ``(latitude, longitude)`` in EPSG:4326, or ``None`` if the filename
        does not match the expected ``lat_lon.png`` pattern.
    """
    m = _LAT_LON_RE.match(Path(image_name).name)
    if m is None:
        return None
    return float(m.group(1)), float(m.group(2))


def grid_cell(lat: float, lon: float, cell_size: float = 0.25) -> tuple[int, int]:
    """Assign ``(lat, lon)`` to a ``(row, col)`` grid cell.

    Parameters
    ----------
    lat, lon : float
        Chip centroid coordinates in EPSG:4326.
    cell_size : float
        Grid cell size in degrees (default 0.25° ≈ 28 km at the equator).

    Returns
    -------
    tuple[int, int]
        ``(row, col)`` grid indices.
    """
    row = math.floor(lat / cell_size)
    col = math.floor(lon / cell_size)
    return row, col


def assign_splits(
    cells: list[tuple[int, int]],
    ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
    seed: int = 42,
) -> dict[tuple[int, int], str]:
    """Randomly assign unique grid cells to train/val/test splits.

    Parameters
    ----------
    cells : list[tuple[int, int]]
        Grid cells (may contain duplicates; deduplicated internally).
    ratios : tuple[float, float, float]
        Desired ``(train, val, test)`` fractions.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict[tuple[int, int], str]
        Mapping from cell → ``"train"`` / ``"val"`` / ``"test"``.
    """
    rng = np.random.default_rng(seed)
    unique = list(set(cells))
    rng.shuffle(unique)
    n = len(unique)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])

    mapping: dict[tuple[int, int], str] = {}
    for i, cell in enumerate(unique):
        if i < n_train:
            mapping[cell] = "train"
        elif i < n_train + n_val:
            mapping[cell] = "val"
        else:
            mapping[cell] = "test"
    return mapping


def remap_label_line(line: str) -> str:
    """Remap the class ID in a YOLO-OBB label line.

    Source class 0 and FCBK (1) both become output class 0 (FCBK); Zigzag (2)
    becomes output class 1 (Zigzag).  Coordinate strings are preserved
    verbatim.

    Parameters
    ----------
    line : str
        One label line: ``"<class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>"``.

    Returns
    -------
    str
        Remapped line with the new class ID as the first token.
    """
    parts = line.split()
    if not parts:
        return line
    original_id = int(parts[0])
    parts[0] = str(CLASS_REMAP.get(original_id, original_id))
    return " ".join(parts)


def _load_boundary(boundary_path: Path) -> Any:
    """Load the Bangladesh boundary GeoJSON and return a prepared geometry.

    Parameters
    ----------
    boundary_path : Path
        Path to a GeoJSON file containing polygon(s).

    Returns
    -------
    shapely.prepared.PreparedGeometry
        A prepared geometry supporting fast ``contains()`` checks.
    """
    gdf = gpd.read_file(boundary_path)
    union = gdf.union_all()
    return prep(union)


def _parquet_path(dataset_dir: Path, split: str) -> Path:
    """Return the expected Parquet path for a given split."""
    return dataset_dir / split / f"{split}.parquet"


def _write_dataset_yaml(output_dir: Path) -> None:
    """Write the Ultralytics YOLO-OBB ``dataset.yaml``."""
    lines = [
        "path: .",
        "train: train/images",
        "val: val/images",
        "test: test/images",
        "",
        "names:",
    ]
    for cls_id in sorted(OUTPUT_CLASSES):
        lines.append(f"  {cls_id}: {OUTPUT_CLASSES[cls_id]}")
    (output_dir / "dataset.yaml").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------


def _stream_boundary_cells(
    dataset_dir: Path,
    boundary_prep: Any,
    cell_size: float,
    batch_size: int,
) -> tuple[set[tuple[int, int]], dict[tuple[int, int], set[str]], int, int]:
    """First streaming pass: collect grid cells and shipped-split leakage data.

    Only the ``image_name`` column is read from each Parquet file.

    Parameters
    ----------
    dataset_dir : Path
        Root directory containing the three Parquet files.
    boundary_prep : PreparedGeometry
        Prepared Bangladesh boundary for fast point-in-polygon tests.
    cell_size : float
        Grid cell size in degrees.

    Returns
    -------
    cells : set[tuple[int, int]]
        All unique grid cells that contain at least one Bangladesh chip.
    cell_shipped_splits : dict[cell, set[str]]
        For each cell, the set of *shipped* splits whose chips fall in it.
        Used to compute the leakage report.
    total_bd : int
        Total number of Bangladesh chips.
    total_all : int
        Total number of chips across all files.
    """
    cells: set[tuple[int, int]] = set()
    cell_shipped_splits: dict[tuple[int, int], set[str]] = {}
    total_bd = 0
    total_all = 0

    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.exists():
            continue
        pf = pq.ParquetFile(pq_path)
        for batch in pf.iter_batches(
            batch_size=batch_size, columns=[COL_IMAGE_NAME]
        ):
            names = batch.to_pydict()[COL_IMAGE_NAME]
            for name in names:
                total_all += 1
                parsed = parse_latlon(name)
                if parsed is None:
                    continue
                lat, lon = parsed
                if not boundary_prep.contains(Point(lon, lat)):
                    continue
                total_bd += 1
                cell = grid_cell(lat, lon, cell_size)
                cells.add(cell)
                cell_shipped_splits.setdefault(cell, set()).add(split)

    return cells, cell_shipped_splits, total_bd, total_all


def _write_chips(
    dataset_dir: Path,
    output_dir: Path,
    boundary_prep: Any,
    cell_split: dict[tuple[int, int], str],
    cell_size: float,
    counts: dict[str, dict[str, int]],
    keep_names: set[str] | None = None,
    batch_size: int = 4096,
) -> tuple[int, int]:
    """Second streaming pass: write PNG + label files for Bangladesh chips.

    Reads ``image_name``, ``image``, and ``yolo_obb_label`` from each Parquet
    file in batches, filters to Bangladesh, and writes output files.

    Parameters
    ----------
    dataset_dir : Path
        Root directory containing the three Parquet files.
    output_dir : Path
        Target YOLO directory tree.
    boundary_prep : PreparedGeometry
        Prepared Bangladesh boundary.
    cell_split : dict[cell, str]
        Mapping from grid cell to output split name.
    cell_size : float
        Grid cell size in degrees.
    counts : dict
        Mutable counts dict to populate: ``{split: {class_name: n}}``.

    Returns
    -------
    tuple[int, int]
        ``(chips_written, labels_written)``.
    """
    chips_written = 0
    labels_written = 0

    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.exists():
            continue
        pf = pq.ParquetFile(pq_path)
        for batch in pf.iter_batches(
            batch_size=batch_size,
            columns=[COL_IMAGE_NAME, COL_IMAGE, COL_OBB],
        ):
            name_col = batch.column(batch.schema.get_field_index(COL_IMAGE_NAME))
            image_col = batch.column(batch.schema.get_field_index(COL_IMAGE))
            label_col = batch.column(batch.schema.get_field_index(COL_OBB))

            for name_value, image_value, label_value in zip(name_col, image_col, label_col):
                name = name_value.as_py()
                img_bytes = image_value.as_py()
                obb = label_value.as_py()
                parsed = parse_latlon(name)
                if parsed is None:
                    continue
                if keep_names is not None and name not in keep_names:
                    continue
                lat, lon = parsed
                if not boundary_prep.contains(Point(lon, lat)):
                    continue

                cell = grid_cell(lat, lon, cell_size)
                out_split = cell_split[cell]

                img_dir = output_dir / out_split / "images"
                lbl_dir = output_dir / out_split / "labels"
                img_dir.mkdir(parents=True, exist_ok=True)
                lbl_dir.mkdir(parents=True, exist_ok=True)

                dst_img = img_dir / name
                dst_img.write_bytes(img_bytes)
                chips_written += 1

                dst_lbl = lbl_dir / (Path(name).stem + ".txt")
                remapped: list[str] = []
                for line in (obb or []):
                    if not line:
                        continue
                    remapped_line = remap_label_line(line)
                    remapped.append(remapped_line)
                    new_cls = int(remapped_line.split()[0])
                    cls_name = OUTPUT_CLASSES.get(new_cls, f"unknown_{new_cls}")
                    counts[out_split][cls_name] = (
                        counts[out_split].get(cls_name, 0) + 1
                    )
                    labels_written += 1

                dst_lbl.write_text(
                    "\n".join(remapped) + ("\n" if remapped else "")
                )

    return chips_written, labels_written


def _compute_leakage(
    cell_shipped_splits: dict[tuple[int, int], set[str]],
    cells: set[tuple[int, int]],
) -> dict[str, Any]:
    """Compute the shipped-split leakage report.

    A grid cell is "contaminated" if chips in it came from more than one
    shipped split (train/val/test Parquet file).  Because the shipped split
    is class-stratified (not spatial), adjacent chips can appear in different
    splits — a data-leakage risk.

    Parameters
    ----------
    cell_shipped_splits : dict[cell, set[str]]
        Shipped splits per cell.
    cells : set[tuple[int, int]]
        All Bangladesh grid cells.

    Returns
    -------
    dict
        Leakage metrics.
    """
    contaminated = [
        cell for cell, splits in cell_shipped_splits.items() if len(splits) > 1
    ]
    n_contaminated = len(contaminated)
    n_total = len(cells)
    pct = (n_contaminated / n_total * 100) if n_total else 0.0

    risk = "HIGH" if pct > 50 else ("MEDIUM" if pct > 10 else "LOW")

    return {
        "method": (
            "Per 0.25° grid cell: a cell is 'contaminated' if chips in it "
            "span more than one shipped split (train/val/test parquet file)."
        ),
        "contaminated_cells": n_contaminated,
        "total_cells": n_total,
        "contaminated_pct": round(pct, 2),
        "risk": risk,
        "explanation": (
            "The shipped split is class-wise stratified, not spatially blocked. "
            "With 30-pixel (300 m) overlap between adjacent patches, chips "
            "viewing the same kiln can land in different splits, causing "
            "train/test leakage. The spatial-block re-split eliminates this."
        ),
        "shipped_split_strategy": "class-wise stratified",
        "chip_overlap_px": 30,
        "chip_overlap_m": 300,
    }


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------


def convert_dataset(
    dataset_dir: Path,
    boundary_path: Path,
    output_dir: Path,
    cell_size: float = 0.25,
    seed: int = 42,
    batch_size: int = 4096,
    ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
) -> dict[str, dict[str, int]]:
    """Convert SentinelKilnDB Parquet files to a spatial-block-split YOLO-OBB dataset.

    Reads three Parquet files (``train/train.parquet``, ``val/val.parquet``,
    ``test/test.parquet``) inside ``dataset_dir`` in streaming batches,
    filters chips to Bangladesh using the boundary polygon, merges the rare source type into
    FCBK, re-splits by 0.25° spatial blocks, and writes PNG images, YOLO-OBB
    label files, ``dataset.yaml``, and ``split_report.json`` to ``output_dir``.

    Parameters
    ----------
    dataset_dir : Path
        Root of the raw SentinelKilnDB download (contains ``train/``,
        ``val/``, ``test/`` sub-directories with ``.parquet`` files).
    boundary_path : Path
        GeoJSON of the Bangladesh boundary polygon.
    output_dir : Path
        Target directory for the converted YOLO-OBB dataset.
    cell_size : float
        Grid cell size in degrees for spatial blocking (default 0.25°).
    seed : int
        Random seed for split assignment.
    batch_size : int
        Number of rows per ``iter_batches`` call (never loads a full file).
    ratios : tuple[float, float, float]
        Desired ``(train, val, test)`` fractions.

    Returns
    -------
    dict[str, dict[str, int]]
        Nested dict ``{split: {class_name: count}}`` for the output classes.
    """
    from rich import print as rprint

    boundary_prep = _load_boundary(boundary_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        for kind in ("images", "labels"):
            split_dir = output_dir / split / kind
            if split_dir.exists():
                shutil.rmtree(split_dir)
            split_dir.mkdir(parents=True, exist_ok=True)

    # --- Pass 1: discover Bangladesh cells + shipped-split leakage ---------
    rprint("[cyan]Pass 1: scanning Parquet files for Bangladesh chips ...[/cyan]")
    cells, cell_shipped_splits, total_bd, total_all = _stream_boundary_cells(
        dataset_dir, boundary_prep, cell_size, batch_size
    )
    rprint(
        f"  {total_bd} of {total_all} chips inside Bangladesh "
        f"({len(cells)} unique {cell_size} degree grid cells)."
    )

    leakage = _compute_leakage(cell_shipped_splits, cells)
    rprint(
        f"  Shipped-split leakage: {leakage['contaminated_cells']} / "
        f"{leakage['total_cells']} cells contaminated "
        f"({leakage['contaminated_pct']}%) - risk: {leakage['risk']}"
    )

    # --- Assign output splits to cells ---------------------------------------
    cell_split = assign_splits(
        list(cells), ratios=ratios, seed=seed
    )

    # Collect centre metadata only, then remove cross-split neighbours from val/test.
    from src.eval.check_leakage import (
        DEFAULT_THRESHOLD_M,
        dropped_counts_by_split,
        filter_cross_split_leakage,
    )

    centre_records: list[dict[str, Any]] = []
    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.exists():
            continue
        pf = pq.ParquetFile(pq_path)
        for batch in pf.iter_batches(batch_size=batch_size, columns=[COL_IMAGE_NAME]):
            for name in batch.to_pydict()[COL_IMAGE_NAME]:
                parsed = parse_latlon(name)
                if parsed is None:
                    continue
                lat, lon = parsed
                if boundary_prep.contains(Point(lon, lat)):
                    centre_records.append({
                        "image_name": name,
                        "latitude": lat,
                        "longitude": lon,
                        "split": cell_split[grid_cell(lat, lon, cell_size)],
                    })
    keep_names, dropped_names, min_cross_split_m = filter_cross_split_leakage(centre_records)
    dropped_per_split = dropped_counts_by_split(centre_records, dropped_names)
    rprint(
        f"  Leakage filter dropped {len(dropped_names)} val/test chips within "
        f"{DEFAULT_THRESHOLD_M:g} m Chebyshev (EPSG:9680): {dropped_per_split}"
    )
    rprint(
        "  Final minimum cross-split Chebyshev distance: "
        f"{min_cross_split_m if min_cross_split_m is not None else 'N/A'} m"
    )

    # --- Pass 2: write PNG + label files ------------------------------------
    rprint("[cyan]Pass 2: writing PNG and YOLO-OBB label files ...[/cyan]")
    counts: dict[str, dict[str, int]] = {
        s: {c: 0 for c in OUTPUT_CLASSES.values()} for s in SPLITS
    }
    chips_written, labels_written = _write_chips(
        dataset_dir, output_dir, boundary_prep, cell_split, cell_size, counts,
        keep_names, batch_size,
    )
    rprint(
        f"  Wrote {chips_written} images and {labels_written} label lines."
    )

    # --- Write dataset.yaml --------------------------------------------------
    _write_dataset_yaml(output_dir)
    rprint(f"[green]dataset.yaml written to {output_dir / 'dataset.yaml'}[/green]")

    # --- Write split_report.json --------------------------------------------
    report: dict[str, Any] = {
        "dataset": "SentinelKilnDB",
        "license": "CC BY-NC 4.0",
        "cell_size_deg": cell_size,
        "seed": seed,
        "ratios": {"train": ratios[0], "val": ratios[1], "test": ratios[2]},
        "merge_rare_source_class_into_fcbk": True,
        "original_classes": ORIGINAL_CLASSES,
        "output_classes": OUTPUT_CLASSES,
        "chips_inside_bangladesh": total_bd,
        "chips_total": total_all,
        "chips_written": chips_written,
        "leakage_filter_metric": "Chebyshev (L-inf) between chip centres, EPSG:9680",
        "leakage_filter_threshold_m": DEFAULT_THRESHOLD_M,
        "leakage_filter_dropped_val_test": len(dropped_names),
        "leakage_filter_dropped_per_split": dropped_per_split,
        "minimum_cross_split_distance_m": min_cross_split_m,
        "label_lines_written": labels_written,
        "counts_per_split_per_class": counts,
        "shipped_split_leakage": leakage,
        "shipped_split_strategy": "class-wise stratified (ignored, re-split spatially)",
    }
    report_path = output_dir / "split_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    rprint(f"[green]split_report.json written to {report_path}[/green]")
    rprint(f"  Counts: {counts}")

    return counts


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    from pathlib import Path as P

    convert_dataset(
        dataset_dir=P("data/raw/sentinelkilndb"),
        boundary_path=P("data/raw/bangladesh_boundary.geojson"),
        output_dir=P("data/interim/yolo_obb"),
    )
