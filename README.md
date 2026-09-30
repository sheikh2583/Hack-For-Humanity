# KilnWatch BD 🏭🛰️

> **Current status:** See [docs/PROGRESS.md](docs/PROGRESS.md) and the
> [training run history](docs/TRAINING_RUN_HISTORY.md) for verified
> implementation and outstanding checks. Conversion, lint, and 82 tests passed
> before the latest runner changes; the current test suite has not been rerun.
> The Windows RTX 4070 smoke run completed; the first full stage completed six
> epochs and was interrupted during epoch 7. The Linux RTX 3090 overnight run
> is planned, not started. The partial checkpoint is not a final model. The user manages future GPU runs unless explicitly
> asking an agent to perform one. Earth Engine export has not run.
> `config/preprocessing.yaml` deliberately keeps `preprocessing_verified: false`
> because published SentinelKilnDB date ranges conflict; do not enable export
> until the authors' intended dates and a paired-chip calibration are reviewed.

> Satellite-based brick kiln compliance triage for Bangladesh  
> *Hack for Humanity Bangladesh 2026*

## Overview

KilnWatch BD detects brick kilns in Sentinel-2 satellite imagery, checks each
against siting and technology rules from Bangladesh's Brick Manufacturing and
Kiln Establishment (Control) Act 2013, ranks them by community exposure, and
displays the results on an interactive map.

**⚠️ Advisory only** — all outputs require field verification before any
enforcement action.

## Dataset

- **SentinelKilnDB** (CC BY-NC 4.0) — 128×128 px Sentinel-2 chips at 10 m
  resolution. The detector outputs FCBK and Zigzag; two rare source records
  in the Bangladesh data are merged into FCBK.

## Project Structure

```
kilnwatch-bd/
├── AGENTS.md                # Agent rules
├── config/
│   ├── aoi.yaml             # Areas of interest & season
│   └── rules.yaml           # Legal compliance rules (UNVERIFIED)
├── data/
│   ├── raw/                 # Original downloads (not committed)
│   ├── interim/             # Intermediate artefacts
│   └── processed/           # Pipeline outputs (GeoParquet)
├── src/
│   ├── cli.py               # Typer CLI — one command per pipeline stage
│   ├── data/                # Dataset conversion & export
│   ├── detect/              # YOLO inference & NMS
│   ├── geo/                 # OSM layers & spatial utilities
│   ├── rules/               # Compliance rule engine
│   ├── score/               # Priority scoring
│   ├── eval/                # Error analysis & audit sampling
│   └── app/                 # (reserved)
├── app/
│   └── streamlit_app.py     # Interactive dashboard
├── notebooks/               # Training notebooks (local GPU / Colab / Kaggle)
├── scripts/                 # Cross-platform setup and review-archive helpers
├── results/                 # Numbered run manifests, GPU provenance, logs
├── tests/                   # Pytest suite
├── pyproject.toml
└── README.md
```

## Quick Start

### Create a minimal review ZIP

Run the standalone PowerShell script from the repository root (or pass its path
from another directory). It includes source, configuration, tests, and
documentation, and excludes data, virtual environments, caches, and model
weights:

```powershell
.\scripts\make_review_zip.ps1
```

Upload `kilnwatch_bd_share.zip` to Claude Web and use
[docs/CLAUDE_WEB_PROMPT.md](docs/CLAUDE_WEB_PROMPT.md) for the review prompt.

```bash
# Create a virtual environment
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install only the extras for the stages you will run; see
# docs/MEMORY_AND_DOWNLOADS.md for which groups pull the model stack.
pip install -e ".[dev,geo,app]"
# Add ".[ee]" for Earth Engine export or ".[detect]" for local inference.

# Run the pipeline
kilnwatch --help

# Launch the dashboard
streamlit run app/streamlit_app.py
```

See [docs/MEMORY_AND_DOWNLOADS.md](docs/MEMORY_AND_DOWNLOADS.md) for the
memory/download review, cache behavior, and unmeasured limitations.
See [docs/TRAINING_READINESS.md](docs/TRAINING_READINESS.md) for the checked
prerequisites and the cross-platform training handoff.

## Initialize a Training Machine

After cloning, use the initializer for that OS. It creates `.venv`, installs
the shared pinned GPU stack, development tools, and Jupyter runtime, then
prepares the converted dataset and pretrained YOLOv8 OBB weights where the
required inputs are available. It does not run a CUDA probe, smoke test, or
training job.

Linux (RTX 3090 lab PC):

```bash
bash scripts/init_linux.sh --dataset-archive yolo_obb_1300m.zip
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\init_windows.ps1 -DatasetArchive .\yolo_obb_1300m.zip
```

Both use `requirements-gpu-cu130.txt` with Python 3.11 or 3.12. If you have a
current converted dataset archive (including the 1,300 m leakage filter), pass
it with `--dataset-archive` on Linux or `-DatasetArchive` on Windows. The
existing root `yolo_obb_bd.zip` is stale and will be rejected. Otherwise,
provide the reviewed `data/raw/bangladesh_boundary.geojson`; the initializer
can then offer to download the pinned 3.74 GB SentinelKilnDB source and convert
it. It will not guess or download an unreviewed boundary. See
[docs/TRAINING_READINESS.md](docs/TRAINING_READINESS.md) for the handoff steps.

To create the Python environment and install dependencies before supplying
training assets, pass `--skip-assets` on Linux or `-SkipAssetSetup` on Windows.
Rerun the initializer without that option after placing a valid dataset archive
or reviewed boundary. Empty `data/raw/`, `data/interim/`, and `data/processed/`
folders are tracked with placeholders; downloaded datasets, generated outputs,
archives, model weights, and `.venv/` stay local and must be supplied or created
on each machine.

To build or refresh `yolo_obb_1300m.zip` from this checkout's current converted
dataset, run:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_training_assets.py --make-dataset-archive yolo_obb_1300m.zip
```

On Linux use `.venv/bin/python` with the same script and arguments. Copy that
ignored archive alongside the clone, then pass it explicitly to the
initializer.

## Run Training

The shared runner is `scripts/train.py`, configured by `config/training.yaml`.
After environment and assets are prepared, one command starts smoke and then
the staged full run. It continues the active numbered run after interruption.
Each `results/run_NNNN/` folder contains a Git-staged run manifest with the
dataset fingerprint and per-stage GPU/host identity, metric CSV chunks, and
an ignored `checkpoints/` directory. Transfer the dataset archive separately
to each machine.

Linux (RTX 3090), one command:

```bash
bash scripts/train_linux.sh
```

Windows (RTX 4070), one command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\train_windows.ps1
```

The one-command launcher runs the 3-epoch smoke gate, proceeds to full training
only when it passes, and resumes incomplete stages from `last.pt` on the next
invocation. To run one step manually use `bash scripts/train_linux.sh smoke`
or `bash scripts/train_linux.sh full` on Linux. On Windows, pass `smoke` or
`full` to `powershell -ExecutionPolicy Bypass -File .\scripts\train_windows.ps1`.
Use `start` or `continue` to resume the active run.
The workflow selects candidates on validation
mAP50 and tests the selected model once. Numbered runs are never overwritten.
The default device is CUDA index `0`; choose another GPU with `--device 1`, or
use `--device cpu` on Linux or `-Device cpu` on Windows. The selected
accelerator details are saved in `run.json` when each stage starts.

To continue on another machine, copy `results/run_NNNN/` and the same dataset,
then invoke `bash scripts/train_linux.sh continue --run-id run_NNNN` or
`powershell -ExecutionPolicy Bypass -File .\scripts\train_windows.ps1 continue -RunId run_NNNN`.
The dataset fingerprint must match. `run.json` records GPU
model, VRAM, host, runtime, and stage. Metric chunks and the manifest are
automatically staged in Git; inspect and commit them manually. Checkpoints and
plots remain out of Git.

The earlier partial output under `runs/yolov8n-obb-256/` is preserved, but is
not automatically imported into the numbered runner. New runs start from the
configured pretrained weights; numbered runs created by this runner resume
from their own checkpoints.

The notebook in `notebooks/train.ipynb` is an optional UI for these same
commands; it does not define a separate training pipeline.

## Pipeline Stages

| # | Command | Description |
|---|---------|-------------|
| 1 | `kilnwatch convert` | Convert SentinelKilnDB to spatial-block-split YOLO-OBB format |
| 2 | `scripts/train_linux.sh` / `scripts/train_windows.ps1` | One-command user-managed smoke plus staged training on local GPUs |
| 3 | `kilnwatch export-s2` | Export Sentinel-2 composites via Earth Engine |
| 4 | `kilnwatch infer` | Run kiln detection on exported imagery |
| 5 | `kilnwatch fetch-osm` | Download OSM layers (schools, hospitals, etc.) |
| 6 | `kilnwatch check-rules` | Evaluate compliance rules per kiln |
| 7 | `kilnwatch score` | Compute priority scores |
| 8 | `kilnwatch audit-sample` | Generate audit sample for manual validation |

## Legal Disclaimer

All rule thresholds in `config/rules.yaml` are **unverified placeholders** from
secondary sources. They must be checked against the original Act and gazette
before any use beyond prototyping.

## Licence

Code: MIT  
Dataset: SentinelKilnDB is CC BY-NC 4.0 — cite the authors.
