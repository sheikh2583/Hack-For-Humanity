# KilnWatch BD — Round 2 submission

## The problem

The project brief reports 112 brick kilns in Chapainawabganj without valid Department of Environment clearance in 2022. That figure and its underlying register have not been independently checked in this repository. Inspectors need a ranked review queue to help prioritize limited attention instead of starting from a flat list.

## What we built

KilnWatch BD combines free Sentinel-2 imagery, YOLOv8s-OBB kiln detection, project rule signals informed by the [Brick Manufacturing and Kiln Establishment (Control) Act, 2013 (Act 59 of 2013)](https://bdlaws.minlaw.gov.bd/act-details-1140.html), an exposure-weighted priority score, and a Streamlit inspector dashboard. The rule signals and mapped features are screening proxies; they do not determine legal status.

The workflow is:

```mermaid
flowchart LR
    A[Sentinel-2 imagery] --> B[Preprocess and tile]
    B --> C[YOLOv8s-OBB detection]
    C --> D[Geographic candidate points]
    D --> E[Configured rule signals]
    E --> F[Exposure-weighted priority]
    F --> G[Streamlit review dashboard]
```

## Current reach

The processed priority dataset contains 2,150 candidate rows across five pilot districts: Chapainawabganj, Gazipur, Rajshahi, Dhaka, and Chittagong. Counts below are rows in the current local output, not a census of kilns.

| District | Candidate rows |
| --- | ---: |
| Chapainawabganj | 282 |
| Gazipur | 270 |
| Rajshahi | 257 |
| Dhaka | 613 |
| Chittagong | 728 |
| **Total** | **2,150** |

The requested estimate of 4,000+ candidates is not supported by the current processed parquet files, so it is not used here.

## Model evaluation

On the held-out SentinelKilnDB chip test split, the reported metrics are:

| Metric | Result |
| --- | ---: |
| mAP50 | 0.752 |
| mAP50-95 | 0.493 |
| Precision | 0.699 |
| Recall | 0.734 |
| FCBK AP50 | 0.601 |
| Zigzag AP50 | 0.904 |

Source: held-out test set, SentinelKilnDB dataset chips only. These metrics do not describe the raster pilot or field accuracy.

## Human review

An earlier, separate manual Google Earth cross-check found visible kiln structures in 17 of 30 candidates overall and 15 of 15 above confidence 0.44. This was an exploratory review of a prior run. The cutoff was selected after examining that same sample, so these figures are not an unbiased accuracy estimate and do not validate the current five-district outputs.

A later 20-row targeted review is also not a representative random sample. It must be reported separately from the earlier 30-row review; the two runs must not be pooled because their candidate IDs do not match. Human review and field checks remain necessary before operational use.

## Adding districts and data

Sentinel-2 data products are systematically available free of charge from Copernicus ([mission data access](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2)). Earth Engine account, quota, export, and storage conditions may still apply. The current pipeline has processed five districts; adding another district also requires its AOI configuration, boundary-name mapping, imagery export, and checks of available mapped features. We have not demonstrated that every future district can be added through only one export and one configuration edit.

## Stack and data license

The stack includes Python, PyTorch/Ultralytics YOLOv8, Google Earth Engine, GeoPandas, pyrosm, and Streamlit. The training/evaluation dataset is SentinelKilnDB, Mondal et al., NeurIPS 2025 ([paper](https://openreview.net/forum?id=efGzsxVSEC), [dataset](https://huggingface.co/datasets/SustainabilityLabIITGN/SentinelKilnDB)), licensed CC BY-NC 4.0; attribution and non-commercial terms apply to that dataset. This does not establish the license of every project component or output.

## Advisory status and limitations

Every detection is a screening candidate that needs human review. Rule signals, mapped distances, class labels, and priority scores are screening outputs, not proof of clearance status or a basis for an inspection decision without field review. The FCBK technology signal is a project heuristic, not proof of age, technology compliance, or legal status. OpenStreetMap coverage and geometry may be incomplete or differ from legally controlling boundaries. Preprocessing and field performance have not been independently assessed across all five districts.
