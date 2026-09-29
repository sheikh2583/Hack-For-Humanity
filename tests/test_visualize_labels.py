"""Tests for src.eval.visualize_labels."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.eval.visualize_labels import (
    CHIP_SIZE_PX,
    UPSCALE,
    _build_contact_sheet,
    _class_name,
    _collect_chips,
    _draw_boxes,
    _parse_label,
    visualize_labels,
)


@pytest.fixture
def synthetic_yolo_dataset(tmp_path: Path) -> Path:
    """Create a tiny converted YOLO-OBB dataset with 6 positive + 3 negative chips."""
    import numpy as np
    from PIL import Image

    ds = tmp_path / "yolo_obb"
    ds.mkdir()

    for split in ("train",):
        (ds / split / "images").mkdir(parents=True)
        (ds / split / "labels").mkdir(parents=True)

    # Create 64×64 images (small for speed) — we'll treat CHIP_SIZE_PX as 64
    chip = Image.fromarray(np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8))

    # FCBK chips (class 0)
    for i in range(4):
        img = chip.copy()
        img.save(ds / "train" / "images" / f"fcbk_{i}.png")
        (ds / "train" / "labels" / f"fcbk_{i}.txt").write_text(
            "0 0.1 0.1 0.3 0.1 0.3 0.3 0.1 0.3\n"
        )

    # Zigzag chips (class 1)
    for i in range(4):
        img = chip.copy()
        img.save(ds / "train" / "images" / f"zigzag_{i}.png")
        (ds / "train" / "labels" / f"zigzag_{i}.txt").write_text(
            "1 0.5 0.5 0.7 0.5 0.7 0.7 0.5 0.7\n"
        )

    # Negative chips (empty labels)
    for i in range(4):
        img = chip.copy()
        img.save(ds / "train" / "images" / f"neg_{i}.png")
        (ds / "train" / "labels" / f"neg_{i}.txt").write_text("")

    (ds / "train" / "labels" / "missing_label.txt").write_text("0 0.1 0.1 0.3 0.3 0.3 0.3 0.1 0.3\n")

    return ds


class TestParseLabel:
    def test_parses_valid(self) -> None:
        path = Path("/fake")
        # Write a temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8\n")
            f.write("1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9\n")
            path = Path(f.name)
        result = _parse_label(path)
        assert len(result) == 2
        assert result[0][0] == 0.0
        assert result[1][0] == 1.0
        assert len(result[0]) == 9
        path.unlink()

    def test_missing_file(self) -> None:
        assert _parse_label(Path("/nonexistent.txt")) == []

    def test_empty_file(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            path = Path(f.name)
        assert _parse_label(path) == []
        path.unlink()


class TestDrawBoxes:
    def test_preserves_size(self) -> None:
        import numpy as np
        from PIL import Image

        img = Image.fromarray(np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8))
        boxes = [[0, 0.1, 0.1, 0.3, 0.1, 0.3, 0.3, 0.1, 0.3]]
        result = _draw_boxes(img, boxes, chip_size=64, upscale=4)
        assert result.size == (256, 256)

    def test_multiple_classes(self) -> None:
        import numpy as np
        from PIL import Image

        img = Image.fromarray(np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8))
        boxes = [
            [0, 0.1, 0.1, 0.3, 0.1, 0.3, 0.3, 0.1, 0.3],  # FCBK
            [1, 0.5, 0.5, 0.7, 0.5, 0.7, 0.7, 0.5, 0.7],  # Zigzag
        ]
        result = _draw_boxes(img, boxes, chip_size=64, upscale=4)
        assert result.size == (256, 256)


class TestBuildContactSheet:
    def test_grid_size(self) -> None:
        import numpy as np
        from PIL import Image

        imgs = [
            Image.fromarray(np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8))
            for _ in range(16)
        ]
        sheet = _build_contact_sheet(imgs, cols=4, chip_size=64, upscale=4)
        assert sheet.size == (1024, 1024)


class TestClassName:
    def test_fcbk(self) -> None:
        assert _class_name(0) == "FCBK"

    def test_zigzag(self) -> None:
        assert _class_name(1) == "Zigzag"


class TestVisualizeLabels:
    def test_creates_contact_sheet(self, synthetic_yolo_dataset: Path, tmp_path: Path) -> None:
        """verify the full pipeline produces a valid PNG."""
        output = tmp_path / "label_check.png"
        result = visualize_labels(
            dataset_dir=synthetic_yolo_dataset,
            output_path=output,
            n_positive=12,
            n_negative=4,
        )
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_png_is_valid(self, synthetic_yolo_dataset: Path, tmp_path: Path) -> None:
        """The output must be a valid PNG image."""
        from PIL import Image

        output = tmp_path / "label_check.png"
        visualize_labels(
            dataset_dir=synthetic_yolo_dataset,
            output_path=output,
            n_positive=8,
            n_negative=4,
        )
        img = Image.open(output)
        img.verify()  # raises if invalid

    def test_contact_sheet_dimensions(self, synthetic_yolo_dataset: Path, tmp_path: Path) -> None:
        """Sheet dimensions = ceil(n_chips / cols) × cols × (chip_size × upscale)."""
        from PIL import Image

        output = tmp_path / "label_check.png"
        # Fixture has 8 positive + 4 negative = 12 chips; request more than exist
        # so the test is data-driven rather than hard-coded to 16.
        n_positive, n_negative = 12, 4
        visualize_labels(
            dataset_dir=synthetic_yolo_dataset,
            output_path=output,
            n_positive=n_positive,
            n_negative=n_negative,
        )
        img = Image.open(output)

        # Count how many chips the fixture actually has
        positive, negative = _collect_chips(synthetic_yolo_dataset)
        n_chips = min(n_positive, len(positive)) + min(n_negative, len(negative))
        cols, chip_size, upscale = 4, CHIP_SIZE_PX, UPSCALE
        rows = (n_chips + cols - 1) // cols
        assert img.size == (cols * chip_size * upscale, rows * chip_size * upscale)
