"""Create and verify the self-contained KilnWatch BD review ZIP.

Inputs: optional output ZIP path (relative paths are resolved from the caller's
working directory); the configured source directories and files in the project.
Output: deterministic ZIP archive at the requested path, containing review
sources and documentation while excluding datasets, weights, caches, and
credentials. Identical input bytes produce identical ZIP bytes on Windows/Linux.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

INCLUDE_PATHS = (
    "app",
    "config",
    "docs",
    "notebooks",
    "src",
    "tests",
    "tools",
    "scripts",
    "results",
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    ".gitignore",
    ".gitattributes",
    "requirements-gpu-cu130.txt",
    "requirements-gpu-windows-py312.txt",
    "explore_labels.py",
    "explore_parquet.py",
    "kilnwatch_scaffold.md",
)
REQUIRED_ENTRIES = (
    "AGENTS.md",
    "requirements-gpu-cu130.txt",
    "requirements-gpu-windows-py312.txt",
    "docs/PROGRESS.md",
    "docs/TRAINING_READINESS.md",
    "docs/TRAINING_RUN_HISTORY.md",
    "docs/RUNBOOK.md",
    "docs/screening_provenance.md",
    "results/README.md",
    "docs/legal_basis.md",
    "docs/CLAUDE_WEB_PROMPT.md",
    "docs/CLAUDE_SHARING_AND_SETUP.md",
    "notebooks/train.ipynb",
)
EXCLUDE_PATTERN = re.compile(
    r"(^|/)(__pycache__|\.pytest_cache|\.ruff_cache|\.mypy_cache|\.cache|cache|"
    r"\.ipynb_checkpoints|__MACOSX|\.venv|venv|runs|wandb|\.git|\.kilo|"
    r"results/run_[0-9]{4,})(/|$)"
)
EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pt",
    ".pth",
    ".onnx",
    ".engine",
    ".parquet",
    ".tif",
    ".tiff",
    ".key",
    ".pem",
    ".log",
    ".zip",
    ".tmp",
    ".bak",
}
EXCLUDE_NAMES = {
    "credentials.json",
    "service-account.json",
    "training_results.json",
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}


def is_excluded(archive_name: str) -> bool:
    """Return whether a slash-separated archive path is excluded."""
    path = PurePosixPath(archive_name.replace("\\", "/"))
    name = path.name
    return (
        EXCLUDE_PATTERN.search(archive_name) is not None
        or path.suffix.lower() in EXCLUDE_EXTENSIONS
        or name.startswith(".env")
        or name.casefold() in EXCLUDE_NAMES
    )


def make_review_zip(output_path: Path, project_root: Path | None = None) -> Path:
    """Build and validate a deterministic archive; return the output path.

    Input schema: project tree matching ``INCLUDE_PATHS`` and destination path.
    Output schema: ZIP with normalized metadata and sorted slash-separated names.
    """
    project_root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    destination = output_path.expanduser()
    if not destination.is_absolute():
        destination = Path.cwd() / destination
    destination = destination.resolve()

    missing = [
        item
        for item in INCLUDE_PATHS
        if not (project_root / item).exists()
    ]
    if missing:
        raise FileNotFoundError(f"Review ZIP input is missing: {', '.join(missing)}")

    members: list[tuple[str, Path]] = []
    for item in INCLUDE_PATHS:
        source = project_root / item
        files = [source] if source.is_file() else sorted(source.rglob("*"))
        for file_path in files:
            if not file_path.is_file() or file_path.is_symlink():
                continue
            archive_name = file_path.relative_to(project_root).as_posix()
            if not is_excluded(archive_name):
                members.append((archive_name, file_path))

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for archive_name, file_path in sorted(members, key=lambda item: item[0]):
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            info.flag_bits = 0
            archive.writestr(info, file_path.read_bytes())

    with zipfile.ZipFile(destination, "r") as archive:
        names = set(archive.namelist())
        for required in REQUIRED_ENTRIES:
            if required not in names:
                raise ValueError(f"Review ZIP is missing required entry: {required}")
        forbidden = sorted(name for name in names if is_excluded(name))
        if forbidden:
            raise ValueError(f"Review ZIP contains excluded entries: {', '.join(forbidden)}")

    return destination


def main() -> int:
    """Parse command-line arguments and create the review archive."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_path",
        nargs="?",
        type=Path,
        help="output ZIP path (default: <project root>/kilnwatch_bd_share.zip)",
    )
    args = parser.parse_args()
    default_path = Path(__file__).resolve().parent.parent / "kilnwatch_bd_share.zip"
    output_path = args.output_path if args.output_path is not None else default_path
    try:
        result = make_review_zip(output_path)
    except (FileNotFoundError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    size_mb = result.stat().st_size / (1024 * 1024)
    print(f"Created and verified {result} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
