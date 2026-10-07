"""Screening priority scoring for kiln candidates.

Input
-----
- ``kilns_scored_path``: Path to ``kilns_scored.parquet`` (output of
  ``src.rules.engine``).

Output
------
- ``kilns_prioritised.parquet`` — all existing columns plus:

  =====================  =========  =============================================
  Column                 Dtype      Description
  =====================  =========  =============================================
  exposure               float      Weighted normalized school, hospital, settlement components
  priority               float      screening score × detector confidence × (1 + exposure)
  priority_rank          int        1 = highest priority
  =====================  =========  =============================================

Formula
-------
    priority = screening score * detector confidence * (1 + exposure)

    exposure = weighted sum of the three separately normalized components

    R defaults to ``scoring.exposure_radius_m`` in ``config/rules.yaml``.

Contract
--------
>>> from src.score.priority import compute_priority
>>> compute_priority(kilns_scored_path, output)
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

from src.geo.crs import centroid_longitude, get_projected_crs

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_scoring_config() -> dict:
    """Load the scoring section from config/rules.yaml."""
    rules_path = _PROJECT_ROOT / "config" / "rules.yaml"
    with open(rules_path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("scoring", {})


def _normalise_component(values: np.ndarray, method: str = "percentile_rank") -> np.ndarray:
    """Normalize one pilot-wide exposure component to [0, 1]."""
    values = np.asarray(values, dtype=float)
    if not len(values):
        return values
    if method == "percentile_rank":
        normalized = pd.Series(values).rank(method="average", pct=True).to_numpy().copy()
        normalized[values == 0] = 0.0
        return normalized
    if method == "minmax":
        low, high = float(values.min()), float(values.max())
        return np.zeros_like(values) if high == low else (values - low) / (high - low)
    raise ValueError(f"Unsupported exposure normalization: {method}")


def _score_priority_components(
    kilns: pd.DataFrame,
    n_schools: np.ndarray,
    n_hospitals: np.ndarray,
    settlement_area: np.ndarray,
    weights: dict[str, float],
    normalization: str = "percentile_rank",
) -> pd.DataFrame:
    """Append raw and normalized components, exposure, priority and rank."""
    result = kilns.copy()
    components = {
        "n_schools": n_schools,
        "n_hospitals": n_hospitals,
        "settlement_area": settlement_area,
    }
    exposure = np.zeros(len(result), dtype=float)
    for name, values in components.items():
        result[name] = values
        normalized = _normalise_component(values, normalization)
        result[f"{name}_normalized"] = normalized
        exposure += float(weights.get(name, 0.0)) * normalized
    result["exposure"] = exposure
    result["priority"] = result["breach_score"] * result["confidence"] * (1 + exposure)
    result["priority_rank"] = result["priority"].rank(ascending=False, method="min").astype(int)
    return result


def _count_features_within(
    kilns_proj: gpd.GeoDataFrame,
    features_proj: gpd.GeoDataFrame,
    radius_m: float,
) -> np.ndarray:
    """Count features within a radius of each kiln.

    Parameters
    ----------
    kilns_proj : gpd.GeoDataFrame
        Kilns in projected CRS.
    features_proj : gpd.GeoDataFrame
        Point/polygon features in the same CRS.
    radius_m : float
        Search radius in metres.

    Returns
    -------
    np.ndarray
        Count per kiln, shape ``(len(kilns_proj),)``.
    """
    if features_proj.empty:
        return np.zeros(len(kilns_proj))

    from shapely import STRtree  # type: ignore[import-untyped]

    tree = STRtree(features_proj.geometry.values)
    counts = np.zeros(len(kilns_proj))
    buffers = kilns_proj.geometry.buffer(radius_m)
    for i, buf in enumerate(buffers):
        hits = tree.query(buf, predicate="intersects")
        counts[i] = len(hits)
    return counts


def _settlement_area_within(
    kilns_proj: gpd.GeoDataFrame,
    settlements_proj: gpd.GeoDataFrame,
    radius_m: float,
) -> np.ndarray:
    """Sum settlement area (km²) within a radius of each kiln.

    Parameters
    ----------
    kilns_proj : gpd.GeoDataFrame
        Kilns in projected CRS.
    settlements_proj : gpd.GeoDataFrame
        Settlement polygons in the same CRS.
    radius_m : float
        Search radius in metres.

    Returns
    -------
    np.ndarray
        Total settlement area in km² per kiln.
    """
    if settlements_proj.empty:
        return np.zeros(len(kilns_proj))

    from shapely import STRtree  # type: ignore[import-untyped]

    tree = STRtree(settlements_proj.geometry.values)
    areas = np.zeros(len(kilns_proj))
    buffers = kilns_proj.geometry.buffer(radius_m)
    for i, buf in enumerate(buffers):
        hits = tree.query(buf, predicate="intersects")
        if len(hits) > 0:
            # Intersection area
            for j in hits:
                inter = buf.intersection(settlements_proj.geometry.values[j])
                areas[i] += inter.area / 1e6  # m² → km²
    return areas


def compute_priority(
    kilns_scored_path: Path,
    output: Path,
    radius_m: float | None = None,
    osm_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Compute priority scores for each kiln.

    Parameters
    ----------
    kilns_scored_path : Path
        Path to ``kilns_scored.parquet``.
    output : Path
        Path to write ``kilns_prioritised.parquet``.
    radius_m : float, optional
        Radius for exposure calculation. If None, reads
        ``scoring.exposure_radius_m`` from ``config/rules.yaml``.
    osm_dir : Path, optional
        Path to OSM layer cache. If None, uses the default
        ``data/interim`` relative to project root.

    Returns
    -------
    gpd.GeoDataFrame
        Kilns with priority columns appended.
    """
    from rich import print as rprint

    scoring_cfg = _load_scoring_config()
    if radius_m is None:
        radius_m = float(scoring_cfg.get("exposure_radius_m", 1000))

    kilns = gpd.read_parquet(kilns_scored_path)
    proj_crs = get_projected_crs(centroid_longitude(kilns))
    kilns_proj = kilns.to_crs(proj_crs)

    if osm_dir is None:
        osm_dir = Path(kilns_scored_path).resolve().parent.parent / "interim"

    # Load school + hospital features
    school_gdfs = []
    hospital_gdfs = []
    settlement_gdfs = []

    osm_root = osm_dir / "osm"
    for district_dir in osm_root.iterdir() if osm_root.exists() else []:
        for path, container in [
            (district_dir / "schools.parquet", school_gdfs),
            (district_dir / "hospitals.parquet", hospital_gdfs),
            (district_dir / "settlements.parquet", settlement_gdfs),
        ]:
            if path.exists():
                container.append(gpd.read_parquet(path))

    def _concat_proj(gdfs: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        if not gdfs:
            return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=proj_crs)
        merged = pd.concat(gdfs, ignore_index=True)
        return gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326").to_crs(proj_crs)

    schools_proj = _concat_proj(school_gdfs)
    hospitals_proj = _concat_proj(hospital_gdfs)
    settlements_proj = _concat_proj(settlement_gdfs)

    n_schools = _count_features_within(kilns_proj, schools_proj, radius_m)
    n_hospitals = _count_features_within(kilns_proj, hospitals_proj, radius_m)
    settlement_area = _settlement_area_within(kilns_proj, settlements_proj, radius_m)

    kilns = _score_priority_components(
        kilns, n_schools, n_hospitals, settlement_area,
        weights={k: float(v) for k, v in scoring_cfg.get("weights", {}).items()},
        normalization=str(scoring_cfg.get("normalization", "percentile_rank")),
    )

    kilns = kilns.sort_values("priority_rank")

    output.parent.mkdir(parents=True, exist_ok=True)
    kilns.to_parquet(output)
    rprint(f"[green]Prioritised kilns written to {output}[/green]")
    rprint(f"  Top 5 priority scores: {kilns['priority'].head().tolist()}")
    return kilns


def sensitivity_analysis(
    kilns_scored_path: Path,
    osm_dir: Path | None = None,
    weight_sets: list[dict[str, float]] | None = None,
    radii: list[float] | None = None,
) -> pd.DataFrame:
    """Run sensitivity analysis by varying weights and radius.

    Parameters
    ----------
    kilns_scored_path : Path
        Path to ``kilns_scored.parquet``.
    osm_dir : Path, optional
        OSM layer cache directory.
    weight_sets : list[dict], optional
        Each dict maps component name to weight multiplier.
    radii : list[float], optional
        List of radii (metres) to test.

    Returns
    -------
    pd.DataFrame
        Spearman correlations of top-20 rankings across parameter sets.
    """
    from rich import print as rprint
    from scipy.stats import spearmanr  # type: ignore[import-untyped]

    scoring_cfg = _load_scoring_config()
    if radii is None:
        radii = [float(r) for r in scoring_cfg.get("sensitivity_radii_m", [500, 750, 1000, 1500, 2000])]

    if weight_sets is None:
        baseline_weights = {k: float(v) for k, v in scoring_cfg.get("weights", {}).items()}
        weight_sets = [baseline_weights]
        for name in baseline_weights:
            changed = baseline_weights.copy()
            changed[name] = changed[name] * 2 if changed[name] else 1.0
            weight_sets.append(changed)

    results = []
    baseline_ranking = None

    for radius in radii:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir) / "priority.parquet"
            gdf = compute_priority(
                kilns_scored_path, output=tmp_path, radius_m=radius, osm_dir=osm_dir
            )
            for weights in weight_sets:
                rescored = _score_priority_components(
                    gdf,
                    gdf["n_schools"].to_numpy(),
                    gdf["n_hospitals"].to_numpy(),
                    gdf["settlement_area"].to_numpy(),
                    weights,
                    str(scoring_cfg.get("normalization", "percentile_rank")),
                )
                top20 = rescored.nsmallest(20, "priority_rank")["kiln_id"].tolist()
                if baseline_ranking is None:
                    baseline_ranking = top20
                baseline_ranks = {kid: i for i, kid in enumerate(baseline_ranking)}
                current_ranks = {kid: i for i, kid in enumerate(top20)}
                common = set(baseline_ranking) & set(top20)
                if len(common) >= 3:
                    x = [baseline_ranks[k] for k in common]
                    y = [current_ranks[k] for k in common]
                    corr, _ = spearmanr(x, y)
                else:
                    corr = float("nan")
                results.append({
                    "radius_m": radius,
                    "weights": weights,
                    "top20_overlap": len(common),
                    "spearman_rho": corr,
                })

    df = pd.DataFrame(results)
    rprint(df.to_string(index=False))
    return df
