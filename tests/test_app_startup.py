"""Synthetic checks for dashboard deployment data preflight."""

from pathlib import Path

from app.startup import DATA_FILENAME, check_prioritised_data


def test_check_prioritised_data_reports_missing_file(tmp_path: Path, caplog) -> None:
    """A missing synthetic data file prints actionable setup instructions."""
    with caplog.at_level("WARNING"):
        message = check_prioritised_data(tmp_path)

    assert message is not None
    assert DATA_FILENAME in message
    assert "does not run inference" in message
    assert message in caplog.text


def test_check_prioritised_data_accepts_existing_file(tmp_path: Path) -> None:
    """An existing synthetic data file passes the deployment preflight."""
    (tmp_path / DATA_FILENAME).touch()

    assert check_prioritised_data(tmp_path) is None
