# KilnWatch BD progress and verification

**Checked:** 2026-09-29. This document tracks the implementation against
[`kilnwatch_scaffold.md`](../kilnwatch_scaffold.md) and the later project requests.

## Assessment

The prototype is on track for its local pipeline, but it is not ready for an
end-to-end result or a legal compliance claim. The largest changes since the
original scaffold are the trained-model plan (smoke test, three YOLOv8n image
sizes, then YOLOv8s at the selected size), tile-level SentinelKilnDB
normalization, a confidence-weighted exposure formula, and a 1,300 m
Chebyshev leakage filter. The old prompts below are historical where they
conflict with those decisions.

## Verified locally

- Dataset conversion was rerun from the local three-split Parquet dataset into
  `data/interim/yolo_obb/`. The current `split_report.json` records 11,517
  Bangladesh chips before leakage removal and 11,250 written chips after it.
- Current per-class counts: train FCBK 1,773 / Zigzag 5,589; val FCBK 214 /
  Zigzag 1,803; test FCBK 246 / Zigzag 1,025.
- Leakage filtering dropped 141 val and 126 test chips, dropped no train chips,
  and reports a final minimum cross-split Chebyshev distance of 1,322.41 m in
  EPSG:9680. This clears the configured 1,300 m threshold.
- The dataset ZIP contains 8,058 training PNGs at 128x128. Their pooled RGB
  medians are 51/71/57, p99 values are 191/191/184, maximum pixel value is 254,
  and the count of pixels equal to 255 is zero. These observed values differ
  somewhat from the earlier estimate of 53/72/58 and p99 about 195.
- Configured AOIs resolve to one ADM2 polygon each: Chapainawabganj maps to the
  boundary file's `Nawabganj` name, and Gazipur maps to `Gazipur`. OSM queries
  now use the polygon extent and clip returned features to the district polygon.
- Synthetic tests cover normalization, inference channel order and `imgsz`,
  priority component weights, the rules-to-priority-to-dashboard-loader path,
  district clipping, and unverified preprocessing refusal.
- Memory/network review: inference streams raster windows, conversion honors a
  tunable Parquet batch size, OSM fetches reuse a complete local cache unless
  `--refresh` is supplied, and Folium maps no longer fetch remote background
  tiles. See [`docs/MEMORY_AND_DOWNLOADS.md`](MEMORY_AND_DOWNLOADS.md); actual
  full-data RAM/VRAM benchmarks remain unmeasured.
- Training start readiness is documented in
  [`docs/TRAINING_READINESS.md`](TRAINING_READINESS.md): converted splits are
  present locally (about 351 MiB), but a hosted CUDA runtime and reachable
  dataset path must be prepared before the smoke test. The notebook rejects
  CPU-only runtime setup and checks Ultralytics is at least version 8.1.
- Installed `.[dev,geo,detect,ee,app]` into the workspace `.venv`. The
  environment is Python 3.12.10 (the project targets Python 3.11), with
  Earth Engine, rasterio, and Ultralytics dependencies now present. Latest run:
  82 pytest tests pass; `ruff check .` passes.
- The workspace has no `.git` directory, so repository history, the complete
  working-tree diff, and the earlier requested baseline commit cannot be
  verified from this checkout.

## Implemented but awaiting external or human validation

- `notebooks/train.ipynb` contains the smoke test and requested staged model
  selection. It has not been run on Colab/Kaggle GPU; no weights or model
  metrics are verified.
- `config/preprocessing.yaml`, `src/data/export_s2.py`,
  `src/data/normalize.py`, and `tools/calibrate_preprocessing.py` implement the
  recorded repository recipe. `preprocessing_verified` intentionally remains
  false, so Earth Engine export is blocked until the date discrepancy below is
  resolved. No paired exported chips are available, so real chip-difference
  calibration and a divisor estimate have not been produced.
- `src/detect/infer.py` has synthetic tests, but has not been run against a
  trained checkpoint and exported GeoTIFFs. Detection placement, raster CRS,
  and cross-tile duplicate removal still need a visual spot-check.
- `config/rules.yaml` values remain unverified. The legal caveat and forest/hill
  note are informational; do not treat imagery flags as findings. No legal
  threshold is verified by this project.
- OSM clipping is covered by a synthetic geometry test, but the downloaded
  layer coverage has not been checked against imagery. Railways and optional
  HDX/WDPA forest data are not implemented yet.
- `src/eval/audit_sample.py` samples confidence terciles. It does not yet create
  the requested 15 samples from negative regions. The Chapainawabganj 2022
  reported-count comparison and Gazipur closed-kiln CSV/check are also pending.
- `docs/legal_basis.md` and `docs/RUNBOOK.md` are absent. The legal-source
  extraction and exact ordered operator commands should be added before a
  handoff/demo.

## SentinelKilnDB date evidence: unresolved

The currently published sources do not identify one consistent acquisition
period:

| Source | Reported date |
|---|---|
| Current authors' downloader code | `filterDate('2024-01-01', '2025-02-28')`; Earth Engine treats the end as exclusive |
| Authors' GitHub README | September 2023-February 2024 |
| NeurIPS 2025 paper supplement | September 2023-February 2024 |
| Hugging Face dataset card | November 2023-February 2024 |

The YAML currently records the downloader's literal filter because that is the
only exact executable recipe. It does **not** prove which dates produced the
released training chips. Keep `preprocessing_verified: false` until the authors'
intended date range is confirmed and the choice is recorded.

Sources checked on 2026-09-29:

- [Authors' downloader, current main branch](https://github.com/rishabh-mondal/SENTINELKILNDB_NeurIPS_2025/blob/main/data_scripts/sentinel_tile_bulk_download.py)
- [Authors' repository README](https://github.com/rishabh-mondal/SENTINELKILNDB_NeurIPS_2025)
- [NeurIPS 2025 paper supplement](https://papers.nips.cc/paper_files/paper/2025/file/9ab8bb568825d49ce31aa87b7e2f4ad7-Supplemental-Datasets_and_Benchmarks_Track.pdf)
- [Hugging Face dataset card](https://huggingface.co/datasets/SustainabilityLabIITGN/SentinelKilnDB)

## Next verification steps

1. Confirm the intended acquisition date range with the dataset authors; keep
   preprocessing locked until then.
2. After that confirmation, update the YAML source note and have a human set
   `preprocessing_verified: true`; authenticate Earth Engine and export a small
   pilot first.
3. Pair exported RGB chips with their same-named training PNGs and run:

   ```powershell
   .\.venv\Scripts\python.exe tools\calibrate_preprocessing.py <exported-chip-dir> <training-png-dir>
   ```

4. Run the notebook on a GPU, use the resulting `best.pt` and matching training
   `imgsz`, then spot-check raster alignment and detections.
5. Finish the missing validation utilities, legal basis, and runbook before the
   demo. Review the unverified rules and OSM data coverage by hand.
