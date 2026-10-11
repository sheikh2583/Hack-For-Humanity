# Round 2 audit summary

Labels: `data\processed\audit_round2\audit_human_review_BLIND_completed.csv`  
Confidence key: `data\processed\audit_round2\matching_key.csv`

Precision is TP / (TP + FP); SKIP labels are excluded. Intervals are 95% Wilson.
Confidence terciles use equal-count quantiles computed from the merged confidence values.
This is a 20-row targeted review and is descriptive, not a representative district-wide estimate.

| Confidence group | TP / decided | SKIP | Precision | 95% Wilson CI |
|---|---:|---:|---:|---:|
| low | 1 / 7 | 0 | 14.3% | 2.6%-51.3% |
| mid | 1 / 6 | 0 | 16.7% | 3.0%-56.4% |
| high | 3 / 7 | 0 | 42.9% | 15.8%-75.0% |
| Overall | 5 / 20 | 0 | 25.0% | 11.2%-46.9% |

Rows merged: 20.
