# Claude review context: training artifacts and prediction plots

This note records the visual sampling limitation in the completed benchmark
run; it is not a statement that the dashboard outputs are confirmed findings.
Current candidate wording, CSV notices, provenance fields, and unresolved legal
and spatial source dependencies are documented in
[`screening_provenance.md`](screening_provenance.md).

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

For each of the first three saved test batches, the label and prediction JPEGs
are byte-for-byte identical:

- `results/run_0002/checkpoints/heldout_test/val_batch0_labels.jpg` and
  `val_batch0_pred.jpg`
- `results/run_0002/checkpoints/heldout_test/val_batch1_labels.jpg` and
  `val_batch1_pred.jpg`
- `results/run_0002/checkpoints/heldout_test/val_batch2_labels.jpg` and
  `val_batch2_pred.jpg`

This is consistent with the sample contents: the first 48 sorted test label
files (16 images per batch) are empty, and those mosaics show no predictions at
the plot display threshold. The validator saves only the first three batches,
so these artifacts do not visually review positive kiln detections. The
identical files alone do not indicate a broken OBB renderer. If improving
manual review, select representative positive and negative examples instead of
assuming the current first-three-batch mosaics are representative.

The saved confusion matrix and PR/F1 curves indicate weaker FCBK results than
Zigzag (test AP50 0.601 versus 0.904). The confusion matrix shows 151 FCBK
matches out of 246 true FCBK instances, 68 FCBK instances classified as
Zigzag, and 27 missed as background. For Zigzag, it shows 890 matches out of
1,025 true instances, 92 classified as FCBK, and 43 missed as background. It
also shows 359 background false positive detections (125 FCBK, 234 Zigzag).

## Review request

Review low-risk options for making manual review plots representative of both
positive and negative test examples. Do not change training or evaluation
semantics, and do not rerun training or held-out test evaluation as part of a
code proposal.

The ZIP intentionally excludes `results/run_0002/`, model weights, and dataset
files. The descriptions above record the observed state so the source review
has current context; the image artifacts remain local if direct inspection is
needed. No geographic placement or legal conclusions have been verified.
