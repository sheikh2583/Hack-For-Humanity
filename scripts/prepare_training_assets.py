"""Fetch or validate local SentinelKilnDB training inputs and OBB starting weights.

Input schema: the pinned public Hugging Face Parquet files or an existing
converted YOLO-OBB archive, plus the reviewed Bangladesh conversion boundary
when conversion is needed. Output schema: raw Parquet files under
``data/raw/sentinelkilndb/``, a validated YOLO dataset under
``data/interim/yolo_obb/``, and starting weights under ``data/models/``.
This preparation utility does not start a GPU workload.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import yaml

REPOSITORY = "SustainabilityLabIITGN/SentinelKilnDB"
REVISION = "48242579f58fbec5b40316f9eb03aac573676f2e"
RAW_FILES = {
    "train/train.parquet": (
        2_351_086_566,
        "90107b0e4e922f3d84c2996acd2bb371f36dbbd3cdd9b305057bd44e9a62c484",
    ),
    "val/val.parquet": (
        783_379_148,
        "e8f92d816ebc88391d0bc6532a7bef775e242951f1d267553720fedd6f7be57e",
    ),
    "test/test.parquet": (
        608_368_722,
        "8a26ecf01f00ca45cffb741fbe4e8067ef601f6e33fb6905931d1f87c181cd4d",
    ),
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT_ROOT / "data/raw/sentinelkilndb"
DATASET_ROOT = PROJECT_ROOT / "data/interim/yolo_obb"
BOUNDARY = PROJECT_ROOT / "data/raw/bangladesh_boundary.geojson"
MODEL_ROOT = PROJECT_ROOT / "data/models"


def is_valid_converted_dataset(dataset_root: Path) -> bool:
    """Return whether the converted dataset has the expected splits and report.

    Input: a directory candidate containing dataset YAML, split report, and
    ``train/val/test`` image and label directories. Output: a readiness boolean.
    """
    import json

    dataset_root = Path(dataset_root)
    report_path = dataset_root / "split_report.json"
    if not (dataset_root / "dataset.yaml").is_file() or not report_path.is_file():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if report.get("leakage_filter_threshold_m") != 1300.0:
        return False
    try:
        dataset_config = yaml.safe_load(
            (dataset_root / "dataset.yaml").read_text(encoding="utf-8")
        )
        names = {
            int(class_id): name for class_id, name in dataset_config.get("names", {}).items()
        }
    except (AttributeError, OSError, TypeError, ValueError, yaml.YAMLError):
        return False
    if names != {0: "FCBK", 1: "Zigzag"}:
        return False
    for split in ("train", "val", "test"):
        images = dataset_root / split / "images"
        labels = dataset_root / split / "labels"
        if not images.is_dir() or not labels.is_dir():
            return False
        if not any(images.glob("*.png")) or not any(labels.glob("*.txt")):
            return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_file(relative_path: str, expected_size: int, expected_sha256: str) -> None:
    """Download one pinned Hugging Face file and verify its size and digest."""
    destination = RAW_ROOT / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = (
        f"https://huggingface.co/datasets/{REPOSITORY}/resolve/"
        f"{REVISION}/{relative_path}"
    )
    partial = destination.with_suffix(destination.suffix + ".partial")
    print(f"Downloading {relative_path} ({expected_size / 1_000_000_000:.2f} GB)...")
    digest = hashlib.sha256()
    received = 0
    last_reported = 0
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as target:
            while block := response.read(8 * 1024 * 1024):
                target.write(block)
                digest.update(block)
                received += len(block)
                if received - last_reported >= 256 * 1024 * 1024:
                    print(
                        f"  {received / 1_000_000_000:.2f} / "
                        f"{expected_size / 1_000_000_000:.2f} GB"
                    )
                    last_reported = received
        if received != expected_size or digest.hexdigest() != expected_sha256:
            raise ValueError(
                f"Verification failed for {relative_path}: bytes={received}, "
                f"sha256={digest.hexdigest()}"
            )
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def _extract_dataset_archive(archive_path: Path) -> None:
    """Safely extract a converted YOLO dataset archive into ``data/interim``."""
    target_root = (PROJECT_ROOT / "data/interim").resolve()
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if not members:
            raise ValueError(f"Dataset archive is empty: {archive_path}")
        for member in members:
            member_path = PurePosixPath(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe path in dataset archive: {member.filename}")
            if not member_path.parts or member_path.parts[0] != "yolo_obb":
                raise ValueError(
                    "Converted dataset archive must have a top-level yolo_obb/ directory"
                )
            output = (target_root / Path(*member_path.parts)).resolve()
            if not output.is_relative_to(target_root):
                raise ValueError(f"Unsafe path in dataset archive: {member.filename}")
        archive.extractall(target_root)


def _create_dataset_archive(archive_path: Path) -> Path:
    """Create an uncompressed, portable bundle of the checked converted dataset."""
    if not is_valid_converted_dataset(DATASET_ROOT):
        raise ValueError(f"No current 1,300 m leakage-filter dataset at {DATASET_ROOT}")
    archive_path = Path(archive_path).expanduser()
    if not archive_path.is_absolute():
        archive_path = (PROJECT_ROOT / archive_path).resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_suffix(archive_path.suffix + ".partial")
    files = sorted(path for path in DATASET_ROOT.rglob("*") if path.is_file())
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for index, path in enumerate(files, 1):
                archive.write(
                    path,
                    arcname=(Path("yolo_obb") / path.relative_to(DATASET_ROOT)).as_posix(),
                )
                if index % 2_000 == 0:
                    print(f"Bundled {index}/{len(files)} dataset files...")
        temporary.replace(archive_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Created dataset transfer bundle: {archive_path} ({len(files)} files)")
    return archive_path


def _ensure_raw_dataset(download: bool) -> None:
    """Validate local Parquet files or fetch the pinned public dataset."""
    missing = [rel for rel in RAW_FILES if not (RAW_ROOT / rel).is_file()]
    if missing and not download:
        raise FileNotFoundError(f"Missing SentinelKilnDB Parquet files: {', '.join(missing)}")
    if missing:
        for relative_path, (size, digest) in RAW_FILES.items():
            if not (RAW_ROOT / relative_path).is_file():
                _download_file(relative_path, size, digest)
    for relative_path, (expected_size, expected_digest) in RAW_FILES.items():
        path = RAW_ROOT / relative_path
        if path.stat().st_size != expected_size:
            raise ValueError(f"Unexpected file size for {path}: {path.stat().st_size}")
        if _sha256(path) != expected_digest:
            raise ValueError(f"SHA-256 mismatch for {path}")


def _convert_raw_dataset() -> None:
    """Run the project conversion using a manually reviewed country boundary."""
    if not BOUNDARY.is_file():
        raise FileNotFoundError(
            "Raw Parquet data is present, but conversion requires your reviewed "
            f"Bangladesh boundary at {BOUNDARY}. The initializer will not fetch or "
            "guess a boundary source. Place the reviewed file there, then rerun."
        )
    command = [
        sys.executable,
        "-m",
        "src.cli",
        "convert",
        str(RAW_ROOT),
        "--boundary",
        str(BOUNDARY),
        "--output-dir",
        str(DATASET_ROOT),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _ensure_starting_weights() -> None:
    """Download canonical OBB starting weights using Ultralytics on CPU only."""
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    from ultralytics import YOLO

    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    for filename in ("yolov8n-obb.pt", "yolov8s-obb.pt"):
        destination = MODEL_ROOT / filename
        if destination.is_file() and destination.stat().st_size > 1_000_000:
            print(f"Starting weight already present: {destination.relative_to(PROJECT_ROOT)}")
            continue
        model = YOLO(filename, task="obb")
        source = Path(model.ckpt_path)
        if not source.is_file():
            raise FileNotFoundError(f"Ultralytics did not provide the downloaded weight: {source}")
        shutil.copy2(source, destination)
        del model
        print(f"Prepared starting weight: {destination.relative_to(PROJECT_ROOT)}")


def _find_archive(argument: str | None) -> Path | None:
    """Resolve only an explicitly supplied converted dataset archive."""
    if argument:
        archive = Path(argument).expanduser()
        if not archive.is_absolute():
            archive = (PROJECT_ROOT / archive).resolve()
        if not archive.is_file():
            raise FileNotFoundError(f"Dataset archive not found: {archive}")
        return archive
    return None


def main() -> int:
    """Prepare all available training inputs without starting GPU computation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-archive", help="Existing converted yolo_obb_bd.zip")
    parser.add_argument(
        "--download-raw",
        action="store_true",
        help="Confirm download of the pinned 3.74 GB SentinelKilnDB source files",
    )
    parser.add_argument(
        "--make-dataset-archive",
        metavar="PATH",
        help="Create a portable archive from the current converted dataset and exit",
    )
    args = parser.parse_args()

    if args.make_dataset_archive:
        _create_dataset_archive(Path(args.make_dataset_archive))
        return 0

    if not is_valid_converted_dataset(DATASET_ROOT):
        archive = _find_archive(args.dataset_archive)
        if archive:
            _extract_dataset_archive(archive)
        else:
            if not BOUNDARY.is_file():
                print(
                    "Training data is absent. Supply a converted yolo_obb_bd.zip or "
                    "place your reviewed Bangladesh boundary at "
                    f"{BOUNDARY}. The boundary is required to build the converted dataset."
                )
                return 2
            download = args.download_raw
            if not download and sys.stdin.isatty():
                answer = input(
                    "Download pinned SentinelKilnDB Parquet files (about 3.74 GB)? [y/N] "
                )
                download = answer.strip().lower() in {"y", "yes"}
            if not download:
                print("No dataset download requested. Pass --download-raw to download it.")
                return 2
            _ensure_raw_dataset(download=True)
            _convert_raw_dataset()

    if not is_valid_converted_dataset(DATASET_ROOT):
        raise ValueError(
            f"Converted dataset at {DATASET_ROOT} is incomplete or predates the "
            "verified 1,300 m leakage-filter conversion. Rebuild it from reviewed inputs."
        )
    _ensure_starting_weights()
    print(f"Training dataset ready: {DATASET_ROOT}")
    print("No CUDA availability probe, smoke test, or training run was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
