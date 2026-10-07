# Training start readiness

**Checked:** 2026-09-29. See [TRAINING_RUN_HISTORY.md](TRAINING_RUN_HISTORY.md)
for the Windows run evidence and next Linux run plan. The Windows RTX 4070
smoke test completed. The first full stage has six completed validation rows;
the saved console shows interruption during epoch 7. The user plans a fresh
overnight run on the Linux RTX 3090; it has not started or been verified. No
GPU workload may be started by an agent unless the user explicitly requests
that specific work; the user manages GPU runs by default.

## Dataset and weights

The raw SentinelKilnDB Parquet files are present at
`data/raw/sentinelkilndb/`: train 71,856 rows, val 23,952, and test 18,492.
The converted YOLO-OBB dataset is present at `data/interim/yolo_obb/`:

| Split | Images | Labels | FCBK instances | Zigzag instances |
|---|---:|---:|---:|---:|
| train | 8,058 | 8,058 | 1,773 | 5,589 |
| val | 1,662 | 1,662 | 214 | 1,803 |
| test | 1,530 | 1,530 | 246 | 1,025 |

Ultralytics 8.4.165 accepts the dataset YAML when its `path` points to the
resolved dataset root. The label audit found no malformed lines; every OBB row
has a class ID and eight normalized coordinates. `split_report.json` records a
1,300 m Chebyshev leakage filter and a 1,322.41 m minimum cross-split distance.
The dataset tree is about 350.7 MiB.

Pretrained `yolov8n-obb.pt` (6,567,590 bytes) and `yolov8s-obb.pt`
(23,267,238 bytes) are stored in `data/models/` and load as Ultralytics OBB
models. These are initialization weights, not kiln-trained checkpoints. The
selected final `best.pt` does not exist yet.

Both boundary files are present. Basic checks found EPSG:4326 geometries, a
`shapeName` field and the required `Nawabganj`/`Gazipur` names in the 64-row
ADM2 file. Their source provenance, licence, and human review have not been
verified. This does not block training on the already converted chips, but
verify those items before making geographic claims from project outputs.

## Windows and Linux GPU setup and training

The shared pinned CUDA-enabled PyTorch/torchvision and Ultralytics versions
are in `requirements-gpu-cu130.txt`. The initializer creates `.venv`, installs
the project training dependencies, and prepares available input assets:

Linux (lab RTX 3090): `bash scripts/init_linux.sh --dataset-archive yolo_obb_1300m.zip`

Windows: `powershell -ExecutionPolicy Bypass -File .\scripts\init_windows.ps1 -DatasetArchive .\yolo_obb_1300m.zip`

The initializer itself does not run a CUDA probe, smoke test, or training job.
If a current converted dataset archive is available, pass `--dataset-archive`
on Linux or `-DatasetArchive` on Windows. The old root `yolo_obb_bd.zip` is
rejected because it lacks the leakage filter. Otherwise, the initializer
downloads the pinned 3.74 GB SentinelKilnDB source, fetches the Bangladesh
ADM0 GeoJSON from geoBoundaries' current gbOpen API when absent, validates it,
and converts the dataset. Ultralytics downloads the pretrained OBB weights.
Use `--skip-assets` / `-SkipAssetSetup` to install dependencies without these
downloads; initialization does not start a GPU workload.

Bundle the checked converted data for the lab machine with:

```bash
.venv/bin/python scripts/prepare_training_assets.py \
  --make-dataset-archive yolo_obb_1300m.zip
```

On Windows invoke `.venv\Scripts\python.exe` and the same script/arguments.
Copy the ignored archive separately from the Git clone and pass its path to
the initializer.

The 3-epoch smoke test passed locally on the RTX 4070 at imgsz 256, batch 8,
and zero loader workers. The retained training CSV's final row is mAP50 0.52184
and mAP50-95 0.25290. Older notes cite a separate validation result of 0.5226
and 0.2527; that separate metric record is not present locally. See the run
history for this discrepancy. Smoke metrics validate the training path only.

The first stage ran YOLOv8n at 256px for 6 of 50 configured epochs, then was
interrupted partway through epoch 7. `results.csv` records six completed rows;
`best.pt` and `last.pt` are present
in `runs/yolov8n-obb-256/weights/`. These are partial-run checkpoints, not a
selected final model. Stages at 384/512px, YOLOv8s, held-out test evaluation,
and final artifact copy did not run. The epoch 6 validation values recorded in
`results.csv` are mAP50 0.46018 and mAP50-95 0.22179; treat them as an
incomplete run snapshot, not final evaluation. The trainer process was
verified stopped.

That legacy output remains preserved but is not auto-imported by the numbered
runner. Its `last.pt` will not be used by `scripts/train.py`; new numbered runs
start from the configured pretrained weights.

The canonical CLI is `scripts/train.py`, wrapped by `scripts/train_linux.sh`
and `scripts/train_windows.ps1`. Running either launcher without arguments
starts the smoke gate and then full training. The next invocation continues
the current numbered run from its last checkpoint. Each `results/run_NNNN/`
stores a portable manifest with GPU/host identity and dataset fingerprint,
Git-staged epoch logs, and ignored model checkpoints. Use the same dataset on
both hosts. See `Run Training` in the README for commands and transfer steps.

The user owns all GPU runs, including smoke tests. Do not start, stop, or
inspect GPU workloads unless the user explicitly requests that specific
action. The RTX 3090 host has not been inspected from this checkout, so its
driver compatibility and CUDA availability remain for the user to check.

The runner writes metric CSV chunks into
`results/run_NNNN/logs/<stage>/epochs_XXXX-YYYY.csv` after each 10 completed
epochs and saves a final partial chunk on normal exit. New chunks and the
updated `run.json` manifest are staged automatically; review and commit them
when ready. Checkpoints remain ignored under `results/run_NNNN/checkpoints/`.

Colab and Kaggle are not the supported scripts in this local cross-platform
workflow. The supported GPU hosts are the Windows RTX 4070 and Linux RTX 3090.

If adapting the shared runner to Colab, the data and model paths must point to
the uploaded assets, and run state/logs should be saved to persistent storage:

```python
DATASET_ROOT = Path("/content/drive/MyDrive/kilnwatch/yolo_obb")
MODEL_ROOT = Path("/content/drive/MyDrive/kilnwatch/models")
OUTPUT_DIR = Path("/content/drive/MyDrive/kilnwatch/runs")
```

For Kaggle, set `DATASET_ROOT` to the attached dataset under `/kaggle/input/`,
`MODEL_ROOT` to an attached model dataset if used, and `OUTPUT_DIR` under
`/kaggle/working/`.

## Why the training step needs no Earth Engine signup

The training inputs are already downloaded SentinelKilnDB chips, converted to
local PNG/OBB labels. Training reads those files and the local pretrained
weights; it does not request new Sentinel-2 imagery. The public dataset is
already present in this checkout. A Hugging Face account is not part of the
local training steps.

Earth Engine is a later step for exporting new Sentinel-2 composites for
inference. That API requires authentication and an authorized Google Cloud
project; the acquisition-date conflict must also be resolved before enabling
the project export. See Google's [Earth Engine authentication guide](https://developers.google.com/earth-engine/guides/auth).

## Separate project gates

- Resolve the conflicting SentinelKilnDB acquisition dates before enabling
  Earth Engine export. This uncertainty does not prevent training on the
  converted chips.
- Legal thresholds, Earth Engine chip parity, OSM coverage, inference placement,
  and dashboard outputs still need their own verification before any compliance
  interpretation or complete demo.

## Not verified

- The multi-stage training plan and held-out test evaluation remain incomplete.
- The saved partial checkpoint has not been evaluated on the held-out test set.
- GPU memory requirements and a complete-run time estimate remain unverified.
