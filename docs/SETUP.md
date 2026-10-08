# KilnWatch BD setup (Windows and Linux)

Use Python 3.11 or 3.12. Run commands from the repository root. The project
does not start training or inference during installation. Choose the smallest
dependency set for the work you intend to do.

## Source review, tests, and lint

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

If `py -3.11` or `python3.11` is unavailable, install Python 3.11 or 3.12 and
substitute its command. The virtual environment's Python executable is used
directly below, so shell activation is optional.

## Dashboard and OSM

Install the geographic and dashboard extras into the same environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -e ".[geo,app]"
```

```bash
# Linux
.venv/bin/python -m pip install -e '.[geo,app]'
```

OSM has two configured input paths:

- **Local PBF:** place the Geofabrik Bangladesh extract at
  `data/raw/osm/bangladesh-latest.osm.pbf`. This supports restricted/offline
  networks and is preferred when present. Pyrosm reads it and the pipeline
  writes district caches under `data/interim/`.
- **Overpass:** without the PBF, the fetcher queries a public Overpass API.
  It needs working network and DNS access; no API key is configured or
  required. If the request fails and the PBF exists, the fetcher falls back to
  the local extract. The download page is
  [Geofabrik Bangladesh](https://download.geofabrik.de/asia/bangladesh.html).

Pyrosm's `cykhash` dependency may need a native compiler if pip has no wheel
for the installed Python version. On Windows install Visual Studio Build
Tools with the C++ build tools workload, then retry the pip command. On
Debian/Ubuntu install `build-essential` and Python development headers (for
example, `sudo apt install build-essential python3-dev`) before retrying.

Start the dashboard with:

```powershell
# Windows
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

```bash
# Linux
.venv/bin/streamlit run app/streamlit_app.py
```

The app needs a processed kiln GeoParquet and supporting layer caches to show
the full screening view. Check `data/interim/` and `data/processed/` before
expecting a populated map.

## Local inference

Install the detector dependencies in addition to the geo and app extras:

```powershell
# Windows
.\.venv\Scripts\python.exe -m pip install -e ".[detect,geo,app]"
```

```bash
# Linux
.venv/bin/python -m pip install -e '.[detect,geo,app]'
```

PyTorch's selected wheel determines CPU/CUDA support. For the project's pinned
CUDA 13.0 stack, use `requirements-gpu-cu130.txt` with the full training
initializer below. For other CUDA versions, follow the current PyTorch
installation selector and confirm compatibility with the local driver. A
CPU-only environment is suitable where inference speed is acceptable.

Before running inference, supply the trained `best.pt` checkpoint, test chips
or exported GeoTIFFs, and the required OSM inputs. The reproducible pipeline
command and model-size caveat are documented in [docs/RUNBOOK.md](RUNBOOK.md).
The project does not export from Earth Engine as part of local inference.

## Full training environment

The existing initializers install the pinned CUDA 13.0 stack, development and
training tools, then prepare training assets unless the skip option is used.
The asset preparation can download about 3.74 GB of dataset files and model
weights. It does not start a GPU workload.

Linux:

```bash
bash scripts/init_linux.sh --skip-assets
# To prepare/download the training assets too, omit --skip-assets.
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\init_windows.ps1 -SkipAssetSetup
# To prepare/download the training assets too, omit -SkipAssetSetup.
```

For an existing converted dataset archive, pass `--dataset-archive PATH` on
Linux or `-DatasetArchive PATH` on Windows. Training itself is a separate,
explicit action using `scripts/train_linux.sh` or `scripts/train_windows.ps1`;
see [docs/TRAINING_READINESS.md](TRAINING_READINESS.md).

## Optional Earth Engine export

Only new Sentinel-2 imagery export requires Earth Engine. Install `.[ee]`,
authenticate with an authorized Google Cloud project, and set
`KILNWATCH_EE_PROJECT`. The project currently keeps export gated while
`preprocessing_verified` is false in `config/preprocessing.yaml`; do not
change that verification state without resolving the documented date conflict
and recording evidence. OSM, local inference, rule checking, scoring, and the
dashboard do not require Earth Engine.

## Local files and sharing

Data, checkpoints, environments, and generated outputs are intentionally
local and are not included in the source review ZIP. See
[docs/CLAUDE_SHARING_AND_SETUP.md](CLAUDE_SHARING_AND_SETUP.md) for creating a
cross-platform reproducible review archive and checksum comparison. Never
put credentials or private data in that archive.
