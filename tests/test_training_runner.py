"""Synthetic tests for portable training configuration and run identity."""

import json
from pathlib import Path

import pytest

from src.training.run_store import (
    allocate_run,
    dataset_fingerprint,
    load_run,
    read_training_config,
    write_json,
)


def test_dataset_fingerprint_tracks_paths_and_metadata(tmp_path: Path) -> None:
    """Fingerprint includes dataset metadata and the split file inventory."""
    for split in ("train", "val", "test"):
        images = tmp_path / split / "images"
        images.mkdir(parents=True)
        (images / "one.png").write_bytes(b"image")
    (tmp_path / "dataset.yaml").write_text("names: [kiln]\n", encoding="utf-8")
    (tmp_path / "split_report.json").write_text('{"filter": 1300}\n', encoding="utf-8")
    initial = dataset_fingerprint(tmp_path)
    (tmp_path / "train/images/two.png").write_bytes(b"more")
    assert dataset_fingerprint(tmp_path) != initial


def test_reads_shared_stage_config(tmp_path: Path) -> None:
    """Validate required fields for each declared model stage."""
    path = tmp_path / "training.yaml"
    valid = (
        "stages:\n"
        "  - {name: n256, model: n.pt, imgsz: 256, epochs: 3}\n"
        "  - {name: n384, model: n.pt, imgsz: 384, epochs: 3}\n"
        "  - {name: n512, model: n.pt, imgsz: 512, epochs: 3}\n"
    )
    path.write_text(valid, encoding="utf-8")
    assert read_training_config(path)["stages"][0]["name"] == "n256"
    path.write_text(
        "stages:\n"
        "  - {name: n256, model: n.pt, imgsz: 256, epochs: 3}\n"
        "  - {name: n384, model: n.pt, imgsz: 384, epochs: 3}\n"
        "  - {name: incomplete}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="name/model/imgsz/epochs"):
        read_training_config(path)


def test_run_state_is_atomic_json_and_validated(tmp_path: Path) -> None:
    """Write and reload state for a sequentially allocated run number."""
    run_id, run_dir = allocate_run(tmp_path)
    state = {"run_id": run_id, "status": "smoke"}
    write_json(run_dir / "run.json", state)
    assert json.loads((run_dir / "run.json").read_text(encoding="utf-8")) == state
    assert load_run(tmp_path, run_id) == state
    with pytest.raises(ValueError, match="Invalid run number"):
        load_run(tmp_path, "../escape")
