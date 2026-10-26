"""Configuration, dataset identity, numbered run state, and GPU provenance.

Input schema: training YAML plus the YOLO OBB dataset tree. Output schema:
portable JSON manifests and dataset-local YAML files under the project results
directory; runtime metadata records only the GPU selected by the user.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN_ID_PATTERN = re.compile(r"^run_([0-9]{4,})$")


def read_training_config(path: Path) -> dict[str, Any]:
    """Read shared YAML settings and reject incomplete stage declarations."""
    with path.open(encoding="utf-8") as source:
        config = yaml.safe_load(source)
    if not isinstance(config, dict) or not isinstance(config.get("stages"), list):
        raise ValueError(f"Invalid training configuration: {path}")  # noqa: TRY004
    required = ("name", "model", "imgsz", "epochs")
    for stage in config["stages"]:
        if not isinstance(stage, dict) or not all(key in stage for key in required):
            raise ValueError(
                "Each configured stage needs name/model/imgsz/epochs: "
                f"{stage}"
            )
    if len(config["stages"]) < 3:
        raise ValueError("Training configuration must define at least three YOLOv8n stages")
    return config


def dataset_fingerprint(dataset_dir: Path) -> str:
    """Hash metadata and all dataset bytes to verify cross-host run compatibility."""
    root = dataset_dir.resolve()
    digest = hashlib.sha256()
    for metadata in (root / "dataset.yaml", root / "split_report.json"):
        if not metadata.is_file():
            raise FileNotFoundError(f"Required training dataset metadata is missing: {metadata}")
        digest.update(metadata.name.encode())
        digest.update(metadata.read_bytes())
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name in {"dataset.yaml", "dataset_local.yaml", "split_report.json"}:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def training_provenance(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Capture config bytes, parsed settings, and Git source state for a new run."""
    resolved_config = config_path.resolve()
    try:
        config_ref = resolved_config.relative_to(ROOT).as_posix()
    except ValueError:
        config_ref = resolved_config.name
    config_bytes = resolved_config.read_bytes()
    source_commit: str | None = None
    changed_paths: list[str] = []
    try:
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
            check=True, capture_output=True, text=True,
        ).stdout
        changed_paths = [line[3:] for line in status.splitlines() if len(line) >= 4]
    except (OSError, subprocess.CalledProcessError):
        pass
    return {
        "config_file": config_ref,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "config_yaml": config_bytes.decode("utf-8"),
        "config_values": config,
        "source_commit": source_commit,
        "source_worktree_dirty": bool(changed_paths),
        "source_changed_paths": changed_paths,
    }


def prepare_dataset(dataset_dir: Path, test_split: str) -> tuple[Path, str]:
    """Validate split folders and write a host-local YAML for Ultralytics."""
    for split in ("train", "val", test_split):
        for child in ("images", "labels"):
            if not (dataset_dir / split / child).is_dir():
                raise FileNotFoundError(f"Missing dataset folder: {dataset_dir / split / child}")
    source = dataset_dir / "dataset.yaml"
    if not source.is_file():
        raise FileNotFoundError(f"Missing dataset YAML: {source}")
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid dataset YAML: {source}")  # noqa: TRY004
    payload["path"] = str(dataset_dir.resolve())
    local_yaml = dataset_dir / "dataset_local.yaml"
    local_yaml.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return local_yaml, dataset_fingerprint(dataset_dir)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON through an atomic replace to preserve state after interruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_run(results_dir: Path, run_id: str) -> dict[str, Any]:
    """Load one numbered run manifest after validating its directory name."""
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(f"Invalid run number: {run_id!r}; expected run_0001 or higher")
    path = results_dir / run_id / "run.json"
    if not path.is_file():
        raise FileNotFoundError(f"No run manifest found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def allocate_run(results_dir: Path) -> tuple[str, Path]:
    """Reserve the next sequential run directory without overwriting prior work."""
    results_dir.mkdir(parents=True, exist_ok=True)
    numbers = [int(match.group(1)) for path in results_dir.iterdir()
               if (match := RUN_ID_PATTERN.fullmatch(path.name))]
    number = max(numbers, default=0) + 1
    while True:
        run_id = f"run_{number:04d}"
        run_dir = results_dir / run_id
        try:
            run_dir.mkdir()
        except FileExistsError:
            number += 1
            continue
        return run_id, run_dir


def get_current_run(results_dir: Path) -> str | None:
    """Return the current-run pointer if it references an existing run."""
    pointer = results_dir / "current_run.json"
    if not pointer.is_file():
        return None
    run_id = json.loads(pointer.read_text(encoding="utf-8")).get("run_id")
    if (not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id)
            or not (results_dir / run_id / "run.json").is_file()):
        return None
    return run_id


def set_current_run(results_dir: Path, run_id: str) -> None:
    """Persist the active numbered run used by the one-command launcher."""
    write_json(results_dir / "current_run.json", {"run_id": run_id})


def gpu_identity(requested_device: str) -> dict[str, Any]:
    """Capture host and selected accelerator identity when training is invoked."""
    import torch

    identity: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pytorch": torch.__version__,
        "requested_device": requested_device,
    }
    if requested_device.strip().lower() == "cpu":
        identity.update({"accelerator": "CPU", "cuda_runtime": torch.version.cuda})
        return identity
    if not torch.cuda.is_available():
        raise RuntimeError(
            f"Device {requested_device!r} requested, but CUDA is unavailable. "
            "Check the host driver and installed CUDA-enabled PyTorch build."
        )
    raw_devices = requested_device.removeprefix("cuda:").split(",")
    selected: list[dict[str, Any]] = []
    for raw_index in raw_devices:
        index = int(raw_index.strip())
        if index < 0 or index >= torch.cuda.device_count():
            raise ValueError(f"Requested CUDA device {index}; found {torch.cuda.device_count()} GPU(s)")
        properties = torch.cuda.get_device_properties(index)
        selected.append({
            "index": index,
            "name": torch.cuda.get_device_name(index),
            "memory_bytes": properties.total_memory,
            "compute_capability": f"{properties.major}.{properties.minor}",
        })
    identity.update({"accelerator": "CUDA", "cuda_runtime": torch.version.cuda,
                     "gpus": selected})
    return identity
