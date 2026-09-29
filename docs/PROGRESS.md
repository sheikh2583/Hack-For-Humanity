# KilnWatch BD progress and verification

**Checked:** 2026-09-29. This document tracks the implementation against
[`kilnwatch_scaffold.md`](../kilnwatch_scaffold.md) and the later project requests.
For the machine-run evidence and planned Linux overnight run, see
[`TRAINING_RUN_HISTORY.md`](TRAINING_RUN_HISTORY.md).

Cross-platform initialization scripts, shared CUDA 13.0 pins, a shared
Linux/Windows training runner, and ten-epoch Git-staged metric archives have
since been added. These changes were reviewed by code inspection and static
syntax/CLI checks only; the training setup has not been run on the Linux RTX
3090 host, and the new synthetic tests have not been executed.

## Assessment

The prototype is on track for its local pipeline, but it is not ready for an
end-to-end result or a legal compliance claim. The largest changes since the
original scaffold are the trained-model plan (smoke test, three YOLOv8n image
sizes, then YOLOv8s at the selected size), tile-level SentinelKilnDB
normalization, a confidence-weighted exposure formula, and a 1,300 m
Chebyshev leakage filter. The old prompts below are historical where they
conflict with those decisions.

## Verified locally

- The raw SentinelKilnDB Parquet files are present and readable: train 71,856
  rows, val 23,952 rows, and test 18,492 rows. Their byte sizes match the
  published Hugging Face manifest.
- The converted YOLO-OBB dataset is present at `data/interim/yolo_obb/`:
  train 8,058, val 1,662, and test 1,530 image/label pairs. Ultralytics accepts
  its dataset YAML when its root is set to the resolved dataset directory; all
  label lines passed a class, eight-coordinate, and normalized-range audit.
  The split report records the 1,300 m Chebyshev filter and 1,322.41 m minimum
  cross-split distance.
- The root `yolo_obb_bd.zip` is an older converted dataset bundle. Its report
  lacks the 1,300 m leakage-filter threshold and must not be used for training;
  the initializer rejects it. Use the checked `data/interim/yolo_obb/` data or
  create a new transfer archive from that directory.
- The pretrained starting weights `data/models/yolov8n-obb.pt` and
  `data/models/yolov8s-obb.pt` load as Ultralytics OBB models. An interrupted
  YOLOv8n checkpoint exists under ignored `runs/yolov8n-obb-256/weights/`;
  it has not been evaluated on the held-out test split and is not a final
  model.
- Both boundary files are present. The ADM2 file has 64 valid EPSG:4326
  features, a `shapeName` field, and includes `Nawabganj` and `Gazipur`. The
  country boundary is one valid EPSG:4326 feature. Their provenance, licence,
  and human review have not been verified. Earth Engine exports, OSM caches,
  and processed detections are not present.
- The implementation has synthetic coverage for normalization, inference
  channel order and `imgsz`, priority component weights, the rules-to-priority
  path, district clipping, and refusal while preprocessing is unverified.
- Synthetic tests cover normalization, inference channel order and `imgsz`,
  priority component weights, the rules-to-priority-to-dashboard-loader path,
  district clipping, and unverified preprocessing refusal.
- Memory/network review: inference streams raster windows, conversion honors a
  tunable Parquet batch size, OSM fetches reuse a complete local cache unless
  `--refresh` is supplied, and Folium maps no longer fetch remote background
  tiles. See [`docs/MEMORY_AND_DOWNLOADS.md`](MEMORY_AND_DOWNLOADS.md); actual
  full-data RAM/VRAM benchmarks remain unmeasured.
- Training start readiness is documented in
  [`docs/TRAINING_READINESS.md`](TRAINING_READINESS.md): the converted data and
  starting weights are ready. The Windows `.venv` has CUDA-enabled PyTorch.
  Its RTX 4070 smoke run completed 3 epochs. The full YOLOv8n 256px stage has
  six completed validation rows and the console capture shows interruption
  during epoch 7; later stages and test evaluation did not run. The Linux RTX
  3090 overnight run is planned but has not started. See the run history for
  recorded metrics, artifacts, and handoff steps. The user manages GPU
  workloads; agents must not touch the GPU unless explicitly asked.
- The Windows development machine has an NVIDIA GeForce RTX 4070 (8 GB). The active `.venv` is
  Python 3.12.10 with Ultralytics 8.4.165. Ruff passes for `src`, `app`, `tests`,
  and `tools`; all 82 tests passed after the CUDA package change. Partial
  training output is under ignored `runs/`; final test-split metrics are not yet
  available.
- `scripts/init_linux.sh` and `scripts/init_windows.ps1` share
  `requirements-gpu-cu130.txt`; the Linux RTX 3090 host and its NVIDIA driver
  have not been inspected. `scripts/prepare_training_assets.py` uses a pinned
  SentinelKilnDB revision and checks file digests, but requires either a
  current converted dataset archive or a user-reviewed boundary before
  raw-data conversion. The stale root dataset ZIP is intentionally rejected.
- `src/training/run_store.py`, `src/training/engine.py`, and
  `src/training/runner.py` separate run identity/configuration, Ultralytics
  execution/logging, and workflow coordination. Each run is numbered under
  `results/run_NNNN/`; manifests record the host/GPU used per stage, checkpoints
  are ignored, and epoch CSV archives are Git-staged every 10 epochs.
- `docs/TRAINING_RUN_HISTORY.md` records the completed Windows smoke run, the
  interrupted full-stage evidence, and the planned new Linux run. The Linux run
  remains explicitly unstarted until the user launches it.
- Git metadata and an upstream tracking branch are present. A separate nested
  `Hack-For-Humanity/` copy is ignored and remains outside the active project.
- Git metadata is present in this checkout, but no history review was needed
  for the changes recorded here.

## Implemented but awaiting external or human validation

- `notebooks/train.ipynb` delegates smoke and staged model selection to the
  canonical script runner. The historical partial validation metrics are in
  `runs/yolov8n-obb-256/results.csv`; no final held-out evaluation exists.
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
- `docs/legal_basis.md` and `docs/RUNBOOK.md` now record the evidence fields,
  operator commands, and human-only gates. They do not verify legal claims or
  external services.

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

4. Run the cross-platform training runner on a GPU, use the resulting `best.pt`
   and matching training `imgsz`, then spot-check raster alignment/detections.
5. Finish the missing validation utilities, legal basis, and runbook before the
   demo. Review the unverified rules and OSM data coverage by hand.
