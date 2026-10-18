# Dhoa dashboard guide

## What the dashboard delivers

The Streamlit dashboard reads the precomputed
`data/processed/kilns_prioritised.parquet` file. It does not run model inference,
training, or Earth Engine exports. It presents a review workspace with:

- a district summary when one district is selected: candidate total, high-priority
  count, estimated candidate-area footprint, most common rule signal, and a short
  risk summary;
- a selectable high-priority candidate list beside an interactive map of all
  candidates that match the active filters;
- map markers grouped by priority, with an optional high-priority heatmap layer;
- candidate details, navigation links, and a one-candidate inspection PDF;
- a CSV export of the currently filtered candidate set, including coordinates
  and rule-distance fields.

## Review a district and candidate

1. Open **“কীভাবে ব্যবহার করবেন? এখানে ক্লিক করুন”** for the short Bengali usage
   guide, if needed.
2. Open **ফিল্টার** in the sidebar. Choose a district, kiln type, priority,
   confidence range, and any rule signals. **🆕 শুধু নতুন প্রার্থী** limits the
   view to candidates marked as new against the 2023–24 survey. The map style
   can be switched between street and satellite imagery.
3. With a specific district selected, use the summary above the map to see its
   totals, approximate spatial footprint, and most common rule signal. The
   summary is hidden for **All Districts**.
4. Select a row in **অগ্রাধিকার তালিকা** with **ভাটাটি দেখুন**, or click a map
   marker. The map focuses on the selected candidate, and the detail section
   shows its type, confidence, priority, district, coordinates, detection
   status, and available rule distances. Missing mapped distances are shown as
   unavailable rather than as a numeric value.
5. Use the directions, Street View, or Google Earth links to inspect the
   location. After selecting a candidate, use **📄 নির্বাচিত প্রার্থীর PDF
   ডাউনলোড** above the map to download its one-page report.

The candidate list contains high-priority rows only; the map shows all
priority bands that pass the filters. Marker colors distinguish high, medium,
and low priority. The heatmap is an optional map layer and is off by default.

## Export the filtered review queue

Use **⬇ বাছাইকৃত তালিকা CSV ডাউনলোড** in the sidebar. The CSV follows the active
filters and includes candidate ID, district, type, confidence, priority,
detection status, latitude, longitude, rule distances, signal count, review
flag, and rule-data notes. Missing distance values remain empty/NaN; they do not
mean the candidate is near that feature.

The PDF contains one candidate's identity and location, triggered rule signals
with their available distances, and map-navigation URLs. It is generated in
memory when requested; the dashboard does not write report files to disk.

## Community search and report

In the community view, search by place name or coordinates, then set the
search radius with the **search radius (metres)** slider (250 to 5,000 m, in
250 m steps; default 1,000 m). The displayed candidate count and table, blue
map circle, and downloadable community PDF all use the selected radius. Changing
the slider refreshes the results and report. Distances are calculated from the
search point to candidate coordinates using the configured local projected CRS.

The community PDF reports the chosen radius and lists candidate distance, kiln
type, priority, and coordinates. It is generated in memory and is not saved to
disk.

## Responsive use

On desktop, the high-priority list and map appear side by side. On narrow
screens, the sidebar can be opened for filters and exports, the list becomes a
compact selectable view, and the map moves below it. Verify the list selection,
map controls, PDF button, and CSV download in the target browser before a live
demonstration.

## Interpretation

The dashboard is a screening and review interface. A model confidence score is
not field accuracy, and a rule distance is measured to the mapped data used by
the pipeline. Data gaps and source-layer limitations are documented in
[`screening_provenance.md`](screening_provenance.md) and
[`legal_basis.md`](legal_basis.md).
