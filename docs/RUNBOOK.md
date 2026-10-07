# KilnWatch BD Operator Runbook

**Updated:** 2026-10-08. **Scope:** completed local GPU training and the later
imagery/pilot handoff.

## Current Verified State

- Raw SentinelKilnDB Parquet files are present in
  `data/raw/sentinelkilndb/{train,val,test}/` and were readable with PyArrow.
- Converted YOLO-OBB images, labels, YAML, and split report are present in
  `data/interim/yolo_obb/`. Ultralytics accepted the resolved YAML paths, and
  split image/label counts and OBB label structure were checked.
- Pretrained starting weights are present in `data/models/`:
  `yolov8n-obb.pt` and `yolov8s-obb.pt`; both load as OBB models.
- Linux run `run_0002` completed on host `NDAG-M-Lab` with an RTX 3090, Python
  3.12.2, PyTorch 2.14.0+cu130, and Ultralytics 8.4.165. All four stages and
  one held-out test evaluation completed. See `docs/TRAINING_RUN_HISTORY.md`.
- The Windows RTX 4070 smoke run completed historically; its first full stage
  stopped during epoch 7 after six completed validation rows. It was not used
  to resume `run_0002`.
- The ADM2 and Bangladesh boundary files are present and pass basic CRS,
  geometry, field, and required-district checks. Source provenance, licence,
  and human review still need confirmation before geographic claims are made.
- The selected trained checkpoint is
  `results/run_0002/checkpoints/final/best.pt`; its test metrics are in
  `results/run_0002/checkpoints/heldout_test/test_metrics.json`. Real-raster
  inference, geographic-placement checks, Earth Engine exports, OSM caches,
  and processed detection GeoParquet are not verified here.

## Local Checks

Run from the project root:

```powershell
python -m pip check
python -m pytest -q
ruff check src app tests tools
```

Historical local verification: `ruff check src app tests tools` passed and
the 2026-10-06 test run reported 101 passed and one skipped. Latest targeted
screening UI, CSV, rule-provenance, OSM-provenance, inference, and pipeline
checks reported 32 passed and 3 deselected because OSMnx is unavailable in the
active `.venv`; the full test suite was not run. The full suite includes the
ADM2 boundary test when that file is present.

## Dataset Conversion

The current converted dataset is already available. To regenerate it, review
the boundary provenance/licence and run:

```powershell
python -m src.cli explore data/raw/sentinelkilndb
python -m src.cli convert data/raw/sentinelkilndb `
  --boundary data/raw/bangladesh_boundary.geojson `
  --output-dir data/interim/yolo_obb
```

The converter expects the boundary path above for chip filtering. Keep the
ADM2 boundary used by AOI and OSM code at the separate path documented in the
current configuration. Confirm the file CRS, `shapeName` field, and geometry
coverage before conversion.

## Cross-Platform Training Setup

GPU runs are user-managed. Do not start or stop training, smoke tests,
inference, or benchmarks unless the user explicitly asks for that specific
GPU task. These instructions are for the user to run.

1. After cloning, run the initializer for the operating system:

   Linux:

   ```bash
   bash scripts/init_linux.sh
   ```

   Windows PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\init_windows.ps1
   ```

   Both scripts use Python 3.11 or 3.12 and install
   `requirements-gpu-cu130.txt`, project development/inference dependencies,
   and JupyterLab. They do not start a GPU workload.
2. If the converted dataset is missing, pass a local converted archive to the
   initializer or let it download the pinned 3.74 GB source Parquet files from
   Hugging Face. It obtains Bangladesh ADM0 from geoBoundaries' current gbOpen
   API when needed, validates the GeoJSON, and runs the project converter.
   Ultralytics downloads the configured OBB starting weights. Use
   `--skip-assets` (Linux) or `-SkipAssetSetup` (Windows) to skip these downloads.
3. Run `bash scripts/train_linux.sh` or `scripts/train_windows.ps1` with no
   arguments. The one-command launcher runs smoke and, on success, full training.
   Running it again resumes the current numbered run; `continue` is available
   as an explicit command.
4. Run manifests record dataset fingerprint, host, requested GPU, GPU model and
   VRAM by stage. Transfer the complete `results/run_NNNN/` folder with the
   matching dataset when continuing on another machine.
5. The runner archives metric CSVs under `results/run_NNNN/logs/` every 10
   completed epochs and at normal run end; it stages those files and the
   manifest automatically. Review and commit them explicitly. Checkpoints
   remain ignored under `results/run_NNNN/checkpoints/`.

The Linux host and installed CUDA wheel were exercised by `run_0002`. For a
future run, use the one-command launcher; it runs smoke and proceeds to full
training only when smoke passes. A completed current run causes the runner to
allocate the next numbered run rather than overwrite existing outputs.

Colab and Kaggle remain optional alternatives; upload the ignored data folders
and set the corresponding paths in the notebook when using those runtimes.

## Accounts and External Services by Stage

| Stage | Account or service needed? | Reason/status |
|---|---|---|
| SentinelKilnDB download | No separate account for this public dataset | Already downloaded from [Hugging Face](https://huggingface.co/datasets/SustainabilityLabIITGN/SentinelKilnDB); training consumes these local chips. |
| Pretrained YOLO weights | No account | Both starting checkpoints are already in `data/models/`. |
| Local detector training | No cloud account | Uses the user's Linux RTX 3090 or Windows RTX 4070, CUDA PyTorch, local dataset, and local checkpoints. |
| GitHub source collaboration | GitHub account | Already set up for pushing the project repository. |
| New Sentinel-2 imagery export | Google account plus an authorized Google Cloud project registered for Earth Engine | Earth Engine requires an enabled API, project registration, permissions, and authentication. This is the later inference-data stage, not model training. See Google's [access](https://developers.google.com/earth-engine/guides/access) and [authentication](https://developers.google.com/earth-engine/guides/auth) guides. Export is also gated on resolving the published acquisition-date conflict. |
| OSM enrichment | Network access to the configured OSM service | Used after inference; no Earth Engine or Hugging Face account is involved. Inspect coverage and observe service use policies. |
| Legal verification | Authoritative Act/gazette sources and human review | No account setup makes unverified thresholds reliable; keep verification flags false until the primary sources are checked. |

The missing steps were not prerequisites to the training stage. This repo
already has the released satellite-chip dataset, processed training chips,
and pretrained starting weights. New Sentinel-2 imagery comes later, when
running inference across an area of interest. Earth Engine access setup and
date resolution are mandatory before that export, not before training.

Do not treat `yolov8n-obb.pt` or `yolov8s-obb.pt` as kiln-trained models.

## Earth Engine Pilot

Do not enable export while `config/preprocessing.yaml` has
`preprocessing_verified: false`. The published SentinelKilnDB acquisition
periods conflict. A human must confirm the intended dates with the dataset
authors, record the evidence in `docs/PROGRESS.md`, and only then update the
verification flag. Authenticate Earth Engine and run a small pilot before a
full district export.

## Inference and Review

After a trained checkpoint and exported GeoTIFFs exist:

```powershell
python -m src.cli infer path\to\best.pt `
  --raster-dir data/interim/s2_composites `
  --output data/processed/kilns.parquet `
  --imgsz <training-image-size>
```

Then fetch or load reviewed OSM caches, run rules and scoring, and generate an
audit CSV. Inspect detections, coordinate placement, OSM coverage, and the
advisory screening labels before sharing results. Every marker/detail popup and
CSV should retain its caveat and explain that distances are measured to mapped
features, which may not be legally controlling boundaries. See
[`screening_provenance.md`](screening_provenance.md) for traceability fields
and review-state definitions.

## Explicitly Not Automatable Here

- Legal threshold verification and changing `verified` flags.
- Resolving the SentinelKilnDB date conflict.
- Earth Engine credentials and export approval.
- GPU training and judging model quality.
- Visual inspection of detections and OSM completeness.
- Claims about enforcement, compliance, or field suitability.
