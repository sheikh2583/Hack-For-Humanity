# Training run history

**Updated:** 2026-10-08. Completed runs below are tied to local manifests and
artifacts; the interrupted Windows run is kept as historical evidence.

## Evidence and tracking status (2026-10-08)

There was no new training run recorded on 2026-10-08. The work on that date
was inference, OSM/rule/score pipeline execution, visualization, and project
documentation. The newest training run remains Linux `run_0002`, completed
2026-10-07.

| Machine/run | Training evidence | Git status and limits |
|---|---|---|
| Linux `NDAG-M-Lab`, RTX 3090, `run_0002` | `run.json` records host/platform, Python, PyTorch/CUDA, per-stage GPU identity, run status, model, image size, validation result, dataset fingerprint, and held-out metrics. The four stage CSV logs and smoke CSV are retained. | Manifest, CSV chunks, a retrospective config snapshot, training source, run history, and summarized metrics are Git-trackable. Checkpoints are ignored. The separate raw `test_metrics.json` is absent from this checkout; held-out metric values are present in the tracked `run.json`. Runtime source revision cannot be proven retrospectively. |
| Windows, RTX 4070 Laptop, historical partial run | Recovered smoke and full-run `args.yaml`, metric CSVs, and captured console output identify the machine/runtime and six completed full-stage epochs. | Non-weight evidence is preserved in `results/legacy_windows_rtx4070_20260929/` for Git tracking. The original `runs/` remains ignored. No original per-run manifest, dataset fingerprint, source revision, or full epoch-7 result exists, so full provenance remains incomplete. |

The `run_0002` staged method is documented in its retrospective
`training_config.yaml` snapshot, `config/training.yaml`, and the runner source:
a 3-epoch YOLOv8n-OBB smoke gate, YOLOv8n at 256/384/512, then
YOLOv8s at the best YOLOv8n size, with candidate selection from validation
metrics and one held-out test evaluation. The shared configuration also sets
batch 8, workers 0, patience 10, seed 0, vertical flip 0.5, and rotation 90
degrees. The manifest has been updated with a retrospective pointer to the
config snapshot and its hash. The source commit at runtime remains unknown:
the commit containing that matching config was created after the run finished.
The Windows partial run predates this shared numbered-run manifest workflow
and should not be presented as having equivalent per-machine proof.

The history and progress edits, new manifest support, and recovered Windows
records are currently local changes pending commit. Checkpoints are
intentionally excluded from Git; retain them with their run folder for
reproducibility. A Git-tracked manifest and metrics support auditability, but
do not by themselves reproduce training without the matching dataset, starting
weights, code revision, and environment.

## Linux RTX 3090 run `run_0002`

Run `results/run_0002/` completed on host `NDAG-M-Lab` with Python 3.12.2,
PyTorch 2.14.0+cu130, and Ultralytics 8.4.165. The manifest records the RTX
3090, CUDA runtime 13.0, dataset fingerprint, and hardware identity for each
stage. The smoke gate passed all three epochs, the four configured stages
completed, and the selected model was evaluated once on the held-out test
split.

| Stage | Image size | Epochs | Validation mAP50 |
|---|---:|---:|---:|
| `yolov8n-obb-256` | 256 | 50 | 0.60908 |
| `yolov8n-obb-384` | 384 | 50 | 0.60752 |
| `yolov8n-obb-512` | 512 | 50 | 0.69292 |
| `yolov8s-obb-best` | 512 | 50 | 0.70546 |

The selected checkpoint is
`results/run_0002/checkpoints/final/best.pt` (YOLOv8s-OBB, 512 px). Held-out
metrics, recorded in the Git-tracked `run.json`, are:

| Metric | Result |
|---|---:|
| mAP50 | 0.75244 |
| mAP50-95 | 0.49299 |
| Precision | 0.69856 |
| Recall | 0.73354 |

The test report gives class AP50 0.601 for FCBK and 0.904 for Zigzag. The
confusion matrix records 151 FCBK matches of 246 true instances (68 assigned
to Zigzag, 27 missed), 890 Zigzag matches of 1,025 true instances (92 assigned
to FCBK, 43 missed), and 359 background false positive detections. These
metrics are dataset evaluation results, not field-accuracy evidence.

Epoch metrics are archived in `results/run_0002/logs/`; the run manifest is
`results/run_0002/run.json`; the separate test metrics file is not present in
this checkout. The final checkpoint is ignored by Git under `checkpoints/`.

The saved validation mosaics cover only the first three batches. All 48
corresponding test label files are empty, so labels and prediction mosaics are
identical and do not visually review positive detections. This is consistent
with the sampled inputs and does not by itself indicate a plotting defect.
Manual review should include representative positive detections and false
positives before the checkpoint is used.

## Historical Windows RTX 4070 run

The Windows smoke run completed three epochs using YOLOv8n-OBB at 256 px,
batch 8, workers 0. Its retained CSV final row records validation mAP50
0.52184 and mAP50-95 0.25290. Earlier notes cite a separate validation value
of 0.5226 / 0.2527; that separate metric record is not retained, so the values
remain distinct.

The first full YOLOv8n 256 px stage was interrupted partway through epoch 7
after six completed validation rows. Its partial checkpoint remains under
ignored `runs/yolov8n-obb-256/` and was not resumed by `run_0002`, which started
a fresh numbered run from the configured pretrained weights. Recovered
non-weight logs and arguments are in
[`results/legacy_windows_rtx4070_20260929/`](../results/legacy_windows_rtx4070_20260929/README.md).

## Future runs and review

The next invocation without a run ID allocates the next run number because
`run_0002` is complete. To continue an incomplete numbered run, use
`bash scripts/train_linux.sh continue --run-id run_NNNN` with the same dataset
fingerprint and its complete run folder. Review and commit staged manifests and
CSV logs explicitly; checkpoint weights remain ignored.

The training user manages GPU runs. Do not start or stop training, inference,
smoke tests, or benchmarks without explicit authorization for that workload.

## Still outstanding

- Visual review of representative positive predictions and false positives.
- Inference on exported real Sentinel-2 GeoTIFFs and geographic placement
  review.
- Earth Engine acquisition-date resolution and paired-chip calibration before
  enabling preprocessing verification.
- Human verification of legal thresholds and OSM coverage before any
  compliance interpretation.
