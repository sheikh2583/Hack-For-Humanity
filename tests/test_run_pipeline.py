"""Tests for the pipeline command sequence and fail-fast behavior."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts.run_pipeline import (
    configured_district_names,
    district_for_raster,
    osm_cache_complete,
    pipeline_steps,
    run_pipeline,
)


def test_pipeline_commands_are_in_requested_order() -> None:
    """Pipeline stages preserve inference, fetch, rules, and score order."""
    raster = Path("kilnwatch_chapai_test.tif")
    labels = [label for label, _ in pipeline_steps(real_rasters=[raster])]
    assert labels == [
        f"Real raster inference: {raster}",
        "Merge raster candidates",
        "2. Fetch OSM layers",
        "3. Check rules",
        "4. Score priorities",
    ]


def test_pipeline_adds_audit_summary_stage_when_labels_are_supplied(tmp_path: Path) -> None:
    """A labelled audit CSV is summarized after the normal scoring stages."""
    labels_csv = tmp_path / "audit_labeled.csv"
    labels_csv.write_text("confidence,label\n0.8,TP\n", encoding="utf-8")
    steps = pipeline_steps(
        include_fetch=False, real_rasters=[Path("kilnwatch_chapai_test.tif")], audit_labels=labels_csv
    )
    audit_label, audit_command = steps[-1]
    assert audit_label == "5. Summarize labelled audit results"
    assert audit_command[-2:] == ["--labels", str(labels_csv)]


def test_pipeline_stops_after_failed_stage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed subprocess prevents execution of later stages."""
    # Plant a real file so resolve_weights succeeds; failure comes from the stage.
    fake_weights = tmp_path / "best.pt"
    fake_weights.write_bytes(b"stub")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 7, stdout="stage output", stderr="failure")

    monkeypatch.setattr(
        "scripts.run_pipeline.exported_rasters", lambda: [tmp_path / "kilnwatch_chapai_test.tif"]
    )
    monkeypatch.setattr("scripts.run_pipeline.subprocess.run", fake_run)
    assert run_pipeline(fake_weights) == 7
    assert len(calls) == 1


def test_osm_cache_requires_every_configured_layer(tmp_path: Path) -> None:
    """Fetch is skippable only when all district layer files exist."""
    import yaml

    from src.geo.osm_layers import LAYER_TAGS

    config = tmp_path / "aoi.yaml"
    config.write_text(yaml.safe_dump({"districts": [{"name": "Test"}]}), encoding="utf-8")
    interim = tmp_path / "interim"
    district_dir = interim / "osm" / "Test"
    district_dir.mkdir(parents=True)
    assert not osm_cache_complete(interim, config)
    for layer in LAYER_TAGS:
        (district_dir / f"{layer}.parquet").touch()
    assert osm_cache_complete(interim, config)
    (district_dir / "water.parquet").unlink()
    assert not osm_cache_complete(interim, config)


def test_real_raster_stage_resolves_chapai_to_configured_district(tmp_path: Path) -> None:
    """The Chapai filename token resolves to the configured full district name."""
    config = tmp_path / "aoi.yaml"
    config.write_text(
        "districts:\n  - {name: Chapainawabganj, boundary_name: Nawabganj}\n",
        encoding="utf-8",
    )
    raster = tmp_path / "kilnwatch_chapai_test.tif"
    assert district_for_raster(raster, config) == "Chapainawabganj"
    steps = pipeline_steps(
        Path("model.pt"), include_fetch=False, real_rasters=[raster], aoi_config=config
    )
    inference_step = next(step for step in steps if step[0].startswith("Real raster inference:"))
    assert any("kilns_chapainawabganj.parquet" in arg for arg in inference_step[1])
    assert "--point-output" in inference_step[1]
    assert inference_step[1][inference_step[1].index("--imgsz") + 1] == "512"

    custom_steps = pipeline_steps(
        Path("model.pt"), include_fetch=False, real_rasters=[raster],
        aoi_config=config, imgsz=384,
    )
    custom_inference_step = next(
        step for step in custom_steps if step[0].startswith("Real raster inference:")
    )
    assert custom_inference_step[1][custom_inference_step[1].index("--imgsz") + 1] == "384"
    assert custom_inference_step[1][custom_inference_step[1].index("--device") + 1] == "cpu"


def test_district_for_raster_handles_uppercase_gazipur_filename(tmp_path: Path) -> None:
    """Export filenames retain title case while district matching remains case-insensitive."""
    config = tmp_path / "aoi.yaml"
    config.write_text("districts:\n  - {name: Gazipur}\n", encoding="utf-8")
    raster = tmp_path / "kilnwatch_Gazipur_2025-11-01_2026-02-28.tif"
    assert district_for_raster(raster, config) == "Gazipur"


@pytest.mark.parametrize(
    ("district", "bbox"),
    [
        ("Rajshahi", (88.1, 24.0, 88.8, 24.6)),
        ("Dhaka", (89.9, 23.5, 90.7, 24.1)),
        ("Chittagong", (91.6, 22.1, 92.4, 22.9)),
    ],
)
def test_new_district_pipeline_resolves_and_merges_candidates(
    tmp_path: Path, district: str, bbox: tuple[float, float, float, float]
) -> None:
    """A selected new district yields inference, merge, rules, and score commands."""
    west, south, east, north = bbox
    config = tmp_path / "aoi.yaml"
    config.write_text(
        f"districts:\n  - name: {district}\n    boundary_name: {district}\n"
        f"    bbox: {{west: {west}, south: {south}, east: {east}, north: {north}}}\n",
        encoding="utf-8",
    )
    assert configured_district_names(config) == [district]
    raster = tmp_path / f"kilnwatch_{district.lower()}_test.tif"
    assert district_for_raster(raster, config) == district
    steps = pipeline_steps(
        Path("model.pt"), include_fetch=False, real_rasters=[raster],
        aoi_config=config, district_filter=district,
    )
    labels = [label for label, _ in steps]
    assert labels == [
        f"Real raster inference: {raster}",
        "Merge raster candidates",
        "3. Check rules",
        "4. Score priorities",
    ]
    inference = steps[0][1]
    assert inference[inference.index("--district-name") + 1] == district
    merge = steps[1][1]
    assert "--output" in merge and merge[merge.index("--output") + 1].endswith("kilns.parquet")
    check_rules = steps[2][1]
    assert check_rules[check_rules.index("--kilns") + 1].endswith("kilns.parquet")
