# KilnWatch BD progress and verification

**Updated:** 2026-10-08. This document tracks implementation against
[`kilnwatch_scaffold.md`](../kilnwatch_scaffold.md) and later project requests.
Linux training run `run_0002` completed; see
[`TRAINING_RUN_HISTORY.md`](TRAINING_RUN_HISTORY.md) for stage metrics and
artifacts. The pre-run snapshot below is explicitly marked historical.

Cross-platform initialization scripts, shared CUDA 13.0 pins, a shared
Linux/Windows training runner, and ten-epoch Git-staged metric archives have
since been added. The Linux RTX 3090 runner was exercised in `run_0002`.
The latest full Windows environment check on 2026-10-08 reported 151 tests
passed and Ruff clean. The runbook records the exact check and warning summary.

## Update 2026-10-08: pipeline work and training evidence audit

- No new model training run is recorded for 2026-10-08. The latest training is
  Linux RTX 3090 `run_0002`, completed 2026-10-07. The October 8 local work was
  inference, OSM extraction, rule checking, scoring, visualization, and docs.
- `run_0002/run.json` labels every smoke, training, and held-out test stage with
  host/platform, GPU, runtime, requested device, and timestamps. Its dataset
  fingerprint, stage outcomes, and selected model are recorded. Metric CSV
  chunks, the manifest, training configuration/source, and summary are
  Git-tracked.
- The historical Windows RTX 4070 smoke/full attempt is described in
  [`TRAINING_RUN_HISTORY.md`](TRAINING_RUN_HISTORY.md). Recovered arguments,
  raw metric CSVs, and console output are copied to
  `results/legacy_windows_rtx4070_20260929/`; the original `runs/` remains
  ignored. It has no original manifest or dataset fingerprint.
- The shared staged method is in `config/training.yaml` and the training
  runner: smoke, YOLOv8n at 256/384/512, then YOLOv8s at the best YOLOv8n
  image size, followed by one held-out test evaluation. `run_0002/training_config.yaml`
  and its hash were added retrospectively from the Git commit that contains
  the run manifest. That commit postdates the final training event, so the
  exact runtime source revision is still unknown. The manifest now records
  this limitation explicitly.
- `run.json` contains held-out metrics. The separate `test_metrics.json` is
  absent from this checkout; checkpoints remain intentionally ignored by Git.
  The matching data and checkpoints must be retained separately for a
  reproducible rerun.
- The recovered Windows records, manifest update, and documentation were
  committed locally in `0a822d1` (`Record per-machine training evidence`). No
  training or Earth Engine call was made for that evidence repair.
- Added `tools/date_forensics.py` and `docs/DATE_FORENSICS.md` as a future,
  author-independent diagnostic. It was not run; it does not change the
  preprocessing verification state. See the diagnostic guide for the command,
  output columns, and remaining spatial/compositing interpretation limits.

## Update 2026-10-07: completed Linux training run

- Run `results/run_0002/` completed the smoke gate, all four configured stages,
  and one held-out test evaluation on the RTX 3090. The selected checkpoint is
  `results/run_0002/checkpoints/final/best.pt` (YOLOv8s-OBB at 512 px).
- Selected validation mAP50 was 0.70546. Held-out test mAP50 was 0.75244 and
  mAP50-95 was 0.49299. See the run history for precision, recall, per-stage
  results, and artifact paths.
- The first three saved test batches contain 48 blank-label images. Their label
  and prediction mosaics are identical, so they do not provide a visual review
  of positive examples. Select representative positive and negative samples
  before relying on visual spot checks.
- Training completion does not complete the project pilot: real-raster
  inference, geographic placement review, Earth Engine date/calibration gates,
  OSM coverage, legal verification, and field review remain outstanding.

## Assessment

The prototype is on track for its local pipeline, but it is not ready for an
end-to-end result or a legal compliance claim. The largest changes since the
original scaffold are the trained-model plan (smoke test, three YOLOv8n image
sizes, then YOLOv8s at the selected size), tile-level SentinelKilnDB
normalization, a confidence-weighted exposure formula, and a 1,300 m
Chebyshev leakage filter. The old prompts below are historical where they
conflict with those decisions.

## Update 2026-10-07: pre-run review of the shared snapshot

CPU-only review (no GPU workload, no training, no inference, no network). On this
snapshot: 106 tests pass and 1 is skipped (it needs the ADM2 boundary file, which
review archives omit); `ruff` reports two TRY004 style findings in
`src/training/run_store.py` that were left alone because they change the raised
exception type.

**Defects found in the training runner and fixed (before run `run_0002`):**

1. `src/training/engine.py` passed a *relative* `project` to Ultralytics. Ultralytics
   8.4.165 resolves a relative project under its own `runs_dir/<task>/`, so results
   would not have appeared under `results/run_NNNN/checkpoints/<stage>/`. The runner
   then read 0 epoch rows, the smoke gate still reported "passed", and stage 1 would
   have trained for hours before failing. `project` is now absolute, and
   `train_stage` raises if Ultralytics reports a different `save_dir`.
2. `validation_map50` read the *last* `results.csv` row, but `best.pt` is the epoch with
   the highest mAP50-95 (the box fitness weights are `[0, 0, 0, 1]`). With
   `patience: 10` those differ by up to 10 epochs, so candidates were ranked on numbers
   that did not describe the checkpoint that gets tested. It now returns the mAP50 of
   the best-fitness epoch.
3. `_run_smoke` now refuses to record "passed" unless `results.csv` has the configured
   number of epoch rows.
4. The fourth stage was named `yolov8s-obb-256` although its image size is chosen
   from stage 1; it is now `yolov8s-obb-best`.

Each fix has a test that fails on the previous code. Resuming a half-finished stage
on a *different* machine is not safe: Ultralytics restores the `save_dir` stored in
the checkpoint. The new guard turns that into a clear error; resume on the same host,
or move only completed stages.

**Cross-checks against the evidence dossier (documents, not new measurements):**

- `config/preprocessing.yaml` and `src/data/normalize.py` match the dossier's recorded
  recipe: B4/B3/B2 plus QA60 bit 10, `<1%` cloud, stride 98 from origin (0, 0) with a
  far-edge patch, and the per-band, per-patch `uint8((b-min)/(max-min+1e-5)*255)` stretch.
- Class balance after the leakage filter: FCBK 2,233 vs Zigzag 8,417 instances
  (21.0% FCBK). The paper's Bangladesh table gives 1,461 vs 5,440 kilns (21.2%).
  Instance counts are about 1.5x the kiln counts, which is plausible for 30 px chip
  overlap; this has not been checked kiln by kiln.
- The authors trained at the native `imgsz=128` (YOLOv11L-OBB, 100 epochs, batch 16);
  the staged plan here starts at 256 and has no native-size baseline.
- The paper's Bangladesh numbers use a different protocol (out-of-region Dhaka,
  leave-one-country-out), so they are context for the order of magnitude only.
- `config/rules.yaml` and `docs/legal_basis.md` were annotated with the dossier's
  candidate passages. No threshold or `verified` flag was changed. Two corrections
  of substance: the old note that Zigzag/HHK/VSBK/tunnel "are permitted" has no
  support in the evidence (the Act defines a kiln by performance, not by type), and
  the 400 m figure is an exception for **existing** Hybrid Hoffman/Tunnel kilns, not
  a general rule. A single 2 km forest buffer also over-applies: 2 km is for
  **government** forest only.

## Pre-run snapshot (2026-10-06; historical)

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
- Training setup and completed-run evidence are summarized in
  [`docs/TRAINING_READINESS.md`](TRAINING_READINESS.md). The earlier Windows
  RTX 4070 run remains historical: its smoke completed, and its first full
  stage stopped during epoch 7. The Linux RTX 3090 run subsequently completed
  as `run_0002`; see the run history. The user manages future GPU workloads;
  agents must not run them unless explicitly asked.
- The Windows development machine has an NVIDIA GeForce RTX 4070 (8 GB). The
  2026-10-06 static check recorded Ruff passing for `src`, `app`, `tests`, and
  `tools`, with 101 tests passing and one skipped. This is historical test
  evidence and does not cover later changes. Linux
  run `run_0002` produced held-out test metrics, but they do not establish field
  accuracy.
- `scripts/init_linux.sh` and `scripts/init_windows.ps1` share
  `requirements-gpu-cu130.txt`; the Linux RTX 3090 host and CUDA stack were
  exercised by run `run_0002`. `scripts/prepare_training_assets.py` uses a pinned
  SentinelKilnDB revision and checks file digests. Without a converted archive,
  it now fetches and validates Bangladesh ADM0 from geoBoundaries before raw-data
  conversion, then downloads pretrained weights. The stale root dataset ZIP is
  intentionally rejected.
- `src/training/run_store.py`, `src/training/engine.py`, and
  `src/training/runner.py` separate run identity/configuration, Ultralytics
  execution/logging, and workflow coordination. Each run is numbered under
  `results/run_NNNN/`; manifests record the host/GPU used per stage, checkpoints
  are ignored, and epoch CSV archives are Git-staged every 10 epochs. New runs
  snapshot the parsed and raw training config, its SHA-256, and the Git source
  revision/working-tree state at run creation.
- `docs/TRAINING_RUN_HISTORY.md` records the historical Windows runs and
  completed Linux run `run_0002`.
- Git metadata and an upstream tracking branch are present. A separate nested
  `Hack-For-Humanity/` copy is ignored and remains outside the active project.
- Git metadata is present in this checkout, but no history review was needed
  for the changes recorded here.

## Implemented but awaiting external or human validation

- `notebooks/train.ipynb` delegates smoke and staged model selection to the
  canonical script runner. Recovered Windows metrics are in
  `results/legacy_windows_rtx4070_20260929/`; Linux held-out metrics are in
  `results/run_0002/run.json`.
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
- `src/eval/audit_sample.py` samples confidence terciles and now includes
  `sample_negative_regions()` to draw random boundary points that are far from
  any detection (default 15 samples, 2 000 m minimum distance). The sampler
  requires a user-supplied boundary GeoJSON and detection GeoParquet; it does
  not fabricate locations. Two synthetic tests pass. The human must supply the
  boundary file and run the sampler after detections exist.
- `src/eval/validate_counts.py` (added 2026-10-06) provides
  `compare_district_counts()` and `check_closure_proximity()`. Both accept
  user-supplied reference CSVs and detection GeoParquet; they do not invent
  coordinates, reported counts, or legal interpretations. Eight synthetic tests
  pass. The human must supply Chapainawabganj 2022 reported counts and the
  Gazipur closed-kiln CSV before running them on real data.
- `src/eval/error_analysis.py` saves top-N false-positive and missed-kiln
  image crops. Three synthetic tests now exist (added 2026-10-06); the module
  has not been run against real test-split predictions.
- `docs/legal_basis.md`, `docs/RUNBOOK.md`, and
  `docs/screening_provenance.md` record evidence fields, operator commands,
  screening limits, and unresolved review gates. They do not verify legal
  claims or external services.

## SentinelKilnDB date evidence: unresolved

The currently published sources do not identify one consistent acquisition
period:

| Source | Reported date |
|---|---|
| Current authors' downloader code | `filterDate('2024-01-01', '2025-02-28')`; Earth Engine treats the end as exclusive |
| Authors' GitHub README | September 2023-February 2024 |
| NeurIPS 2025 proceedings, main paper text (per the evidence dossier) | November 2023-February 2024 |
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

4. Review representative positive and negative detections from `run_0002`,
   then run inference on an approved real-raster pilot and spot-check raster
   alignment and cross-tile deduplication.
5. Resolve the date/calibration gate, complete legal and OSM human review, and
   finish the outstanding validation utilities before making pilot claims.
