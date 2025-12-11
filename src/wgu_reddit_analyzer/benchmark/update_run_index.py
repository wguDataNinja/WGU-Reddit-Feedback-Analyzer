"""
Append Stage 1 benchmark run summaries to a Markdown index document.

This tool reads manifest.json and metrics.json for selected runs,
extracts key fields, formats them into a Markdown table block,
and appends that block to the run index file.

This enables reproducible, consistent documentation for each
benchmark run without manual editing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    """
    Load manifest.json from a run directory.
    """
    manifest_path = run_dir / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_metrics(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load metrics JSON file referenced by the manifest.
    """
    metrics_path = Path(manifest["metrics_path"])
    with metrics_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def format_run_block(run_label: str, rows: List[Dict[str, Any]]) -> str:
    """
    Create a Markdown block summarizing all runs under one label.
    """
    lines = []
    lines.append(f"## {run_label}")
    lines.append("")
    lines.append(
        "| model | provider | split | prompt | num_examples | tp | fp | fn | tn | precision | recall | f1 | accuracy | run_dir |"
    )
    lines.append(
        "|-------|----------|-------|--------|--------------|----|----|----|----|-----------|--------|----|----------|---------|"
    )

    for row in rows:
        lines.append(
            "| {model_name} | {provider} | {split} | {prompt_filename} | {num_examples} | "
            "{tp} | {fp} | {fn} | {tn} | {precision:.3f} | {recall:.3f} | {f1:.3f} | "
            "{accuracy:.3f} | {run_dir} |".format(**row)
        )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """
    Scan selected run directories, extract manifest and metrics for each,
    build a Markdown summary block, and append it to the run index file.

    Typical usage:
        python -m wgu_reddit_analyzer.benchmark.update_run_index \
            --runs-dir artifacts/benchmark/stage1/runs \
            --glob "*_DEV_20251119_*" \
            --index docs/benchmark/run_index_25dev.md \
            --run-label run02_fewshot_v1_25dev
    """
    parser = argparse.ArgumentParser(description="Append run summaries to a Markdown run index.")
    parser.add_argument("--runs-dir", required=True, help="Directory containing run subdirectories.")
    parser.add_argument("--glob", default="*_DEV_*", help="Glob pattern to select run dirs.")
    parser.add_argument("--index", required=True, help="Path to run index markdown file.")
    parser.add_argument("--run-label", required=True, help="Label to group these runs.")
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    index_path = Path(args.index)
    run_dirs = sorted(d for d in runs_dir.glob(args.glob) if d.is_dir())

    if not run_dirs:
        raise SystemExit(f"No run directories matched {args.glob} under {runs_dir}")

    rows: List[Dict[str, Any]] = []

    for rd in run_dirs:
        manifest = load_manifest(rd)
        metrics = load_metrics(manifest)

        rows.append(
            {
                "model_name": manifest["model_name"],
                "provider": manifest["provider"],
                "split": manifest["split"],
                "prompt_filename": manifest.get("prompt_filename", ""),
                "num_examples": metrics["num_examples"],
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "tn": metrics["tn"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "accuracy": metrics["accuracy"],
                "run_dir": manifest["run_dir"],
            }
        )

    block = format_run_block(args.run_label, rows)

    if index_path.exists():
        existing = index_path.read_text(encoding="utf-8")
        new_text = existing.rstrip() + "\n\n" + block + "\n"
    else:
        new_text = block + "\n"

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(new_text, encoding="utf-8")
    print(f"Appended {len(rows)} rows to {index_path} under {args.run_label}")


if __name__ == "__main__":
    main()