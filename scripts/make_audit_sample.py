"""Create blind Round 2 kiln-candidate label sheets and a separate audit key.

Input schema: district point GeoParquets with kiln_id, confidence, class_name,
district, lat, lon, and the original Chapainawabganj label CSV. Output schema:
two blind CSV sheets, an audit key, and instructions and population reports.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point

from src.geo.crs import centroid_longitude, get_projected_crs

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data/processed/audit_round2"
DISTRICTS = {
    "Chapainawabganj": {
        "path": OUTPUT_DIR / "kilns_chapainawabganj.parquet",
        "targets": {"low": 5, "mid": 25, "high": 10},
    },
    "Gazipur": {
        "path": OUTPUT_DIR / "kilns_gazipur.parquet",
        "targets": {"low": 10, "mid": 30, "high": 20},
    },
}
BANDS = ("low", "mid", "high")
SEED = 42
SHEET_COLUMNS = [
    "kiln_id", "district", "lat", "lon", "google_earth_link", "label",
    "kiln_class", "imagery_date", "labeler_confidence", "cloud_haze", "notes",
]
KEY_COLUMNS = [
    "kiln_id", "district", "model_confidence", "band",
    "tercile_within_district", "predicted_class", "is_overlap", "assigned_sheet",
]


def _components_within_50m(frame: gpd.GeoDataFrame, crs: object) -> list[list[int]]:
    """Return connected components of candidate centroids separated by <=50 m."""
    projected = frame.to_crs(crs)
    points = list(projected.geometry)
    parent = list(range(len(points)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        root_first, root_second = find(first), find(second)
        if root_first != root_second:
            parent[root_second] = root_first

    for first, point in enumerate(points):
        for second in range(first + 1, len(points)):
            if point.distance(points[second]) <= 50:
                union(first, second)
    groups: dict[int, list[int]] = {}
    for index in range(len(points)):
        groups.setdefault(find(index), []).append(index)
    return list(groups.values())


def _eligible_district(
    district: str,
    source: Path,
    old_labels_path: Path,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Filter old nearby candidates and duplicates, then assign confidence bands."""
    source_frame = gpd.read_parquet(source)
    frame = source_frame.copy()
    required = {"kiln_id", "confidence", "class_name", "district", "lat", "lon", "geometry"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{source} missing required fields: {sorted(required - set(frame.columns))}")
    if frame.crs is None:
        raise ValueError(f"{source} has no CRS")
    frame = frame[frame["district"].astype(str).eq(district)].copy()
    frame["confidence"] = pd.to_numeric(frame["confidence"], errors="coerce")
    frame = frame[frame["confidence"].ge(0.10)].copy()
    if frame.empty:
        raise ValueError(f"No candidates at confidence >= 0.10 for {district} in {source}")
    frame["kiln_id"] = frame["kiln_id"].astype(str)
    projected_crs = get_projected_crs(centroid_longitude(frame))
    old_exclusions: set[str] = set()
    old_id_exclusion_count = 0
    old_nearby_count = 0
    if district == "Chapainawabganj":
        old = pd.read_csv(old_labels_path)
        if not {"kiln_id", "lat", "lon"}.issubset(old.columns):
            raise ValueError(f"{old_labels_path} must contain kiln_id, lat, and lon")
        old_ids = set(old["kiln_id"].dropna().astype(str))
        id_matches = set(frame["kiln_id"]) & old_ids
        old_id_exclusion_count = len(id_matches)
        old_exclusions.update(id_matches)
        old_points = old.dropna(subset=["lat", "lon"])
        transformer = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
        old_xy = [transformer.transform(float(row.lon), float(row.lat)) for row in old_points.itertuples()]
        candidate_projected = frame.to_crs(projected_crs)
        for row, geometry in zip(frame.itertuples(), candidate_projected.geometry):
            if str(row.kiln_id) in old_exclusions:
                continue
            point = geometry.centroid
            if any(point.distance(Point(x, y)) <= 50 for x, y in old_xy):
                old_exclusions.add(str(row.kiln_id))
                old_nearby_count += 1
    all_duplicate_groups = [
        group for group in _components_within_50m(frame, projected_crs) if len(group) > 1
    ]
    frame = frame[~frame["kiln_id"].isin(old_exclusions)].copy()
    frame = frame.reset_index(drop=True)

    groups = _components_within_50m(frame, projected_crs)
    keep_indices = [max(group, key=lambda index: float(frame.iloc[index]["confidence"])) for group in groups]
    frame = frame.iloc[keep_indices].copy().reset_index(drop=True)
    ranks = frame["confidence"].rank(method="first")
    frame["tercile_within_district"] = pd.qcut(
        ranks, 3, labels=["low", "mid", "high"]
    ).astype(str)
    confidence = frame["confidence"]
    frame["band"] = np.select(
        [confidence.lt(0.25), confidence.lt(0.45)], ["low", "mid"], default="high"
    )
    stats = {
        "source_rows": len(source_frame),
        "confidence_rows": int((source_frame["confidence"] >= 0.10).sum()),
        "old_id_exclusions": old_id_exclusion_count,
        "old_nearby_exclusions": old_nearby_count,
        "near_duplicate_groups": len(all_duplicate_groups),
        "near_duplicate_excess": sum(len(group) - 1 for group in all_duplicate_groups),
        "population_low": int(frame["band"].eq("low").sum()),
        "population_mid": int(frame["band"].eq("mid").sum()),
        "population_high": int(frame["band"].eq("high").sum()),
    }
    stats["population_after_exclusions_and_dedup"] = len(frame)
    frame["district"] = district
    return frame, stats


def _allocate_overlap(sampled: pd.DataFrame, count: int) -> set[str]:
    """Choose overlap candidates proportionally across district and band strata."""
    strata = [(district, band) for district in DISTRICTS for band in BANDS]
    sizes = [len(sampled[(sampled.district == district) & (sampled.band == band)]) for district, band in strata]
    if sum(sizes) < count:
        raise ValueError(f"Cannot select {count} overlap candidates from {sum(sizes)} sampled rows")
    raw = [count * size / sum(sizes) for size in sizes]
    allocation = [int(value) for value in raw]
    remainder_order = sorted(range(len(raw)), key=lambda index: raw[index] - allocation[index], reverse=True)
    for index in remainder_order[:count - sum(allocation)]:
        allocation[index] += 1
    rng = np.random.default_rng(SEED)
    selected: set[str] = set()
    for (district, band), n in zip(strata, allocation):
        subset = sampled[(sampled.district == district) & (sampled.band == band)]
        if n:
            chosen = rng.choice(subset.index.to_numpy(), size=n, replace=False)
            selected.update(sampled.loc[chosen, "kiln_id"].astype(str))
    return selected


def _write_readme(output_dir: Path) -> None:
    """Write folder-level instructions that protect the separate audit key."""
    text = """# Round 2 candidate labeling kit

Labelers should open only their assigned blind sheet and `LABELING_INSTRUCTIONS.md`.
Do not open `audit_key.csv`; it contains model confidence and screening strata.
Keep the two sheets separate until both labelers have finished.

Fill the empty response columns in `audit_blind_A.csv` or `audit_blind_B.csv`.
Do not sort away or delete `kiln_id`. Return the completed CSV files for analysis.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def _write_labeling_instructions(output_dir: Path) -> None:
    """Write human labeling definitions and visual review guidance."""
    text = """# Labeling instructions

Use only the blind sheet assigned to you. Do not look at model confidence.

- `label`: TP = a brick kiln is clearly visible at the location; FP = no kiln; SKIP = imagery unclear, cloudy, or undecidable. Prefer SKIP over guessing.
- `kiln_class`: FCBK (fixed-chimney, usually circular/oval with a tall chimney), Zigzag (rectangular, zigzag brick layout), unsure, or n/a for FP/SKIP.
- `imagery_date`: enter the date shown in Google Earth for the view used. Check the history slider and note in `notes` if a kiln appears on some dates but not others.
- `labeler_confidence`: high / medium / low.
- `cloud_haze`: none / light / heavy.
- A cleared or abandoned kiln footprint is FP unless a kiln structure is present.
- Leave `kiln_class` as n/a for FP or SKIP.
- Leave a short reason in `notes` when useful. Do not open `audit_key.csv`.
"""
    (output_dir / "LABELING_INSTRUCTIONS.md").write_text(text, encoding="utf-8")


def make_audit_sample(
    output_dir: Path = OUTPUT_DIR,
    *,
    old_labels_path: Path = ROOT / "temporary doc share/audit_labeled.csv",
    overlap_count: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create 100 stratified candidate rows, blind sheets, key, and reports."""
    rng = np.random.default_rng(SEED)
    frames: list[pd.DataFrame] = []
    stats_by_district: dict[str, dict[str, int]] = {}
    for district, config in DISTRICTS.items():
        if not config["path"].is_file():
            raise FileNotFoundError(f"Missing {district} source candidates: {config['path']}")
        frame, stats = _eligible_district(district, config["path"], old_labels_path)
        stats_by_district[district] = stats
        for band in BANDS:
            candidates = frame[frame["band"] == band]
            requested = config["targets"][band]
            count = min(requested, len(candidates))
            stats[f"requested_{band}"] = requested
            stats[f"sampled_{band}"] = count
            stats[f"shortfall_{band}"] = requested - count
            if count:
                chosen = rng.choice(candidates.index.to_numpy(), count, replace=False)
                frames.append(frame.loc[chosen].copy())
    sampled = pd.concat(frames, ignore_index=True)
    if len(sampled) < overlap_count:
        raise ValueError(f"Sample contains {len(sampled)} candidates; cannot assign {overlap_count} overlap rows")
    overlap_ids = _allocate_overlap(sampled, overlap_count)
    sampled["is_overlap"] = sampled["kiln_id"].astype(str).isin(overlap_ids)
    non_overlap = sampled.loc[~sampled["is_overlap"]].sample(frac=1, random_state=SEED).copy()
    half = len(non_overlap) // 2
    assigned_a = set(non_overlap.iloc[:half]["kiln_id"].astype(str))
    sampled["assigned_sheet"] = sampled.apply(
        lambda row: "A+B" if row["is_overlap"] else ("A" if str(row["kiln_id"]) in assigned_a else "B"), axis=1
    )
    sampled["model_confidence"] = sampled["confidence"].astype(float)
    sampled["predicted_class"] = sampled["class_name"].astype(str)
    sampled["google_earth_link"] = sampled.apply(
        lambda row: f"https://earth.google.com/web/@{row['lat']},{row['lon']},0a,500d,35y,0h,0t,0r",
        axis=1,
    )
    for field in ("label", "kiln_class", "imagery_date", "labeler_confidence", "cloud_haze", "notes"):
        sampled[field] = ""

    key = sampled[KEY_COLUMNS].copy()
    output_dir.mkdir(parents=True, exist_ok=True)
    for sheet in ("A", "B"):
        include = sampled["is_overlap"] | sampled["assigned_sheet"].eq(sheet)
        sheet_frame = sampled.loc[include, SHEET_COLUMNS].sample(frac=1, random_state=SEED + ord(sheet)).copy()
        sheet_frame.to_csv(output_dir / f"audit_blind_{sheet}.csv", index=False)
    key.to_csv(output_dir / "audit_key.csv", index=False)

    date_text = datetime.now(ZoneInfo("Asia/Dhaka")).date().isoformat()
    report_lines = [
        "# Round 2 screening sample report", "", f"- Seed: {SEED}", f"- Date: {date_text}",
        f"- Chapainawabganj source: `{DISTRICTS['Chapainawabganj']['path'].as_posix()}`",
        f"- Gazipur source: `{DISTRICTS['Gazipur']['path'].as_posix()}`",
        f"- Earlier label file read without modification: `{old_labels_path.as_posix()}`",
        "- Near candidates were grouped by centroid distance <=50 m in the project distance CRS; the highest-confidence candidate was retained per group.",
        "- Chapainawabganj candidates matching any earlier kiln_id or within 50 m of an earlier labeled point were excluded before grouping.",
        "", "| District | Band | Eligible population after exclusions/dedup | Requested | Sampled | Shortfall |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for district in DISTRICTS:
        stats = stats_by_district[district]
        for band in BANDS:
            report_lines.append(
                f"| {district} | {band} | {stats[f'population_{band}']} | "
                f"{stats[f'requested_{band}']} | {stats[f'sampled_{band}']} | {stats[f'shortfall_{band}']} |"
            )
    for district in DISTRICTS:
        stats = stats_by_district[district]
        report_lines.append(
            f"- {district}: source {stats['source_rows']} rows; {stats['confidence_rows']} at confidence >=0.10; "
            f"near-candidate groups {stats['near_duplicate_groups']} ({stats['near_duplicate_excess']} excess rows); "
            f"earlier ID exclusions {stats['old_id_exclusions']}; nearby exclusions {stats['old_nearby_exclusions']}."
        )
    report_lines.extend([
        "", f"- Total selected: {len(sampled)}; overlap set: {int(sampled['is_overlap'].sum())}.",
        (f"- Sheet A rows: {int((sampled['is_overlap'] | sampled['assigned_sheet'].eq('A')).sum())}; "
         f"sheet B rows: {int((sampled['is_overlap'] | sampled['assigned_sheet'].eq('B')).sum())}."),
        "- Earlier Chapainawabganj set: 30 IDs checked; ID and 50 m exclusions are included above.",
        "",
    ])
    (output_dir / "audit_sampling_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    _write_readme(output_dir)
    _write_labeling_instructions(output_dir)
    print(f"Round 2 labeling sheets and audit key written to {output_dir}")
    return sampled, key


def main() -> None:
    """Create the standard Round 2 candidate label kit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--old-labels", type=Path, default=ROOT / "temporary doc share/audit_labeled.csv")
    args = parser.parse_args()
    make_audit_sample(args.output_dir, old_labels_path=args.old_labels)


if __name__ == "__main__":
    main()
