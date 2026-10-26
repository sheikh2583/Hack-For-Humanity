"""Print technical summary statistics for a GeoTIFF export.

Input schema: a readable raster dataset accepted by Rasterio. Output: CRS,
pixel size, dimensions, band count/dtypes, per-band min/max and zero-pixel
fraction (a pixel counts as zero when every band is zero).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


def inspect_raster(path: Path) -> dict[str, Any]:
    """Read a raster by block and return metadata plus per-band statistics."""
    if not path.is_file():
        raise FileNotFoundError(f"Raster not found: {path}")
    with rasterio.open(path) as dataset:
        mins = np.full(dataset.count, np.inf, dtype=np.float64)
        maxs = np.full(dataset.count, -np.inf, dtype=np.float64)
        zero_count = 0
        pixel_count = dataset.width * dataset.height
        for _, window in dataset.block_windows(1):
            data = dataset.read(window=window)
            for band_index in range(dataset.count):
                band = data[band_index]
                if band.size:
                    mins[band_index] = min(mins[band_index], float(np.nanmin(band)))
                    maxs[band_index] = max(maxs[band_index], float(np.nanmax(band)))
            zero_count += int(np.all(data == 0, axis=0).sum())
        return {
            "crs": str(dataset.crs),
            "pixel_size": (abs(float(dataset.transform.a)), abs(float(dataset.transform.e))),
            "shape": (dataset.height, dataset.width),
            "band_count": dataset.count,
            "dtype": tuple(dataset.dtypes),
            "band_min_max": tuple((float(lo), float(hi)) for lo, hi in zip(mins, maxs)),
            "zero_pixel_fraction": zero_count / pixel_count if pixel_count else 0.0,
        }


def main() -> None:
    """Parse the raster path and print its inspection summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raster", required=True, type=Path)
    args = parser.parse_args()
    info = inspect_raster(args.raster)
    print(f"CRS: {info['crs']}")
    print(f"Pixel size: {info['pixel_size']}")
    print(f"Shape (height, width): {info['shape']}")
    print(f"Band count: {info['band_count']}")
    print(f"Dtype: {info['dtype']}")
    for index, (minimum, maximum) in enumerate(info["band_min_max"], start=1):
        print(f"Band {index} min/max: {minimum} / {maximum}")
    print(f"Zero-pixel fraction (all bands zero): {info['zero_pixel_fraction']:.6f}")


if __name__ == "__main__":
    main()
