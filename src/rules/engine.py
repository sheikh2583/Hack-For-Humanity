"""GIS screening engine — generate candidate signals from mapped features.

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
  breached_rules              list[str]  Legacy internal IDs of candidate signals
  breach_count                int        Number of candidate signals
  breach_score                float      Sum of configured screening severities
  dist_schools_m              float      Distance to nearest school (metres)
  dist_hospitals_m            float      Distance to nearest hospital/clinic
  dist_settlements_m          float      Distance to nearest residential area
  technology_flagged          bool       True if kiln class is FCBK
  rules_version               str        Version string from rules.yaml
  rules_verified              bool       False if *any* rule has verified=false
  signal_provenance_json      str        JSON source, method, and review record per signal
  ==========================  =========  =========================================

Contract
--------
>>> from src.rules.engine import evaluate_rules
>>> evaluate_rules(kilns_path, rules_config, osm_dir, output)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

from src.geo.crs import centroid_longitude, get_projected_crs

REVIEW_STATES = (
    "unverified_candidate",
    "human_reviewed",
    "authority_confirmed",
    "dismissed",
)
DEFAULT_REVIEW_STATE = "unverified_candidate"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_rules(rules_config: Path) -> dict[str, Any]:
    """Load and return the rules YAML config."""
    with open(rules_config) as f:
        return yaml.safe_load(f)


def _nearest_feature(
    kilns_proj: gpd.GeoDataFrame,
    features_proj: gpd.GeoDataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """Return nearest mapped-feature distance and feature row for each kiln.

    Parameters
    ----------
    kilns_proj : gpd.GeoDataFrame
        Kilns in a projected CRS (metres).
    features_proj : gpd.GeoDataFrame
        OSM features in the same projected CRS.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Distance metres and feature row arrays. Missing features have infinite
        distance and feature index -1.
    """
    if features_proj.empty:
        return np.full(len(kilns_proj), np.inf), np.full(len(kilns_proj), -1)

    from shapely import STRtree  # type: ignore[import-untyped]

    tree = STRtree(features_proj.geometry.values)
    indices, distances = tree.query_nearest(
        kilns_proj.geometry.values, return_distance=True, all_matches=False
    )
    # tree.query_nearest returns (input_idx, geom_idx) pairs — we need
    # to aggregate to one distance per kiln.
    result = np.full(len(kilns_proj), np.inf)
    feature_rows = np.full(len(kilns_proj), -1, dtype=int)
    result[indices[0]] = distances
    feature_rows[indices[0]] = indices[1]
    return result, feature_rows


def _optional_text(value: object) -> str | None:
    """Convert present scalar metadata to text without serializing NaN as data."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _ensure_class_column(kilns: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Accept either legacy ``class`` or demo ``class_name`` detection schema."""
    if "class" not in kilns.columns and "class_name" in kilns.columns:
        kilns = kilns.copy()
        kilns["class"] = kilns["class_name"]
    if "class" not in kilns.columns:
        raise ValueError("Kiln data must contain a 'class' or 'class_name' column")
    return kilns


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
    kilns = _ensure_class_column(gpd.read_parquet(kilns_path))
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
    provenance_data: list[list[dict[str, Any]]] = [[] for _ in range(len(kilns))]
    breach_scores: np.ndarray = np.zeros(len(kilns))

    # Add tech severity for flagged kilns
    for i, flagged in enumerate(kilns["technology_flagged"]):
        if flagged:
            breach_data[i].append("technology_flagged")
            breach_scores[i] += tech_severity
            candidate = kilns.iloc[i]
            provenance_data[i].append({
                "signal_id": "technology_flagged",
                "review_state": DEFAULT_REVIEW_STATE,
                "reviewer": None,
                "reviewed_at": None,
                "evidence_references": ["docs/legal_basis.md#rule-evidence-table"],
                "review_notes": "Model class signal only; no technology or legal status is established.",
                "rule_config_version": rules.get("version", "unknown"),
                "rule_config_reference": "config/rules.yaml#technology",
                "source_layer_id": None,
                "source_authority": None,
                "source_url": None,
                "source_version_date": None,
                "source_accessed_at": None,
                "instrument_id": None,
                "effective_dates": None,
                "feature_id": None,
                "geometry_provenance": (
                    _optional_text(candidate.get("detection_geometry_provenance"))
                    or f"Input kiln geometry ({candidate.geometry.geom_type}) in {kilns.crs}; detector geometry lineage not separately recorded"
                ),
                "distance_m": None,
                "measurement_method": "detector class label; no GIS/legal conclusion",
                "detector_model": _optional_text(candidate.get("detector_model")),
                "detector_version": _optional_text(candidate.get("detector_version")),
                "detector_model_version": " / ".join(filter(None, [
                    _optional_text(candidate.get("detector_model")),
                    _optional_text(candidate.get("detector_version")),
                ])) or None,
                "detector_confidence": float(candidate["confidence"]),
                "imagery_date": _optional_text(candidate.get("imagery_date")),
            })

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

        distances, nearest_rows = _nearest_feature(kilns_proj, features_proj)
        col_name = f"dist_{feature_layer}_m"
        distance_cols[col_name] = distances

        # Check breaches
        for i, dist in enumerate(distances):
            if dist < buffer_m:
                breach_data[i].append(rule_id)
                breach_scores[i] += severity
                feature = features.iloc[int(nearest_rows[i])]
                candidate = kilns.iloc[i]
                source_url = _optional_text(feature.get("source_url"))
                provenance_data[i].append({
                    "signal_id": rule_id,
                    "review_state": DEFAULT_REVIEW_STATE,
                    "reviewer": None,
                    "reviewed_at": None,
                    "evidence_references": ["docs/legal_basis.md#rule-evidence-table"],
                    "review_notes": "Mapped-feature screening signal; legal instrument mapping and applicability are unresolved.",
                    "rule_config_version": rules.get("version", "unknown"),
                    "rule_config_reference": f"config/rules.yaml#siting_rules.{rule_id}",
                    "source_layer_id": _optional_text(feature.get("source_layer_id")) or f"openstreetmap:{feature_layer}",
                    "source_authority": _optional_text(feature.get("source_authority")) or "OpenStreetMap contributors",
                    "source_url": source_url or "https://www.openstreetmap.org/",
                    "source_version_date": _optional_text(feature.get("source_version_date")),
                    "source_accessed_at": _optional_text(feature.get("source_accessed_at")),
                    "instrument_id": None,
                    "effective_dates": None,
                    "feature_id": _optional_text(feature.get("feature_id")),
                    "geometry_provenance": (
                        _optional_text(feature.get("geometry_provenance"))
                        or "Geometry provenance not recorded on this cached feature"
                    ),
                    "distance_m": float(dist),
                    "measurement_method": (
                        "Shapely nearest geometry distance from kiln detection "
                        f"({candidate.geometry.geom_type}) to mapped feature geometry in {proj_crs}; not necessarily "
                        "distance to a legally controlling boundary"
                    ),
                    "detector_model": _optional_text(candidate.get("detector_model")),
                    "detector_version": _optional_text(candidate.get("detector_version")),
                    "detector_model_version": " / ".join(filter(None, [
                        _optional_text(candidate.get("detector_model")),
                        _optional_text(candidate.get("detector_version")),
                    ])) or None,
                    "detector_confidence": float(candidate["confidence"]),
                    "imagery_date": _optional_text(candidate.get("imagery_date")),
                })

    # Assemble output columns
    for col_name, values in distance_cols.items():
        kilns[col_name] = values

    kilns["breached_rules"] = breach_data
    kilns["breach_count"] = [len(b) for b in breach_data]
    kilns["breach_score"] = breach_scores
    kilns["rules_version"] = rules.get("version", "unknown")
    kilns["rules_verified"] = not any_unverified
    kilns["signal_provenance_json"] = [
        json.dumps(items, ensure_ascii=False, separators=(",", ":"))
        for items in provenance_data
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    kilns.to_parquet(output)
    rprint(f"[green]Scored kilns written to {output}[/green]")
    rprint(f"  Kiln candidates with one or more configured rule signals: {(kilns['breach_count'] > 0).sum()}/{len(kilns)}")
    return kilns
