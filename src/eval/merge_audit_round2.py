"""Merge the separate Round 2 labels and confidence key for precision analysis.

Input CSV schemas
-----------------
Labels: a shared ``kiln_id`` column and a human ``label`` column containing
TP, FP, or SKIP.
Key: a shared ``kiln_id`` column and a numeric ``confidence`` column. Other
key columns are allowed and ignored.

Output schemas
--------------
The merged CSV contains exactly ``kiln_id``, ``confidence``, and ``label``.
The Markdown summary reports Wilson 95% precision intervals overall and for
confidence terciles. SKIP labels are excluded from precision denominators.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.eval.audit_sample import _wilson_interval


def merge_audit_round2(
    labels_path: Path,
    key_path: Path,
    output_csv: Path = Path("data/processed/audit_round2_merged.csv"),
    summary_path: Path = Path("docs/AUDIT_ROUND2_SUMMARY.md"),
) -> dict[str, object]:
    """Join Round 2 human labels to confidence, calculate Wilson summaries.

    Parameters
    ----------
    labels_path:
        CSV containing ``kiln_id`` and ``label``.
    key_path:
        CSV containing ``kiln_id`` and ``confidence``.
    output_csv:
        Destination for the three-column merged CSV.
    summary_path:
        Destination for the Markdown precision summary.

    Returns
    -------
    dict[str, object]
        Counts and precision estimates, including Wilson confidence bounds.
    """
    labels = pd.read_csv(labels_path, dtype={"kiln_id": "string"})
    key = pd.read_csv(key_path, dtype={"kiln_id": "string"})
    _require_columns(labels, {"kiln_id", "label"}, labels_path)
    _require_columns(key, {"kiln_id", "confidence"}, key_path)
    if labels["kiln_id"].isna().any() or key["kiln_id"].isna().any():
        raise ValueError("kiln_id cannot be blank in either Round 2 CSV")
    if labels["kiln_id"].duplicated().any():
        raise ValueError(f"Duplicate kiln_id values in labels file: {labels_path}")
    if key["kiln_id"].duplicated().any():
        raise ValueError(f"Duplicate kiln_id values in key file: {key_path}")

    label_ids = set(labels["kiln_id"])
    key_ids = set(key["kiln_id"])
    missing_key = sorted(label_ids - key_ids)
    extra_key = sorted(key_ids - label_ids)
    if missing_key or extra_key:
        raise ValueError(
            "Labels/key kiln_id values do not match; "
            f"missing in key={missing_key}, extra in key={extra_key}"
        )

    merged = labels[["kiln_id", "label"]].merge(
        key[["kiln_id", "confidence"]], on="kiln_id", how="inner", validate="one_to_one"
    )[["kiln_id", "confidence", "label"]]
    merged["confidence"] = pd.to_numeric(merged["confidence"], errors="raise")
    if merged["confidence"].isna().any() or not merged["confidence"].between(0, 1).all():
        raise ValueError("confidence values must be numeric values from 0 through 1")

    label_values = merged["label"].astype("string").str.strip().str.upper()
    if label_values.isna().any() or not label_values.isin({"TP", "FP", "SKIP"}).all():
        invalid = sorted(label_values[~label_values.isin({"TP", "FP", "SKIP"})].dropna().unique())
        raise ValueError(f"Expected labels TP, FP, or SKIP; found invalid values: {invalid}")
    merged["label"] = label_values
    # Mirror audit-results: assign equal-count confidence groups using qcut.
    merged["_tercile"] = pd.qcut(
        merged["confidence"], q=3, labels=["low", "mid", "high"], duplicates="drop"
    )

    def summarize(rows: pd.DataFrame) -> dict[str, int | float]:
        decided = rows[rows["label"].isin({"TP", "FP"})]
        total = len(decided)
        true_positives = int(decided["label"].eq("TP").sum())
        lower, upper = _wilson_interval(true_positives, total)
        return {
            "true_positives": true_positives,
            "n": total,
            "skips": int(rows["label"].eq("SKIP").sum()),
            "precision": true_positives / total if total else 0.0,
            "ci_95_lower": lower,
            "ci_95_upper": upper,
        }

    results: dict[str, object] = {
        "n_rows": len(merged),
        "by_tercile": {
            band: summarize(merged[merged["_tercile"] == band])
            for band in ("low", "mid", "high")
        },
        "overall": summarize(merged),
    }
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    merged[["kiln_id", "confidence", "label"]].to_csv(output_csv, index=False)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_summary_markdown(results, labels_path, key_path), encoding="utf-8")
    _print_results(results, output_csv, summary_path)
    return results


def _require_columns(frame: pd.DataFrame, expected: set[str], source: Path) -> None:
    """Raise a useful schema error when required CSV columns are absent."""
    missing = expected - set(frame.columns)
    if missing:
        raise ValueError(f"{source} is missing required column(s): {', '.join(sorted(missing))}")


def _summary_markdown(results: dict[str, object], labels: Path, key: Path) -> str:
    """Render the precision results and input provenance as Markdown."""
    rows = [
        "# Round 2 audit summary",
        "",
        f"Labels: `{labels}`  ",
        f"Confidence key: `{key}`",
        "",
        "Precision is TP / (TP + FP); SKIP labels are excluded. Intervals are 95% Wilson.",
        "Confidence terciles use equal-count quantiles computed from the merged confidence values.",
        "This is a 20-row targeted review and is descriptive, not a representative district-wide estimate.",
        "",
        "| Confidence group | TP / decided | SKIP | Precision | 95% Wilson CI |",
        "|---|---:|---:|---:|---:|",
    ]
    summaries = results["by_tercile"]
    assert isinstance(summaries, dict)
    for band in ("low", "mid", "high"):
        item = summaries[band]
        rows.append(_markdown_row(band, item))
    overall = results["overall"]
    assert isinstance(overall, dict)
    rows.extend([_markdown_row("Overall", overall), "", f"Rows merged: {results['n_rows']}.", ""])
    return "\n".join(rows)


def _markdown_row(name: str, summary: dict[str, int | float]) -> str:
    """Render one tercile or overall summary row."""
    return (
        f"| {name} | {summary['true_positives']} / {summary['n']} | {summary['skips']} | "
        f"{summary['precision']:.1%} | "
        f"{summary['ci_95_lower']:.1%}-{summary['ci_95_upper']:.1%} |"
    )


def _print_results(
    results: dict[str, object], output_csv: Path, summary_path: Path
) -> None:
    """Print merged paths and precision results for the CLI user."""
    print(f"Merged CSV written to {output_csv}")
    print(f"Summary written to {summary_path}")
    print("Confidence group | TP / decided | SKIP | Precision (95% Wilson CI)")
    summaries = results["by_tercile"]
    assert isinstance(summaries, dict)
    for band in ("low", "mid", "high"):
        _print_summary(band, summaries[band])
    overall = results["overall"]
    assert isinstance(overall, dict)
    _print_summary("Overall", overall)


def _print_summary(name: str, summary: dict[str, int | float]) -> None:
    """Print one precision summary line."""
    print(
        f"{name} | {summary['true_positives']} / {summary['n']} | {summary['skips']} | "
        f"{summary['precision']:.1%} ({summary['ci_95_lower']:.1%}-"
        f"{summary['ci_95_upper']:.1%})"
    )
