# Claude Web review prompt

Upload `kilnwatch_bd_share.zip` to Claude Web, then paste this prompt:

```text
Review the attached KilnWatch BD project as an independent technical reviewer.
Read AGENTS.md, docs/PROGRESS.md, docs/TRAINING_READINESS.md,
docs/TRAINING_RUN_HISTORY.md, docs/MEMORY_AND_DOWNLOADS.md, and
kilnwatch_scaffold.md first. Inspect the code/config/notebook in the ZIP before
making claims. Use primary sources and direct links for source-dependent legal
or dataset claims. Do not edit code or invent schemas, legal rules, thresholds,
dates, or coordinates.

## Current verified state

- Linux run results/run_0002 completed on host NDAG-M-Lab using an RTX 3090,
  Python 3.12.2, PyTorch 2.14.0+cu130, and Ultralytics 8.4.165. The smoke gate,
  all four configured stages, and one held-out test evaluation completed.
- The selected checkpoint is results/run_0002/checkpoints/final/best.pt:
  YOLOv8s-OBB at 512 px. Validation mAP50 was 0.70546. Held-out test metrics
  were mAP50 0.75244, mAP50-95 0.49299, precision 0.69856, and recall 0.73354.
  Test AP50 was 0.601 for FCBK and 0.904 for Zigzag. These are dataset metrics,
  not field-accuracy evidence.
- The first three test visualization batches contain 48 blank-label images;
  label and prediction mosaics are identical. They do not visually review
  positive detections. The local artifacts are excluded from the ZIP; see
  docs/CLAUDE_REVIEW_CONTEXT.md for findings.
- The converted dataset is data/interim/yolo_obb/: train 8,058 images, val
  1,662, test 1,530. Its split report records a 1,300 m Chebyshev leakage
  filter and 1,322.41 m minimum cross-split distance. Starting weights are in
  data/models/; the selected trained checkpoint is separate.
- Historical local test evidence from 2026-10-06 was 101 passed and one
  skipped; Ruff passed then. The current suite has not been rerun after later
  changes. Do not claim those checks cover subsequent edits.
- Earth Engine export and inference on exported real Sentinel-2 imagery have
  not run. config/preprocessing.yaml remains preprocessing_verified: false
  because published date ranges conflict and paired-chip calibration has not
  been completed. Rules in config/rules.yaml remain legally unverified.
- No representative positive detections, geographic placement, OSM coverage,
  field accuracy, or legal compliance conclusion has been human-verified.
  GPU workloads remain user-managed unless explicitly requested.

## Review questions

1. Check the SentinelKilnDB acquisition-date discrepancy against primary
   sources. The authors' downloader, repository text, NeurIPS supplement, and
   Hugging Face card have conflicting date ranges. Determine whether evidence
   resolves which dates produced the released chips; otherwise give exact
   clarification questions for the dataset authors.
2. Review the preprocessing and Earth Engine gates. Identify evidence needed
   before setting preprocessing_verified: true; do not infer an acquisition
   period or claim parity without paired-chip results.
3. Review legal claims and thresholds against authoritative Act/gazette
   sources. Identify unsupported claims and exact passages needing human
   review. Do not propose replacement thresholds without primary evidence.
4. Review code for concrete correctness, security, memory, and performance
   issues. Separate code-inspection conclusions from measurements; do not
   claim an optimization is faster without a benchmark.
5. Check whether manual review plots should sample representative positive and
   negative examples instead of only the first three validation batches.
6. Compare scaffold promises with implementation and identify remaining
   blockers for a local demo and a real imagery pilot. Verify all claimed gaps
   against the ZIP rather than copying stale status text.

## Return

- Readiness for model experimentation, local demo, and real imagery pilot,
  assessed separately.
- A prioritized table of concrete blockers, evidence, next action, owner, and
  dependencies.
- Exact dataset-author questions if dates remain unresolved.
- Any stale documentation or contradiction found in the ZIP.
- A short next-step sequence. Preserve the completed model/run artifacts and
  do not rerun training or held-out test evaluation as part of this review.

Be explicit about uncertainty and distinguish verified facts, code-inspection
conclusions, and inference. Do not mark preprocessing or legal rules verified
without evidence.
```
