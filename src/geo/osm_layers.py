"""Fetch OpenStreetMap layers per district via Overpass / osmnx.

Input
-----
- ``aoi_config``:  Path to ``config/aoi.yaml`` (district names).

Output
------
- GeoParquet files cached in ``data/interim/osm/<district>/``:

  ==============  =============================================
  File            Contents
  ==============  =============================================
  schools.parquet      amenity=school
  hospitals.parquet    amenity=hospital|clinic|doctors
  settlements.parquet  landuse=residential + place=village|hamlet
  forests.parquet      landuse=forest|natural=wood
  water.parquet        natural=water|waterway=river|wetland
  railways.parquet     railway=*
  ==============  =============================================

- A completeness report (``completeness.json``) with feature counts
  per km2 and warnings about sparse layers.

Contract
--------
>>> from src.geo.osm_layers import fetch_all_layers
>>> fetch_all_layers(aoi_config=Path("config/aoi.yaml"), output_dir=...)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOUNDARIES = PROJECT_ROOT / "data/raw/boundaries/geoBoundaries_BGD_ADM2.geojson"
DEFAULT_PBF = PROJECT_ROOT / "data/raw/osm/bangladesh-latest.osm.pbf"
PBF_DOWNLOAD_ERROR = (
    "OSM fetch failed. Download bangladesh-latest.osm.pbf from "
    "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf and place it at "
    "data/raw/osm/bangladesh-latest.osm.pbf"
)

# ---------------------------------------------------------------------------
# Layer definitions
# ---------------------------------------------------------------------------

LAYER_TAGS: dict[str, dict[str, Any]] = {
    "schools": {"amenity": "school"},
    "hospitals": {"amenity": ["hospital", "clinic", "doctors"]},
    "settlements": {
        "landuse": "residential",
        "place": ["village", "hamlet"],
    },
    "forests": {
        "landuse": "forest",
        "natural": "wood",
    },
    "water": {
        "natural": ["water", "wetland"],
        "waterway": "river",
    },
    "railways": {"railway": True},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_layer(
    layer_name: str,
    tags: dict[str, Any],
    bbox: tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    """Fetch a single OSM layer within a bbox.

    Parameters
    ----------
    layer_name : str
        Human-readable layer name.
    tags : dict
        OSM tag filter for ``osmnx.features_from_bbox``.
    bbox : tuple
        (west, south, east, north) in EPSG:4326.

    Returns
    -------
    gpd.GeoDataFrame
        Features with geometry in EPSG:4326.
    """
    import osmnx as ox  # type: ignore[import-untyped]
    from osmnx._errors import InsufficientResponseError  # type: ignore[import-untyped]

    # A supplied national snapshot is the deterministic/offline source for this
    # run. Avoid spending minutes retrying a known-unreachable Overpass endpoint.
    if DEFAULT_PBF.is_file():
        return _fetch_layer_from_pbf(layer_name, tags, bbox, DEFAULT_PBF)

    west, south, east, north = bbox
    try:
        gdf = ox.features_from_bbox(bbox=(north, south, east, west), tags=tags)
        gdf = _annotate_source_provenance(
            gdf,
            layer_name,
            str(getattr(ox.settings, "overpass_url", None) or "https://www.openstreetmap.org/"),
        )
        # Keep only geometry and key columns
        keep_cols = [c for c in [
            "name", "amenity", "landuse", "natural", "place", "waterway", "railway",
            "feature_id", "source_layer_id", "source_authority", "source_url",
            "source_accessed_at", "source_version_date", "geometry_provenance",
        ]
                     if c in gdf.columns]
        gdf = gdf[keep_cols + ["geometry"]].copy()
        gdf = gdf.to_crs("EPSG:4326")
        return gdf
    except InsufficientResponseError:
        # No features of this type in the area - return empty GDF
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    except Exception as overpass_error:
        if not DEFAULT_PBF.is_file():
            raise RuntimeError(PBF_DOWNLOAD_ERROR) from overpass_error
        try:
            return _fetch_layer_from_pbf(layer_name, tags, bbox, DEFAULT_PBF)
        except Exception as pbf_error:
            raise RuntimeError(
                f"Overpass failed and local PBF fallback failed for {layer_name}: {pbf_error}"
            ) from pbf_error


@lru_cache(maxsize=4)
def _pbf_reader(pbf_path: str, bbox: tuple[float, float, float, float]) -> Any:
    """Create a cached Pyrosm reader restricted to a district bounding box."""
    try:
        from pyrosm import OSM  # type: ignore[import-untyped]
    except ImportError as error:
        raise ImportError("PBF fallback requires pyrosm; install with `pip install 'kilnwatch-bd[geo]'`") from error
    from shapely.geometry import box

    return OSM(pbf_path, bounding_box=box(*bbox), engine="out_of_core")


def _fetch_layer_from_pbf(
    layer_name: str,
    tags: dict[str, Any],
    bbox: tuple[float, float, float, float],
    pbf_path: Path,
) -> gpd.GeoDataFrame:
    """Extract the layer's OSM tag union from a local PBF within ``bbox``.

    Input schema: layer tag mapping used by Overpass and a national OSM PBF.
    Output schema: WGS84 GeoDataFrame compatible with the Overpass cache.
    """
    import pandas as pd

    reader = _pbf_reader(str(pbf_path.resolve()), bbox)
    extracts: list[gpd.GeoDataFrame] = []
    # Existing OSMnx tag mappings represent a union over tag keys. Query each key
    # separately so Pyrosm's key/value filters preserve that same union.
    for key, value in tags.items():
        # Pyrosm expects exact tag values as a list. ``True`` is its special
        # value meaning any tag value and is accepted directly.
        filter_value = value if value is True or isinstance(value, list) else [value]
        result = reader.get_data_by_custom_criteria(
            custom_filter={key: filter_value},
            osm_keys_to_keep=[key],
            tags_as_columns=["name", *tags.keys()],
            keep_other_tags=False,
        )
        if result is not None and not result.empty:
            extracts.append(result)
    if not extracts:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(pd.concat(extracts), geometry="geometry", crs="EPSG:4326")
    dedupe_keys = [
        (repr(index), geometry.wkb if geometry is not None else None)
        for index, geometry in zip(gdf.index, gdf.geometry)
    ]
    gdf = gdf.loc[~pd.Index(dedupe_keys).duplicated(keep="first")].copy()
    keep_cols = [
        column for column in [
            "name", "amenity", "landuse", "natural", "place", "waterway", "railway",
        ] if column in gdf.columns
    ]
    gdf = gdf[keep_cols + ["geometry"]].to_crs("EPSG:4326")
    gdf = _annotate_source_provenance(
        gdf,
        layer_name,
        "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf",
        source_description="local Geofabrik Bangladesh PBF snapshot",
    )
    return gdf


def _annotate_source_provenance(
    gdf: gpd.GeoDataFrame,
    layer_name: str,
    source_url: str,
    source_description: str = "OpenStreetMap geometry returned by Overpass",
) -> gpd.GeoDataFrame:
    """Attach source and feature provenance to one OSM layer.

    Input schema: GeoDataFrame returned by Overpass or Pyrosm; feature index retained.
    Output schema: copy with source, feature ID, retrieval timestamp, and
    geometry-provenance columns. OSM snapshot date remains null because the
    current request path does not expose it.
    """
    result = gdf.copy()
    result["feature_id"] = [repr(value) for value in result.index]
    result["source_layer_id"] = f"openstreetmap:{layer_name}"
    result["source_authority"] = "OpenStreetMap contributors"
    result["source_url"] = source_url
    result["source_accessed_at"] = datetime.now(UTC).isoformat()
    result["source_version_date"] = None
    result["geometry_provenance"] = (
        f"{source_description}; downstream pipeline clips "
        "it to configured ADM2 polygon; not a legally controlling boundary"
    )
    return result


def _bbox_area_km2(bbox: tuple[float, float, float, float]) -> float:
    """Approximate bbox area in km2 using a simple lat/lon scaling.

    Parameters
    ----------
    bbox : tuple
        (west, south, east, north) in degrees.
    """
    import math

    west, south, east, north = bbox
    mid_lat = math.radians((south + north) / 2)
    width_km = (east - west) * 111.32 * math.cos(mid_lat)
    height_km = (north - south) * 110.574
    return abs(width_km * height_km)


def _district_bbox(
    district_name: str, boundaries_path: Path = DEFAULT_BOUNDARIES
) -> tuple[float, float, float, float]:
    """Resolve an ADM2 district name to its EPSG:4326 extent."""
    geometry = _district_geometry(district_name, boundaries_path)
    return tuple(float(value) for value in geometry.bounds)


def _district_geometry(
    district_name: str, boundaries_path: Path = DEFAULT_BOUNDARIES
) -> Any:
    """Resolve an ADM2 district name to its EPSG:4326 polygon."""
    if not boundaries_path.exists():
        raise FileNotFoundError(f"ADM2 boundaries not found: {boundaries_path}")
    boundaries = gpd.read_file(boundaries_path)
    if "shapeName" not in boundaries.columns:
        raise ValueError("ADM2 GeoJSON must contain the geoBoundaries shapeName field")
    matches = boundaries[boundaries["shapeName"].str.casefold() == district_name.casefold()]
    if len(matches) != 1:
        raise ValueError(f"Expected one ADM2 polygon named {district_name!r}; found {len(matches)}")
    return matches.to_crs("EPSG:4326").geometry.iloc[0]


def _clip_features_to_district(
    features: gpd.GeoDataFrame, district_geometry: Any
) -> gpd.GeoDataFrame:
    """Keep only fetched OSM features intersecting the district polygon."""
    if features.empty:
        return features
    return gpd.clip(features.to_crs("EPSG:4326"), district_geometry)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def fetch_all_layers(
    aoi_config: Path,
    output_dir: Path,
    refresh: bool = False,
) -> dict[str, dict[str, Any]]:
    """Fetch all OSM layers for every district in the AOI config.

    Parameters
    ----------
    aoi_config : Path
        Path to ``config/aoi.yaml``.
    output_dir : Path
        Base directory for cached outputs.
    refresh : bool
        Re-query Overpass even when a complete local cache is available.

    Returns
    -------
    dict
        Nested report: ``{district: {layer: {count, count_per_km2}}}``.
    """
    from rich import print as rprint

    with open(aoi_config) as f:
        cfg = yaml.safe_load(f)

    report: dict[str, dict[str, Any]] = {}

    for district in cfg["districts"]:
        name = district["name"]
        boundary_name = district.get("boundary_name", name)
        district_geometry = _district_geometry(boundary_name)
        bbox = tuple(float(value) for value in district_geometry.bounds)
        area_km2 = _bbox_area_km2(bbox)
        rprint(f"[cyan]Fetching OSM layers for {name} (~{area_km2:.0f} km2)...[/cyan]")

        dist_dir = output_dir / "osm" / name
        dist_dir.mkdir(parents=True, exist_ok=True)
        cache_marker = dist_dir / ".cache_version"
        cache_ready = cache_marker.is_file() and cache_marker.read_text().strip() == "2"
        if refresh:
            cache_marker.unlink(missing_ok=True)
        report[name] = {}

        for layer_name, tags in LAYER_TAGS.items():
            out_path = dist_dir / f"{layer_name}.parquet"
            if cache_ready and not refresh and out_path.exists():
                gdf = gpd.read_parquet(out_path)
                rprint(f"  -> {layer_name}: loaded local cache ({len(gdf)} features)")
            else:
                source = "local PBF" if DEFAULT_PBF.is_file() else "Overpass"
                rprint(f"  -> {layer_name}: loading from {source}...")
                gdf = _fetch_layer(layer_name, tags, bbox)
                gdf = _clip_features_to_district(gdf, district_geometry)
                gdf.to_parquet(out_path)
            count = len(gdf)
            report[name][layer_name] = {
                "count": count,
                "count_per_km2": round(count / area_km2, 3) if area_km2 > 0 else 0,
            }
            rprint(f"    {count} features ({report[name][layer_name]['count_per_km2']}/km2)")

        # Write completeness report
        report_path = dist_dir / "completeness.json"
        report_path.write_text(json.dumps(report[name], indent=2))
        cache_marker.write_text("2\n", encoding="utf-8")

        # Render a map per layer
        render_layer_maps(name, bbox, dist_dir)

    rprint("[green]OSM layers fetched and cached.[/green]")
    return report


# ---------------------------------------------------------------------------
# Layer map visualisation
# ---------------------------------------------------------------------------

LAYER_COLORS: dict[str, str] = {
    "schools": "#e74c3c",
    "hospitals": "#3498db",
    "settlements": "#f39c12",
    "forests": "#27ae60",
    "water": "#2980b9",
    "railways": "#7f3c8d",
}


def render_layer_maps(
    district_name: str,
    bbox: tuple[float, float, float, float],
    dist_dir: Path,
) -> None:
    """Render a Folium HTML map for each OSM layer in a district.

    Parameters
    ----------
    district_name : str
        Human-readable district name.
    bbox : tuple
        (west, south, east, north) in EPSG:4326.
    dist_dir : Path
        Directory containing the layer GeoParquet files.

    Output
    ------
    Writes ``<dist_dir>/<layer>_map.html`` for each layer.
    """
    try:
        import folium  # type: ignore[import-untyped]
    except ImportError:
        return  # folium is optional; skip map rendering

    west, south, east, north = bbox
    center = [(south + north) / 2, (west + east) / 2]

    for layer_name in LAYER_TAGS:
        parquet_path = dist_dir / f"{layer_name}.parquet"
        if not parquet_path.exists():
            continue

        gdf = gpd.read_parquet(parquet_path)
        if gdf.empty:
            continue

        m = folium.Map(location=center, zoom_start=11, tiles=None)
        color = LAYER_COLORS.get(layer_name, "#888888")

        for _, row in gdf.iterrows():
            geom = row.geometry
            name_label = row.get("name", layer_name)
            if geom.geom_type == "Point":
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    tooltip=str(name_label),
                ).add_to(m)
            else:
                folium.GeoJson(
                    geom.__geo_interface__,
                    style_function=lambda _feat, c=color: {
                        "color": c,
                        "weight": 2,
                        "fillOpacity": 0.3,
                    },
                    tooltip=str(name_label),
                ).add_to(m)

        map_path = dist_dir / f"{layer_name}_map.html"
        m.save(str(map_path))
