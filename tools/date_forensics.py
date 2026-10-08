"""Compare training chips with candidate Sentinel-2 dates and composites.

Input schema: RGB PNG files named ``latitude_longitude.png`` and one or more
ISO date windows. Output schema: CSV rows for each chip/window/scene or median
composite, including clear-pixel counts, best one-pixel-shift metrics, and the
best-scoring candidate marker. This is a diagnostic, not date verification.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import re
import urllib.request
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

from src.data.normalize import minmax_uint8

CHIP_COORDINATES = re.compile(r"^(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)$")
CSV_COLUMNS = (
    "chip_filename",
    "latitude",
    "longitude",
    "window_start_inclusive",
    "window_end_exclusive",
    "candidate_kind",
    "candidate_id",
    "scene_date_utc",
    "cloudy_pixel_percentage",
    "scenes_in_window",
    "scenes_in_median",
    "valid_pixel_count",
    "valid_pixel_fraction",
    "offset_dx",
    "offset_dy",
    "pearson_r",
    "pearson_g",
    "pearson_b",
    "mean_pearson",
    "histogram_distance_r",
    "histogram_distance_g",
    "histogram_distance_b",
    "mean_histogram_distance",
    "best_for_chip_window",
    "status",
)


@dataclass(frozen=True)
class DateWindow:
    """An ISO calendar date range with an inclusive start and exclusive end."""

    start: date
    end: date

    @property
    def start_text(self) -> str:
        return self.start.isoformat()

    @property
    def end_text(self) -> str:
        return self.end.isoformat()


@dataclass(frozen=True)
class Chip:
    """A training chip and its filename-derived WGS84 coordinate pair."""

    path: Path
    latitude: float
    longitude: float
    rgb: np.ndarray


@dataclass(frozen=True)
class CandidateImage:
    """One scene or composite's raw RGB patch and clear-pixel mask."""

    kind: str
    candidate_id: str
    scene_date_utc: str | None
    cloudy_pixel_percentage: float | None
    scenes_in_window: int
    scenes_in_median: int
    raw_rgb: np.ndarray
    valid_mask: np.ndarray


@dataclass(frozen=True)
class Comparison:
    """Best spatial alignment metrics for one imagery candidate."""

    offset_dx: int
    offset_dy: int
    pearson: tuple[float | None, float | None, float | None]
    mean_pearson: float | None
    histogram_distance: tuple[float | None, float | None, float | None]
    mean_histogram_distance: float | None
    valid_pixel_count: int


CandidateFetcher = Callable[[Chip, DateWindow], Sequence[CandidateImage]]


def parse_chip_coordinates(filename: str) -> tuple[float, float]:
    """Parse filename coordinates; return ``(latitude, longitude)`` in WGS84."""
    match = CHIP_COORDINATES.fullmatch(Path(filename).stem)
    if match is None:
        raise ValueError(f"Expected chip filename latitude_longitude.png: {filename}")
    latitude, longitude = map(float, match.groups())
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError(f"Chip coordinates out of WGS84 range: {filename}")
    return latitude, longitude


def parse_date_window(value: str) -> DateWindow:
    """Parse ``START/END`` as ISO dates, where END is exclusive."""
    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError("Date window must have the form YYYY-MM-DD/YYYY-MM-DD")
    try:
        start, end = (date.fromisoformat(part) for part in parts)
    except ValueError as error:
        raise ValueError(f"Invalid ISO date window: {value}") from error
    if end <= start:
        raise ValueError("Window end is exclusive and must be later than its start")
    return DateWindow(start=start, end=end)


def date_is_in_window(scene_date: str, window: DateWindow) -> bool:
    """Return whether an ISO scene date is inside ``[start, end)``."""
    value = date.fromisoformat(scene_date[:10])
    return window.start <= value < window.end


def load_chips(training_dir: Path, *, size_px: int, max_samples: int | None,
               seed: int) -> list[Chip]:
    """Load named PNG chips; optional random sampling is repeatable by seed."""
    paths = sorted(training_dir.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"No PNG chips found in {training_dir}")
    chips: list[Chip] = []
    for path in paths:
        latitude, longitude = parse_chip_coordinates(path.name)
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        if rgb.shape != (size_px, size_px, 3):
            raise ValueError(
                f"Expected {size_px}x{size_px} RGB chip in {path}, got {rgb.shape}"
            )
        chips.append(Chip(path, latitude, longitude, rgb))
    if max_samples is not None:
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        if len(chips) > max_samples:
            random.Random(seed).shuffle(chips)
            chips = sorted(chips[:max_samples], key=lambda chip: chip.path.name)
    return chips


def _pearson(first: np.ndarray, second: np.ndarray) -> float | None:
    """Return Pearson r, or ``None`` when either channel has no variance."""
    a, b = first.astype(np.float64), second.astype(np.float64)
    if a.size < 2 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _histogram_distance(first: np.ndarray, second: np.ndarray, bins: int = 32) -> float:
    """Return total-variation distance between 8-bit channel histograms [0, 1]."""
    hist_a = np.histogram(first, bins=bins, range=(0, 256))[0].astype(np.float64)
    hist_b = np.histogram(second, bins=bins, range=(0, 256))[0].astype(np.float64)
    hist_a /= max(float(hist_a.sum()), 1.0)
    hist_b /= max(float(hist_b.sum()), 1.0)
    return float(0.5 * np.abs(hist_a - hist_b).sum())


def compare_patch(
    training_rgb: np.ndarray,
    raw_candidate_rgb: np.ndarray,
    valid_mask: np.ndarray,
    *,
    max_offset: int = 1,
) -> Comparison:
    """Normalize valid candidate pixels and find the best offset up to one pixel.

    Inputs are an RGB uint8 training patch, raw RGB reflectance values, and a
    Boolean clear-pixel mask. Output metrics compare only overlapping clear pixels.
    """
    if training_rgb.shape != raw_candidate_rgb.shape or training_rgb.ndim != 3:
        raise ValueError("Training and candidate RGB arrays must have the same HxWx3 shape")
    if training_rgb.shape[2] != 3 or valid_mask.shape != training_rgb.shape[:2]:
        raise ValueError("Expected three RGB channels and an HxW valid-pixel mask")
    if max_offset < 0 or max_offset > 1:
        raise ValueError("The diagnostic permits offsets from zero to one pixel")

    valid_mask = np.asarray(valid_mask, dtype=bool)
    valid_indices = np.flatnonzero(valid_mask)
    normalized = np.zeros(training_rgb.shape, dtype=np.uint8)
    if valid_indices.size:
        valid_values = np.asarray(raw_candidate_rgb, dtype=np.float64).reshape(-1, 3)[valid_indices]
        normalized_values = minmax_uint8(valid_values[np.newaxis, :, :])[0]
        normalized.reshape(-1, 3)[valid_indices] = normalized_values

    height, width, _ = training_rgb.shape
    options: list[tuple[tuple[float, float, int, int, int], Comparison]] = []
    for dy in range(-max_offset, max_offset + 1):
        for dx in range(-max_offset, max_offset + 1):
            if dy >= 0:
                train_y, candidate_y = slice(0, height - dy), slice(dy, height)
            else:
                train_y, candidate_y = slice(-dy, height), slice(0, height + dy)
            if dx >= 0:
                train_x, candidate_x = slice(0, width - dx), slice(dx, width)
            else:
                train_x, candidate_x = slice(-dx, width), slice(0, width + dx)

            reference = training_rgb[train_y, train_x]
            candidate = normalized[candidate_y, candidate_x]
            mask = valid_mask[candidate_y, candidate_x]
            reference_values = reference[mask]
            candidate_values = candidate[mask]
            count = int(mask.sum())
            pearson = tuple(
                _pearson(reference_values[:, channel], candidate_values[:, channel])
                for channel in range(3)
            )
            hist = tuple(
                _histogram_distance(reference_values[:, channel], candidate_values[:, channel])
                if count else None
                for channel in range(3)
            )
            valid_corr = [value for value in pearson if value is not None and np.isfinite(value)]
            valid_hist = [value for value in hist if value is not None]
            mean_corr = float(np.mean(valid_corr)) if valid_corr else None
            mean_hist = float(np.mean(valid_hist)) if valid_hist else None
            comparison = Comparison(dx, dy, pearson, mean_corr, hist, mean_hist, count)
            rank = (
                -(mean_corr if mean_corr is not None else -1.0),
                mean_hist if mean_hist is not None else float("inf"),
                abs(dx) + abs(dy),
                dy,
                dx,
            )
            options.append((rank, comparison))
    return min(options, key=lambda item: item[0])[1]


def _get_info(value: Any) -> Any:
    """Resolve a small EE metadata value at the explicit service boundary."""
    return value.getInfo()


def _utm_crs(longitude: float) -> str:
    """Choose the documented Bangladesh UTM zone for local patch sampling."""
    return "EPSG:32645" if longitude < 90 else "EPSG:32646"


def _decode_geotiff(payload: bytes, *, size_px: int) -> tuple[np.ndarray, np.ndarray]:
    """Decode the 4-band EE TIFF (RGB reflectance plus valid-pixel indicator)."""
    from rasterio.io import MemoryFile

    tiff_bytes = payload
    if payload[:4] != b"II*\x00" and payload[:4] != b"MM\x00*":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith((".tif", ".tiff"))]
            if not names:
                raise ValueError("Earth Engine download ZIP contained no GeoTIFF")
            tiff_bytes = archive.read(names[0])
    with MemoryFile(tiff_bytes) as memory, memory.open() as dataset:
        if dataset.count < 4 or dataset.width != size_px or dataset.height != size_px:
            raise ValueError("Earth Engine patch response has unexpected band count or dimensions")
        bands = dataset.read((1, 2, 3), masked=False).astype(np.float64)
        valid = dataset.read(4, masked=False) > 0
    return np.moveaxis(bands, 0, -1), valid


def _download_ee_patch(image: Any, region: Any, *, size_px: int, crs: str) -> tuple[np.ndarray, np.ndarray]:
    """Download one projected chip-sized patch through the Earth Engine boundary."""
    url = image.getDownloadURL({
        "bands": ["B4", "B3", "B2", "valid"],
        "region": region,
        "crs": crs,
        "dimensions": [size_px, size_px],
        "format": "GEO_TIFF",
        "filePerBand": False,
    })
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read()
    return _decode_geotiff(payload, size_px=size_px)


def fetch_ee_candidates(
    chip: Chip,
    window: DateWindow,
    *,
    config: dict[str, Any],
    ee_module: Any | None = None,
) -> list[CandidateImage]:
    """Query and download clear S2 scene/composite candidates for one chip.

    All Earth Engine object creation, metadata access, URL generation, and image
    downloads live here so callers/tests can replace this boundary with a fixture.
    ``filterDate(start, end)`` uses the start-included/end-excluded contract.
    """
    if ee_module is None:
        import ee as ee_module  # type: ignore[import-untyped,no-redef]

    patches = config["patches"]
    size_px, scale_m = int(patches["size_px"]), float(config["output"]["scale_m"])
    half_width = size_px * scale_m / 2
    crs = _utm_crs(chip.longitude)
    point = ee_module.Geometry.Point([chip.longitude, chip.latitude], proj="EPSG:4326")
    projected_center = point.transform(crs, maxError=1)
    region = projected_center.buffer(half_width, maxError=1, proj=crs).bounds(
        maxError=1, proj=crs
    )
    collection = (
        ee_module.ImageCollection(str(config["collection"]))
        .filterBounds(region)
        .filterDate(window.start_text, window.end_text)
        .sort("system:time_start")
    )
    scene_count = int(_get_info(collection.size()))
    if scene_count == 0:
        return []

    rgb_bands = list(config["rgb_bands"])
    qa = config["cloud_mask"]
    qa_band, qa_bit = str(qa["band"]), int(qa["qa60_bit"])
    cloud = config["cloud_filter"]
    low_cloud_collection = collection.filter(
        ee_module.Filter.lt(
            str(cloud["property"]), float(cloud["property_less_than"])
        )
    )
    median_count = int(_get_info(low_cloud_collection.size()))

    def clear_mask(image: Any) -> Any:
        clear = image.select(qa_band).bitwiseAnd(1 << qa_bit).eq(0)
        for band in rgb_bands:
            clear = clear.And(image.select(band).mask())
        return clear

    candidates: list[CandidateImage] = []
    images = collection.toList(scene_count)
    for index in range(scene_count):
        scene = ee_module.Image(images.get(index))
        scene_id_value = scene.get("system:id")
        scene_id_info = _get_info(scene_id_value) if scene_id_value is not None else None
        scene_id = str(scene_id_info) if scene_id_info else f"scene-{index}"
        scene_date = str(_get_info(
            ee_module.Date(scene.get("system:time_start")).format("YYYY-MM-dd")
        ))
        try:
            cloud_value = scene.get(str(config["cloud_filter"]["property"]))
            cloud_cover = None if cloud_value is None else float(_get_info(cloud_value))
        except (TypeError, ValueError):
            cloud_cover = None
        valid = clear_mask(scene)
        rgb = scene.select(rgb_bands).updateMask(valid).unmask(-9999)
        download_image = rgb.addBands(valid.unmask(0).rename("valid"))
        raw_rgb, valid_pixels = _download_ee_patch(download_image, region, size_px=size_px, crs=crs)
        candidates.append(CandidateImage(
            "scene", scene_id, scene_date, cloud_cover, scene_count, median_count,
            raw_rgb, valid_pixels
        ))

    if median_count:
        clear_collection = low_cloud_collection.map(
            lambda image: image.select(rgb_bands).updateMask(clear_mask(image))
        )
        median = clear_collection.median()
        valid = median.select(rgb_bands).mask().reduce(ee_module.Reducer.min()).gt(0)
        download_image = median.select(rgb_bands).unmask(-9999).addBands(
            valid.unmask(0).rename("valid")
        )
        raw_rgb, valid_pixels = _download_ee_patch(
            download_image, region, size_px=size_px, crs=crs
        )
        candidates.append(CandidateImage(
            "median_composite",
            f"median:{window.start_text}/{window.end_text}",
            None,
            None,
            scene_count,
            median_count,
            raw_rgb,
            valid_pixels,
        ))
    return candidates


def _row_for_candidate(
    chip: Chip,
    window: DateWindow,
    candidate: CandidateImage,
    comparison: Comparison,
    *,
    size_px: int,
) -> dict[str, Any]:
    """Flatten one result into the stable CSV output schema."""
    return {
        "chip_filename": chip.path.name,
        "latitude": chip.latitude,
        "longitude": chip.longitude,
        "window_start_inclusive": window.start_text,
        "window_end_exclusive": window.end_text,
        "candidate_kind": candidate.kind,
        "candidate_id": candidate.candidate_id,
        "scene_date_utc": candidate.scene_date_utc,
        "cloudy_pixel_percentage": candidate.cloudy_pixel_percentage,
        "scenes_in_window": candidate.scenes_in_window,
        "scenes_in_median": candidate.scenes_in_median,
        "valid_pixel_count": int(candidate.valid_mask.sum()),
        "valid_pixel_fraction": float(candidate.valid_mask.mean()) if size_px else None,
        "offset_dx": comparison.offset_dx,
        "offset_dy": comparison.offset_dy,
        "pearson_r": comparison.pearson[0],
        "pearson_g": comparison.pearson[1],
        "pearson_b": comparison.pearson[2],
        "mean_pearson": comparison.mean_pearson,
        "histogram_distance_r": comparison.histogram_distance[0],
        "histogram_distance_g": comparison.histogram_distance[1],
        "histogram_distance_b": comparison.histogram_distance[2],
        "mean_histogram_distance": comparison.mean_histogram_distance,
        "best_for_chip_window": False,
        "status": "ok" if comparison.valid_pixel_count else "no_clear_pixels",
    }


def run_diagnostic(
    training_dir: Path,
    windows: Sequence[DateWindow],
    output_csv: Path,
    *,
    config_path: Path,
    max_samples: int | None = None,
    seed: int = 0,
    fetcher: CandidateFetcher | None = None,
) -> Path:
    """Compare selected chips and write one row per candidate to the output CSV."""
    with config_path.open(encoding="utf-8") as source:
        config = yaml.safe_load(source)
    if not isinstance(config, dict):
        raise TypeError(f"Expected a preprocessing config mapping: {config_path}")
    size_px = int(config["patches"]["size_px"])
    chips = load_chips(training_dir, size_px=size_px, max_samples=max_samples, seed=seed)
    if fetcher is None:
        fetcher = lambda chip, window: fetch_ee_candidates(chip, window, config=config)

    rows: list[dict[str, Any]] = []
    for chip in chips:
        for window in windows:
            candidates = list(fetcher(chip, window))
            candidate_rows: list[dict[str, Any]] = []
            for candidate in candidates:
                comparison = compare_patch(chip.rgb, candidate.raw_rgb, candidate.valid_mask)
                candidate_rows.append(_row_for_candidate(
                    chip, window, candidate, comparison, size_px=size_px
                ))
            comparable = [
                row for row in candidate_rows if row["mean_pearson"] is not None
            ]
            if comparable:
                best = min(
                    comparable,
                    key=lambda row: (
                        -row["mean_pearson"],
                        row["mean_histogram_distance"],
                        abs(row["offset_dx"]) + abs(row["offset_dy"]),
                        row["candidate_id"],
                    ),
                )
                best["best_for_chip_window"] = True
            if not candidate_rows:
                candidate_rows.append({
                    "chip_filename": chip.path.name,
                    "latitude": chip.latitude,
                    "longitude": chip.longitude,
                    "window_start_inclusive": window.start_text,
                    "window_end_exclusive": window.end_text,
                    "candidate_kind": "none",
                    "candidate_id": "",
                    "scene_date_utc": "",
                    "cloudy_pixel_percentage": "",
                    "scenes_in_window": 0,
                    "scenes_in_median": 0,
                    "valid_pixel_count": 0,
                    "valid_pixel_fraction": 0.0,
                    "offset_dx": "",
                    "offset_dy": "",
                    "pearson_r": "",
                    "pearson_g": "",
                    "pearson_b": "",
                    "mean_pearson": "",
                    "histogram_distance_r": "",
                    "histogram_distance_g": "",
                    "histogram_distance_b": "",
                    "mean_histogram_distance": "",
                    "best_for_chip_window": False,
                    "status": "no_scenes",
                })
            rows.extend(candidate_rows)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_csv


def main() -> None:
    """Parse CLI arguments, authenticate Earth Engine, and run the diagnostic."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-dir", type=Path, required=True)
    parser.add_argument(
        "--window", action="append", required=True, metavar="START/END",
        help="ISO dates; start included, end excluded. Repeat to compare windows.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--preprocessing-config", type=Path,
        default=Path("config/preprocessing.yaml"),
    )
    args = parser.parse_args()
    windows = [parse_date_window(value) for value in args.window]
    import os

    project = os.environ.get("KILNWATCH_EE_PROJECT")
    if not project:
        parser.error("Set KILNWATCH_EE_PROJECT before running the Earth Engine diagnostic")
    try:
        import ee  # type: ignore[import-untyped]
    except ImportError as error:
        parser.error(f"Install the Earth Engine extra first: {error}")
    ee.Initialize(project=project)
    print(run_diagnostic(
        args.training_dir,
        windows,
        args.output,
        config_path=args.preprocessing_config,
        max_samples=args.max_samples,
        seed=args.seed,
    ))


if __name__ == "__main__":
    main()
