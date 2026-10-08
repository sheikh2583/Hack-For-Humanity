"""Tests for the pipeline command sequence and fail-fast behavior."""

from pathlib import Path
from subprocess import CompletedProcess

from scripts.run_pipeline import (
    district_for_raster,
    osm_cache_complete,
    pipeline_steps,
    run_pipeline,
)


def test_pipeline_commands_are_in_requested_order() -> None:
    """Pipeline stages preserve inference, fetch, rules, and score order."""
    labels = [label for label, _ in pipeline_steps()]
    assert labels == ["1. Demo inference", "2. Fetch OSM layers", "3. Check rules", "4. Score priorities"]


def test_pipeline_stops_after_failed_stage(monkeypatch) -> None:
    """A failed subprocess prevents execution of later stages."""
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return CompletedProcess(command, 7, stdout="stage output", stderr="failure")

    monkeypatch.setattr("scripts.run_pipeline.subprocess.run", fake_run)
    assert run_pipeline() == 7
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
    assert "Real raster inference:" in steps[1][0]
    assert any("kilns_chapainawabganj.parquet" in arg for arg in steps[1][1])
    assert "--point-output" in steps[1][1]
