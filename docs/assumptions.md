# Assumptions — SentinelKilnDB Conversion

This document records every assumption made in the existing converter
(`src/data/convert_sentinelkilndb.py`), the explore command (`src/cli.py`), and
the standalone exploration scripts (`explore_parquet.py`, `explore_labels.py`)
that **contradicts the actual on-disk dataset**.  Each item lists what the old
code assumed, what the data actually is, and how the code was fixed.

## Verified facts about the dataset

The dataset ships as three Parquet files, one row group each:

| File                                      | Rows   |
|-------------------------------------------|--------|
| `data/raw/sentinelkilndb/train/train.parquet` | 71 856 |
| `data/raw/sentinelkilndb/val/val.parquet`     | 23 952 |
| `data/raw/sentinelkilndb/test/test.parquet`   | 18 492 |
| **Total**                                     | 114 300 |

Each row has exactly five columns:

| Column          | Arrow type          | Description                                              |
|-----------------|---------------------|----------------------------------------------------------|
| `image_name`    | string              | `lat_lon.png` — lat/lon joined by an **underscore**       |
| `image`         | binary              | Raw PNG bytes, 128×128 px, 8-bit RGB                     |
| `dota_label`    | list&lt;string&gt;    | DOTA-format lines (empty list = negative chip)            |
| `yolo_aa_label` | list&lt;string&gt;    | YOLO-AABB lines (empty list = negative chip)             |
| `yolo_obb_label`| list&lt;string&gt;    | YOLO-OBB lines (empty list = negative chip)               |

### Label format (verified, NOT ambiguous)

Each entry in `yolo_obb_label` is a **single string** that is one label line:

```
<class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>
```

- All nine tokens are **space-separated**.
- `<class_id>` is an **integer**, not a class name.
- Coordinates are **normalised** to [0, 1] (chip is 128 px).
- Class-ID → name mapping, cross-validated against `dota_label`:

| Class ID | Name  | Count (bboxes) |
|----------|-------|-----------------|
| 0        | rare source class | 3 030           |
| 1        | FCBK  | 52 654          |
| 2        | Zigzag| 41 964          |
| **Total**|       | **97 648**      |

- `yolo_aa_label` lines: `<class_id> <xc> <yc> <w> <h>` (normalised, space-separated).
- `dota_label` lines: `x1 y1 x2 y2 x3 y3 x4 y4 <class_name> <difficult>` (pixel coords).
- All three columns are **consistent**: every row that has ≥ 1 OBB box also has 1
  AA box and 1 DOTA entry; rows with `[]` in all three are negative chips
  (41 070 negative / 73 230 positive).

**Conclusion on ambiguity:** the label format is **not ambiguous** once the actual
Parquet data is inspected.  The *README* documentation is misleading (see
contradictions below), but the data itself is internally consistent.

---

## Contradictions between code assumptions and the real dataset

### C1 — Filename delimiter: comma vs underscore

| | Assumed by old code | Actual data |
|---|---|---|
| `README.md` (line 39) | `lat,lon.png` (comma) | `lat_lon.png` (underscore) |
| `convert_sentinelkilndb.py` `_parse_latlon_from_filename` | `stem.split(",")` (comma) | underscore |
| `explore_labels.py` | regex with `_` (underscore) | underscore ✓ (already correct) |

**Fix:** the parser now uses the regex `^(-?\d+\.\d+)_(-?\d+\.\d+)\.png$` —
underscore only, matching the real `image_name` values (e.g. `20.1249_72.7295.png`).

### C2 — Data layout: directory tree vs single Parquet file

| | Assumed by old code | Actual data |
|---|---|---|
| `README.md` (lines 83-94) | `dataset/{train,val,test}/{images,labels}/` directories with separate `.png` / `.txt` files | Single Parquet file per split: `{split}/{split}.parquet` |
| `convert_sentinelkilndb.py` | `dataset_dir.rglob("*.png")` to enumerate images | No PNG files on disk; bytes are in the `image` column |
| `explore` CLI command | `dataset_dir.rglob("*")` walking a filesystem tree | Must read Parquet files |

**Fix:** the converter discovers three Parquet files at
`dataset_dir/{train,val,test}/{split}.parquet` and reads them via
`pyarrow.parquet.ParquetFile.iter_batches()` (streaming, never loading a full
file).

### C3 — Label source: on-disk `.txt` files vs Parquet list columns

| | Assumed by old code | Actual data |
|---|---|---|
| `README.md` (lines 83-94, 140-151) | Separate `.txt` label files per chip | Labels are `list<string>` columns inside Parquet |
| `convert_sentinelkilndb.py` | `label_path = img_path.with_suffix(".txt"); label_path.read_text()` | Labels are in the `yolo_obb_label` column of the Parquet batch |

**Fix:** labels are read from the `yolo_obb_label` column of each batch and
written to `.txt` files in the output directory.

### C4 — Label class field: class name vs integer ID

| | Assumed by old code / README | Actual data |
|---|---|---|
| `README.md` (line 55) | `class_name, x1, y1, …` (string like `FCBK`) | `0`, `1`, `2` (integer) |
| `convert_sentinelkilndb.py` | `int(line.split()[0])` — expects integer | integer ✓ (code was coincidentally correct) |

**Fix:** the converter reads `int(parts[0])` from each label string, which
matches the actual integer class IDs.  No change needed here, but the README
description is incorrect.

### C5 — Label delimiter: comma vs whitespace

| | Assumed by old code / README | Actual data |
|---|---|---|
| `README.md` (line 55) | `class_name, x1, y1, …` (looks comma-separated) | space-separated: `1 0.665175 0.547922 …` |

**Fix:** the converter splits on whitespace (`line.split()`), matching the actual
format.  This was already correct in the old code.

### C6 — Image storage: PNG files vs raw bytes in Parquet

| | Assumed by old code | Actual data |
|---|---|---|
| `README.md` (lines 98-126) | `.png` files written to disk by a separate extraction step | PNG bytes stored as `binary` in the `image` column |

**Fix:** the converter extracts `image` bytes from each batch and writes them
directly to `.png` files in the output directory (no decode/re-encode).

### C7 — Shipped split: class-wise stratified vs arbitrary Parquet partitions

| | Assumed by old code / README | Actual data |
|---|---|---|
| `README.md` (line 72) | "class-wise stratified" split — implies class balance across splits | Three unrelated Parquet files; split assignment is arbitrary (by file) |
| `convert_sentinelkilndb.py` | Ignores shipped split entirely (reads all `*.png`) | Must discover that the shipped split is in the filename of the Parquet file itself |

**Fix:** the converter ignores the shipped split (the parquet file a row comes
from) for output assignment, and instead re-splits by spatial blocks.  The
shipped split is still recorded during the first streaming pass to compute a
**leakage report** (see C8).

### C8 — Split strategy: class-stratified vs spatial-block

| | Assumed by old code | Actual data + task requirement |
|---|---|---|
| `README.md` (line 72) | Class-wise stratified (random within class) | Task requires: **ignore shipped split, re-split by 0.25° spatial blocks** at 70/15/15 |
| `convert_sentinelkilndb.py` | Already re-splits by grid cells — ✓ | Retained + improved |

**Leakage risk in the shipped split:** because the shipped split is
class-stratified (random assignment by class, not spatial), chips that are
spatially adjacent — and with 30-pixel (300 m) overlap between patches — can
easily land in different splits (e.g. the same kiln appearing in both train and
test).  The converter now reports, per 0.25° grid cell, how many cells contain
chips from more than one shipped split, as a quantitative leakage indicator.

### C9 — Class merging: rare source class kept separate vs merged into FCBK

| | Assumed by old code / README | Task requirement |
|---|---|---|
| `README.md` (lines 43-47) | Three classes: rare source class, FCBK, Zigzag | **Merge rare source class into FCBK** (rare source class has only 2 Bangladesh records; severe imbalance) |
| `convert_sentinelkilndb.py` | `CLASS_NAMES = {0: rare source class, 1: FCBK, 2: Zigzag}` — three output classes | Must produce two output classes: FCBK (0), Zigzag (1) |

**Fix:** class 0 (rare source class) and class 1 (FCBK) are both remapped to output class
0 (FCBK); class 2 (Zigzag) → output class 1 (Zigzag).

### C10 — Boundary filter: bounding box vs polygon

| | Assumed by old code / explore scripts | Task requirement |
|---|---|---|
| `explore_labels.py` (line 17) | `df.lat.between(20.5, 26.7) & df.lon.between(88.0, 92.7)` — a rough **bbox** | Must use `data/raw/bangladesh_boundary.geojson` polygon (not a bbox) |
| `convert_sentinelkilndb.py` | `_chip_in_boundary` — uses boundary polygon ✓ | Retained, now also used by the explore command |

**Fix:** all Bangladesh filtering uses the boundary polygon from
`bangladesh_boundary.geojson` loaded via `geopandas` and tested with a prepared
Shapely geometry.  The bbox approach in `explore_labels.py` was removed.

### C11 — Memory: full file load vs streaming batches

| | Assumed by old code | Task requirement |
|---|---|---|
| `explore_parquet.py` (line 9) | `next(pf.iter_batches(batch_size=5))` — only samples | Must stream all rows in batches, never `pq.read_table()` (full load) |
| `explore_labels.py` (lines 5-10) | `pq.read_table(...).to_pandas()` — loads 72 K rows into a pandas DataFrame | Must use `iter_batches` |

**Fix:** both the converter and the explore command use
`ParquetFile.iter_batches(batch_size=N, columns=[...])` to process rows in
fixed-size batches and never materialise the full file.

### C12 — Boundary file existence

The file `data/raw/bangladesh_boundary.geojson` does **not** currently exist in
the repository.  It is listed as a manual step in the scaffold
(`kilnwatch_scaffold.md`) — the user must download it (e.g. from GADM or
geoBoundaries).  The converter asserts its existence and raises a clear error if
it is missing.  Tests provide a synthetic boundary GeoJSON.

### C13 — Cross-split leakage filter: Euclidean 400 m vs Chebyshev 1300 m

| | Assumed by old code | Chip geometry |
|---|---|---|
| `src/eval/check_leakage.py` | Drop val/test chips whose nearest other-split centre is within 400 m (Euclidean) | Chips are 128 px at 10 m = 1.28 km square, so two chips overlap when \|dx\| < 1280 m **and** \|dy\| < 1280 m, i.e. Chebyshev distance < 1280 m |

**Fix:** the filter uses `cKDTree(...).query(p=inf)` on EPSG:9680 coordinates with a
default threshold of 1300 m (1280 m plus a 20 m margin). Val/test chips within the
threshold of a chip in a different split are dropped; train chips never are. A close
val/test pair loses both members. `split_report.json` records the metric, threshold,
dropped counts per split and the final minimum cross-split Chebyshev distance. The
1300 m threshold assumes chips are axis-aligned in EPSG:9680; TM 90 NE grid north
differs slightly from the chip grid, which the 20 m margin is meant to absorb (unverified).
