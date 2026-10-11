# KilnWatch BD: Next Steps Guide

**Written:** 10 Oct 2026 | **Round 2 prototype deadline:** 14 Oct 2026 | **Finale:** 24 Oct 2026

**Goal:** a working, honest, advisory-only demo plus submission materials, delivered with a day of buffer.

**Where you are now**
- Final model: `results/run_0002/checkpoints/final/best.pt` (YOLOv8s-OBB, 512 px)
- Real raster: `data/raw/exports/kilnwatch_chapai_test.tif`
- Audit file: `audit_labeled.csv` (30 rows, 17 TP / 13 FP)
- Still unchecked: the dashboard with the final checkpoint

**Hard rules until the demo is done**
- Do not retrain the model.
- Do not change legal thresholds or coordinates.
- Do not set `preprocessing_verified` to `true`.
- Do not use the audit labels as training data.
- Keep the UI and CSV advisory: describe detections as candidates, configured checks as rule signals, and prompt for human review.

---

## Phase 1: Today (10 Oct) — make the demo trustworthy

### Step 1. Turn the audit labels into a reproducible report
- [ ] Run the `audit-results` command if it exists. If not, ask the coding agent to add it.
- [ ] It should report precision per confidence tercile with Wilson 95% intervals.
- [ ] Save the output next to the audit file and do not edit `audit_labeled.csv`.

**Your pilot numbers, to check against:**

| Tercile | Confidence range | TP / labeled | Precision | Wilson 95% CI |
|---|---|---|---|---|
| Low | 0.10 – 0.22 | 0 / 10 | 0% | 0 – 28% |
| Mid | 0.25 – 0.52 | 7 / 10 | 70% | 40 – 89% |
| High | 0.62 – 0.82 | 10 / 10 | 100% | 72 – 100% |
| Overall | | 17 / 30 | 57% | 39 – 73% |

**Done when:** the generated report matches the table above.

### Step 2. Fix the advisory warning
- [ ] Make the "Advisory only" banner always visible, independent of the `verified` flag in `config/rules.yaml`.
- [ ] A separate display-control field (for example `suppress_dashboard_warning: false`) is one option. Check it against the actual repo before applying.
- [ ] Leave `rules.yaml` thresholds and legal-status fields untouched.

**Done when:** the banner shows on the dashboard with `verified: true` in the config.

### Step 3. Run the real pipeline with the final checkpoint

```powershell
python scripts/run_pipeline.py --weights results\run_0002\checkpoints\final\best.pt --imgsz 512
streamlit run app/streamlit_app.py
```

- [ ] Detections appear on the map for Chapainawabganj.
- [ ] Marker popups show class, confidence and rule signals.
- [ ] CSV export works and uses screening language.
- [ ] The advisory banner is visible.
- [ ] The dashboard shows which parquet file and modification time were loaded.

**Done when:** all five boxes are ticked.

---

## Phase 2: 11 Oct — improve and capture

### Step 4. Add a confidence slider
- [ ] Add a slider to the dashboard and set the default to about 0.3–0.4 instead of 0.1.
- [ ] Why: in your audit, all 10 low-tercile detections were false positives, and every detection above about 0.44 was a true positive (15 of 15).
- [ ] Caveat: this default comes from a 30-row pilot, so describe it as chosen from a pilot, not validated.

### Step 5. Record the backup demo video (2 minutes)
Record this as soon as the dashboard works, not on the last day.
- [ ] Show the map with detections.
- [ ] Open one marker popup.
- [ ] Show the sidebar metrics.
- [ ] Show the advisory notice clearly.
- [ ] Show the CSV export.
- [ ] Save a copy in two places.

---

## Phase 3: 12 Oct — document

### Step 6. Write `docs/ARCHITECTURE.md`
- [ ] Mermaid data-flow diagram: Sentinel-2 raster → patching and normalization → YOLOv8s-OBB → NMS → OSM and rule signals → screening score → dashboard.
- [ ] Model card with the numbers below.
- [ ] A Limitations section (see Step 7).
- [ ] Advisory language throughout: "kiln candidate", "candidate rule signal", "screening score", "screening priority".

**Model numbers (held-out test set, SentinelKilnDB chips)**

| Metric | Value |
|---|---|
| mAP50 | 0.752 |
| mAP50-95 | 0.493 |
| Precision | 0.699 |
| Recall | 0.734 |
| FCBK AP50 | 0.601 |
| Zigzag AP50 | 0.904 |

Do not quote train/val/test split counts until the supporting artifact is identified.

### Step 7. Write the limitations section honestly
Include these points:
- [ ] The test metrics come from dataset chips, not the Chapainawabganj raster.
- [ ] The audit is a 30-row pilot spot-check. The intervals are wide (mid tercile 40–89%).
- [ ] The audit measures precision only. Recall is unknown.
- [ ] Labels mark kiln present or absent, not class (FCBK vs Zigzag).
- [ ] FCBK performance is weaker and its test sample is small.
- [ ] Google Earth imagery may differ in date from the Sentinel-2 scene, and the dataset's own date range is unresolved.
- [ ] Distances are to mapped features (OSM and similar), which may not be the legally controlling boundaries.
- [ ] Legal rule values are screening proxies, not legal conclusions.

### Step 8. Draft the submission materials
- [ ] Describe the project as a non-commercial prototype (the dataset is CC BY-NC 4.0).
- [ ] State clearly that outputs are preliminary candidates for human review.
- [ ] Attach or link the demo video and the architecture doc.

---

## Phase 4: 13–14 Oct — verify and submit

### Step 9. Clean-state check
- [ ] Re-run the full pipeline from a fresh start.
- [ ] Run the tests (should be at least 127 passing) and Ruff (should be clean).
- [ ] Open the dashboard once more and check that nothing has broken.

### Step 10. Submit
- [ ] Aim to submit on 13 Oct and keep 14 Oct as a fallback day.
- [ ] Keep the backup video accessible in case the live demo fails.

---

## Optional, only if time remains

| Item | Value |
|---|---|
| Label about 20 more rows in the mid band (0.25–0.45) | Narrows the widest interval |
| Relabel boundary rows without seeing the confidence column | Checks for anchoring bias |
| Provenance fields and per-popup caveats (Manus prompt) | Stronger audit trail |
| Screen-space and navigation-tab UI polish | Cosmetic only |

---

## Housekeeping
- [ ] **Rotate credentials.** The Manus replay exposed credentials. If they are real and still active, rotate them now.
- [ ] **Check memory use.** Confirm the pipeline reads the 6,680 × 7,793 float64 raster in windows, not all at once.
- [ ] **Keep the audit file untouched** as the record of your pilot labeling.

---

## Quick priority view

1. Advisory fix (Step 2)
2. Dashboard check with final checkpoint (Step 3)
3. Audit report (Step 1)
4. Backup video (Step 5)
5. Architecture doc and limitations (Steps 6–7)
6. Submission (Steps 8–10)
7. Everything else if time allows
