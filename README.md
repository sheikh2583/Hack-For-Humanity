# KilnWatch BD 🏭🛰️

> **Current status:** See [docs/PROGRESS.md](docs/PROGRESS.md) for verified
> implementation and outstanding checks. The local conversion, tests, and
> lint pass, but Earth Engine export and GPU training have not been run.
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
├── notebooks/               # Training notebooks (Colab/Kaggle)
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
prerequisites to start the training notebook's smoke test.

## Pipeline Stages

| # | Command | Description |
|---|---------|-------------|
| 1 | `kilnwatch convert` | Convert SentinelKilnDB to spatial-block-split YOLO-OBB format |
| 2 | *(Colab notebook)* | Train YOLOv8 OBB detector |
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
