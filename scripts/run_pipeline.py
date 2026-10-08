"""Run inference, OSM retrieval, rule screening, and priority scoring in order.

Input: prepared test chips, a YOLO OBB checkpoint, AOI/rules config and network
access for OSM. Outputs: processed GeoParquet files consumed by the dashboard.
Inference is explicitly forced to CPU by ``demo_inference.py``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def osm_cache_complete(
    interim_dir: Path = ROOT / "data/interim",
    aoi_config: Path = ROOT / "config/aoi.yaml",
) -> bool:
    """Check for every configured district/layer GeoParquet cache file."""
    from src.geo.osm_layers import LAYER_TAGS

    config = yaml.safe_load(aoi_config.read_text(encoding="utf-8"))
    districts = config.get("districts", [])
    expected = [
        interim_dir / "osm" / district["name"] / f"{layer}.parquet"
        for district in districts
        for layer in LAYER_TAGS
    ]
    return bool(expected) and all(path.is_file() for path in expected)


def pipeline_steps(
    weights: Path | None = None,
    *,
    include_fetch: bool = True,
    real_rasters: list[Path] | None = None,
    aoi_config: Path = ROOT / "config/aoi.yaml",
    imgsz: int = 512,
) -> list[tuple[str, list[str]]]:
    """Return ordered commands, optionally excluding fetch and setting raster imgsz."""
    inference = [sys.executable, "-m", "src.eval.demo_inference"]
    if weights is not None:
        inference.extend(["--weights", str(weights)])
    steps = [("1. Demo inference", inference)]
    for raster in real_rasters or []:
        district = district_for_raster(raster, aoi_config)
        output_name = re.sub(r"[^a-z0-9]+", "_", district.casefold()).strip("_")
        output = ROOT / "data/processed" / f"kilns_{output_name}.parquet"
        command = [
            sys.executable, "-m", "src.cli", "infer", str(weights),
            "--raster-dir", str(raster), "--output", str(output), "--imgsz", str(imgsz),
            "--point-output", "--district-name", district,
        ]
        steps.append((f"Real raster inference: {raster}", command))
    if include_fetch:
        steps.append(("2. Fetch OSM layers", [sys.executable, "-m", "src.cli", "fetch-osm"]))
    steps.extend([
        ("3. Check rules", [sys.executable, "-m", "src.cli", "check-rules"]),
        ("4. Score priorities", [sys.executable, "-m", "src.cli", "score"]),
    ])
    return steps


def district_for_raster(raster: Path, aoi_config: Path = ROOT / "config/aoi.yaml") -> str:
    """Resolve a raster filename to one configured AOI district name.

    Input: raster filename plus AOI YAML district names. Output: exact configured
    district name, matched as a full name or a filename token prefix.
    """
    config = yaml.safe_load(aoi_config.read_text(encoding="utf-8"))
    tokens = [token.casefold() for token in re.findall(r"[a-z0-9]+", raster.stem)]
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


def run_pipeline(weights: Path | None = None, imgsz: int = 512) -> int:
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
    rasters = exported_rasters()
    for label, command in pipeline_steps(
        resolved_weights, include_fetch=fetch_needed, real_rasters=rasters, imgsz=imgsz
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
    print("Dashboard ready — run: streamlit run app/streamlit_app.py")
    return 0


def main() -> None:
    """Parse optional checkpoint override and run the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=None)
    parser.add_argument("--imgsz", type=int, default=512)
    args = parser.parse_args()
    raise SystemExit(run_pipeline(args.weights, imgsz=args.imgsz))


if __name__ == "__main__":
    main()
