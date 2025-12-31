from __future__ import annotations

"""
Stage 3 global cluster validation runner.

This script selects a Stage 3 run directory containing fully
processed global clusters and validates them using
`validate_global_clusters`.

Inputs:
    - global_clusters.json
    - cluster_global_index.csv

Outputs:
    - Validation messages and errors (if any) printed to console.

Behavior:
    - Fully deterministic, artifact-only.
    - No LLM calls, no randomness, no thresholds.
    - If --run-dir is not provided, the latest valid run under
      artifacts/stage3/runs is automatically selected.
"""

import argparse
from pathlib import Path
from typing import Optional

from wgu_reddit_analyzer.stage3.validate_global_clusters import validate_global_clusters


def _latest_run_with_required_files(runs_dir: Path) -> Path:
    if not runs_dir.exists():
        raise FileNotFoundError(f"Stage 3 runs dir not found: {runs_dir}")

    # newest first
    for d in sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True):
        if (d / "global_clusters.json").is_file() and (d / "cluster_global_index.csv").is_file():
            return d

    raise FileNotFoundError(f"No Stage 3 run dir contains global_clusters.json and cluster_global_index.csv under {runs_dir}")


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Stage 3: artifact-only global cluster validation entrypoint.")
    p.add_argument("--run-dir", type=str, default="", help="Stage 3 run directory. If omitted, selects latest valid run.")
    p.add_argument("--runs-dir", type=str, default="artifacts/stage3/runs", help="Directory containing Stage 3 run dirs.")
    args = p.parse_args(argv)

    run_dir = Path(args.run_dir) if args.run_dir else _latest_run_with_required_files(Path(args.runs_dir))
    validate_global_clusters(run_dir=run_dir)


if __name__ == "__main__":
    main()