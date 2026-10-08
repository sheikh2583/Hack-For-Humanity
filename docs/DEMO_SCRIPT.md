# KilnWatch BD — 5-minute finale demo

## Before the judges arrive

Start the local Streamlit dashboard with a processed GeoParquet available in `data/processed/`. Confirm which `kilns*.parquet` file the app will select. Keep [ROUND2_SUBMISSION.md](ROUND2_SUBMISSION.md) open for the pipeline and limitations.

**Current-build note:** the checked-in dashboard shows map markers, summary counts, class/confidence/rule IDs/priority in the marker popup, and a CSV download. It currently has no district/class filter controls, and its popup does not show the school-distance field. The source parquet may contain `dist_schools_m`, but the dashboard popup does not display it. Do not pretend those two requested interactions work: state the gap plainly and use the time to show the available counts and CSV fields. The script below preserves the requested timing and gives an honest fallback.

## Run of show (5:00)

### 1. Open the dashboard and orient the judges (0:00–0:30)

**Say:** “This is KilnWatch BD, a local screening dashboard for possible brick-kiln locations in Bangladesh. Each marker is a model candidate, colored by screening priority. The basemap can switch between street and satellite views. A marker is a lead for review, not a legal finding.”

Point out the total detections, class counts, district summary, and layer control. Basemap tiles need an internet connection.

### 2. Inspect a high-priority candidate (0:30–1:30)

Click a red/high-priority marker. Point to the detected class, detector confidence, candidate rule IDs, and priority rank.

**Say:** “The popup separates the model's confidence from the mapped-feature rule signals. In this dashboard build the popup does not expose the nearest-school distance, so I won't infer one from the marker. The processed output can include `dist_schools_m`; exposing it here is a follow-up.”

If judges require the school distance, open the matching row in the exported/processed data only if the currently selected file actually has a non-null `dist_schools_m` value. Describe it as distance to mapped feature geometry, not a legally controlling boundary.

### 3. Explain district and class counts (1:30–2:00)

**Say:** “The sidebar currently reports overall FCBK and Zigzag counts and the district names represented in the loaded file. Interactive district and class filters are not implemented in this build, so these totals do not change when I select a filter.”

Show the class totals and explain that filtering is a requested interface improvement, not a capability to claim in this live demo.

### 4. Export and inspect the CSV (2:00–2:30)

Click **Export CSV**, open the downloaded file, and show a few headers. The dashboard exports the loaded GeoParquet attributes with geometry removed. In the current prioritized sample these include `kiln_id`, `class`/`class_name`, `confidence`, `district`, `lat`, `lon`, `dist_schools_m`, `dist_hospitals_m`, `dist_settlements_m`, `breached_rules`, `breach_score`, `priority`, and `priority_rank`; exact columns depend on the selected input file.

**Say:** “These fields let an analyst review candidate type, confidence, mapped distances, rule signals, and rank. They remain advisory attributes.”

### 5. Walk through the pipeline (2:30–3:30)

Show the Mermaid diagram in [ROUND2_SUBMISSION.md](ROUND2_SUBMISSION.md).

**Say:** “Sentinel-2 chips go through preprocessing and tiling. YOLOv8s-OBB proposes oriented kiln candidates. We place them geographically, compare their locations with available mapped features and configured draft rules, then calculate a screening priority from exposure. The dashboard reads the resulting GeoParquet. The rule stage identifies candidate signals; it does not establish a legal violation.”

Mention that the team re-split chips by spatial blocks and applied a 1,300 m cross-split leakage filter; the exact Bangladesh chip count is being reconciled between the brief and generated report.

### 6. State limitations (3:30–4:00)

**Say:** “This is advisory screening, not legal evidence. Preprocessing remains unverified because published SentinelKilnDB acquisition dates conflict and exported chips have not been calibrated against the training chips. We have no field validation, legal rules remain unverified, and the FCBK test AP50 is weaker than Zigzag. These markers are candidates for human review, not findings.”

### 7. Judge Q&A preparation (4:00–5:00)

1. **How accurate is it in the field?** “We do not have field-validation results. The reported test mAP50 is 0.752 on a held-out dataset split; it should not be read as field accuracy.”
2. **Why is FCBK weaker?** “Its test AP50 is 0.601 versus 0.904 for Zigzag. That gap is a known limitation; we need representative error review and more validation before operational use.”
3. **Are the legal thresholds verified?** “No. The project records the Act section and candidate distances, but rule values, current legal force, feature coverage, and GIS boundary interpretation remain unverified.”
4. **Why is preprocessing unverified?** “The dataset's published date sources conflict, and we do not have paired exported chips to calibrate the Earth Engine preprocessing against the training data. The export gate stays closed until those checks are resolved.”
5. **How did you prevent train/test leakage, and how many chips are used?** “We re-split spatially using 0.25° cells and a 1,300 m Chebyshev-distance filter. The Round 2 brief says 11,409 Bangladesh chips, while the current report says 11,517 inside Bangladesh and 11,250 written after filtering; we will reconcile that count before making a final dataset-size claim.”
