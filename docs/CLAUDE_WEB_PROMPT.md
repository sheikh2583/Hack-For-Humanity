# Claude Web review prompt

Upload `kilnwatch_bd_share.zip` to Claude Web, then paste this prompt:

```text
Review the attached KilnWatch BD project as an independent technical reviewer.
Read AGENTS.md, README.md, docs/CLAUDE_SHARING_AND_SETUP.md,
docs/screening_provenance.md, docs/legal_basis.md, docs/PROGRESS.md,
docs/TRAINING_RUN_HISTORY.md, and kilnwatch_scaffold.md first. Inspect the
code/config/notebook in the ZIP before
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
- On 2026-10-08 the Windows workspace completed the full local pipeline using
  `runs/yolov8n-obb-256/weights/best.pt`: 1,880 demo-chip detections over 1,530
  chips; 1,219 real-raster detections over 5,440 tiles; local PBF extraction
  for six OSM layers in Chapainawabganj and Gazipur; rule checks; and priority
  scoring. This did not call Earth Engine. The runtime outputs and PBF are
  excluded from the share ZIP.
- The real-raster run used `imgsz=512` with a checkpoint trained at 256 px and
  emitted a warning. CPU/CUDA outputs from a prior run differed by one
  detection. Inspect geographic placement and representative predictions;
  these results are not field validation.
- The full pytest suite reported 146 passed on 2026-10-08. Changed OSM files
  passed Ruff; a repository-wide Ruff scan found six pre-existing findings in
  `app/popup.py`, `scripts/make_review_zip.py`, `src/training/run_store.py`,
  and `tests/test_priority.py` at that time. Re-run checks against the actual
  ZIP contents before relying on these statuses.
- No Earth Engine export was made. `config/preprocessing.yaml` remains
  `preprocessing_verified: false` because published date ranges conflict and
  paired-chip calibration has not been completed. Legal thresholds must only
  be treated as verified if the included config and primary-source evidence
  support that status; do not infer verification from an output field alone.
- No representative positive detections, geographic placement, OSM coverage,
  field accuracy, or legal/administrative status has been confirmed by an
  authorized reviewer. Dashboard and CSV values are advisory screening
  candidates. Rule signals default to `unverified_candidate`; detector
  confidence is not legal confirmation. See docs/screening_provenance.md for
  known provenance limits, legacy-data gaps, and unresolved source dependencies.
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
5. Review whether current provenance fields can be populated from actual
   producers and identify compatibility risks for legacy data.
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

Do not describe a model or GIS result as a breach, illegal, non-compliant, or
verified. Distances are to mapped features and may not match legally controlling
boundaries. Do not change legal thresholds or verification fields based on
secondary sources alone.

Be explicit about uncertainty and distinguish verified facts, code-inspection
conclusions, and inference. Do not mark preprocessing or legal rules verified
without evidence.
```
