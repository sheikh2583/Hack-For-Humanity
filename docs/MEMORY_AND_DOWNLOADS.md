# Memory and download review

**Review date:** 2026-09-29

This review targets avoidable peak memory and repeated network traffic in the
current prototype. It does not claim a measured reduction: no district raster,
GPU training run, or full Overpass fetch was benchmarked during this review.

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
- Training batch size remains 16. The notebook already comments that it may
  need to be lowered for `yolov8s-obb` at image size 512. GPU memory behavior
  has not been measured; lower the batch only after observing an actual OOM or
  available GPU memory.

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
