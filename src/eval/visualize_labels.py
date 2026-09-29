"""Visualize converted YOLO-OBB labels by drawing oriented boxes on image chips.

Reads a converted YOLO-OBB dataset directory (as produced by
``src.data.convert_sentinelkilndb``), samples chips with kilns (mix of
FCBK and Zigzag) and negative chips, draws oriented bounding boxes and
class names on 4×-upscaled images, and saves a contact-sheet PNG.

Input
-----
- ``dataset_dir``: Converted YOLO-OBB directory tree::

      dataset_dir/
        train/{images,labels}/
        val/{images,labels}/
        test/{images,labels}/

      Each label file is YOLO-OBB: ``<class_id> <x1> <y1> <x2> <y2>
      <x3> <y3> <x4> <y4>`` (normalised [0,1] coordinates).
      Output classes: 0 = FCBK, 1 = Zigzag.

Output
------
- ``output_path``: A single PNG contact sheet (``data/processed/label_check.png``
  by default) containing a 4×4 grid of sampled chips.

Contract
--------
>>> from src.eval.visualize_labels import visualize_labels
>>> visualize_labels(dataset_dir=Path("data/interim/yolo_obb"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.data.convert_sentinelkilndb import SPLITS

CHIP_SIZE_PX: int = 128
UPSCALE: int = 4
N_POSITIVE: int = 12
N_NEGATIVE: int = 4
DEFAULT_OUTPUT: Path = Path("data/processed/label_check.png")

#: Colour per output class (FCBK=0 → red, Zigzag=1 → blue).
CLASS_COLORS: dict[int, tuple[int, int, int]] = {
    0: (220, 30, 30),
    1: (30, 80, 220),
}


def _parse_label(path: Path) -> list[list[float]]:
    """Parse a YOLO-OBB label file into a list of box rows.

    Parameters
    ----------
    path : Path
        Path to a ``.txt`` label file.

    Returns
    -------
    list[list[float]]
        Each element is ``[class_id, x1, y1, x2, y2, x3, y3, x4, y4]``
        with coordinates normalised to [0, 1].  Returns ``[]`` for
        a missing or empty file (negative chip).
    """
    if not path.exists():
        return []
    text = path.read_text().strip()
    if not text:
        return []
    rows: list[list[float]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 9:
            rows.append([float(p) for p in parts[:9]])
    return rows


def _collect_chips(dataset_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Scan all splits and collect positive and negative chip metadata.

    Parameters
    ----------
    dataset_dir : Path
        Root of the converted YOLO-OBB dataset (contains ``train/``,
        ``val/``, ``test/`` sub-directories).

    Returns
    -------
    positive_chips : list[dict]
        Each dict has ``image``, ``label``, ``split``, ``class_ids``
        (set of output class IDs present in the label).
    negative_chips : list[dict]
        Each dict has ``image``, ``label``, ``split``.
    """
    positive_chips: list[dict[str, Any]] = []
    negative_chips: list[dict[str, Any]] = []

    for split in SPLITS:
        img_dir = dataset_dir / split / "images"
        lbl_dir = dataset_dir / split / "labels"
        if not img_dir.is_dir():
            continue
        for img_path in sorted(img_dir.glob("*.png")):
            label_path = lbl_dir / (img_path.stem + ".txt")
            boxes = _parse_label(label_path)
            chip: dict[str, Any] = {
                "image": img_path,
                "label": label_path,
                "split": split,
            }
            if boxes:
                chip["class_ids"] = {int(b[0]) for b in boxes}
                positive_chips.append(chip)
            else:
                negative_chips.append(chip)

    return positive_chips, negative_chips


def _draw_boxes(
    img: Any,
    boxes: list[list[float]],
    chip_size: int = CHIP_SIZE_PX,
    upscale: int = UPSCALE,
) -> Any:
    """Draw oriented OBB boxes and class names on an upscaled image.

    Parameters
    ----------
    img : PIL.Image.Image
        Original chip image (128×128).
    boxes : list[list[float]]
        Parsed label rows ``[class_id, x1, y1, ..., x4, y4]``.
    chip_size : int
        Original chip dimension in pixels (default 128).
    upscale : int
        Integer upscale factor (default 4).

    Returns
    -------
    PIL.Image.Image
        Upscaled image (512×512) with boxes drawn on it.
    """
    from PIL import Image, ImageDraw, ImageFont

    upscaled = img.resize(
        (chip_size * upscale, chip_size * upscale),
        Image.NEAREST,
    )
    draw = ImageDraw.Draw(upscaled)
    try:
        font = ImageFont.truetype("arial", 14)
    except OSError:
        font = ImageFont.load_default()

    ux = chip_size * upscale

    for box in boxes:
        cls = int(box[0])
        color = CLASS_COLORS.get(cls, (255, 255, 255))
        coords = box[1:9]  # x1 y1 x2 y2 x3 y3 x4 y4
        polygon = [(coords[i] * ux, coords[i + 1] * ux) for i in range(0, 8, 2)]
        draw.polygon(polygon, outline=color, width=2)
        # Draw class name near the first vertex
        cx, cy = polygon[0]
        label_text = _class_name(cls)
        draw.text((cx + 4, cy - 16), label_text, fill=(255, 255, 255), font=font)
        # Black outline for readability
        draw.text((cx + 3, cy - 17), label_text, fill=(0, 0, 0), font=font)

    return upscaled


def _class_name(cls_id: int) -> str:
    """Return the display name for an output class ID."""
    from src.data.convert_sentinelkilndb import OUTPUT_CLASSES
    return OUTPUT_CLASSES.get(cls_id, f"class_{cls_id}")


def _build_contact_sheet(
    images: list[Any],
    cols: int = 4,
    chip_size: int = CHIP_SIZE_PX,
    upscale: int = UPSCALE,
) -> Any:
    """Arrange a list of PIL images into a contact sheet grid.

    Parameters
    ----------
    images : list[PIL.Image.Image]
        List of upscaled images (each ``chip_size * upscale`` per side).
    cols : int
        Number of columns in the grid (default 4).
    chip_size : int
        Original chip dimension (default 128).
    upscale : int
        Upscale factor (default 4).

    Returns
    -------
    PIL.Image.Image
        The contact sheet image.
    """
    from PIL import Image

    cell = chip_size * upscale
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (40, 40, 40))

    for i, img in enumerate(images):
        col = i % cols
        row = i // cols
        x = col * cell
        y = row * cell
        sheet.paste(img, (x, y))

    return sheet


def visualize_labels(
    dataset_dir: Path = Path("data/interim/yolo_obb"),
    output_path: Path = DEFAULT_OUTPUT,
    n_positive: int = N_POSITIVE,
    n_negative: int = N_NEGATIVE,
    seed: int = 42,
) -> Path:
    """Sample chips, draw OBB labels on 4×-upscaled images, save contact sheet.

    Parameters
    ----------
    dataset_dir : Path
        Root of the converted YOLO-OBB dataset.
    output_path : Path
        Where to write the contact-sheet PNG.
    n_positive : int
        Number of chips **with kilns** to sample (default 12).
    n_negative : int
        Number of negative chips (no kilns) to sample (default 4).
    seed : int
        Random seed for reproducible sampling.

    Returns
    -------
    Path
        The path to the saved contact-sheet PNG.
    """
    import random

    from PIL import Image
    from rich import print as rprint

    from src.data.convert_sentinelkilndb import OUTPUT_CLASSES

    positive_chips, negative_chips = _collect_chips(dataset_dir)

    rprint(
        f"[cyan]Found {len(positive_chips)} positive and "
        f"{len(negative_chips)} negative chips across splits.[/cyan]"
    )

    # Split positives by class for a balanced mix
    fcbk_chips = [c for c in positive_chips if 0 in c.get("class_ids", set())]
    zigzag_chips = [c for c in positive_chips if 1 in c.get("class_ids", set())]

    rng = random.Random(seed)
    rng.shuffle(fcbk_chips)
    rng.shuffle(zigzag_chips)

    # Sample 6 FCBK + 6 Zigzag (adjust if insufficient)
    half = n_positive // 2
    sampled_positive: list[dict[str, Any]] = []
    sampled_positive += fcbk_chips[: min(half, len(fcbk_chips))]
    sampled_positive += zigzag_chips[: n_positive - len(sampled_positive)]
    if len(sampled_positive) < n_positive:
        remaining = positive_chips.copy()
        rng.shuffle(remaining)
        for c in remaining:
            if c not in sampled_positive:
                sampled_positive.append(c)
                if len(sampled_positive) >= n_positive:
                    break

    rng.shuffle(negative_chips)
    sampled_negative = negative_chips[:n_negative]

    sampled: list[dict[str, Any]] = []
    for chip in sampled_positive:
        sampled.append({**chip, "is_negative": False})
    for chip in sampled_negative:
        sampled.append({**chip, "is_negative": True})

    rprint(f"[cyan]Sampling {len(sampled_positive)} positive + {len(sampled_negative)} negative chips.[/cyan]")

    # Draw boxes and upscale
    drawn: list[Image.Image] = []
    for chip in sampled:
        img = Image.open(chip["image"])
        if chip["is_negative"]:
            drawn.append(img.resize(
                (CHIP_SIZE_PX * UPSCALE, CHIP_SIZE_PX * UPSCALE),
                Image.NEAREST,
            ))
        else:
            boxes = _parse_label(chip["label"])
            drawn.append(_draw_boxes(img, boxes))

    # Build contact sheet
    sheet = _build_contact_sheet(drawn, cols=4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    rprint(f"[green]Contact sheet saved to {output_path} ({len(drawn)} chips)[/green]")
    rprint(f"  Classes: {OUTPUT_CLASSES}")

    return output_path


if __name__ == "__main__":
    visualize_labels()
