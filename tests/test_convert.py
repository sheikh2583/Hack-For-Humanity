"""Tests for src.data.convert_sentinelkilndb.

Uses tiny synthetic Parquet files — no real dataset needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data.convert_sentinelkilndb import (
    COL_IMAGE,
    COL_IMAGE_NAME,
    COL_OBB,
    ORIGINAL_CLASSES,
    SPLITS,
    assign_splits,
    convert_dataset,
    grid_cell,
    parse_latlon,
    remap_label_line,
)

# ---------------------------------------------------------------------------
# Helpers: create minimal synthetic Parquet fixtures
# ---------------------------------------------------------------------------

_PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x00\x02\x00\x01\xe2\x1f\xbc\x33"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_row(name: str, obb: list[str]) -> dict:
    """Build a single row dict matching the SentinelKilnDB Parquet schema."""
    return {
        COL_IMAGE_NAME: name,
        COL_IMAGE: _PNG_1x1,
        "dota_label": [f"0 0 10 0 10 10 0 10 {ORIGINAL_CLASSES[int(l.split()[0])]} 0" for l in obb],
        "yolo_aa_label": [f"{l.split()[0]} 0.5 0.5 0.1 0.1" for l in obb],
        COL_OBB: list(obb),
    }


def _write_parquet(path: Path, rows: list[dict]) -> None:
    """Write synthetic rows into a Parquet file with the expected schema."""
    schema = pa.schema([
        ("image_name", pa.string()),
        ("image", pa.binary()),
        ("dota_label", pa.list_(pa.string())),
        ("yolo_aa_label", pa.list_(pa.string())),
        ("yolo_obb_label", pa.list_(pa.string())),
    ])
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, row_group_size=len(rows))


def _write_boundary(path: Path, lon_min: float, lon_max: float, lat_min: float, lat_max: float) -> None:
    """Write a synthetic rectangular GeoJSON boundary."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon_min, lat_min],
                        [lon_max, lat_min],
                        [lon_max, lat_max],
                        [lon_min, lat_max],
                        [lon_min, lat_min],
                    ]],
                },
                "properties": {"name": "synthetic"},
            }
        ],
    }
    path.write_text(json.dumps(geojson))


@pytest.fixture
def synthetic_dataset(tmp_path: Path) -> tuple[Path, Path]:
    """Create a tiny three-split Parquet dataset with a synthetic boundary.

    Returns ``(dataset_dir, boundary_path)``.
    """
    ds_dir = tmp_path / "synthetic"
    ds_dir.mkdir()

    # Chips inside Bangladesh (24.0–24.5 lat, 88.0–88.5 lon)
    # Note: val chip 24.15_88.15 shares a grid cell with train chip 24.1_88.1
    # (both → cell (96, 352)), demonstrating shipped-split leakage.
    # Chips outside Bangladesh (outside the boundary)
    rows = {
        "train": [
            _make_row("24.1_88.1.png", ["1 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),      # FCBK, inside
            _make_row("24.2_88.2.png", ["0 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),      # rare source class→FCBK, inside
            _make_row("24.3_88.3.png", ["2 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),      # Zigzag, inside
            _make_row("24.4_88.4.png", []),                                          # negative, inside
        ],
        "val": [
            _make_row("24.15_88.15.png", ["1 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),    # same cell as train, leakage
            _make_row("24.45_88.45.png", ["2 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),     # Zigzag, inside
        ],
        "test": [
            _make_row("24.25_88.25.png", ["0 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),    # rare source class→FCBK, inside
            # Outside Bangladesh:
            _make_row("10.0_10.0.png", ["1 0.5 0.5 0.6 0.5 0.6 0.6 0.5 0.6"]),       # outside, filtered
        ],
    }

    for split in SPLITS:
        split_dir = ds_dir / split
        split_dir.mkdir()
        _write_parquet(split_dir / f"{split}.parquet", rows[split])

    boundary = tmp_path / "boundary.geojson"
    _write_boundary(boundary, 88.0, 88.5, 24.0, 24.5)

    return ds_dir, boundary


# ---------------------------------------------------------------------------
# Unit tests for pure functions
# ---------------------------------------------------------------------------

class TestParseLatLon:
    """Tests for filename → (lat, lon) parsing."""

    def test_basic(self) -> None:
        lat, lon = parse_latlon("24.123_88.456.png")
        assert abs(lat - 24.123) < 1e-6
        assert abs(lon - 88.456) < 1e-6

    def test_negative_coords(self) -> None:
        lat, lon = parse_latlon("-24.123_-88.456.png")
        assert abs(lat - (-24.123)) < 1e-6
        assert abs(lon - (-88.456)) < 1e-6

    def test_full_path(self) -> None:
        lat, lon = parse_latlon("/some/dir/24.1_88.2.png")
        assert abs(lat - 24.1) < 1e-6
        assert abs(lon - 88.2) < 1e-6

    def test_invalid_filename(self) -> None:
        assert parse_latlon("no_coords_here.png") is None

    def test_comma_format_rejected(self) -> None:
        """Comma-delimited names (old README format) must NOT match."""
        assert parse_latlon("24.123,88.456.png") is None


class TestGridCell:
    """Tests for spatial grid cell assignment."""

    def test_basic(self) -> None:
        assert grid_cell(24.1, 88.3, 0.25) == (96, 353)

    def test_boundary(self) -> None:
        assert grid_cell(24.0, 88.0, 0.25) == (96, 352)

    def test_same_cell_nearby(self) -> None:
        """Two nearby points should land in the same cell."""
        assert grid_cell(24.10, 88.20, 0.25) == grid_cell(24.11, 88.21, 0.25)


class TestAssignSplits:
    """Tests for spatial block split assignment."""

    def test_all_cells_assigned(self) -> None:
        cells = [(i, j) for i in range(10) for j in range(10)]
        mapping = assign_splits(cells, ratios=(0.7, 0.15, 0.15), seed=42)
        assert set(mapping.keys()) == set(cells)
        assert set(mapping.values()) <= {"train", "val", "test"}

    def test_deterministic(self) -> None:
        """Same seed → same assignment."""
        cells = [(0, 0), (0, 1), (0, 2), (0, 3)]
        a = assign_splits(cells, seed=42)
        b = assign_splits(cells, seed=42)
        assert a == b

    def test_seed_changes_assignment(self) -> None:
        cells = [(i, j) for i in range(20) for j in range(20)]
        a = assign_splits(cells, seed=42)
        b = assign_splits(cells, seed=99)
        assert a != b

    def test_approximate_ratios(self) -> None:
        cells = [(i, j) for i in range(20) for j in range(20)]
        mapping = assign_splits(cells, ratios=(0.7, 0.15, 0.15), seed=42)
        counts = {"train": 0, "val": 0, "test": 0}
        for v in mapping.values():
            counts[v] += 1
        total = sum(counts.values())
        assert abs(counts["train"] / total - 0.7) < 0.05


class TestRemapLabelLine:
    """Tests for class ID remapping (rare source class→FCBK, FCBK→FCBK, Zigzag→Zigzag)."""

    def test_rare_source_class_to_fcbk(self) -> None:
        """Class 0 (rare source class) → output class 0 (FCBK)."""
        result = remap_label_line("0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8")
        assert result.startswith("0 ")

    def test_fcbk_stays_fcbk(self) -> None:
        """Class 1 (FCBK) → output class 0 (FCBK)."""
        result = remap_label_line("1 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8")
        assert result.startswith("0 ")

    def test_zigzag_stays_zigzag(self) -> None:
        """Class 2 (Zigzag) → output class 1 (Zigzag)."""
        result = remap_label_line("2 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8")
        assert result.startswith("1 ")

    def test_coords_preserved(self) -> None:
        """Coordinate values must be unchanged after remapping."""
        original = "1 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8"
        result = remap_label_line(original)
        parts = result.split()
        assert parts[1:] == ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8"]


class TestNoSplitLeakage:
    """Assert that chips in the same grid cell end up in the same split."""

    def test_nearby_chips_same_split(self) -> None:
        lat_a, lon_a = 24.100, 88.200
        lat_b, lon_b = 24.101, 88.201  # ~140 m apart, same cell

        cell_a = grid_cell(lat_a, lon_a, 0.25)
        cell_b = grid_cell(lat_b, lon_b, 0.25)

        assert cell_a == cell_b, "Nearby chips should fall in the same grid cell"

        mapping = assign_splits([cell_a, cell_b], seed=42)
        assert mapping[cell_a] == mapping[cell_b]


# ---------------------------------------------------------------------------
# Integration test: full convert_dataset with synthetic Parquet
# ---------------------------------------------------------------------------

class TestConvertDataset:
    """End-to-end test of convert_dataset on synthetic Parquet fixtures."""

    def test_filters_outside_bangladesh(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """Chips outside the boundary polygon must not be written."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output"

        convert_dataset(ds_dir, boundary, output, batch_size=1)

        # The chip at 10.0_10.0.png is outside the boundary; it should be excluded.
        # Total inside chips: 4 (train) + 2 (val) + 1 (test) = 7
        img_files = list((output / "train" / "images").glob("*.png")) + \
            list((output / "val" / "images").glob("*.png")) + \
            list((output / "test" / "images").glob("*.png"))
        assert len(img_files) == 7, f"Expected 7 Bangladesh chips, got {len(img_files)}"

    def test_rare_source_class_merged_into_fcbk(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """rare source class (class 0) and FCBK (class 1) both produce output class 0 (FCBK)."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output2"

        counts = convert_dataset(ds_dir, boundary, output)

        assert set(counts["train"].keys()) == {"FCBK", "Zigzag"}
        assert set(counts["val"].keys()) == {"FCBK", "Zigzag"}
        assert set(counts["test"].keys()) == {"FCBK", "Zigzag"}

    def test_writes_dataset_yaml(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """dataset.yaml must exist with correct class names."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output3"

        convert_dataset(ds_dir, boundary, output)

        yaml_path = output / "dataset.yaml"
        assert yaml_path.is_file()
        text = yaml_path.read_text()
        assert "FCBK" in text
        assert "Zigzag" in text
        assert "train/images" in text
        assert "val/images" in text
        assert "test/images" in text

    def test_writes_split_report(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """split_report.json must contain leakage analysis and counts."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output4"

        counts = convert_dataset(ds_dir, boundary, output)

        report_path = output / "split_report.json"
        assert report_path.is_file()
        report = json.loads(report_path.read_text())
        assert report["merge_rare_source_class_into_fcbk"] is True
        assert report["output_classes"] == {"0": "FCBK", "1": "Zigzag"}
        assert report["chips_inside_bangladesh"] == 7
        assert report["shipped_split_leakage"]["contaminated_cells"] >= 1
        assert report["counts_per_split_per_class"] == counts
        assert report["leakage_filter_threshold_m"] == 1300.0
        assert "Chebyshev" in report["leakage_filter_metric"]
        per_split = report["leakage_filter_dropped_per_split"]
        assert per_split["train"] == 0
        assert per_split["val"] + per_split["test"] == report["leakage_filter_dropped_val_test"]

    def test_label_remap_in_output(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """Output .txt files must contain remapped class IDs."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output5"

        convert_dataset(ds_dir, boundary, output)

        # Find a label file and verify class IDs are 0 or 1 only
        for split in SPLITS:
            label_dir = output / split / "labels"
            if label_dir.exists():
                for txt in label_dir.glob("*.txt"):
                    content = txt.read_text().strip()
                    if content:
                        for line in content.splitlines():
                            cls = int(line.split()[0])
                            assert cls in (0, 1), f"Unexpected class ID {cls}"

    def test_empty_label_for_negative(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """Negative chips must produce empty .txt label files."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output6"

        convert_dataset(ds_dir, boundary, output)

        # The negative chip is 24.4_88.4.png — find which split it landed in
        label_path = None
        for split in SPLITS:
            candidate = output / split / "labels" / "24.4_88.4.txt"
            if candidate.exists():
                label_path = candidate
                break
        assert label_path is not None, "Negative chip label file not found"
        assert label_path.read_text().strip() == ""

    def test_png_bytes_copied_verbatim(self, synthetic_dataset: tuple[Path, Path]) -> None:
        """Output PNG bytes must match the synthetic 1×1 PNG."""
        ds_dir, boundary = synthetic_dataset
        output = ds_dir.parent / "output7"

        convert_dataset(ds_dir, boundary, output)

        for split in SPLITS:
            img = output / split / "images" / "24.1_88.1.png"
            if img.exists():
                assert img.read_bytes() == _PNG_1x1
