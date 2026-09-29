# Training start readiness

**Checked:** 2026-09-29. The local training inputs were inspected; CUDA was
enabled in `.venv` and the 3-epoch smoke test passed. The staged full training
run is in progress.

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

## Local GPU setup and training

The pinned CUDA-enabled PyTorch/torchvision pair is installed in the project
environment. To reproduce the setup:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-gpu-windows-py312.txt
   ```

Confirm that PyTorch sees the RTX 4070:

   ```powershell
   .\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no CUDA device')"
   ```

The 3-epoch smoke test passed locally on the RTX 4070 at imgsz 256, batch 8,
and zero loader workers. Its validation mAP50 was 0.5226 and mAP50-95 was
0.2527; it completed all 3 epochs and produced confusion-matrix and PR-curve
plots. These smoke metrics only validate the training path; they are not the
final model evaluation.

The full staged notebook run has started at `runs/yolov8n-obb-256/`. It trains
YOLOv8n at 256/384/512, then YOLOv8s at the selected size. The single held-out
test evaluation and final artifact copy are still pending.

Colab and Kaggle remain alternatives. Their setup blocks are in the notebook;
cloud accounts are needed only if choosing those hosted runtimes.

For Colab, the path setup can look like this after mounting Drive and uploading
the converted dataset and optional weights:

```python
from google.colab import drive
drive.mount("/content/drive")
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

- The staged full training run has not completed yet.
- No training duration, GPU memory requirement, kiln-model metric, or selected
  trained checkpoint has been measured or produced.
