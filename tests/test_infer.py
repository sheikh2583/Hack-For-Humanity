"""Tests for src.detect.infer — coordinate transforms and NMS.

Uses tiny synthetic data — no real raster or model needed.
"""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from src.detect.infer import (
    _nms_polygons,
    _pixel_to_geo,
    _point_output_records,
    _polygon_iou,
    _predict_tile,
    _tile_starts,
)


def test_predict_tile_passes_bgr_and_imgsz() -> None:
    """RGB tile is reversed to BGR and configured imgsz reaches model.predict."""
    class FakeModel:
        def predict(self, image, **kwargs):
            assert image.dtype == np.uint8
            np.testing.assert_array_equal(image[0, 1], np.array([50, 101, 127]))
            np.testing.assert_array_equal(image[1, 1], np.array([254, 254, 254]))
            assert kwargs["imgsz"] == 384
            assert kwargs["conf"] == 0.1
            assert kwargs["device"] == "cpu"
            return "result"

    tile = {"array": np.array(
        [[[100, 0, 10], [200, 40, 30]], [[150, 80, 90], [300, 100, 110]]],
        dtype=np.uint16,
    )}
    assert _predict_tile(FakeModel(), tile, imgsz=384, conf_threshold=0.1) == "result"


def test_tile_starts_align_last_patch_to_far_edge() -> None:
    """Last origin reaches the far edge while earlier origins use configured stride."""
    assert _tile_starts(length=300, chip_size=128, stride=98) == [0, 98, 172]


def test_tile_raster_yields_windows_incrementally(tmp_path) -> None:
    """Raster windows are yielded one-by-one rather than retained as a full list."""
    import rasterio
    from rasterio.transform import from_origin

    from src.detect.infer import _tile_raster

    path = tmp_path / "small.tif"
    data = np.ones((3, 128, 226), dtype=np.float64)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=128,
        width=226,
        count=3,
        dtype="float64",
        crs="EPSG:32646",
        transform=from_origin(400000, 2700000, 10, 10),
    ) as dst:
        dst.write(data)

    tiles = _tile_raster(path, chip_size=128, overlap=30)
    assert iter(tiles) is tiles
    first = next(tiles)
    assert first["array"].shape == (128, 128, 3)
    assert first["array"].dtype == np.float64
    second = next(tiles)
    assert second["array"].shape == (128, 128, 3)
    with pytest.raises(StopIteration):
        next(tiles)


def test_point_output_schema_uses_wgs84_centroids() -> None:
    """Polygon detections become Point rows with the requested output columns."""
    records = _point_output_records(
        [{"kiln_id": "id-1", "geometry": box(90, 24, 90.2, 24.2), "class": "FCBK", "confidence": 0.8}],
        "Chapainawabganj",
    )
    row = records[0]
    assert isinstance(row["geometry"], Point)
    assert abs(row["lat"] - 24.1) < 1e-12
    assert abs(row["lon"] - 90.1) < 1e-12
    assert row["class_name"] == "FCBK"
    assert row["district"] == "Chapainawabganj"
    assert set(row) == {"kiln_id", "geometry", "class_name", "confidence", "district", "lat", "lon"}


class FakeAffine:
    """Minimal affine transform for testing (mimics rasterio/affine)."""

    def __init__(self, a: float, b: float, c: float, d: float, e: float, f: float):
        self.a = a  # pixel width
        self.b = b  # rotation (0 for north-up)
        self.c = c  # x origin (west)
        self.d = d  # rotation (0 for north-up)
        self.e = e  # pixel height (negative for north-up)
        self.f = f  # y origin (north)


class TestPixelToGeo:
    """Verify pixel-to-geographic coordinate conversion."""

    def test_identity(self) -> None:
        """Pixel (0,0) should map to the raster origin."""
        transform = FakeAffine(
            a=0.0001, b=0.0, c=88.0,
            d=0.0, e=-0.0001, f=25.0,
        )
        coords = np.array([[0.0, 0.0]])
        geo = _pixel_to_geo(coords, transform)
        assert abs(geo[0, 0] - 88.0) < 1e-10
        assert abs(geo[0, 1] - 25.0) < 1e-10

    def test_offset(self) -> None:
        """Pixel (10, 20) should shift by the affine coefficients."""
        transform = FakeAffine(
            a=0.0001, b=0.0, c=88.0,
            d=0.0, e=-0.0001, f=25.0,
        )
        coords = np.array([[10.0, 20.0]])
        geo = _pixel_to_geo(coords, transform)
        expected_x = 88.0 + 10 * 0.0001
        expected_y = 25.0 + 20 * (-0.0001)
        assert abs(geo[0, 0] - expected_x) < 1e-10
        assert abs(geo[0, 1] - expected_y) < 1e-10

    def test_known_box(self) -> None:
        """A 128×128 chip at known location should produce correct bounds."""
        # 10m resolution → ~0.00009° per pixel at equator
        pix_deg = 10.0 / 111320.0  # approx
        transform = FakeAffine(
            a=pix_deg, b=0.0, c=88.5,
            d=0.0, e=-pix_deg, f=24.5,
        )
        # Box corners: (0,0), (128,0), (128,128), (0,128)
        corners = np.array([
            [0.0, 0.0],
            [128.0, 0.0],
            [128.0, 128.0],
            [0.0, 128.0],
        ])
        geo = _pixel_to_geo(corners, transform)
        # Width in degrees should be ~128 pixels * pix_deg
        width = geo[1, 0] - geo[0, 0]
        assert abs(width - 128 * pix_deg) < 1e-10


class TestPolygonIoU:
    """Tests for polygon IoU calculation."""

    def test_identical(self) -> None:
        p = box(0, 0, 1, 1)
        assert abs(_polygon_iou(p, p) - 1.0) < 1e-6

    def test_no_overlap(self) -> None:
        p1 = box(0, 0, 1, 1)
        p2 = box(2, 2, 3, 3)
        assert abs(_polygon_iou(p1, p2) - 0.0) < 1e-6

    def test_half_overlap(self) -> None:
        p1 = box(0, 0, 2, 1)
        p2 = box(1, 0, 3, 1)
        # Intersection = 1, Union = 3
        assert abs(_polygon_iou(p1, p2) - 1.0 / 3.0) < 1e-6


class TestNMS:
    """Tests for polygon NMS."""

    def test_suppresses_overlap(self) -> None:
        dets = [
            {"geometry": box(0, 0, 1, 1), "confidence": 0.9},
            {"geometry": box(0.1, 0.1, 1.1, 1.1), "confidence": 0.7},  # high IoU with above
        ]
        kept = _nms_polygons(dets, iou_threshold=0.3)
        assert len(kept) == 1
        assert kept[0]["confidence"] == 0.9

    def test_keeps_non_overlapping(self) -> None:
        dets = [
            {"geometry": box(0, 0, 1, 1), "confidence": 0.9},
            {"geometry": box(5, 5, 6, 6), "confidence": 0.8},
        ]
        kept = _nms_polygons(dets, iou_threshold=0.3)
        assert len(kept) == 2


class TestUTMToWGS84Reprojection:
    """Verify that detections in a UTM raster reproject correctly to EPSG:4326.

    Creates a synthetic 128×128 raster in EPSG:32646 at a known UTM origin,
    places a box at pixel (10,10)→(20,20), converts via affine → UTM coords,
    then reprojects to EPSG:4326 and checks the centroid lands within 20 m
    of the expected WGS84 point.
    """

    def test_utm_box_reprojects_within_20m(self) -> None:
        import geopandas as gpd
        import pyproj

        # Known point: approximately Gazipur, Bangladesh
        # UTM 46N easting/northing for ~90.4°E, 24.0°N
        transformer_to_utm = pyproj.Transformer.from_crs(
            "EPSG:4326", "EPSG:32646", always_xy=True
        )
        transformer_to_wgs = pyproj.Transformer.from_crs(
            "EPSG:32646", "EPSG:4326", always_xy=True
        )

        # Pick a known lon/lat and convert to UTM origin
        known_lon, known_lat = 90.4, 24.0
        origin_e, origin_n = transformer_to_utm.transform(known_lon, known_lat)

        # Raster: 10m/pixel, north-up
        pixel_size = 10.0
        transform = FakeAffine(
            a=pixel_size,      # 10 m/pixel in easting
            b=0.0,
            c=origin_e,        # UTM easting origin
            d=0.0,
            e=-pixel_size,     # 10 m/pixel in northing (negative = north-up)
            f=origin_n,        # UTM northing origin
        )

        # Box at pixels (10,10)→(20,20) — a 100m × 100m square
        box_pixels = np.array([
            [10.0, 10.0],
            [20.0, 10.0],
            [20.0, 20.0],
            [10.0, 20.0],
        ])

        # Convert to UTM coordinates
        utm_coords = _pixel_to_geo(box_pixels, transform)
        polygon_utm = Polygon(utm_coords)

        # Expected centroid in UTM
        expected_e = origin_e + 15 * pixel_size   # mid of cols 10-20
        expected_n = origin_n + 15 * (-pixel_size)  # mid of rows 10-20

        # Verify UTM centroid
        assert abs(polygon_utm.centroid.x - expected_e) < 0.01
        assert abs(polygon_utm.centroid.y - expected_n) < 0.01

        # Reproject to EPSG:4326 (mimicking what run_inference now does)
        gdf = gpd.GeoDataFrame(
            [{"geometry": polygon_utm}], crs="EPSG:32646"
        ).to_crs("EPSG:4326")

        centroid_4326 = gdf.geometry.iloc[0].centroid

        # Expected lon/lat of the centroid
        expected_lon, expected_lat = transformer_to_wgs.transform(expected_e, expected_n)

        # Compute distance in metres between expected and actual
        geod = pyproj.Geod(ellps="WGS84")
        _, _, dist_m = geod.inv(
            expected_lon, expected_lat,
            centroid_4326.x, centroid_4326.y,
        )

        assert dist_m < 20.0, (
            f"Reprojected centroid is {dist_m:.1f} m from expected "
            f"(expected ({expected_lon:.6f}, {expected_lat:.6f}), "
            f"got ({centroid_4326.x:.6f}, {centroid_4326.y:.6f}))"
        )

