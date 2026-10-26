"""Synthetic checks for candidate PDF report generation."""

from __future__ import annotations

from src.eval.generate_report import generate_kiln_report


def test_generate_kiln_report_returns_pdf_bytes() -> None:
    """One valid synthetic candidate produces a PDF document in memory."""
    report = generate_kiln_report(
        {
            "kiln_id": "demo-1", "district": "Dhaka", "class": "Zigzag",
            "confidence": 0.8, "priority_band": "High", "lat": 23.7,
            "lon": 90.4, "detection_status": "New candidate (2025-26)",
            "breached_rules": ["near_school"], "dist_schools_m": 125.0,
        }
    )
    assert report is not None
    assert report.startswith(b"%PDF")
