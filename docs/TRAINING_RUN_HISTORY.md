# Training run history and next run

**Updated:** 2026-09-29. This records the actual Windows training artifacts and
the planned Linux run. A planned run is not evidence that training started.

## Historical Windows RTX 4070 run

Evidence is in the local, Git-ignored `runs/` directory. These artifacts are
not in `results/` and are not part of the new numbered runner's automatic
resume path.

| Run | Configuration | Outcome | Evidence |
|---|---|---|---|
| Smoke | `yolov8n-obb.pt`, 256 px, 3 epochs, batch 8, workers 0 | Completed all 3 epochs | `runs/smoke-yolov8n-obb-256/results.csv`, plots in `runs/smoke-yolov8n-obb-256/` and `runs/smoke_artifacts/` |
| First full stage | `yolov8n-obb.pt`, 256 px, 50 planned epochs, batch 8, workers 0 | Six validation epochs completed; the saved console ends partway through epoch 7. The user stopped the run. | `runs/yolov8n-obb-256/results.csv`, `runs/full_training_console.log`, and `runs/yolov8n-obb-256/weights/{best,last}.pt` |

The smoke `results.csv` final row records validation mAP50 **0.52184** and
mAP50-95 **0.25290**. Earlier project notes report a separate smoke validation
at **0.5226** and **0.2527**; the separate metric record is not present among
the retained artifacts, so keep the CSV values attributed to the training run
and do not merge the two measurements.

The full-stage CSV has six completed rows. Its epoch 6 validation values are
mAP50 **0.46018** and mAP50-95 **0.22179**. These are an incomplete-run
snapshot, not final validation or test results. The files `best.pt` and
`last.pt` are partial checkpoints; neither was evaluated on the held-out test
split. No 384/512 px stage, YOLOv8s stage, final model selection, or test
evaluation completed.

## Planned Linux RTX 3090 run

The user plans to start a new run overnight on the lab Linux RTX 3090. At this
update, the current checkout has no numbered result folder; `results/run_0001/`
is the expected first ID if no other process creates a run first. This is a
**fresh numbered run**, not a continuation of the old Windows
`runs/yolov8n-obb-256` checkpoint. Confirm the converted dataset and both
pretrained weights are available on the lab machine first. If its clone lacks
the converted dataset, transfer the ignored archive separately and initialize
with:

```bash
bash scripts/init_linux.sh --dataset-archive yolo_obb_1300m.zip
```

After the Linux initializer and data/weight preflight are complete, the user
starts the automatic smoke-then-full flow with:

```bash
bash scripts/train_linux.sh
```

If interrupted, rerunning that command continues the active numbered run. To
name the continuation explicitly:

```bash
bash scripts/train_linux.sh continue --run-id run_0001
```

The runner records the actual host, requested device, GPU model, VRAM, PyTorch
and CUDA versions, and stage in `results/run_0001/run.json`. Epoch metric
archives and the manifest are staged by the runner; model checkpoints remain
ignored under `results/run_0001/checkpoints/`.

## Morning handoff

After the Linux run, inspect `run.json` to confirm the recorded accelerator is
the lab RTX 3090, check the run status and completed epoch rows, and retain the
final console output. Report any failed or interrupted stage before attempting
to continue. Held-out test metrics should only be recorded if the runner
reached its test-evaluation step. Update this history with the actual run ID,
dates, outcome, saved artifacts, and metrics; do not fill planned values in as
completed results.

The lab host, driver compatibility, actual overnight duration, and achieved
metrics remain unverified until the user runs and inspects that job.
