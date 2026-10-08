# Claude handoff context — 2026-10-08

Copy this file into Claude to continue work on KilnWatch BD.

## Project

This is the KilnWatch BD project at `X:\AIUB Hackathon`, a Python application for detecting brick kilns in Sentinel-2 imagery, checking siting/technology rules, ranking exposure, and showing results on a map. The environment is Windows PowerShell with a project virtual environment at `.venv`.

Read `AGENTS.md` before changing code. Key requirements:

- Never invent schemas, legal thresholds, or coordinates. Legal values live in `config/rules.yaml`.
- Store geometry in EPSG:4326; do spatial distance/area calculations in EPSG:9680, with the documented UTM fallback.
- Modules need type hints, input/output schema docstrings, and a synthetic-data pytest.
- Do not call Earth Engine unless specifically directed. GPU workloads also require explicit user authorization.
- At the end, report what could not be verified and what needs a manual check.

## Work completed today

### Real-raster inference wiring and output

- Updated `src/detect/infer.py` to read three-band raster windows as float64, tile with configured size/overlap, normalize each band per tile with `src.data.normalize.minmax_uint8`, convert to uint8, reverse RGB to BGR, run YOLO OBB, and transform detections through the raster affine transform into WGS84.
- Added centroid Point output support with `kiln_id`, `geometry`, `class_name`, `confidence`, `district`, `lat`, and `lon` fields.
- Updated `src/cli.py` to support raster-file input, point output, district name, and a new `--device` option (`cpu`, `0`, `cuda:0`, etc.). Device defaults to CPU.
- Updated `scripts/run_pipeline.py` to add real-raster inference for exported TIFFs and produce district-named output files.
- Updated `app/streamlit_app.py` to load the most recently modified `kilns*.parquet` and show its district.
- Added/updated synthetic tests for inference, pipeline raster selection, and Streamlit result-file selection.

### Actual inference runs

Input raster: `data/raw/exports/kilnwatch_chapai_test.tif` (the user reported it was inspected: EPSG:4326; pixel size 8.983e-5 degrees; 6680 x 7793; three float64 bands; reflectance 137–4784; no zero pixels).

Checkpoint: `runs/yolov8n-obb-256/weights/best.pt` (the non-smoke checkpoint available in the workspace).

- First run used CPU and wrote `data/processed/kilns_chapai_real.parquet`: 5,440 tiles; 1,219 detections (18 FCBK, 1,201 Zigzag).
- The user then authorized GPU use and asked to restart with CUDA. CUDA was available as an NVIDIA GeForce RTX 4070 Laptop GPU.
- The first CUDA CLI attempt failed because `infer` had no `--device` option. Added `device` argument through CLI and inference functions, defaulting to CPU. Then reran with `--device 0`.
- CUDA run wrote `data/processed/kilns_chapai_real_cuda.parquet`: 5,440 tiles; 1,220 detections (18 FCBK, 1,202 Zigzag).
- The CUDA output was read back and verified in the prior CPU run; the CUDA command completed successfully and printed counts. Both outputs are intentionally preserved.
- Inference requested `imgsz=512`, while the checkpoint records training `imgsz=256`; the code prints a warning and continues. This difference may affect detections. CPU and CUDA totals differed by one detection.

## Verification

- Latest full pytest run after adding device support: `146 passed` (10 warnings).
- Ruff check passed for `src/detect/infer.py`, `src/cli.py`, and `tests/test_infer.py`.
- No Earth Engine calls were made.
- The full pipeline was not run (it includes OSM fetch and downstream rules/scoring); Streamlit was not launched.

## Workspace state and cleanup

`git status --short` showed changes accumulated across this and earlier work, including modifications to `app/streamlit_app.py`, configs, `pyproject.toml`, CLI/data/detection/geo/rules code, multiple tests, and new pipeline/evaluation/tool files. Do not discard or reset them without reviewing their ownership and purpose.

The untracked `cache/` contains JSON files dated today. `temporary doc share/training log round 1` is a 125,616-byte file last modified yesterday. Neither was removed: their purpose is unclear and they may be user data. The generated raster and GeoParquet results under `data/` are also preserved; they are ignored by Git.

## Suggested next checks

1. Review the CUDA GeoParquet detections on the map and verify geographic placement and class labels.
2. Decide whether inference should use 256 to match this checkpoint or whether a checkpoint trained at 512 is available.
3. If desired, run the app against the newest output and validate the real-raster stage in `scripts/run_pipeline.py` without triggering external services unexpectedly.
4. Inspect the existing `git status` changes before committing; this workspace contains accumulated work from several requests.
