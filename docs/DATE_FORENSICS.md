# SentinelKilnDB imagery-date diagnostic

`tools/date_forensics.py` compares sampled training PNGs with Sentinel-2 SR
Harmonized scene and low-cloud median candidates for user-specified dates. It
uses the WGS84 latitude/longitude parsed from each PNG filename; it does not
contain sample coordinates. The current preprocessing recipe supplies the
collection, B4/B3/B2 bands, QA60 bit 10 cloud mask, patch dimensions, and
10-metre sampling scale.

Each `--window START/END` uses an **inclusive start and exclusive end**, matching
Earth Engine `filterDate`. Repeat `--window` to compare the public source
date descriptions. The tool does not read or change
`preprocessing_verified`, set an acceptance threshold, or declare a window
verified.

## Install and authenticate

Use the lightweight optional group; it does not install PyTorch or Ultralytics:

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -e ".[date-forensics]"
earthengine authenticate
$env:KILNWATCH_EE_PROJECT = "your-authorized-google-cloud-project-id"
```

```bash
# Linux
.venv/bin/python -m pip install -e '.[date-forensics]'
earthengine authenticate
export KILNWATCH_EE_PROJECT="your-authorized-google-cloud-project-id"
```

The Cloud project must be registered for Earth Engine, the account must have
access, and credentials must be available to the Earth Engine Python client.
Authentication and imagery requests happen only when the user runs the
diagnostic. This coding task did not call Earth Engine or access the network.

## Command shape

Run from the repository root after substituting date windows you want to
compare. The ranges below are the public descriptions already recorded in
`config/preprocessing.yaml`; their conflicting meanings remain unresolved.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe tools\date_forensics.py `
  --training-dir data\interim\yolo_obb\train\images `
  --window 2023-09-01/2024-03-01 `
  --window 2023-11-01/2024-03-01 `
  --window 2024-01-01/2025-02-28 `
  --output results\date_forensics.csv `
  --max-samples 48 --seed 42
```

Linux:

```bash
.venv/bin/python tools/date_forensics.py \
  --training-dir data/interim/yolo_obb/train/images \
  --window 2023-09-01/2024-03-01 \
  --window 2023-11-01/2024-03-01 \
  --window 2024-01-01/2025-02-28 \
  --output results/date_forensics.csv \
  --max-samples 48 --seed 42
```

The first window reflects the repository/paper September 2023–February 2024
description, the second the dataset-card November 2023–February 2024
description, and the third the downloader's literal filter. Because the third
end is exclusive, `2025-02-28` itself is not included, exactly as in that
filter. The first two translate month-only statements to full calendar-month
half-open windows (ending on March 1); that conversion is an interpretation.
These are candidate interpretations for diagnosis, not endorsed dates.
Omit `--max-samples` to process every PNG; a small seeded sample is recommended
because each matching scene requires an imagery download.

## CSV columns

| Column | Meaning |
|---|---|
| `chip_filename`, `latitude`, `longitude` | Source PNG name and its parsed filename coordinates. |
| `window_start_inclusive`, `window_end_exclusive` | Requested date window. |
| `candidate_kind`, `candidate_id`, `scene_date_utc` | Individual scene, median composite, or no-scene row; Earth Engine ID/date where applicable. |
| `cloudy_pixel_percentage` | Scene-level metadata where present. |
| `scenes_in_window`, `scenes_in_median` | Scene counts for the requested window and the configured `<1%` cloud-filtered median. |
| `valid_pixel_count`, `valid_pixel_fraction` | Count and fraction of clear QA60 pixels returned for the sampled patch. |
| `offset_dx`, `offset_dy` | Best candidate-to-training alignment among shifts of at most one pixel. |
| `pearson_r`, `pearson_g`, `pearson_b`, `mean_pearson` | Per-channel and mean pixel Pearson correlations after per-patch normalization. |
| `histogram_distance_r`, `histogram_distance_g`, `histogram_distance_b`, `mean_histogram_distance` | Per-channel and mean total-variation distances between 32-bin normalized histograms (0 is identical; 1 is maximally different). |
| `best_for_chip_window` | Highest mean correlation (histogram distance breaks ties) among returned candidates for that chip/window. This is a ranking only. |
| `status` | `ok`, `no_clear_pixels`, or `no_scenes`. |

The cloud mask tests QA60 bit 10, and reflectance is stretched per valid patch
and band with the existing `src.data.normalize.minmax_uint8` implementation.
Scene rows include clear-pixel counts; the median uses scenes below the
configured cloud-cover limit. The chip footprint is centered on the parsed
coordinate and sampled in the configured UTM zone at the configured scale.
The one-pixel search allows a small alignment difference but does not establish
the exact source transform or compositing recipe.

## Interpretation limits

This output is evidence for human investigation, not automatic proof of the
training acquisition dates. Low correlations can result from compositing,
resampling, georeferencing, cloud masking, seasonal change, or a mismatch
between the filename coordinate and the original patch grid. A high score also
does not prove that every source chip used that scene or window. Inspect the
returned candidates and sampled chips, compare more samples if needed, and
record the rationale separately. Do not change
`config/preprocessing.yaml`'s `preprocessing_verified` flag based on this CSV
alone.
