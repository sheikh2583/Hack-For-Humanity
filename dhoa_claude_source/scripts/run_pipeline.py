"""Run local inference, OSM retrieval, rule screening, and priority scoring.

Input: local Sentinel-2 GeoTIFF exports or prepared demo chips, a YOLO OBB
checkpoint, AOI/rules config, and cached or retrievable OSM layers. Output:
processed GeoParquet candidates consumed by the dashboard. Inference defaults
to CPU.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_LABELS = ROOT / "temporary doc share" / "audit_labeled.csv"


def osm_cache_complete(
    interim_dir: Path = ROOT / "data/interim",
    aoi_config: Path = ROOT / "config/aoi.yaml",
) -> bool:
    """Check for every configured district/layer cache file."""
    from src.geo.osm_layers import LAYER_CACHE_VERSION, LAYER_TAGS

    config = yaml.safe_load(aoi_config.read_text(encoding="utf-8"))
    configured_version = int(config.get("osm_cache_version", 1))
    if configured_version != LAYER_CACHE_VERSION:
        return False
    districts = config.get("districts", [])
    expected = []
    for district in districts:
        for layer in LAYER_TAGS:
            extension = ".gpkg" if layer == "railways" else ".parquet"
            expected.append(interim_dir / "osm" / district["name"] / f"{layer}{extension}")
        water_marker = interim_dir / "osm" / district["name"] / ".water_cache_version"
        if not water_marker.is_file() or water_marker.read_text(encoding="utf-8").strip() != "1":
            return False
        cache_marker = interim_dir / "osm" / district["name"] / ".cache_version"
        if not cache_marker.is_file() or cache_marker.read_text(encoding="utf-8").strip() != str(configured_version):
            return False
    return bool(expected) and all(path.is_file() for path in expected)


def configured_district_names(
    aoi_config: Path = ROOT / "config/aoi.yaml",
) -> list[str]:
    """Return district names from the configured AOI YAML.

    Input schema: AOI YAML containing a ``districts`` list with ``name`` fields.
    Output schema: exact configured district names in YAML order.
    """
    config = yaml.safe_load(aoi_config.read_text(encoding="utf-8"))
    return [str(district["name"]) for district in config.get("districts", [])]


def pipeline_steps(
    weights: Path | None = None,
    *,
    include_fetch: bool = True,
    real_rasters: list[Path] | None = None,
    aoi_config: Path = ROOT / "config/aoi.yaml",
    imgsz: int = 512,
    device: str = "cpu",
    district_filter: str | None = None,
    audit_labels: Path | None = None,
) -> list[tuple[str, list[str]]]:
    """Return ordered commands, optionally excluding fetch and setting raster imgsz."""
    rasters = real_rasters or []
    if district_filter:
        rasters = [r for r in rasters if district_for_raster(r, aoi_config).casefold() == district_filter.casefold()]
        if not rasters:
            raise FileNotFoundError(f"No exported raster found for district {district_filter!r}")
    steps: list[tuple[str, list[str]]] = []
    if not rasters:
        raise FileNotFoundError("No exported rasters found; demo inference is not part of this pipeline")
    raster_outputs: list[Path] = []
    for raster in rasters:
        district = district_for_raster(raster, aoi_config)
        output_name = re.sub(r"[^a-z0-9]+", "_", district.casefold()).strip("_")
        output = ROOT / "data/processed" / f"kilns_{output_name}.parquet"
        raster_outputs.append(output)
        command = [
            sys.executable, "-m", "src.cli", "infer", str(weights),
            "--raster-dir", str(raster), "--output", str(output), "--imgsz", str(imgsz),
            "--point-output", "--district-name", district, "--device", device,
        ]
        steps.append((f"Real raster inference: {raster}", command))
    if raster_outputs:
        merged_output = ROOT / "data/processed" / "kilns.parquet"
        configured_outputs = []
        for district in yaml.safe_load(aoi_config.read_text(encoding="utf-8")).get("districts", []):
            name = str(district["name"])
            output_name = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
            output = ROOT / "data/processed" / f"kilns_{output_name}.parquet"
            if output in raster_outputs or output.is_file():
                configured_outputs.append(output)
        merge_command = [sys.executable, str(ROOT / "scripts" / "merge_candidates.py"), "--inputs"]
        merge_command.extend(str(path) for path in configured_outputs)
        merge_command.extend(["--output", str(merged_output)])
        steps.append(("Merge raster candidates", merge_command))
    if include_fetch:
        steps.append(("2. Fetch OSM layers", [sys.executable, "-m", "src.cli", "fetch-osm"]))
    rule_command = [sys.executable, "-m", "src.cli", "check-rules"]
    if raster_outputs:
        rule_command.extend(["--kilns", str(ROOT / "data/processed/kilns.parquet")])
    steps.extend([
        ("3. Check rules", rule_command),
        ("4. Score priorities", [sys.executable, "-m", "src.cli", "score"]),
    ])
    if audit_labels is not None:
        steps.append((
            "5. Summarize labelled audit results",
            [sys.executable, "-m", "src.cli", "audit-results", "--labels", str(audit_labels)],
        ))
    return steps


def district_for_raster(raster: Path, aoi_config: Path = ROOT / "config/aoi.yaml") -> str:
    """Resolve a raster filename to one configured AOI district name.

    Input: raster filename plus AOI YAML district names. Output: exact configured
    district name, matched as a full name or a filename token prefix.
    """
    config = yaml.safe_load(aoi_config.read_text(encoding="utf-8"))
    tokens = re.findall(r"[a-z0-9]+", raster.stem.casefold())
    matches = []
    for district in config.get("districts", []):
        name = str(district["name"])
        normalized = re.sub(r"[^a-z0-9]+", "", name.casefold())
        if normalized in "".join(tokens) or any(
            len(token) >= 5 and normalized.startswith(token) for token in tokens
        ):
            matches.append(name)
    if len(matches) != 1:
        raise ValueError(f"Could not uniquely resolve district for raster {raster.name}: {matches}")
    return matches[0]


def exported_rasters(exports_dir: Path = ROOT / "data/raw/exports") -> list[Path]:
    """Return sorted .tif files from the user's raster export directory."""
    if not exports_dir.is_dir():
        return []
    return sorted((path for path in exports_dir.iterdir() if path.is_file() and path.suffix.casefold() == ".tif"), key=lambda path: path.name.casefold())


def resolve_weights(path: Path | None, root: Path = ROOT) -> Path:
    """Resolve model weights using full-training-first search order."""
    from src.eval.demo_inference import resolve_weights as resolve_demo_weights

    return resolve_demo_weights(path, root)


def run_pipeline(
    weights: Path | None = None,
    imgsz: int = 512,
    device: str = "cpu",
    district_filter: str | None = None,
    audit_labels: Path | None = None,
) -> int:
    """Run each stage, print captured output, and stop at the first failure."""
    try:
        resolved_weights = resolve_weights(weights)
    except FileNotFoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Using weights: {resolved_weights}")
    fetch_needed = not osm_cache_complete()
    if not fetch_needed:
        print("OSM layers already cached, skipping fetch.")
    if audit_labels is None and DEFAULT_AUDIT_LABELS.is_file():
        audit_labels = DEFAULT_AUDIT_LABELS
    if audit_labels is not None and not audit_labels.is_file():
        print(f"ERROR: Audit labels not found: {audit_labels}", file=sys.stderr)
        return 1
    rasters = exported_rasters()
    if not rasters:
        print("ERROR: No exported rasters found in data/raw/exports", file=sys.stderr)
        return 1
    if district_filter:
        try:
            rasters = [r for r in rasters if district_for_raster(r).casefold() == district_filter.casefold()]
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        if not rasters:
            print(f"ERROR: No exported raster found for {district_filter!r}", file=sys.stderr)
            return 1
    for label, command in pipeline_steps(
        resolved_weights, include_fetch=fetch_needed, real_rasters=rasters, imgsz=imgsz,
        device=device,
        district_filter=district_filter,
        audit_labels=audit_labels,
    ):
        print(f"\n=== {label} ===", flush=True)
        if label.startswith("Real raster inference: "):
            print(f"Using raster: {label.removeprefix('Real raster inference: ')}", flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        except OSError as error:
            print(f"ERROR: {error}", file=sys.stderr, flush=True)
            return 1
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        if result.returncode:
            print(f"ERROR: {label} failed with exit code {result.returncode}; stopping.", file=sys.stderr)
            return result.returncode
    if os.name == "nt":
        dashboard_command = r".\.venv\Scripts\streamlit.exe run app\streamlit_app.py"
    else:
        dashboard_command = ".venv/bin/streamlit run app/streamlit_app.py"
    print(f"Dashboard ready - run: {dashboard_command}")
    return 0


def main() -> None:
    """Parse optional checkpoint override and run the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=None)
    parser.add_argument("--imgsz", type=int, default=512)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--district", choices=configured_district_names())
    parser.add_argument("--audit-labels", type=Path, default=None)
    args = parser.parse_args()
    raise SystemExit(run_pipeline(
        args.weights, imgsz=args.imgsz, device=args.device, district_filter=args.district,
        audit_labels=args.audit_labels,
    ))


if __name__ == "__main__":
    main()
