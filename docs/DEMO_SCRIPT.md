# Dhoa — five-minute finale demo

## Before the demo

Open the Streamlit dashboard with the current processed GeoParquet selected. Confirm all five districts appear, the map renders, filters respond, and the CSV button works. Choose a high-priority marker with non-empty class, confidence, rule-signal, and nearest-mapped-school fields. The school distance is to mapped data and is not a legal boundary measurement.

## Run of show (5:00)

### 1. Map and priority colors (0:00–0:30)

**Show:** The map with candidates from Chapainawabganj, Gazipur, Rajshahi, Dhaka, and Chittagong.

**Say:** “Each point is a kiln candidate for human review. Red marks high priority, orange medium, and green low priority. These colors order a review queue; they do not represent legal status.”

### 2. Inspect a high-priority candidate (0:30–1:30)

**Show:** Click the highest-priority red marker and point to its class, confidence, rule signals, and distance to the nearest mapped school.

**Say:** “This popup shows the model class and confidence, the project rule signals associated with the point, and its distance to the nearest mapped school. Those signals depend on available mapped data and need human checking. The marker is a screening candidate, not a screening output that establishes legal status.”

### 3. Filter to FCBK (1:30–2:00)

**Show:** Use the kiln-class filter to select FCBK only.

**Say:** “The map now shows FCBK candidates. Our project flags this class for technology review as a screening heuristic. The class alone does not establish kiln age, actual technology, or legal status.”

### 4. Export CSV (2:00–2:30)

**Show:** Download the CSV and point out candidate ID, district, class, confidence, signals, and priority fields that are present.

**Say:** “This export is a ranked review queue an inspector can check and annotate. It is a starting point for human review, not an official work order or evidence for enforcement.”

### 5. Explain the pipeline (2:30–3:30)

**Show:** The pipeline diagram in [ROUND2_SUBMISSION.md](ROUND2_SUBMISSION.md).

**Say:** “We start with Sentinel-2 imagery, run the YOLOv8s-OBB detector to propose kiln candidates, compare those locations with configured project signals and mapped features, then calculate an exposure-weighted priority score. The dashboard lets a reviewer explore and export the results. Sentinel-2 data products are free; Earth Engine account, quota, and export conditions may still apply.”

### 6. State limitations (3:30–4:00)

**Say:** “This is an advisory five-district pilot. Outputs are preliminary screening candidates. The model’s held-out chip metrics are not field accuracy, and rule signals, mapped-feature coverage, preprocessing, and candidate locations need review. A human must review results before any inspection decision.”

### 7. Likely judge Q&A (4:00–5:00)

Keep answers short; offer to follow up on evidence that is not in the demo.

1. **“Why not use existing kiln maps?”** — “Our goal is to help prioritize review by mapped exposure. Existing maps can be useful inputs; we have not completed a comparative evaluation to claim our ranking is novel.”
2. **“How accurate is it?”** — “Held-out SentinelKilnDB chip mAP50 is 0.752. An earlier exploratory Google Earth review found visible kiln structures in 15 of 15 candidates above confidence 0.44, but that cutoff was examined on the same small sample and the review came from a prior run. It is not a field-accuracy estimate.”
3. **“What if you flag a legal kiln?”** — “The dashboard cannot establish legal status. A reviewer must check the candidate against authoritative records and field evidence before taking action.”
4. **“Does it scale?”** — “We have processed five districts. A new district needs an imagery export and configuration, plus boundary-name and mapped-feature checks. We still need to validate that workflow in additional districts.”
5. **“What’s next?”** — “A Department of Environment pilot, field validation, checking the source for the reported 2022 clearance count, and then adding districts with validated data.”
