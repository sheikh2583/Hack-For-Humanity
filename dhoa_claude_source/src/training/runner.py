"""Coordinate numbered, resumable KilnWatch OBB training runs.

Input schema: configured YOLO OBB dataset, pretrained weights, and training
settings. Output schema: ``results/run_NNNN/`` with a portable run manifest,
GPU history, epoch archives, ignored checkpoints, and final review artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.training.engine import copy_review_plots, evaluate_test, train_stage, validation_map50
from src.training.run_store import (
    ROOT,
    RUN_ID_PATTERN,
    allocate_run,
    get_current_run,
    gpu_identity,
    load_run,
    prepare_dataset,
    read_training_config,
    set_current_run,
    training_provenance,
    write_json,
)


def _save_state(run_dir: Path, state: dict[str, Any]) -> None:
    """Save and stage the small run manifest, never its model weights."""
    manifest = run_dir / "run.json"
    write_json(manifest, state)
    relative = manifest.resolve().relative_to(ROOT).as_posix()
    try:
        subprocess.run(["git", "add", "--", relative], cwd=ROOT, check=True,
                       capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Warning: could not stage run manifest: {error}", file=sys.stderr)


def _record_hardware(
    run_dir: Path, state: dict[str, Any], device: str, stage: str
) -> dict[str, Any]:
    """Record selected host/GPU identity for one stage before its execution."""
    event = gpu_identity(device)
    event["stage"] = stage
    event["event_number"] = len(state.setdefault("hardware_history", [])) + 1
    state["hardware_history"].append(event)
    _save_state(run_dir, state)
    return event


def _new_run(
    config: dict[str, Any], dataset_dir: Path, fingerprint: str, config_path: Path
) -> tuple[str, Path, dict[str, Any]]:
    """Allocate a sequential run folder and write its initial portable manifest."""
    results_dir = (ROOT / config["results_dir"]).resolve()
    run_id, run_dir = allocate_run(results_dir)
    dataset_ref = dataset_dir.resolve()
    try:
        dataset_value = dataset_ref.relative_to(ROOT).as_posix()
    except ValueError:
        dataset_value = str(dataset_ref)
    state: dict[str, Any] = {
        "run_id": run_id,
        "run_number": int(RUN_ID_PATTERN.fullmatch(run_id).group(1)),
        "created_utc": datetime.now(UTC).isoformat(),
        "dataset": dataset_value,
        "dataset_fingerprint": fingerprint,
        "provenance": training_provenance(config_path, config),
        "smoke": {"status": "pending"},
        "stages": {},
        "hardware_history": [],
        "test": {"status": "pending"},
        "status": "initialized",
    }
    set_current_run(results_dir, run_id)
    _save_state(run_dir, state)
    return run_id, run_dir, state


def _select_or_create_run(
    config: dict[str, Any], dataset_dir: Path, fingerprint: str,
    requested_run_id: str | None, *, continue_current: bool, config_path: Path,
) -> tuple[str, Path, dict[str, Any]]:
    """Load an explicit/current incomplete run or reserve the next run number."""
    results_dir = (ROOT / config["results_dir"]).resolve()
    run_id = requested_run_id
    if run_id is None and continue_current:
        candidate = get_current_run(results_dir)
        if candidate:
            current = load_run(results_dir, candidate)
            if current.get("status") != "complete":
                run_id = candidate
    if run_id is None:
        return _new_run(config, dataset_dir, fingerprint, config_path)
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(f"Invalid run number: {run_id!r}; expected run_0001 or higher")
    run_dir = results_dir / run_id
    if (run_dir / "run.json").is_file():
        state = load_run(results_dir, run_id)
        if state.get("dataset_fingerprint") != fingerprint:
            raise ValueError("Dataset bytes differ from this run; start a new numbered run.")
    else:
        raise FileNotFoundError(f"Run {run_id} does not exist under {results_dir}")
    set_current_run(results_dir, run_id)
    return run_id, run_dir, state


def _run_smoke(
    run_id: str, run_dir: Path, state: dict[str, Any], config: dict[str, Any],
    data_yaml: Path, device: str,
) -> None:
    """Run or continue the 3-epoch smoke gate using its last checkpoint."""
    if state.get("smoke", {}).get("status") == "passed":
        print(f"Smoke already passed for {run_id}; continuing the full stages.")
        return
    weights = ROOT / config["models_dir"] / config["smoke"]["model"]
    if not weights.is_file():
        raise FileNotFoundError(f"Missing pretrained weights: {weights}")
    stage = "smoke"
    event = _record_hardware(run_dir, state, device, stage)
    checkpoint_dir = run_dir / "checkpoints"
    last = checkpoint_dir / stage / "weights" / "last.pt"
    state["smoke"] = {"status": "running", "hardware_event": event["event_number"]}
    state["status"] = "smoke_running"
    _save_state(run_dir, state)
    output = train_stage(
        weights=last if last.is_file() else weights,
        data_yaml=data_yaml, checkpoints_dir=checkpoint_dir,
        logs_dir=run_dir / "logs", stage_name=stage,
        imgsz=config["smoke"]["imgsz"], epochs=config["smoke"]["epochs"],
        config=config, device=device, resume=last.is_file(),
    )
    completed = _csv_epochs(output / "results.csv")
    if completed < config["smoke"]["epochs"]:
        state["smoke"] = {"status": "failed", "completed_epochs": completed,
                          "hardware_event": event["event_number"]}
        state["status"] = "smoke_failed"
        _save_state(run_dir, state)
        raise RuntimeError(
            f"Smoke gate recorded {completed} epoch rows in {output / 'results.csv'}; "
            f"expected {config['smoke']['epochs']}. Not marking the smoke test as passed."
        )
    state["smoke"] = {
        "status": "passed", "completed_epochs": completed,
        "result_dir": output.relative_to(run_dir).as_posix(),
        "hardware_event": event["event_number"],
    }
    state["status"] = "smoke_passed"
    _save_state(run_dir, state)
    print(f"Smoke passed for {run_id}.")


def _csv_epochs(path: Path) -> int:
    """Return the count of epoch rows in a run's results.csv."""
    import csv

    if not path.is_file():
        return 0
    with path.open(newline="", encoding="utf-8-sig") as source:
        return sum(1 for row in csv.DictReader(source) if row.get("epoch"))


def _finalize_run(
    run_id: str, run_dir: Path, state: dict[str, Any], config: dict[str, Any],
    selected: dict[str, Any], candidates: list[dict[str, Any]],
    test_metrics: dict[str, float], test_dir: Path,
) -> None:
    """Persist final checkpoint, review plots, metrics, and completed manifest."""
    checkpoint = run_dir / selected["best_checkpoint"]
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Selected model checkpoint not found: {checkpoint}")
    final_dir = run_dir / "checkpoints" / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checkpoint, final_dir / "best.pt")
    copy_review_plots(run_dir / selected["result_dir"], final_dir)
    copy_review_plots(test_dir, final_dir)
    summary = {
        "run_id": run_id, "run_number": state["run_number"],
        "dataset_fingerprint": state["dataset_fingerprint"],
        "selection_metric": config["selection_metric"], "candidates": candidates,
        "selected_candidate": selected, "test_split": config["test_split"],
        "test_metrics": test_metrics, "checkpoint": "checkpoints/final/best.pt",
        "test_evaluations": 1, "hardware_history": state["hardware_history"],
    }
    write_json(final_dir / "training_results.json", summary)
    state["test"] = {"status": "complete", "metrics": test_metrics,
                     "hardware_event": state.get("test", {}).get("hardware_event")}
    state["status"] = "complete"
    _save_state(run_dir, state)
    print(json.dumps(summary, indent=2))


def _run_full(
    run_id: str, run_dir: Path, state: dict[str, Any], config: dict[str, Any],
    data_yaml: Path, device: str,
) -> None:
    """Continue unfinished stages, select on validation, and test once."""
    if state.get("smoke", {}).get("status") != "passed":
        raise ValueError("Smoke must pass before full training can continue.")
    if state.get("test", {}).get("status") == "complete":
        print(f"Run {run_id} is already complete.")
        return
    checkpoint_dir = run_dir / "checkpoints"
    test_marker = checkpoint_dir / "heldout_test" / "test_metrics.json"
    if state.get("test", {}).get("status") == "started":
        if not test_marker.is_file():
            raise ValueError(
                "The held-out test started but did not save its completion marker. "
                "Inspect the heldout_test output before deciding whether to evaluate again."
            )
        recovered = json.loads(test_marker.read_text(encoding="utf-8"))
        selected = state["selected_candidate"]
        candidates = [row for row in state["stages"].values() if row.get("status") == "complete"]
        _finalize_run(
            run_id, run_dir, state, config, selected, candidates,
            recovered["metrics"], test_marker.parent,
        )
        return
    stages = config["stages"]
    candidates: list[dict[str, Any]] = []

    for stage in stages[:3]:
        name = stage["name"]
        result_dir = checkpoint_dir / name
        existing = state.get("stages", {}).get(name)
        if existing and existing.get("status") == "complete":
            candidates.append(existing)
            continue
        weights = ROOT / config["models_dir"] / stage["model"]
        if not weights.is_file():
            raise FileNotFoundError(f"Missing pretrained weights: {weights}")
        last = result_dir / "weights" / "last.pt"
        best = result_dir / "weights" / "best.pt"
        # A crash after the final epoch but before manifest update can be
        # recovered from the completed CSV and best checkpoint without retraining.
        if best.is_file() and _csv_epochs(result_dir / "results.csv") >= stage["epochs"]:
            trained_dir = result_dir
            hardware_event = None
        else:
            event = _record_hardware(run_dir, state, device, name)
            trained_dir = train_stage(
                weights=last if last.is_file() else weights,
                data_yaml=data_yaml, checkpoints_dir=checkpoint_dir,
                logs_dir=run_dir / "logs", stage_name=name, imgsz=stage["imgsz"],
                epochs=stage["epochs"], config=config, device=device,
                resume=last.is_file(),
            )
            hardware_event = event["event_number"]
        candidate = {
            "stage": name, "status": "complete", "imgsz": stage["imgsz"],
            "model": stage["model"],
            "validation_mAP50": validation_map50(trained_dir, config["selection_metric"]),
            "result_dir": trained_dir.relative_to(run_dir).as_posix(),
            "best_checkpoint": (trained_dir / "weights" / "best.pt").relative_to(run_dir).as_posix(),
            "hardware_event": hardware_event,
        }
        state.setdefault("stages", {})[name] = candidate
        state["status"] = f"stage_complete:{name}"
        _save_state(run_dir, state)
        candidates.append(candidate)

    best_n = max(candidates, key=lambda item: item["validation_mAP50"])
    if len(stages) > 3:
        stage = stages[3]
        name = stage["name"]
        existing = state.get("stages", {}).get(name)
        if existing and existing.get("status") == "complete":
            best_s = existing
        else:
            weights = ROOT / config["models_dir"] / stage["model"]
            if not weights.is_file():
                raise FileNotFoundError(f"Missing pretrained weights: {weights}")
            result_dir = checkpoint_dir / name
            last = result_dir / "weights" / "last.pt"
            best = result_dir / "weights" / "best.pt"
            if best.is_file() and _csv_epochs(result_dir / "results.csv") >= stage["epochs"]:
                trained_dir = result_dir
                hardware_event = None
            else:
                event = _record_hardware(run_dir, state, device, name)
                trained_dir = train_stage(
                    weights=last if last.is_file() else weights,
                    data_yaml=data_yaml, checkpoints_dir=checkpoint_dir,
                    logs_dir=run_dir / "logs", stage_name=name, imgsz=best_n["imgsz"],
                    epochs=stage["epochs"], config=config, device=device,
                    resume=last.is_file(),
                )
                hardware_event = event["event_number"]
            best_s = {
                "stage": name, "status": "complete", "imgsz": best_n["imgsz"],
                "model": stage["model"],
                "validation_mAP50": validation_map50(trained_dir, config["selection_metric"]),
                "result_dir": trained_dir.relative_to(run_dir).as_posix(),
                "best_checkpoint": (trained_dir / "weights" / "best.pt").relative_to(run_dir).as_posix(),
                "hardware_event": hardware_event,
            }
            state.setdefault("stages", {})[name] = best_s
            state["status"] = f"stage_complete:{name}"
            _save_state(run_dir, state)
        candidates.append(best_s)

    selected = max(candidates, key=lambda item: item["validation_mAP50"])
    checkpoint = run_dir / selected["best_checkpoint"]
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Selected model checkpoint not found: {checkpoint}")
    event = _record_hardware(run_dir, state, device, "heldout_test")
    state["test"] = {"status": "started", "hardware_event": event["event_number"]}
    state["selected_candidate"] = selected
    state["status"] = "test_started"
    _save_state(run_dir, state)
    test_metrics, test_dir = evaluate_test(
        checkpoint, data_yaml=data_yaml, checkpoints_dir=checkpoint_dir,
        imgsz=selected["imgsz"], device=device, test_split=config["test_split"],
    )
    write_json(test_dir / "test_metrics.json", {"metrics": test_metrics})
    state["test"]["hardware_event"] = event["event_number"]
    _finalize_run(run_id, run_dir, state, config, selected, candidates, test_metrics, test_dir)


def _run_command(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """Run smoke/full directly or execute/resume the entire pipeline in one call."""
    dataset_dir = args.dataset or (ROOT / config["dataset"])
    dataset_yaml, fingerprint = prepare_dataset(dataset_dir.resolve(), config["test_split"])
    continue_current = args.command in {"start", "continue", "full"}
    results_dir = (ROOT / config["results_dir"]).resolve()
    current_run = get_current_run(results_dir)
    if args.command == "full" and not args.run_id:
        if not current_run:
            raise FileNotFoundError("Run start or smoke first, then continue with full.")
        args.run_id = current_run
    if args.command == "continue" and not args.run_id:
        if not current_run:
            raise FileNotFoundError("There is no active run to continue; use start.")
        if load_run(results_dir, current_run).get("status") == "complete":
            raise ValueError("The active run is complete; use start to create the next run.")
    run_id, run_dir, state = _select_or_create_run(
        config, dataset_dir, fingerprint, args.run_id, continue_current=continue_current,
        config_path=args.config,
    )
    print(f"Run {state['run_number']:04d} ({run_id}); results: {run_dir}")
    if args.command == "smoke":
        _run_smoke(run_id, run_dir, state, config, dataset_yaml, args.device)
        return 0
    if args.command in {"start", "continue"} and state.get("smoke", {}).get("status") != "passed":
        _run_smoke(run_id, run_dir, state, config, dataset_yaml, args.device)
    state = load_run((ROOT / config["results_dir"]).resolve(), run_id)
    if args.command in {"full", "start", "continue"}:
        _run_full(run_id, run_dir, state, config, dataset_yaml, args.device)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser shared by Python and operating-system launchers."""
    parser = argparse.ArgumentParser(description="Numbered, resumable KilnWatch OBB training")
    parser.add_argument(
        "command", nargs="?", choices=("start", "continue", "smoke", "full"),
        default="start",
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config/training.yaml")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--run-id", help="Continue a specific run such as run_0001")
    parser.add_argument("--device", default="0", help="CUDA device index (default 0) or cpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Resolve project-relative paths and run the explicitly requested command."""
    os.chdir(ROOT)
    args = build_parser().parse_args(argv)
    config = read_training_config(args.config)
    if args.dataset is not None and not args.dataset.is_absolute():
        args.dataset = ROOT / args.dataset
    return _run_command(args, config)


if __name__ == "__main__":
    sys.exit(main())
