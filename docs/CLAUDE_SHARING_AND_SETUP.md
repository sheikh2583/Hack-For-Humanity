# Claude sharing and operator setup

Updated 2026-10-08. This guide explains how to create a portable source ZIP
and which local services or files are needed for each KilnWatch BD stage.

## Create a Claude review ZIP

The review archive contains project source, configuration, tests, and
documentation. It excludes model weights, datasets, rasters, OSM extracts,
GeoParquet outputs, virtual environments, caches, and credentials. Claude can
review the source without these large/private runtime files. If a reviewer
needs to reproduce inference or GIS outputs, provide the required data and
checkpoint through an approved separate channel.

Run the same Python command from the project root on Windows or Linux:

```bash
python scripts/make_review_zip.py
```

On Windows, the legacy PowerShell entry point delegates to that same Python
builder, so it produces the same archive format:

```powershell
.\scripts\make_review_zip.ps1
```

The default output is `kilnwatch_bd_share.zip` at the repository root. To
choose another path:

```bash
python scripts/make_review_zip.py /path/to/kilnwatch_bd_share.zip
```

The archive fixes member ordering, timestamps, permissions, and compression,
so it is byte-for-byte reproducible when both operating systems build from
identical source file contents. Compare SHA-256 hashes
before uploading or sending the archive:

```powershell
Get-FileHash .\kilnwatch_bd_share.zip -Algorithm SHA256
```

```bash
sha256sum kilnwatch_bd_share.zip
```

If hashes differ, compare the source revisions and changed-file contents first.
The archive does not normalize arbitrary source text; tracked text files use
LF line endings via `.gitattributes`, but uncommitted/platform-specific edits
can still produce different archives.

Upload the ZIP to Claude and paste the review instructions from
[`CLAUDE_WEB_PROMPT.md`](CLAUDE_WEB_PROMPT.md). Include a copy of this document
in the ZIP so the reviewer understands which runtime dependencies are
optional and which data files are intentionally absent.

## Setup by task

For the complete Windows PowerShell and Linux setup, including copyable
commands and the distinction between a lightweight dashboard environment and
the CUDA training environment, see [`SETUP.md`](SETUP.md). The sections below
summarize which external inputs each task needs.

Create an environment using Python 3.11 or 3.12 and install only the extras
needed for the task:

```bash
python -m venv .venv
```

Windows PowerShell activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux activation:

```bash
source .venv/bin/activate
```

### Source review, tests, and lint

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

### OSM layers and dashboard

Install the geo and app extras:

```bash
python -m pip install -e ".[geo,app]"
```

Pyrosm depends on the native `cykhash` extension. If pip cannot find a wheel
for the active Python version, install a C/C++ toolchain before installing
the geo extra: Visual Studio Build Tools with the C++ workload on Windows, or
`build-essential` plus Python development headers on Debian/Ubuntu Linux.

OSM access can use either of these sources:

- **Local PBF (recommended for offline or restricted networks):** place the
  Geofabrik Bangladesh extract at
  `data/raw/osm/bangladesh-latest.osm.pbf`. The project reads it with Pyrosm
  and stores district layer caches in `data/interim/osm/`. A supplied PBF is
  preferred, so the fetch does not wait on Overpass.
- **Overpass API:** if no local PBF exists, OSMnx queries a public Overpass
  endpoint. No API key is configured or required by this project. The machine
  needs network/DNS access to that endpoint, and requests may be rate-limited
  or blocked by a network. If the PBF becomes available after an Overpass
  attempt starts, a failed request falls back to the PBF.

No Google Earth Engine account or API key is needed for OSM fetching. The PBF
is an external input and is excluded from the Claude ZIP. Do not send a PBF
unless the recipient needs it and the transfer channel is appropriate.

### Inference and full pipeline

Install model inference dependencies:

```bash
python -m pip install -e ".[detect,geo,app]"
```

The selected trained checkpoint (`best.pt`), input test chips, and exported
GeoTIFFs are local inputs and are excluded from the ZIP. Use the full trained
checkpoint, not a smoke-test checkpoint. GPU is optional for inference; use
the device option when explicitly running inference on CUDA. Exported imagery
must already exist for the real-raster stage.

### Earth Engine export (optional; separate from OSM)

Only a new Sentinel-2 export needs Earth Engine. Install the extra and follow
Google's current Earth Engine authentication and project-registration steps:

```bash
python -m pip install -e ".[ee]"
```

Set `KILNWATCH_EE_PROJECT` to an authorized Cloud project ID and authenticate
the Earth Engine client. The project intentionally does not call Earth Engine
as part of local inference, OSM fetching, rule checking, scoring, or dashboard
startup. Export also remains gated by the preprocessing verification state in
`config/preprocessing.yaml`.

### Legal and boundary review

No software account resolves legal or boundary questions. Review configured
rule thresholds against authoritative sources and verify boundary source,
licence, and coverage before treating results as anything beyond advisory
screening. Keep verification flags aligned with reviewed evidence.

## Local run notes for reviewers

As of 2026-10-08, this Windows workspace completed demo-chip inference,
inference on the local Chapainawabganj GeoTIFF, local-PBF extraction for the
two configured districts, rule checking, and scoring. These runtime files are
not included in the ZIP. The real-raster checkpoint records training image
size 256 while the run used image size 512; inference printed a warning about
that mismatch. The run is not field validation, a legal determination, or
confirmation that every OSM relation geometry is complete.
