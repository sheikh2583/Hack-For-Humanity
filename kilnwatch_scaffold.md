# KilnWatch BD: Build Scaffold

Prompt-driven build flow for a satellite-based brick kiln compliance triage tool (Hack for Humanity Bangladesh 2026). Each step has a copyable agent prompt and a list of what you must do by hand.

> **Status note (2026-09-29):** This file is the historical scaffold, not the
> source of truth for current settings. Follow [docs/PROGRESS.md](docs/PROGRESS.md)
> for the implemented pipeline and verification state. In particular, the old
> leakage threshold, training plan, single-composite recipe, and priority
> formula below have been superseded. Preprocessing remains locked pending
> confirmation of SentinelKilnDB's conflicting acquisition dates.

**Global assumptions to keep in mind**

- Dataset: SentinelKilnDB, licence CC BY-NC 4.0 (non-commercial, cite the authors).
- Coordinate system for distance math: EPSG:9680 (WGS 84 / TM 90 NE); fallback UTM 45N/46N (EPSG:32645/32646).
- Legal thresholds are NOT verified. Check the Act and the 2020 gazette yourself before setting `verified: true` in `config/rules.yaml`.
- Unverified items: Gazipur kiln count, Earth Engine account approval, existence of any public licence list.

---

## Step 0: AGENTS.md (put in repo root)

```
# KilnWatch BD: agent rules
Goal: detect brick kilns in Sentinel-2 imagery of Bangladesh, check them against siting/technology rules in config/rules.yaml, rank by exposure, show on a map.
Stack: Python 3.11, PyTorch, ultralytics (YOLO OBB), geopandas, shapely, pyproj, osmnx, earthengine-api, streamlit, folium, pytest.

Rules:
1. Never invent dataset schemas, file formats, legal thresholds or coordinates. If unknown, stop and ask me.
2. All legal numbers live in config/rules.yaml. Code reads them; never hardcode.
3. Store geometry in EPSG:4326. Do distance/area math in EPSG:9680 (WGS 84 / TM 90 NE). At startup assert pyproj can build it; otherwise fall back to EPSG:32645 (centroid lon < 90E) or EPSG:32646.
4. Every module: type hints, docstring stating input/output schema, and one pytest using tiny synthetic data.
5. Pipeline outputs are GeoParquet in data/processed/.
6. Training runs on Colab/Kaggle GPU: write notebooks/scripts, do not try to run training.
7. After each task, list what you could not verify and what I must check by hand.
```

---

## Step 1: Scaffold

```
Create this repo layout: config/{rules.yaml,aoi.yaml}, data/{raw,interim,processed}, src/{data,detect,geo,rules,score,eval,app}, notebooks/, tests/, app/streamlit_app.py, pyproject.toml, README.md.
Each module gets a docstring with its input/output contract. Put pipeline entry points in src/cli.py (typer) with one command per stage.
`config/aoi.yaml` currently names Chapainawabganj and Gazipur and resolves them against the ADM2 boundary file. The old placeholder season is not the imagery-export source of truth; dates come from `config/preprocessing.yaml` and remain under review.
Do not fill config/rules.yaml; I will provide it.
```

**Manual:** review the layout. Nothing else.

---

## Step 2: Dataset conversion

```
Goal: build a Bangladesh-only YOLOv8-OBB training set from SentinelKilnDB (CC BY-NC 4.0).
Facts from the dataset card: 128x128 PNG chips at 10 m; files named "lat,lon.png"/"lat,lon.txt"; label formats YOLO-OBB (class, x1..y4), YOLO-AA, DOTA; detector output classes are FCBK and Zigzag; patches overlap by 30 px; the shipped split is class-wise stratified.
Step 1: print the actual directory structure and 5 sample label files, then STOP and wait for my confirmation.
Step 2: after confirmation, write src/data/convert_sentinelkilndb.py to:
 - filter chips to Bangladesh using a boundary polygon file at data/raw/bangladesh_boundary.geojson (not a bbox), using chip lat/lon from filenames;
 - map class names to integer ids consistently;
 - discard the shipped split and re-split by spatial blocks into train/val/test at 70/15/15;
 - remove val/test chips whose chip centres are within 1,300 m Chebyshev distance (EPSG:9680) of a chip in another split; report dropped counts per split and final minimum distance;
 - write dataset.yaml and a report of kiln counts per class per split.
The implemented leakage rule supersedes the old 200 m test prompt. See the
current split report in `data/interim/yolo_obb/split_report.json`.
```

**Manual:**
- Download the data (Kaggle or Hugging Face credentials).
- Get the Bangladesh boundary file (e.g. GADM or geoBoundaries).
- Paste the directory listing and label samples to the agent (it cannot see your files).
- Check licence terms and cite the authors.
- Bangladesh has two records in the rare source class; these are merged into FCBK.

---

## Step 3: Baseline training

```
Use `notebooks/train.ipynb` on a Colab/Kaggle GPU. First run the 3-epoch
`yolov8n-obb` smoke test at imgsz 256. If it passes, train `yolov8n-obb` at
imgsz 256/384/512, then `yolov8s-obb` at the size with best validation mAP50
(50 epochs, patience 10, `degrees=90`, `flipud=0.5`, seed 0). Evaluate the
selected run on test once. The notebook saves `best.pt`, metrics, confusion
matrices, and PR curves. See `docs/TRAINING_READINESS.md` for the checked
dataset and the remaining host setup needed to start.

Report metrics for the two detector output classes: FCBK and Zigzag. The
separate false-positive/missed-kiln crop review in `src/eval/error_analysis.py`
is an evaluation follow-up, not a prerequisite for training.
```

**Manual:**
- Run on a GPU session (watch for disconnects) and save weights.
- Paste metrics back; the agent cannot run GPU jobs or judge whether numbers look sane.
- Check Ultralytics' AGPL licence if you publish the code.

---

## Step 4a: Imagery export

```
Use `config/preprocessing.yaml` as the sole preprocessing specification. Export raw B4/B3/B2 at scale 10, clip to the district ADM2 polygon, and select the district UTM CRS from its longitude. Export is blocked while `preprocessing_verified: false`. The source script's literal dates conflict with the paper, repository README, and dataset card; see `docs/PROGRESS.md`. Do not claim parity until authors' intended dates and paired-chip calibration are checked.
```

**Manual:**
- Create the Earth Engine account and project, authenticate, and run the export (approval time unverified). Copernicus Data Space is an alternative.
- Find the authors' export code in their GitHub repo and paste it to the agent.
- Overlay a few known kilns and look at them yourself. A preprocessing mismatch is the most likely cause of poor results.

---

## Step 4b: Inference

```
Write src/detect/infer.py: normalize each 128x128 RGB tile per band before inference, pass BGR to Ultralytics with the training `imgsz`, convert pixel polygons to geographic polygons using each tile's affine transform, merge duplicates with STRtree-backed polygon-IoU NMS, and write detections to GeoParquet.
Add a test with a synthetic raster and a known box to verify the pixel-to-geographic conversion.
```

**Manual:** eyeball at least 20 detections on a satellite basemap. Agents often get coordinate transforms subtly wrong.

---

## Step 5: OpenStreetMap layers

```
Write src/geo/osm_layers.py using osmnx/Overpass to fetch, per district: schools, hospitals/clinics, residential landuse and place=village/hamlet, forests, rivers/wetlands. Cache to GeoParquet in data/interim/. Also write a completeness report: feature counts per km2 and a map per layer.
Do not fetch anything outside the district polygons.
```

**Manual:**
- View the layers over satellite imagery and judge whether rural settlements and schools are mapped; record gaps as limitations.
- Ecologically Critical Area polygons and public-forest boundaries may need a separate source. Decide that yourself.

---

## Step 6: Rules file and engine

### config/rules.yaml

Values are placeholders taken from secondary sources. Verify each against the Act and the January 2020 gazette before setting `verified: true`.

```yaml
version: draft-0
sources:
  - "Brick Manufacturing and Kiln Establishment (Control) Act 2013, amended 2019 (Legislative Division portal)"
  - "January 2020 gazette (advanced-technology kilns, reported 400 m): locate original"
technology:
  flagged_classes: [FCBK]
  note: "Zigzag, Hybrid Hoffman, VSBK and tunnel are permitted; detector cannot see HHK/VSBK/tunnel"
  severity: 3
  verified: false
siting_rules:
  - {id: near_school,     feature: schools,      buffer_m: 1000, severity: 3, verified: false}
  - {id: near_hospital,   feature: hospitals,    buffer_m: 1000, severity: 3, verified: false}
  - {id: near_settlement, feature: settlements,  buffer_m: 1000, severity: 2, verified: false}
  - {id: near_forest,     feature: forests,      buffer_m: 2000, severity: 2, verified: false}
  - {id: near_wetland,    feature: water,        buffer_m: 1000, severity: 1, verified: false}
not_implemented:
  - "agricultural land (needs land-use data; a strict reading flags almost every kiln)"
  - "ecologically critical areas (needs polygons)"
```

### Engine prompt

```
Write src/rules/engine.py. Read config/rules.yaml. For each kiln in kilns.parquet return: list of breached rule ids, breach count, severity-weighted breach score, distance to nearest feature of each type, and rules_version.
Project to EPSG:9680 for distances. If any rule has verified: false, add a column "rules_verified"=false and print a loud warning. Do not hardcode any numbers. Include a test with synthetic kilns and features at known distances.
```

**Manual (critical):**
- Read the Act and the 2020 gazette yourself, set the numbers, then flip `verified`.
- Agents will confidently state wrong legal details.
- Ask the organizers or a law-student friend to sanity-check.

---

## Step 7: Priority score

```
Write src/score/priority.py. Normalize school count, hospital count, and settlement area separately over the pilot districts, apply configured `scoring.weights`, and calculate `priority = breach_score * confidence * (1 + exposure)`. Keep components as output columns. Sensitivity analysis varies weights and R.
```

**Manual:** choose and justify the weights. Judges may probe this design decision.

---

## Step 8: Dashboard

```
Build app/streamlit_app.py: Folium map of kilns coloured by priority; sidebar filters (district, kiln class, min confidence); a detail panel listing breached rules, distances and nearby sites; a "needs verification" badge below a confidence threshold; a banner "Advisory only: verify before inspection"; CSV export of the filtered list; and a "rules not verified" banner if rules_verified is false.
Load only from data/processed/. Must run offline with no external API calls.
```

**Manual:**
- Test on a projector-size screen and a phone.
- Deploy (Streamlit Community Cloud or laptop).
- Verify it works fully offline.

---

## Step 9: Validation audit

```
Write src/eval/audit_sample.py: sample detections stratified by confidence tercile and include random samples from negative regions to measure false positives around villages and sandbars. See `docs/PROGRESS.md` for current implementation status.
```

**Manual (not automatable):**
- Inspect each location on high-resolution imagery and label it yourself.
- Do not scrape imagery tiles.

---

## Summary: what only humans can do

- Accounts, credentials, licence checks (Kaggle/Hugging Face, Earth Engine, dataset licence).
- Anything needing a GPU or an external service login.
- Verifying the legal rules and choosing score weights.
- Visual sanity checks (imagery alignment, detections, OSM gaps).
- Manual validation of detections.
- Deciding which claims the results honestly support.
- Recording the demo and rehearsing.

**Expect debugging time on:** coordinate transforms, tile-overlap duplicates, preprocessing mismatches between training chips and your composites.
