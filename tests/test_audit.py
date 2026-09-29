"""Tests for src.eval.audit_sample — Wilson interval and sampling."""

from __future__ import annotations

from src.eval.audit_sample import _wilson_interval


class TestWilsonInterval:
    """Tests for the Wilson score confidence interval."""

    def test_perfect_precision(self) -> None:
        lo, hi = _wilson_interval(10, 10)
        assert lo > 0.6  # should be well above 0.5
        assert hi <= 1.0

    def test_zero_precision(self) -> None:
        lo, hi = _wilson_interval(0, 10)
        assert lo >= 0.0
        assert hi < 0.4  # should be well below 0.5

    def test_empty(self) -> None:
        lo, hi = _wilson_interval(0, 0)
        assert lo == 0.0
        assert hi == 0.0

    def test_half(self) -> None:
        lo, hi = _wilson_interval(50, 100)
        assert 0.35 < lo < 0.5
        assert 0.5 < hi < 0.65
