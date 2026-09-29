"""Tests for src.geo.crs — CRS utility."""

from __future__ import annotations

import pyproj

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
