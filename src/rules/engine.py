"""Compliance rule engine — evaluate kilns against siting/technology rules.

Input
-----
- ``kilns_path``:    Path to ``kilns.parquet`` (output of ``src.detect.infer``).
- ``rules_config``:  Path to ``config/rules.yaml``.
- ``osm_dir``:       Directory with OSM GeoParquet layers per district.

Output
------
- ``kilns_scored.parquet`` — original columns plus:

  ==========================  =========  =========================================
  Column                      Dtype      Description
  ==========================  =========  =========================================
  breached_rules              list[str]  IDs of rules this kiln breaches
  breach_count                int        Number of breached rules
  breach_score                float      Sum of severities of breached rules
  dist_schools_m              float      Distance to nearest school (metres)
  dist_hospitals_m            float      Distance to nearest hospital/clinic
  dist_settlements_m          float      Distance to nearest residential area
  dist_forests_m              float      Distance to nearest forest
  dist_water_m                float      Distance to nearest water body
  technology_flagged          bool       True if kiln class is FCBK
  rules_version               str        Version string from rules.yaml
  rules_verified              bool       False if *any* rule has verified=false
  ==========================  =========  =========================================

Contract
--------
>>> from src.rules.engine import evaluate_rules
>>> evaluate_rules(kilns_path, rules_config, osm_dir, output)
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

from src.geo.crs import centroid_longitude, get_projected_crs

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_rules(rules_config: Path) -> dict[str, Any]:
    """Load and return the rules YAML config."""
    with open(rules_config) as f:
        return yaml.safe_load(f)


def _nearest_distance(
    kilns_proj: gpd.GeoDataFrame,
    features_proj: gpd.GeoDataFrame,
) -> np.ndarray:
    """Compute the distance from each kiln to the nearest feature (in metres).

    Parameters
    ----------
    kilns_proj : gpd.GeoDataFrame
        Kilns in a projected CRS (metres).
    features_proj : gpd.GeoDataFrame
        OSM features in the same projected CRS.

    Returns
    -------
    np.ndarray
        Array of distances in metres, shape ``(len(kilns_proj),)``.
        Returns ``np.inf`` where no features exist.
    """
    if features_proj.empty:
        return np.full(len(kilns_proj), np.inf)

    from shapely import STRtree  # type: ignore[import-untyped]

    tree = STRtree(features_proj.geometry.values)
    indices, distances = tree.query_nearest(
        kilns_proj.geometry.values, return_distance=True
    )
    # tree.query_nearest returns (input_idx, geom_idx) pairs — we need
    # to aggregate to one distance per kiln.
    result = np.full(len(kilns_proj), np.inf)
    result[indices[0]] = distances
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def evaluate_rules(
    kilns_path: Path,
    rules_config: Path,
    osm_dir: Path,
    output: Path,
) -> gpd.GeoDataFrame:
    """Evaluate all compliance rules for each detected kiln.

    Parameters
    ----------
    kilns_path : Path
        GeoParquet of detected kilns.
    rules_config : Path
        Path to ``config/rules.yaml``.
    osm_dir : Path
        Directory containing ``osm/<district>/<layer>.parquet`` files.
    output : Path
        Path to write the scored GeoParquet.

    Returns
    -------
    gpd.GeoDataFrame
        Kilns with rule-evaluation columns appended.
    """
    from rich import print as rprint

    rules = _load_rules(rules_config)
    kilns = gpd.read_parquet(kilns_path)
    proj_crs = get_projected_crs(centroid_longitude(kilns))

    # Check if any rule is unverified
    any_unverified = False
    if not rules.get("technology", {}).get("verified", True):
        any_unverified = True
    for sr in rules.get("siting_rules", []):
        if not sr.get("verified", True):
            any_unverified = True
            break

    if any_unverified:
        msg = (
            "WARNING: One or more rules in rules.yaml have verified=false. "
            "All output will be marked rules_verified=false. "
            "Verify thresholds against the Act before use."
        )
        warnings.warn(msg, stacklevel=2)
        rprint(f"[bold red]{msg}[/bold red]")

    kilns = gpd.read_parquet(kilns_path)
    rprint(f"[cyan]Evaluating {len(kilns)} kilns against {len(rules.get('siting_rules', []))} siting rules.[/cyan]")

    # Project for distance calculations
    kilns_proj = kilns.to_crs(proj_crs)

    # Technology check
    flagged_classes = rules.get("technology", {}).get("flagged_classes", [])
    tech_severity = rules.get("technology", {}).get("severity", 0)
    kilns["technology_flagged"] = kilns["class"].isin(flagged_classes)

    # Siting rules — compute distances
    distance_cols: dict[str, np.ndarray] = {}
    breach_data: list[list[str]] = [[] for _ in range(len(kilns))]
    breach_scores: np.ndarray = np.zeros(len(kilns))

    # Add tech severity for flagged kilns
    for i, flagged in enumerate(kilns["technology_flagged"]):
        if flagged:
            breach_data[i].append("technology_flagged")
            breach_scores[i] += tech_severity

    for siting_rule in rules.get("siting_rules", []):
        rule_id = siting_rule["id"]
        feature_layer = siting_rule["feature"]
        buffer_m = siting_rule["buffer_m"]
        severity = siting_rule["severity"]

        # Load OSM features for all districts
        all_features = []
        for district_dir in (osm_dir / "osm").iterdir():
            layer_path = district_dir / f"{feature_layer}.parquet"
            if layer_path.exists():
                all_features.append(gpd.read_parquet(layer_path))

        if all_features:
            features = pd.concat(all_features, ignore_index=True)
            features = gpd.GeoDataFrame(features, geometry="geometry", crs="EPSG:4326")
            features_proj = features.to_crs(proj_crs)
        else:
            features_proj = gpd.GeoDataFrame(
                columns=["geometry"], geometry="geometry", crs=proj_crs
            )

        distances = _nearest_distance(kilns_proj, features_proj)
        col_name = f"dist_{feature_layer}_m"
        distance_cols[col_name] = distances

        # Check breaches
        for i, dist in enumerate(distances):
            if dist < buffer_m:
                breach_data[i].append(rule_id)
                breach_scores[i] += severity

    # Assemble output columns
    for col_name, values in distance_cols.items():
        kilns[col_name] = values

    kilns["breached_rules"] = breach_data
    kilns["breach_count"] = [len(b) for b in breach_data]
    kilns["breach_score"] = breach_scores
    kilns["rules_version"] = rules.get("version", "unknown")
    kilns["rules_verified"] = not any_unverified

    output.parent.mkdir(parents=True, exist_ok=True)
    kilns.to_parquet(output)
    rprint(f"[green]Scored kilns written to {output}[/green]")
    rprint(f"  Breaching at least one rule: {(kilns['breach_count'] > 0).sum()}/{len(kilns)}")
    return kilns
