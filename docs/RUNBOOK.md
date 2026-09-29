# KilnWatch BD Operator Runbook

**Scope:** local GPU training and the later imagery/pilot handoff.

## Current Verified State

- Raw SentinelKilnDB Parquet files are present in
  `data/raw/sentinelkilndb/{train,val,test}/` and were readable with PyArrow.
- Converted YOLO-OBB images, labels, YAML, and split report are present in
  `data/interim/yolo_obb/`. Ultralytics accepted the resolved YAML paths, and
  split image/label counts and OBB label structure were checked.
- Pretrained starting weights are present in `data/models/`:
  `yolov8n-obb.pt` and `yolov8s-obb.pt`; both load as OBB models.
- The previous Windows development machine used an RTX 4070 (8 GB). The new
  training host is expected to be an RTX 3090 on Linux; that host has not been
  inspected or GPU-tested. Both platforms use the shared pinned stack in
  `requirements-gpu-cu130.txt`.
- The Windows smoke run completed, and the first full stage was interrupted
  during epoch 7 after six completed validation rows. The planned Linux
  overnight run has not started. Keep the run-by-run evidence in
  `docs/TRAINING_RUN_HISTORY.md` up to date.
- The ADM2 and Bangladesh boundary files are present and pass basic CRS,
  geometry, field, and required-district checks. Source provenance, licence,
  and human review still need confirmation before geographic claims are made.
- A partial YOLOv8n checkpoint exists under `runs/yolov8n-obb-256/`; it was
  stopped at epoch 6/50 and has not been evaluated on the held-out test split.
  No final trained model, Earth Engine export, OSM cache, or processed
  detection GeoParquet is verified here.

## Local Checks

Run from the project root:

```powershell
python -m pip check
python -m pytest -q
ruff check src app tests tools
```

Latest local verification: `ruff check src app tests tools` passes and
`python -m pytest -q` reports 82 passed. The full test suite includes the
present ADM2 boundary file.

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
   initializer or place the reviewed country boundary at
   `data/raw/bangladesh_boundary.geojson`. With the boundary present, the
   initializer can offer to download the pinned 3.74 GB source Parquet files
   from Hugging Face and run the project converter. It refuses to guess a
   boundary source.
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

The RTX 3090 Linux setup has not been exercised from this Windows checkout.
Confirm the lab host has the dataset, pretrained weights, and a driver
compatible with the installed CUDA wheel. Start with the one-command launcher;
it runs smoke and only proceeds to full training when smoke passes. The runner
records which GPU it used in the numbered result manifest.

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
an audit CSV. Inspect detections, coordinate placement, OSM coverage, and the
advisory-only labels manually before sharing results.

## Explicitly Not Automatable Here

- Legal threshold verification and changing `verified` flags.
- Resolving the SentinelKilnDB date conflict.
- Earth Engine credentials and export approval.
- GPU training and judging model quality.
- Visual inspection of detections and OSM completeness.
- Claims about enforcement, compliance, or field suitability.
