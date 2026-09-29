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
- The machine has an NVIDIA GeForce RTX 4070 (8 GB). Install the project's
  CUDA-enabled PyTorch pair from `requirements-gpu-windows-py312.txt`; the
  previously installed CPU-only build cannot use this GPU.
- The ADM2 and Bangladesh boundary files are present and pass basic CRS,
  geometry, field, and required-district checks. Source provenance, licence,
  and human review still need confirmation before geographic claims are made.
- No trained kiln checkpoint, Earth Engine export, OSM cache, or processed
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

## Local GPU Training

1. Install CUDA training dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-gpu-windows-py312.txt
   ```

2. Confirm `torch.cuda.is_available()` is true and the reported device is the
   RTX 4070.
3. Open `notebooks/train.ipynb` from the repository root. Its defaults point to
   the local converted dataset, `data/models/`, and `runs/`.
4. Run the 3-epoch `yolov8n-obb` smoke test first. Continue to full training
   only if the smoke test passes.
5. Preserve `best.pt`, `training_results.json`, confusion matrices, and PR
   curves, then record the selected image size and metrics.

Colab and Kaggle remain optional alternatives; upload the ignored data folders
and set the corresponding paths in the notebook when using those runtimes.

## Accounts and External Services by Stage

| Stage | Account or service needed? | Reason/status |
|---|---|---|
| SentinelKilnDB download | No separate account for this public dataset | Already downloaded from [Hugging Face](https://huggingface.co/datasets/SustainabilityLabIITGN/SentinelKilnDB); training consumes these local chips. |
| Pretrained YOLO weights | No account | Both starting checkpoints are already in `data/models/`. |
| Local detector training | No cloud account | Uses the local RTX 4070, CUDA PyTorch, local dataset, and local checkpoints. |
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
