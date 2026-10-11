"""Check that the dashboard's precomputed prioritized GeoParquet is available.

Input schema: an optional directory containing
``kilns_prioritised.parquet``. Output: ``None`` when the file exists, or a
printable instruction string when it is missing; no data is generated.
"""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_FILENAME = "kilns_prioritised.parquet"


def check_prioritised_data(data_dir: Path = DATA_DIR) -> str | None:
    """Print and return setup guidance when the prioritized parquet is absent."""
    data_path = data_dir / DATA_FILENAME
    if data_path.is_file():
        return None

    instructions = (
        f"Required dashboard data is missing: {data_path}\n"
        "Generate the prioritized GeoParquet before starting the dashboard, "
        "or include this file in the deployment repository/Space files. "
        "The dashboard does not run inference or Earth Engine exports at startup."
    )
    print(instructions)
    return instructions


if __name__ == "__main__":
    check_prioritised_data()
