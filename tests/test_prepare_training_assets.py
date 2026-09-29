"""Tiny synthetic coverage for converted training dataset readiness checks."""

import json
from pathlib import Path

from scripts.prepare_training_assets import (
    _create_dataset_archive,
    is_valid_converted_dataset,
)


def test_converted_dataset_requires_all_splits_and_leakage_report(tmp_path: Path) -> None:
    """Accept a tiny complete dataset with the required 1,300 m leakage filter."""
    (tmp_path / "dataset.yaml").write_text(
        "names:\n  0: FCBK\n  1: Zigzag\n", encoding="utf-8"
    )
    (tmp_path / "split_report.json").write_text(
        json.dumps({"leakage_filter_threshold_m": 1300.0}), encoding="utf-8"
    )
    for split in ("train", "val", "test"):
        images = tmp_path / split / "images"
        labels = tmp_path / split / "labels"
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        (images / "tiny.png").write_bytes(b"synthetic image placeholder")
        (labels / "tiny.txt").write_text("0 0 0 1 0 1 1 0 1\n", encoding="utf-8")

    assert is_valid_converted_dataset(tmp_path)
    (tmp_path / "split_report.json").write_text(
        json.dumps({"leakage_filter_threshold_m": 300.0}), encoding="utf-8"
    )
    assert not is_valid_converted_dataset(tmp_path)


def test_dataset_archive_uses_yolo_obb_root(tmp_path: Path, monkeypatch) -> None:
    """Create an extractable archive with the expected top-level directory."""
    import scripts.prepare_training_assets as assets

    dataset = tmp_path / "source"
    (dataset / "train/images").mkdir(parents=True)
    (dataset / "train/labels").mkdir()
    (dataset / "val/images").mkdir(parents=True)
    (dataset / "val/labels").mkdir()
    (dataset / "test/images").mkdir(parents=True)
    (dataset / "test/labels").mkdir()
    (dataset / "dataset.yaml").write_text(
        "names:\n  0: FCBK\n  1: Zigzag\n", encoding="utf-8"
    )
    (dataset / "split_report.json").write_text(
        json.dumps({"leakage_filter_threshold_m": 1300.0}), encoding="utf-8"
    )
    for split in ("train", "val", "test"):
        (dataset / split / "images/tiny.png").write_bytes(b"image")
        (dataset / split / "labels/tiny.txt").write_text("0\n", encoding="utf-8")

    monkeypatch.setattr(assets, "DATASET_ROOT", dataset)
    archive_path = _create_dataset_archive(tmp_path / "transfer.zip")
    import zipfile

    with zipfile.ZipFile(archive_path) as archive:
        assert "yolo_obb/split_report.json" in archive.namelist()
