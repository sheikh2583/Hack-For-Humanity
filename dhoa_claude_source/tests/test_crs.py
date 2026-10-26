"""Tests for src.geo.crs — CRS utility."""

from __future__ import annotations

import pyproj
import pytest

from src.geo.crs import get_projected_crs


class TestGetProjectedCRS:
    """Verify that the projected CRS fallback chain works."""

    def test_returns_projected(self) -> None:
        """Should return a projected (metre-based) CRS."""
        crs = get_projected_crs()
        assert crs.is_projected

    def test_is_metre_unit(self) -> None:
        """The CRS axis unit should be metres."""
        crs = get_projected_crs()
        # Check that the first axis uses metre
        axis_info = crs.axis_info
        assert any("metre" in ax.unit_name.lower() for ax in axis_info)

    def test_transformer_builds(self) -> None:
        """Should be able to build a transformer from EPSG:4326."""
        crs = get_projected_crs()
        transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        # Transform a known point in Bangladesh
        x, y = transformer.transform(88.5, 24.0)
        assert x != 0.0 and y != 0.0

    @pytest.mark.parametrize(("longitude", "expected"), [(89.9, 32645), (90.0, 32646)])
    def test_utm_fallback_uses_centroid_longitude(self, monkeypatch, longitude, expected) -> None:
        """When EPSG:9680 is unavailable, select UTM zone from centroid longitude."""
        from pyproj.exceptions import CRSError

        original = pyproj.CRS.from_epsg

        def from_epsg(code):
            if code == 9680:
                raise CRSError("simulated missing CRS")
            return original(code)

        monkeypatch.setattr(pyproj.CRS, "from_epsg", staticmethod(from_epsg))
        assert get_projected_crs(longitude).to_epsg() == expected

    def test_utm_fallback_requires_centroid_longitude(self, monkeypatch) -> None:
        """Do not guess a UTM zone when the required centroid is unavailable."""
        from pyproj.exceptions import CRSError

        original = pyproj.CRS.from_epsg

        def from_epsg(code):
            if code == 9680:
                raise CRSError("simulated missing CRS")
            return original(code)

        monkeypatch.setattr(pyproj.CRS, "from_epsg", staticmethod(from_epsg))
        with pytest.raises(RuntimeError, match="centroid longitude"):
            get_projected_crs()
