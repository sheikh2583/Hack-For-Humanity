"""Synthetic, offline tests for the SentinelKilnDB date-forensics diagnostic."""

import csv
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from tools.date_forensics import (
    CSV_COLUMNS,
    CandidateImage,
    Chip,
    DateWindow,
    compare_patch,
    date_is_in_window,
    parse_chip_coordinates,
    parse_date_window,
    run_diagnostic,
)


def test_parse_filename_coordinates_from_stem() -> None:
    """Filename latitude/longitude are parsed in that order without fixed values."""
    assert parse_chip_coordinates("-12.340_45.670.png") == (-12.34, 45.67)


def test_end_date_is_exclusive() -> None:
    """A scene on the start date is included; one on the end date is excluded."""
    window = parse_date_window("2024-02-01/2024-03-01")
    assert date_is_in_window("2024-02-01", window)
    assert date_is_in_window("2024-02-29T10:30:00Z", window)
    assert not date_is_in_window("2024-03-01", window)
    assert window == DateWindow(date(2024, 2, 1), date(2024, 3, 1))


def test_compare_patch_selects_one_pixel_alignment() -> None:
    """Shift search recovers a one-pixel synthetic displacement per channel."""
    rng = np.random.default_rng(19)
    training = rng.integers(0, 256, size=(24, 24, 3), dtype=np.uint8)
    shifted = np.zeros(training.shape, dtype=np.float64)
    shifted[1:, 1:] = training[:-1, :-1].astype(np.float64) * 1000 + 3000
    comparison = compare_patch(training, shifted, np.ones((24, 24), dtype=bool))

    assert (comparison.offset_dx, comparison.offset_dy) == (1, 1)
    assert comparison.mean_pearson is not None and comparison.mean_pearson > 0.999


def test_run_diagnostic_writes_documented_schema_with_fake_imagery(tmp_path: Path) -> None:
    """A fake scene fetcher exercises output schema without EE/network calls."""
    training_dir = tmp_path / "train"
    training_dir.mkdir()
    yy, xx = np.indices((128, 128))
    training = np.stack((xx, yy, (xx + yy) % 256), axis=-1).astype(np.uint8)
    chip_path = training_dir / "12.340_45.670.png"
    Image.fromarray(training).save(chip_path)
    config_path = tmp_path / "preprocessing.yaml"
    config_path.write_text(
        "patches:\n  size_px: 128\noutput:\n  scale_m: 10\n",
        encoding="utf-8",
    )
    window = parse_date_window("2024-01-01/2024-02-01")

    def fake_fetcher(chip: Chip, requested_window: DateWindow) -> list[CandidateImage]:
        assert chip.path == chip_path
        assert requested_window == window
        return [CandidateImage(
            kind="scene",
            candidate_id="lower-correlation-scene",
            scene_date_utc="2024-01-10",
            cloudy_pixel_percentage=0.4,
            scenes_in_window=2,
            scenes_in_median=1,
            raw_rgb=np.flip(training, axis=0).astype(np.float64) * 1000 + 500,
            valid_mask=np.ones((128, 128), dtype=bool),
        ), CandidateImage(
            kind="scene",
            candidate_id="synthetic-scene",
            scene_date_utc="2024-01-15",
            cloudy_pixel_percentage=0.5,
            scenes_in_window=2,
            scenes_in_median=1,
            raw_rgb=training.astype(np.float64) * 1000 + 500,
            valid_mask=np.ones((128, 128), dtype=bool),
        )]

    output = run_diagnostic(
        training_dir,
        [window],
        tmp_path / "nested" / "forensics.csv",
        config_path=config_path,
        fetcher=fake_fetcher,
    )

    with output.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
    assert tuple(reader.fieldnames or ()) == CSV_COLUMNS
    assert [row["candidate_id"] for row in rows] == [
        "lower-correlation-scene", "synthetic-scene"
    ]
    assert rows[0]["best_for_chip_window"] == "False"
    assert rows[1]["best_for_chip_window"] == "True"
    assert all(row["status"] == "ok" for row in rows)
