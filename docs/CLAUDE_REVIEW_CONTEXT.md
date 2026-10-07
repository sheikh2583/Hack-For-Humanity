# Claude review context: training artifacts and prediction plots

## Current training run

`results/run_0002/` completed on the Linux RTX 3090 using Python 3.12.2,
PyTorch 2.14.0+cu130, and Ultralytics 8.4.165. Its `run.json` status is
`complete`. All four configured training stages completed, the selected
checkpoint is `checkpoints/final/best.pt`, and the held-out test split was
evaluated once.

The selected stage was `yolov8s-obb-best` at 512 px. Validation mAP50 was
0.70546. Held-out test metrics were mAP50 0.75244, mAP50-95 0.49299,
precision 0.69856, and recall 0.73354. These aggregate metrics do not establish
that the individual detections are visually correct.

## Visual review finding

The held-out test prediction mosaics are not usable for a label-versus-prediction
review. For each of the three saved batches, the corresponding label and
prediction JPEGs are byte-for-byte identical:

- `results/run_0002/checkpoints/heldout_test/val_batch0_labels.jpg` and
  `val_batch0_pred.jpg`
- `results/run_0002/checkpoints/heldout_test/val_batch1_labels.jpg` and
  `val_batch1_pred.jpg`
- `results/run_0002/checkpoints/heldout_test/val_batch2_labels.jpg` and
  `val_batch2_pred.jpg`

The images show the chip mosaics without visible box annotations. The saved
confusion matrix and PR/F1 curves are available locally and indicate weaker
FCBK results than Zigzag (test AP50 0.601 versus 0.904). The confusion matrix
shows 151 FCBK matches out of 246 true FCBK instances, 68 FCBK instances
classified as Zigzag, and 27 missed as background. For Zigzag, it shows 890
matches out of 1,025 true instances, 92 classified as FCBK, and 43 missed as
background. It also shows 359 background false positive detections (125 FCBK,
234 Zigzag).

## Review request

Inspect the training and evaluation plotting path, especially the call that
produces the held-out test `val_batch*_labels.jpg` and `val_batch*_pred.jpg`
files. Explain why the outputs are identical and propose a small, testable code
change that creates useful OBB label/prediction comparison images. Preserve
the current model, training results, and test metrics. Do not rerun training or
held-out test evaluation as part of the code proposal.

The ZIP intentionally excludes `results/run_0002/`, model weights, and dataset
files. The descriptions above record the observed state so the source review
has current context; the image artifacts remain local if direct inspection is
needed. No geographic placement or legal conclusions have been verified.
