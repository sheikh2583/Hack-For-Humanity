"""Submit one configured Bangladesh district to Google Earth Engine.

Input: a configured AOI district name and Earth Engine project ID.
Output: started Earth Engine task IDs printed to standard output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from src.data.export_s2 import export_composites

ROOT = Path(__file__).resolve().parents[1]
AOI_CONFIG = ROOT / "config/aoi.yaml"


def configured_district_names(aoi_config: Path = AOI_CONFIG) -> list[str]:
    """Return exact district names accepted by the AOI export configuration.

    Input schema: AOI YAML containing a ``districts`` list with ``name`` fields.
    Output schema: district names in configured order for CLI choices.
    """
    with aoi_config.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    return [str(district["name"]) for district in config.get("districts", [])]


def export_district(district: str, project: str) -> list[str]:
    """Submit exactly one configured district export and return its task IDs."""
    task_ids = export_composites(
        AOI_CONFIG,
        district_name=district,
        project=project,
    )
    for task_id in task_ids:
        print(f"Earth Engine task ID: {task_id}")
    return task_ids


def main() -> None:
    """Parse district/project arguments and submit the export task."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--district", required=True, choices=configured_district_names(),
        help="Configured district name",
    )
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    export_district(args.district, args.project)


if __name__ == "__main__":
    main()
