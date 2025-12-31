"""
Collect false positives from multiple Stage 1 benchmark runs.

This module scans run directories, reads each run's predictions CSV,
identifies posts where the model predicted a positive label but the
gold label is negative, and writes all such rows into a single CSV.

This tool is useful for comparing error patterns across models and
prompt variants. It is typically run once after a complete batch
of runs is finished.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict


def collect_false_positives(run_dirs: List[Path], out_path: Path) -> int:
    """
    Collect false positives from a list of run directories.

    A false positive is defined as:
        true_contains_painpoint = "n"
        pred_contains_painpoint = "y"

    Each run directory must contain:
        predictions_<split>.csv
        manifest.json

    Parameters
    ----------
    run_dirs : list of Path
        Run directories to inspect.
    out_path : Path
        Output CSV file where FP rows are written.

    Returns
    -------
    int
        Number of false positive rows written.
    """
    fp_rows: List[Dict] = []

    for rd in run_dirs:
        manifest_path = rd / "manifest.json"
        if not manifest_path.is_file():
            continue

        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)

        pred_path = Path(manifest["predictions_path"])
        if not pred_path.is_file():
            continue

        with pred_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                true_l = row["true_contains_painpoint"].lower()
                pred_l = row["pred_contains_painpoint"].lower()
                if true_l == "n" and pred_l == "y":
                    row_out = dict(row)
                    row_out["model_name"] = manifest["model_name"]
                    row_out["provider"] = manifest["provider"]
                    row_out["run_dir"] = manifest["run_dir"]
                    fp_rows.append(row_out)

    if fp_rows:
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fp_rows[0].keys())
            writer.writeheader()
            writer.writerows(fp_rows)

    return len(fp_rows)


def main() -> None:
    """
    Entry point for the command-line tool.

    Reads arguments for runs directory, filename glob, and output path,
    collects false positives from matching run directories, and writes
    the combined results to a CSV file.
    """
    parser = argparse.ArgumentParser(description="Collect all false positives from Stage 1 runs.")
    parser.add_argument("--runs-dir", required=True, help="Directory containing run subdirectories.")
    parser.add_argument("--glob", default="*_DEV_*", help="Glob pattern to select run dirs.")
    parser.add_argument("--out", required=True, help="Path to output CSV.")
    args = parser.parse_args()

    run_dirs = sorted(Path(args.runs_dir).glob(args.glob))
    out_path = Path(args.out)

    n = collect_false_positives(run_dirs, out_path)
    print(f"Wrote {n} FP rows to {out_path}")


if __name__ == "__main__":
    main()