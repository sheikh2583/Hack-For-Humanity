# Dhoa — five-minute finale demo

## Before the demo

Start the dashboard with the intended `data/processed/kilns_prioritised.parquet`
available. Check that the data loads, all five pilot districts are selectable,
the candidate list and map render, and both CSV and PDF downloads work. Select a
candidate that has recorded rule distances so its detail view can be shown.
For full operator instructions, see [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md).

## Run of show (5:00)

### 1. Dashboard overview (0:00–0:35)

**Show:** Header metrics, the Bengali **কীভাবে ব্যবহার করবেন? এখানে ক্লিক করুন**
guide control, and the candidate list/map workspace.

**Say:** “This dashboard helps a reviewer explore a ranked set of kiln
candidates. The priority colors organize the review list; they do not show
legal status.”

### 2. Select a district and review the summary (0:35–1:10)

**Show:** Open **ফিল্টার**, select a pilot district, and point out the district
summary: total candidates, high-priority candidates, estimated candidate area,
and the most common rule signal.

**Say:** “The summary updates for the selected district. The area is an
approximate footprint of the candidate locations, and the rule signal is based
on the currently recorded mapped data.”

### 3. Filter and select a candidate (1:10–2:30)

**Show:** Use the priority, confidence, or rule-signal filter. Select **ভাটাটি
দেখুন** beside a high-priority row, then show the matching map location and
candidate details. Briefly point to available distances and the navigation
links. If useful, switch the heatmap on through the map layer control.

**Say:** “The list focuses on high-priority candidates, while the map shows all
priority bands that pass the filters. Selecting a row or marker focuses the map
and opens the candidate details. Distances refer to mapped features.”

### 4. Download the report and filtered CSV (2:30–3:15)

**Show:** With a candidate selected, download its PDF from the control above
the map. Then download the filtered CSV from the sidebar and point out its
latitude, longitude, priority, and rule-distance columns.

**Say:** “The PDF is a single-candidate report with navigation links. The CSV
exports the current filtered review queue, including candidate coordinates and
mapped-distance fields.”

### 5. Explain the pipeline (3:15–4:00)

**Show:** The workflow diagram in [ROUND2_SUBMISSION.md](ROUND2_SUBMISSION.md).

**Say:** “We start with Sentinel-2 imagery, run the YOLOv8s-OBB detector to
propose kiln candidates, compare their locations with configured project
signals and mapped features, then calculate a priority score. The dashboard
lets a reviewer explore and export the results.”

### 6. Limitations and next steps (4:00–5:00)

**Say:** “This is a five-district screening pilot. Held-out chip metrics are not
field accuracy. Mapped features may be incomplete or differ from authoritative
boundaries, and the results need human review. Next steps include field
validation, resolving the imagery-date and preprocessing questions, and
checking coverage before adding districts.”

### Likely judge questions

1. **Why not use existing kiln maps?** — “Existing maps can help with review;
   we have not completed a comparative evaluation to claim this ranking is
   novel.”
2. **How accurate is it?** — “Held-out SentinelKilnDB chip mAP50 is 0.752.
   That metric does not estimate accuracy on the Bangladesh raster pilot or in
   the field.”
3. **What if a candidate is already authorized?** — “The dashboard does not
   establish legal status. A reviewer must check authoritative records before
   any decision.”
4. **Does it scale?** — “The current processed output covers five districts.
   Other districts need imagery, boundary mapping, and mapped-feature coverage
   checks.”
5. **What’s next?** — “Field validation, source and preprocessing review, and a
   pilot with the relevant agencies.”
