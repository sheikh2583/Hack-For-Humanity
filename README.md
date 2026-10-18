# Dhoa

> **Current status (Round 2 prototype):** Dhoa screens kiln candidates
> across five pilot districts: Chapainawabganj, Gazipur, Rajshahi, Dhaka, and
> Chittagong. The processed priority dataset currently contains 2,150 candidate
> rows. The selected model is `results/run_0002/checkpoints/final/best.pt` at
> 512 px. Model metrics are held-out SentinelKilnDB dataset-chip results only;
> they do not describe the raster pilot or field accuracy. Preprocessing remains
> gated by `preprocessing_verified: false` until source dates and calibration
> are reviewed. See [docs/ROUND2_SUBMISSION.md](docs/ROUND2_SUBMISSION.md) and
> [docs/PROGRESS.md](docs/PROGRESS.md) for status and limitations.

> Satellite-based brick kiln candidate screening for Bangladesh
> *Hack for Humanity Bangladesh 2026*

## Overview

Dhoa detects kiln candidates in Sentinel-2 satellite imagery, compares
them with configured siting and technology rules as GIS screening signals,
ranks them by screening priority, and displays the results on an interactive
map. These outputs are screening candidates, not legal or administrative determinations.

**Advisory screening only.** Detector confidence describes the model's
assessment that a kiln candidate exists; rule signals describe comparisons to
mapped features. Neither establishes legal status. Distances are to mapped
features and may differ from distances to legally controlling boundaries.
See [docs/screening_provenance.md](docs/screening_provenance.md) for signal
provenance, review states, and unresolved dependencies.

The SentinelKilnDB imagery-date discrepancy remains unresolved. An optional
offline-testable diagnostic is documented in
[docs/DATE_FORENSICS.md](docs/DATE_FORENSICS.md); it requires the user's own
Earth Engine credentials when run and does not establish a date range by itself.

## Quick start

After the trained checkpoint, exported rasters in `data/raw/exports/`, and
required local data are ready, run the pipeline and then open the dashboard. The
pipeline defaults to CPU; this command also makes that explicit:

```bash
python scripts/run_pipeline.py --weights results/run_0002/checkpoints/final/best.pt --imgsz 512 --device cpu
streamlit run app/streamlit_app.py
```

On Windows PowerShell, start the dashboard through the project environment so
the command works even when the virtual environment is not activated:

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

On Linux/macOS, use:

```bash
.venv/bin/streamlit run app/streamlit_app.py
```

### Dashboard deliverables

The dashboard provides district summaries, filters, a selectable high-priority
list, an interactive map of filtered candidates, candidate details and
navigation links, a one-candidate PDF report, a community search with an
adjustable radius and matching PDF, and a filtered CSV review queue with
coordinates and rule distances. The list and map are arranged side by
side on desktop and adapt for narrow screens. See the
[dashboard guide](docs/DASHBOARD_GUIDE.md) for the operator flow and export
contents. Before a public demo, check selection, map controls, PDF, and CSV in
the target desktop and mobile browsers.

### Mobile view

The sidebar collapses on narrow screens; open it to reach the district and
candidate filters and CSV export. The list becomes a compact selectable view
and the map moves below it. To check the mobile view, use browser developer
tools at 360px, 412px, 768px, and 1280px widths. Confirm that candidate
selection, map controls, PDF download, and CSV export remain usable without
page-level horizontal scrolling. The candidate list has its own horizontal
scroll area on desktop to expose all distance columns.

### Mobile demo

The Expo app lives in [mobile/](mobile/) and demonstrates nearby candidates,
the candidate map, and field capture. Run the backend, install the mobile
dependencies, then start Expo:

```powershell
python -m uvicorn backend.main:app --reload
cd mobile
npm install
npm start
```

Copy `mobile/.env.example` to `mobile/.env` and set
`EXPO_PUBLIC_API_URL` to the backend URL. The app uses fallback demo data when
the backend is unavailable.

#### Backend deployment

For Render, create a Web Service from this repository with:

- Root directory: repository root
- Build command: `pip install -r backend/requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

For Railway, create a service from the repository and use the same start
command. Set `KILNWATCH_DATA` only when the processed GeoParquet is mounted at
a different path. Put the deployed API URL in `mobile/.env` as
`EXPO_PUBLIC_API_URL`, then run `npm start` from `mobile/`.

## Pilot districts

Chapainawabganj, Gazipur, Rajshahi, Dhaka, and Chittagong.

## Dataset

- **SentinelKilnDB, Mondal et al., NeurIPS 2025** ([paper](https://openreview.net/forum?id=efGzsxVSEC), [dataset](https://huggingface.co/datasets/SustainabilityLabIITGN/SentinelKilnDB)) is licensed **CC BY-NC 4.0**. Attribution and non-commercial terms apply to the dataset. It contains 128 by 128 px Sentinel-2 chips at 10 m resolution. The detector outputs FCBK and Zigzag; a rare source category is merged into FCBK.

## Advisory use

All detections and rule signals are screening candidates for human review. The dashboard does not determine legal status. Review mapped distances and signals against authoritative records and field evidence before any inspection decision.

## Project Structure

```
kilnwatch-bd/
â”œâ”€â”€ AGENTS.md                # Agent rules
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ aoi.yaml             # Areas of interest & season
â”‚   â””â”€â”€ rules.yaml           # Unverified screening configuration
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/                 # Original downloads (not committed)
â”‚   â”œâ”€â”€ interim/             # Intermediate artefacts
â”‚   â””â”€â”€ processed/           # Pipeline outputs (GeoParquet)
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ cli.py               # Typer CLI â€” one command per pipeline stage
â”‚   â”œâ”€â”€ data/                # Dataset conversion & export
â”‚   â”œâ”€â”€ detect/              # YOLO inference & NMS
â”‚   â”œâ”€â”€ geo/                 # OSM layers & spatial utilities
â”‚   â”œâ”€â”€ rules/               # Candidate rule-signal engine
â”‚   â”œâ”€â”€ score/               # Priority scoring
â”‚   â”œâ”€â”€ eval/                # Error analysis & audit sampling
â”‚   â””â”€â”€ app/                 # (reserved)
â”œâ”€â”€ app/
â”‚   â””â”€â”€ streamlit_app.py     # Interactive dashboard
â”œâ”€â”€ notebooks/               # Training notebooks (local GPU / Colab / Kaggle)
â”œâ”€â”€ scripts/                 # Cross-platform setup and review-archive helpers
â”œâ”€â”€ results/                 # Numbered run manifests, GPU provenance, logs
â”œâ”€â”€ tests/                   # Pytest suite
â”œâ”€â”€ pyproject.toml
â””â”€â”€ README.md
```

## Share a review ZIP

Run the same Python command on Windows or Linux from the repository root. It
includes source, configuration, tests, and documentation, and excludes data,
virtual environments, caches, and model weights:

```bash
python scripts/make_review_zip.py
```

Upload `kilnwatch_bd_share.zip` to Claude Web and use
[docs/CLAUDE_WEB_PROMPT.md](docs/CLAUDE_WEB_PROMPT.md) for the review prompt.
See [docs/CLAUDE_SHARING_AND_SETUP.md](docs/CLAUDE_SHARING_AND_SETUP.md) for
cross-platform checksum checks and OSM, Overpass, inference, and optional Earth
Engine setup requirements.

For platform-specific install commands, OSM data, optional inference, and
training setup, see [docs/SETUP.md](docs/SETUP.md). See
[docs/MEMORY_AND_DOWNLOADS.md](docs/MEMORY_AND_DOWNLOADS.md) for dependency
groups, memory/download review, cache behavior, and limitations, and
[docs/TRAINING_READINESS.md](docs/TRAINING_READINESS.md) for training
prerequisites.

## Initialize a Training Machine

After cloning, use the initializer for that OS. It creates `.venv`, installs
the shared pinned GPU stack, development tools, and Jupyter runtime, then
downloads and prepares the SentinelKilnDB dataset, Bangladesh boundary, and
pretrained YOLOv8 OBB weights. The raw dataset download is about 3.74 GB. It
does not run a CUDA probe, smoke test, or training job.

Linux (RTX 3090 lab PC):

```bash
bash scripts/init_linux.sh --dataset-archive yolo_obb_1300m.zip
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\init_windows.ps1 -DatasetArchive .\yolo_obb_1300m.zip
```

Both use `requirements-gpu-cu130.txt` with Python 3.11 or 3.12. The initializer
automatically downloads the pinned SentinelKilnDB source files and obtains the
Bangladesh ADM0 GeoJSON from the geoBoundaries current gbOpen API when those
assets are absent. It validates the boundary CRS and geometries before use.
Pretrained OBB weights are downloaded by Ultralytics. If you already have a
current converted dataset archive (including the 1,300 m leakage filter), pass
it with `--dataset-archive` on Linux or `-DatasetArchive` on Windows to skip
the raw dataset conversion. The existing root `yolo_obb_bd.zip` is stale and
will be rejected. See
[docs/TRAINING_READINESS.md](docs/TRAINING_READINESS.md) for the handoff steps.

To create the Python environment without downloading the training assets, pass
`--skip-assets` on Linux or `-SkipAssetSetup` on Windows. Rerun the initializer
without that option to fetch them. Empty `data/raw/`, `data/interim/`, and `data/processed/`
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

An earlier partial Windows training attempt is archived under
`results/legacy_windows_rtx4070_20260929/`; it was not imported into the numbered runner. New runs start from the
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
| 6 | `kilnwatch check-rules` | Generate candidate rule signals from mapped features |
| 7 | `kilnwatch score` | Compute priority scores |
| 8 | `kilnwatch audit-sample` | Generate audit sample for manual validation |

## Screening and legal status

Generated detections and rule signals remain candidates for human review.
Configured thresholds and source layers have not been established as authoritative
legal boundaries or interpretations. Do not use screening outputs to make a legal determination about a kiln. See
[docs/legal_basis.md](docs/legal_basis.md) for legal research and
[docs/screening_provenance.md](docs/screening_provenance.md) for unresolved
legal and spatial-data dependencies.

## Licence

Code: MIT
Dataset: SentinelKilnDB is CC BY-NC 4.0 â€” cite the authors.
