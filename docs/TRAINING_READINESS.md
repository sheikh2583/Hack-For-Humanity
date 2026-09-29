# Training start readiness

**Checked:** 2026-09-29. This is a check against the current scaffold, converted
dataset, and `notebooks/train.ipynb`. Training itself was not run.

## Dataset and notebook status

The local converted dataset is present at `data/interim/yolo_obb/` and is ready
for the notebook's smoke-test input:

| Split | Images | Labels |
|---|---:|---:|
| train | 8,058 | 8,058 |
| val | 1,662 | 1,662 |
| test | 1,530 | 1,530 |

The tree is about 350.7 MiB. Its `dataset.yaml` defines the expected classes
FCBK and Zigzag, and `split_report.json` records the 1,300 m Chebyshev leakage
filter with a final minimum cross-split distance of 1,322.41 m. The notebook
contains the 3-epoch `yolov8n-obb` smoke test and the staged full-training plan.
The workspace search found no pretrained `.pt` weights.

## What is genuinely needed before starting the smoke test

1. **A hosted GPU runtime.** The local workspace has CPU-only PyTorch
   (`2.14.0+cpu`; `torch.cuda.is_available()` is false). The project instructions
   put training on Colab/Kaggle; do not start model training in this local venv.
   The notebook now stops during setup if CUDA is unavailable.
2. **Make the converted dataset reachable from that runtime.** The notebook's
   current default `DATASET_ROOT=Path("data/interim/yolo_obb")` is the local
   repository path. Upload/copy the complete converted folder (about 351 MiB)
   to Drive or attach it as a Kaggle dataset, then set `DATASET_ROOT` to the
   mounted/attached directory containing `dataset.yaml`, `split_report.json`,
   and the `train`, `val`, and `test` subdirectories. The project ZIP does not
   include this data.
3. **Set an output location.** The notebook's default `OUTPUT_DIR=Path("runs")`
   is runtime-local. For results to survive a Colab reset, mount Drive and set
   `OUTPUT_DIR` to a Drive folder. This is needed for persistence, not to launch
   the smoke test.
4. **Allow dependency and initial weight downloads if the runtime cache lacks
   them.** The notebook now checks the installed Ultralytics version and only
   installs when it is missing or older than 8.1. `yolov8n-obb.pt` is fetched
   on first use if not cached; `yolov8s-obb.pt` is needed later for stage 2.

After those setup choices, run notebook cells in order through the data sanity
check, absolute YAML creation, helpers, and smoke-test cell. Continue to the
full configurations only if the smoke-test cell passes.

## Local versus hosted setup examples

The paths below are examples for mounted Google Drive; create/upload the
converted directory first and adjust the Drive paths to match its actual
location:

```python
from google.colab import drive
drive.mount("/content/drive")
DATASET_ROOT = Path("/content/drive/MyDrive/kilnwatch/yolo_obb")
OUTPUT_DIR = Path("/content/drive/MyDrive/kilnwatch/runs")
```

For Kaggle, attach the converted dataset and set `DATASET_ROOT` to its mounted
directory under `/kaggle/input/`; `OUTPUT_DIR` can be under `/kaggle/working/`.

## Not blockers for training the existing converted chips

- The unresolved SentinelKilnDB acquisition-date conflict and
  `preprocessing_verified: false` govern Earth Engine parity/export. They do
  not prevent training on the already converted PNG chips. They must be
  resolved before claiming that newly exported imagery matches training data.
- Legal threshold verification and unfinished downstream evaluation utilities
  are not prerequisites for detector training. They remain blockers to legal
  interpretation or a complete project handoff.

## Still unverified

- The smoke test and full notebook have not run on Colab/Kaggle.
- Hosted GPU availability, storage quota, runtime internet access, and actual
  download behavior are account/session-specific and must be checked there.
- No training duration, GPU memory requirement, model metric, or checkpoint has
  been measured or produced.
