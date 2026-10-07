"""Generate a stratified audit sample for manual validation.

Input
-----
- ``kilns_path``: Path to ``kilns_prioritised.parquet``.

Output
------
- ``audit.csv`` with columns:

  ==============  =========  ============================================
  Column          Dtype      Description
  ==============  =========  ============================================
  kiln_id         str        Unique identifier
  lat             float      Centroid latitude (EPSG:4326)
  lon             float      Centroid longitude (EPSG:4326)
  confidence      float      Detection confidence
  tercile         str        low / mid / high confidence tercile
  google_earth    str        Google Earth link for visual inspection
  label           str        Empty — to be filled manually
  ==============  =========  ============================================

- After the user fills the ``label`` column, ``compute_audit_results``
  computes precision by tercile and overall with Wilson 95% CIs.

Contract
--------
>>> from src.eval.audit_sample import generate_audit_sample
>>> generate_audit_sample(kilns_path, n=30, output=Path("audit.csv"))
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from src.geo.crs import centroid_longitude, get_projected_crs


def _wilson_interval(
    successes: int,
    total: int,
    z: float = 1.96,
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Parameters
    ----------
    successes : int
        Number of successes.
    total : int
        Number of trials.
    z : float
        Z-score for the confidence level (default 1.96 → 95%).

    Returns
    -------
    tuple[float, float]
        (lower, upper) bounds.
    """
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    spread = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def generate_audit_sample(
    kilns_path: Path,
    n: int = 30,
    output: Path = Path("audit.csv"),
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a stratified audit sample from detected kilns.

    Parameters
    ----------
    kilns_path : Path
        GeoParquet of prioritised kilns.
    n : int
        Total number of samples (split equally across 3 terciles).
    output : Path
        Output CSV path.
    seed : int
        Random seed.

    Returns
    -------
    pd.DataFrame
        The audit sample DataFrame (also written to ``output``).
    """
    from rich import print as rprint

    kilns = gpd.read_parquet(kilns_path)

    # Assign confidence terciles
    kilns["tercile"] = pd.qcut(
        kilns["confidence"],
        q=3,
        labels=["low", "mid", "high"],
        duplicates="drop",
    )

    # Stratified sample
    per_tercile = n // 3
    samples = []
    for tercile in ["low", "mid", "high"]:
        subset = kilns[kilns["tercile"] == tercile]
        k = min(per_tercile, len(subset))
        if k > 0:
            samples.append(subset.sample(n=k, random_state=seed))

    sample_df = pd.concat(samples, ignore_index=True)

    # Centroids are calculated in the prescribed projected CRS, then returned
    # to WGS84 for the audit CSV and Google Earth links.
    projected_crs = get_projected_crs(centroid_longitude(kilns))
    centroids = sample_df.to_crs(projected_crs).geometry.centroid.to_crs("EPSG:4326")
    sample_df["lat"] = centroids.y
    sample_df["lon"] = centroids.x

    # Google Earth link
    sample_df["google_earth"] = sample_df.apply(
        lambda r: f"https://earth.google.com/web/@{r['lat']},{r['lon']},0a,500d,35y,0h,0t,0r",
        axis=1,
    )

    # Label column (empty for manual filling)
    sample_df["label"] = ""

    # Select output columns
    out_cols = ["kiln_id", "lat", "lon", "confidence", "tercile", "google_earth", "label"]
    out_df = sample_df[[c for c in out_cols if c in sample_df.columns]]

    output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output, index=False)
    rprint(f"[green]Audit sample ({len(out_df)} kilns) written to {output}[/green]")
    return out_df


def compute_audit_results(
    audit_csv: Path,
    output_json: Path | None = None,
) -> dict:
    """Compute precision by tercile after manual labelling.

    Parameters
    ----------
    audit_csv : Path
        Path to the filled audit CSV (with ``label`` column populated).
    output_json : Path, optional
        Where to write the JSON results. If None, uses
        ``data/processed/audit_results.json``.

    Returns
    -------
    dict
        Precision by tercile and overall, with Wilson 95% CIs.
    """
    from rich import print as rprint

    df = pd.read_csv(audit_csv)
    if "label" not in df.columns or df["label"].isna().all():
        rprint("[red]No labels found. Fill the 'label' column first.[/red]")
        return {}

    results: dict = {"by_tercile": {}, "overall": {}}

    # Overall
    labelled = df[df["label"].isin(["kiln", "not_kiln"])]
    tp = (labelled["label"] == "kiln").sum()
    total = len(labelled)
    precision = tp / total if total > 0 else 0.0
    lo, hi = _wilson_interval(tp, total)
    results["overall"] = {
        "precision": round(precision, 4),
        "ci_95_lower": round(lo, 4),
        "ci_95_upper": round(hi, 4),
        "n": total,
        "true_positives": int(tp),
    }

    # By tercile
    for tercile in ["low", "mid", "high"]:
        subset = labelled[labelled["tercile"] == tercile]
        tp_t = (subset["label"] == "kiln").sum()
        n_t = len(subset)
        prec = tp_t / n_t if n_t > 0 else 0.0
        lo_t, hi_t = _wilson_interval(tp_t, n_t)
        results["by_tercile"][tercile] = {
            "precision": round(prec, 4),
            "ci_95_lower": round(lo_t, 4),
            "ci_95_upper": round(hi_t, 4),
            "n": n_t,
            "true_positives": int(tp_t),
        }

    if output_json is None:
        output_json = Path(audit_csv).parent / "audit_results.json"

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, indent=2))
    rprint(f"[green]Audit results written to {output_json}[/green]")
    rprint(json.dumps(results, indent=2))
    return results


def sample_negative_regions(
    detections_path: Path,
    boundary_path: Path,
    n: int = 15,
    min_distance_m: float = 2000.0,
    output: Path = Path("audit_negatives.csv"),
    seed: int = 42,
) -> pd.DataFrame:
    """Sample random points inside the boundary that are far from any detection.

    Parameters
    ----------
    detections_path : Path
        GeoParquet of detected kilns.
    boundary_path : Path
        GeoJSON of the area-of-interest polygon (e.g. a district boundary).
    n : int
        Number of negative-region samples to draw (default 15).
    min_distance_m : float
        Minimum distance from any detection centroid in metres (default 2000).
    output : Path
        Output CSV path.
    seed : int
        Random seed.

    Returns
    -------
    pd.DataFrame
        The negative-region audit sample.
    """
    from shapely.strtree import STRtree

    detections = gpd.read_parquet(detections_path)
    boundary_wgs84 = gpd.read_file(boundary_path).to_crs("EPSG:4326")
    proj_crs = get_projected_crs(centroid_longitude(boundary_wgs84))
    boundary = boundary_wgs84.to_crs(proj_crs)
    boundary_union = boundary.union_all()

    det_proj = detections.to_crs(proj_crs)
    det_centroids = det_proj.geometry.centroid.values

    rng = np.random.default_rng(seed)
    minx, miny, maxx, maxy = boundary_union.bounds

    samples: list[dict[str, object]] = []
    attempts = 0
    max_attempts = n * 200

    tree = STRtree(det_centroids) if len(det_centroids) > 0 else None

    from pyproj import Transformer

    to_wgs84 = Transformer.from_crs(proj_crs, "EPSG:4326", always_xy=True)

    from shapely.geometry import Point as ShapelyPoint

    while len(samples) < n and attempts < max_attempts:
        attempts += 1
        x = rng.uniform(minx, maxx)
        y = rng.uniform(miny, maxy)
        point = ShapelyPoint(x, y)
        if not boundary_union.contains(point):
            continue
        if tree is not None:
            nearest_idx = tree.nearest(point)
            nearest_dist = point.distance(det_centroids[nearest_idx])
            if nearest_dist < min_distance_m:
                continue

        lon, lat = to_wgs84.transform(x, y)
        samples.append({
            "sample_id": f"neg_{len(samples):03d}",
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "google_earth": (
                f"https://earth.google.com/web/@{lat},{lon},0a,500d,35y,0h,0t,0r"
            ),
            "label": "",
        })

    out_df = pd.DataFrame(samples)
    output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output, index=False)
    return out_df
