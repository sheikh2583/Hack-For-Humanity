"""KilnWatch BD - CLI entry point.

Provides one Typer command per pipeline stage.  Run ``kilnwatch --help``
for the full list.

Usage
-----
    kilnwatch convert       # Step 2: dataset conversion
    kilnwatch export-s2     # Step 4a: Sentinel-2 composite export
    kilnwatch infer         # Step 4b: YOLO-OBB inference
    kilnwatch fetch-osm     # Step 5: OSM layer download
    kilnwatch check-rules   # Step 6: compliance rule evaluation
    kilnwatch score         # Step 7: priority scoring
    kilnwatch audit-sample  # Step 9: generate audit sample
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint

app = typer.Typer(
    name="kilnwatch",
    help="KilnWatch BD - satellite-based brick kiln compliance triage.",
    add_completion=False,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
"""Absolute path to the repository root (one level above ``src/``)."""


def _resolve_config(name: str) -> Path:
    """Return the absolute path to a YAML config file in ``config/``."""
    p = PROJECT_ROOT / "config" / name
    if not p.exists():
        rprint(f"[red]Config file not found:[/red] {p}")
        raise typer.Exit(code=1)
    return p


# ---------------------------------------------------------------------------
# Pipeline commands
# ---------------------------------------------------------------------------


@app.command()
def explore(
    dataset_dir: Annotated[
        Path, typer.Argument(help="Path to the raw SentinelKilnDB directory")
    ],
) -> None:
    """Step 2.1 - Print dataset structure and sample labels, then STOP.

    Reads the three Parquet files (``train/train.parquet``,
    ``val/val.parquet``, ``test/test.parquet``) inside ``dataset_dir``
    via streaming batches and prints schema, row counts, and sample
    labels.  Run this first to confirm the dataset layout matches
    expectations before running ``kilnwatch convert``.
    """
    import pyarrow.parquet as pq

    from src.data.convert_sentinelkilndb import (
        COL_IMAGE_NAME,
        COL_OBB,
        SPLITS,
        _parquet_path,
        parse_latlon,
    )

    rprint(f"\n[bold cyan]Dataset directory:[/bold cyan] {dataset_dir}\n")

    # Discover and summarise Parquet files
    total_all = 0
    rprint("[bold]Parquet files:[/bold]")
    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.is_file():
            rprint(f"  [red]MISSING:[/red] {pq_path}")
            continue
        pf = pq.ParquetFile(pq_path)
        n_rows = pf.metadata.num_rows
        n_groups = pf.num_row_groups
        rprint(f"  {pq_path.relative_to(dataset_dir)} - {n_rows} rows, {n_groups} row group(s)")
        total_all += n_rows

    rprint(f"\n[bold]Total chips across all splits:[/bold] {total_all}")

    # Print schema of the train file (representative)
    train_pq = _parquet_path(dataset_dir, "train")
    if train_pq.is_file():
        pf = pq.ParquetFile(train_pq)
        rprint("\n[bold]Schema (train.parquet):[/bold]")
        rprint(str(pf.schema_arrow).rstrip())

    # Show 5 sample label lines from positive chips (streaming)
    rprint("\n[bold]Sample positive labels (first 5 found via streaming):[/bold]")
    shown = 0
    for split in SPLITS:
        pq_path = _parquet_path(dataset_dir, split)
        if not pq_path.is_file():
            continue
        pf = pq.ParquetFile(pq_path)
        for batch in pf.iter_batches(
            batch_size=4096,
            columns=[COL_IMAGE_NAME, COL_OBB],
        ):
            d = batch.to_pydict()
            for name, obb in zip(d[COL_IMAGE_NAME], d[COL_OBB]):
                if not obb:
                    continue
                parsed = parse_latlon(name)
                if parsed is None:
                    continue
                rprint(f"\n  [cyan]{name}[/cyan]  (from {split})")
                for line in obb:
                    rprint(f"    {line}")
                shown += 1
                if shown >= 5:
                    break
            if shown >= 5:
                break
        if shown >= 5:
            break

    if shown == 0:
        rprint("  [yellow]No positive chips with parseable filenames found.[/yellow]")

    rprint("\n[bold yellow]STOPPED. Review the above, then run "
           "'kilnwatch convert' to proceed.[/bold yellow]")


@app.command()
def convert(
    dataset_dir: Annotated[
        Path, typer.Argument(help="Path to the raw SentinelKilnDB directory")
    ],
    boundary: Annotated[
        Path,
        typer.Option(help="GeoJSON boundary file for Bangladesh"),
    ] = PROJECT_ROOT / "data" / "raw" / "bangladesh_boundary.geojson",
    output_dir: Annotated[
        Path, typer.Option(help="Where to write the converted dataset")
    ] = PROJECT_ROOT / "data" / "interim" / "yolo_obb",
    batch_size: Annotated[
        int, typer.Option(min=1, help="Parquet rows per batch; lower this to reduce peak RAM")
    ] = 4096,
) -> None:
    """Step 2 - Convert SentinelKilnDB to spatial-block-split YOLO-OBB."""
    from src.data.convert_sentinelkilndb import convert_dataset

    convert_dataset(
        dataset_dir=dataset_dir,
        boundary_path=boundary,
        output_dir=output_dir,
        batch_size=batch_size,
    )


@app.command("export-s2")
def export_s2(
    aoi_config: Annotated[
        Path, typer.Option(help="Path to aoi.yaml")
    ] = PROJECT_ROOT / "config" / "aoi.yaml",
    project_id: Annotated[
        str | None, typer.Option(help="Google Cloud project ID; defaults to EARTHENGINE_PROJECT")
    ] = None,
) -> None:
    """Step 4a - Export Sentinel-2 composites via Earth Engine."""
    from src.data.export_s2 import export_composites

    export_composites(aoi_config=aoi_config, project_id=project_id)


@app.command()
def infer(
    weights: Annotated[Path, typer.Argument(help="Path to best.pt")],
    raster_dir: Annotated[
        Path, typer.Option(help="Directory containing exported GeoTIFFs")
    ] = PROJECT_ROOT / "data" / "interim" / "s2_composites",
    output: Annotated[
        Path, typer.Option(help="Output GeoParquet path")
    ] = PROJECT_ROOT / "data" / "processed" / "kilns.parquet",
    imgsz: Annotated[int, typer.Option(help="Must match the training image size")]=512,
) -> None:
    """Step 4b - Run YOLO-OBB inference and write kilns.parquet."""
    from src.detect.infer import run_inference

    run_inference(weights=weights, raster_dir=raster_dir, output=output, imgsz=imgsz)


@app.command("fetch-osm")
def fetch_osm(
    aoi_config: Annotated[
        Path, typer.Option(help="Path to aoi.yaml")
    ] = PROJECT_ROOT / "config" / "aoi.yaml",
    output_dir: Annotated[
        Path, typer.Option(help="Where to cache OSM layers (GeoParquet)")
    ] = PROJECT_ROOT / "data" / "interim",
    refresh: Annotated[
        bool, typer.Option(help="Re-download layers instead of using complete local cache")
    ] = False,
) -> None:
    """Step 5 - Download OpenStreetMap layers per district."""
    from src.geo.osm_layers import fetch_all_layers

    fetch_all_layers(aoi_config=aoi_config, output_dir=output_dir, refresh=refresh)


@app.command("check-rules")
def check_rules(
    kilns: Annotated[
        Path, typer.Option(help="Path to kilns.parquet")
    ] = PROJECT_ROOT / "data" / "processed" / "kilns.parquet",
    rules_config: Annotated[
        Path, typer.Option(help="Path to rules.yaml")
    ] = PROJECT_ROOT / "config" / "rules.yaml",
    osm_dir: Annotated[
        Path, typer.Option(help="Directory with cached OSM GeoParquet layers")
    ] = PROJECT_ROOT / "data" / "interim",
    output: Annotated[
        Path, typer.Option(help="Output GeoParquet path")
    ] = PROJECT_ROOT / "data" / "processed" / "kilns_scored.parquet",
) -> None:
    """Step 6 - Evaluate compliance rules per kiln."""
    from src.rules.engine import evaluate_rules

    evaluate_rules(
        kilns_path=kilns,
        rules_config=rules_config,
        osm_dir=osm_dir,
        output=output,
    )


@app.command()
def score(
    kilns_scored: Annotated[
        Path, typer.Option(help="Path to kilns_scored.parquet")
    ] = PROJECT_ROOT / "data" / "processed" / "kilns_scored.parquet",
    output: Annotated[
        Path, typer.Option(help="Output GeoParquet path")
    ] = PROJECT_ROOT / "data" / "processed" / "kilns_prioritised.parquet",
) -> None:
    """Step 7 - Compute priority scores."""
    from src.score.priority import compute_priority

    compute_priority(kilns_scored_path=kilns_scored, output=output)


@app.command("audit-sample")
def audit_sample(
    kilns: Annotated[
        Path, typer.Option(help="Path to kilns_prioritised.parquet")
    ] = PROJECT_ROOT / "data" / "processed" / "kilns_prioritised.parquet",
    n: Annotated[int, typer.Option(help="Number of samples")] = 30,
    output: Annotated[
        Path, typer.Option(help="Output CSV path")
    ] = PROJECT_ROOT / "data" / "processed" / "audit.csv",
) -> None:
    """Step 9 - Generate a stratified audit sample."""
    from src.eval.audit_sample import generate_audit_sample

    generate_audit_sample(kilns_path=kilns, n=n, output=output)


@app.command("error-analysis")
def error_analysis(
    predictions: Annotated[Path, typer.Option(help="Directory with YOLO prediction labels")],
    ground_truth: Annotated[Path, typer.Option(help="Directory with YOLO ground-truth labels")],
    images: Annotated[Path, typer.Option(help="Directory with PNG image chips")],
    output: Annotated[
        Path, typer.Option(help="Directory for false-positive and missed-kiln crops")
    ] = PROJECT_ROOT / "data" / "processed" / "error_analysis",
    top_n: Annotated[int, typer.Option(min=1, help="Maximum errors per category")] = 50,
) -> None:
    """Save top false-positive and missed-kiln image crops."""
    for path in (predictions, ground_truth, images):
        if not path.is_dir():
            rprint(f"[red]Input directory not found:[/red] {path}")
            raise typer.Exit(code=1)
    from src.eval.error_analysis import run_error_analysis

    run_error_analysis(
        predictions_dir=predictions,
        ground_truth_dir=ground_truth,
        images_dir=images,
        output_dir=output,
        top_n=top_n,
    )


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
