# Memory and download review

**Review date:** 2026-10-07

This review targets avoidable peak memory and repeated network traffic in the
current prototype. Training run `run_0002` has since completed, but it was not a
controlled performance benchmark. No district raster or full Overpass fetch
was benchmarked during this review, and no measured optimization is claimed.

## Repository cleanup

- Removed tracked command-capture files (`convert_out.txt`, `explore_out.txt`,
  and `labels_out.txt`). They were one-time console logs; the conversion log
  described an earlier split with substantial train/validation/test leakage
  and contradicted the current conversion report. Re-run the documented CLI
  commands to obtain current output rather than relying on captured logs.
- Removed tracked `kilnwatch_bd.egg-info/` build metadata. Packaging tools
  recreate this directory during editable installs; it is not project source.
- Removed the unused root `weights/yolo26n.pt`. The project starts from the
  canonical YOLOv8 OBB weights in `data/models/`; keep those files as the
  documented training inputs.
- Root ZIP archives are ignored by Git. The research archive remains
  unreviewed. `yolo_obb_bd.zip` was inspected: its split report lacks the
  current 1,300 m leakage-filter field, so the new initializer rejects it for
  training; use the current `data/interim/yolo_obb/` or create a fresh archive
  from that directory. `kilnwatch_bd_share.zip` can be regenerated with
  `scripts/make_review_zip.ps1`.
- `scripts/init_linux.sh` and `scripts/init_windows.ps1` install the same pinned
  Python/GPU environment. `scripts/prepare_training_assets.py` can extract a
  supplied converted dataset archive or download the three pinned public
  SentinelKilnDB Parquet shards (about 3.74 GB) and convert them with a
  validated Bangladesh ADM0 boundary fetched from geoBoundaries when needed. It obtains OBB starting weights through Ultralytics
  while CUDA devices are hidden; it never starts inference or training.

## Changes made

- Inference now reads and predicts one raster window at a time. Previously,
  `_tile_raster` retained every 128 x 128 tile array for an entire GeoTIFF
  before prediction. It also converts each detection to EPSG:4326 as it is
  created, avoiding temporary per-CRS GeoDataFrames and a concatenated copy.
- Dataset conversion now passes its `batch_size` through every Parquet scan.
  The writing pass accesses Arrow scalars by row rather than converting every
  column in a batch into separate Python lists. Lower `batch_size` when running
  conversion under a tight RAM limit; it may increase processing time.
- OSM layers are reused from `data/interim/osm/<district>/` after a complete
  versioned cache has been written. Use `kilnwatch fetch-osm --refresh` to
  intentionally query Overpass again. First runs and incomplete/old caches
  still fetch the layers. A forced refresh invalidates the cache marker before
  fetching, so a failed refresh does not leave a partial cache marked current.
- Folium maps no longer request CartoDB background tiles. This avoids remote
  tile downloads and makes the map itself work offline, but it has no basemap.
- The training notebook now checks the installed Ultralytics version and
  installs only when it is missing or below 8.1. README installation guidance
  uses task-specific extras instead of installing every optional dependency.

## Downloads that remain expected

- `.[detect]` includes PyTorch and Ultralytics for local inference. PyTorch is
  a large dependency; do not install this extra for conversion, OSM fetching,
  rules, scoring, or the dashboard alone. Colab/Kaggle commonly supply
  PyTorch already; the notebook only installs Ultralytics when absent.
- Ultralytics obtains pretrained `yolov8n-obb.pt` and `yolov8s-obb.pt` weights
  the first time each is used if the runtime cache lacks them. The smoke test
  and three `yolov8n` trials reuse the same architecture weights within a
  persistent runtime. The model weights are part of the requested training
  setup, so these downloads are not removed.
- The SentinelKilnDB source Parquet files, Earth Engine exports, and OSM data
  are input data, not disposable dependency downloads. The project has no
  automatic SentinelKilnDB download command. Earth Engine export targets
  Google Drive; moving those GeoTIFFs to the inference machine is still an
  operator-managed step.

## Remaining memory costs and limits

- Global polygon NMS retains candidate detections and builds a Shapely STRtree
  before output. This is needed by the current cross-tile duplicate-removal
  design; memory grows with the number of predicted boxes, not raster pixels.
- Inference returns the full output GeoDataFrame after writing GeoParquet.
  Callers that need only the file could later be given a no-return/streaming
  option, but that would change the current function contract.
- Dashboard and OSM map rendering load cached GeoParquet layers into memory
  before rendering. Very large layers may still need viewport filtering or
  generalized display geometries; those changes could affect visible detail
  and should be measured against the actual districts first.
- The notebook and `run_0002` used batch size 8. The full staged run completed
  on the Linux RTX 3090. This was an operational training run, not a controlled
  VRAM benchmark; keep the configured value unless a measured optimization or
  an out-of-memory failure justifies changing it.

## Install only what the task needs

```powershell
# Tests and lint
pip install -e ".[dev]"

# OSM fetching and dashboard
pip install -e ".[geo,app]"

# Earth Engine export
pip install -e ".[ee]"

# Local model inference (large PyTorch dependency)
pip install -e ".[detect]"
```

Do not use `pip install -e ".[all]"` unless the machine needs every stage.
Installing extras adds to the current environment; it does not require
uninstalling extras that are already present.

## Not verified here

- Peak RAM before/after on a full district raster or full source Parquet files.
- GPU VRAM for the notebook's four full model configurations.
- OSM cache freshness against Overpass; cache reuse is explicit until `--refresh`
  is passed, and the operator decides when to refresh it. Refresh after AOI or
  boundary changes as well as when newer OSM data is needed.
- Whether the offline, no-basemap map is adequate for field review.
