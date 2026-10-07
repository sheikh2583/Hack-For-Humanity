# Training setup and completed run

**Updated:** 2026-10-08. The Linux RTX 3090 training run completed as
`results/run_0002/`. This document records the verified run and the remaining
review steps. Run-by-run evidence is in
[`TRAINING_RUN_HISTORY.md`](TRAINING_RUN_HISTORY.md).

## Training inputs and environment

The converted SentinelKilnDB YOLO-OBB dataset is in
`data/interim/yolo_obb/`:

| Split | Images/labels | FCBK instances | Zigzag instances |
|---|---:|---:|---:|
| train | 8,058 | 1,773 | 5,589 |
| val | 1,662 | 214 | 1,803 |
| test | 1,530 | 246 | 1,025 |

The dataset report records a 1,300 m Chebyshev leakage filter and 1,322.41 m
minimum cross-split distance. Starting weights are in `data/models/`:
`yolov8n-obb.pt` (6,567,590 bytes) and `yolov8s-obb.pt` (23,267,238 bytes).
These are initialization weights; the trained selected model is recorded below.

Run `run_0002` records Linux, Python 3.12.2, PyTorch 2.14.0+cu130,
Ultralytics 8.4.165, and NVIDIA GeForce RTX 3090 (24,121 MiB reported by
PyTorch). Training completed with batch 8 and zero data-loader workers. The
training host and CUDA stack were exercised by this run.

## Completed run `run_0002`

The 3-epoch smoke gate passed, all four configured stages completed, and the
selected model was evaluated once on the held-out test split using validation
mAP50 for candidate selection. Detailed metrics, stages, artifact paths, and
plot-sampling limitations are recorded once in
[`TRAINING_RUN_HISTORY.md`](TRAINING_RUN_HISTORY.md). The selected checkpoint
is `results/run_0002/checkpoints/final/best.pt` (YOLOv8s-OBB at 512 px).
The test metrics are dataset evaluation results, not evidence of field
accuracy. The first three test mosaics do not cover positive examples; inspect
representative validation examples before use.

## Historical Windows run

The Windows RTX 4070 smoke run completed three epochs. Its first full YOLOv8n
256 px stage was interrupted during epoch 7 after six completed validation
rows. That historical partial checkpoint remains under `runs/` and was not
imported into `run_0002`.

## Running another training job

The canonical runner is `scripts/train.py`, with Linux and Windows wrappers.
The initializer installs dependencies and prepares assets; it does not start
training. For a future new run, use `bash scripts/train_linux.sh` on Linux or
the documented PowerShell wrapper on Windows. The default flow runs smoke and
then configured stages. Use `full` to continue a run whose smoke gate has
already passed. The runner allocates a new numbered run when the current one
is complete; it does not overwrite `run_0002`.

GPU workloads are user-managed. Do not start, stop, or run another training,
inference, smoke test, or benchmark unless the user explicitly requests that
specific GPU work.

## Not established by training

- Visual correctness of individual detections: inspect positive examples and
  false positives manually. Test results show weaker FCBK AP50 (0.601) than
  Zigzag AP50 (0.904).
- Detection placement on real exported Sentinel-2 rasters, cross-tile duplicate
  handling, and field accuracy.
- The provenance, licence, and human review of boundary files.
- Earth Engine preprocessing parity. `config/preprocessing.yaml` remains
  `preprocessing_verified: false` because published acquisition dates conflict
  and paired exported chips have not been calibrated.
- Legal rule thresholds. Values in `config/rules.yaml` remain unverified and
  must not be treated as legal findings.
- OSM coverage for the intended pilot area.

The advisory dashboard/export semantics and signal provenance requirements are
documented in [`screening_provenance.md`](screening_provenance.md).

Training uses the already converted local SentinelKilnDB chips; it does not
require Earth Engine authentication. The date and preprocessing questions
remain gates for new Sentinel-2 exports, not for the completed training run.
