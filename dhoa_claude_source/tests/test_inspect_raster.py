"""Small synthetic raster tests for the inspection helper."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from tools.inspect_raster import inspect_raster


def test_inspect_raster_reports_synthetic_metadata_and_zero_fraction(tmp_path: Path) -> None:
    """A tiny two-band GeoTIFF yields shape, pixel scale, and zero fraction."""
    path = tmp_path / "tiny.tif"
    values = np.array([[[0, 1], [2, 0]], [[0, 2], [4, 0]]], dtype=np.uint16)
    with rasterio.open(
        path, "w", driver="GTiff", height=2, width=2, count=2, dtype="uint16",
        crs="EPSG:4326", transform=from_origin(10, 20, 0.01, 0.01),
    ) as dataset:
        dataset.write(values)
    summary = inspect_raster(path)
    assert summary["crs"] == "EPSG:4326"
    assert summary["pixel_size"] == (0.01, 0.01)
    assert summary["shape"] == (2, 2)
    assert summary["band_count"] == 2
    assert summary["dtype"] == ("uint16", "uint16")
    assert summary["band_min_max"] == ((0.0, 2.0), (0.0, 4.0))
    assert summary["zero_pixel_fraction"] == 0.5
