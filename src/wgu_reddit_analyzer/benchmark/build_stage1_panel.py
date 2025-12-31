from __future__ import annotations

"""
Build a unified Stage 1 post-level analysis panel.

The panel joins:
    - post text (from DEV/TEST_candidates.jsonl)
    - gold labels (from gold_labels.csv)
    - model predictions (from run predictions CSVs)
    - run metadata (from stage1_run_index.csv)

The result is a long-form CSV with one row per (post, run), suitable
for FP/FN analysis, per-course breakdowns, and model/prompt comparison.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Iterable


RUN_INDEX_CSV = Path("artifacts/benchmark/stage1_run_index.csv")
GOLD_LABELS_CSV = Path("artifacts/benchmark/gold/gold_labels.csv")
DEV_CANDIDATES = Path("artifacts/benchmark/DEV_candidates.jsonl")
TEST_CANDIDATES = Path("artifacts/benchmark/TEST_candidates.jsonl")


def load_run_index(split: str, models: List[str] | None, prompts: List[str] | None) -> List[Dict[str, Any]]:
    """
    Load run index entries for the given split, filtered by models and prompts if provided.
    """
    rows: List[Dict[str, Any]] = []
    if not RUN_INDEX_CSV.is_file():
        raise FileNotFoundError(f"Run index not found at {RUN_INDEX_CSV}")

    with RUN_INDEX_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") != split:
                continue
            if models and row.get("model_name") not in models:
                continue
            if prompts and row.get("prompt") not in prompts and row.get("prompt_name") not in prompts:
                continue
            rows.append(row)

    if not rows:
        raise RuntimeError(f"No runs found in {RUN_INDEX_CSV} for split={split} with given filters.")

    return rows


def load_gold_labels_full(split: str) -> Dict[str, Dict[str, Any]]:
    """
    Load full gold labels for a split keyed by post_id.
    """
    gold: Dict[str, Dict[str, Any]] = {}
    if not GOLD_LABELS_CSV.is_file():
        raise FileNotFoundError(f"Gold labels not found at {GOLD_LABELS_CSV}")

    with GOLD_LABELS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") != split:
                continue

            pid = row["post_id"]
            gold[pid] = {
                "split": row.get("split"),
                "course_code": row.get("course_code") or "",
                "gold_contains_painpoint": (row.get("contains_painpoint") or "").strip().lower(),
                "gold_root_cause_summary": row.get("root_cause_summary") or "",
                "gold_ambiguity_flag": row.get("ambiguity_flag") or "",
                "gold_labeler_id": row.get("labeler_id") or "",
                "gold_notes": row.get("notes") or "",
            }

    if not gold:
        raise RuntimeError(f"No gold labels found in {GOLD_LABELS_CSV} for split={split}")

    return gold


def load_posts(split: str) -> Dict[str, Dict[str, Any]]:
    """
    Load candidate post text for a split keyed by post_id.
    """
    if split == "DEV":
        path = DEV_CANDIDATES
    else:
        path = TEST_CANDIDATES

    if not path.is_file():
        raise FileNotFoundError(f"Candidates file not found at {path}")

    posts: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            pid = obj["post_id"]
            title = obj.get("title") or ""
            selftext = obj.get("selftext") or ""
            course_code = obj.get("course_code") or ""

            if selftext:
                combined = f"{title}\n\n{selftext}" if title else selftext
            else:
                combined = title

            posts[pid] = {
                "course_code": course_code,
                "post_title": title,
                "post_selftext": selftext,
                "combined_text": combined,
            }

    if not posts:
        raise RuntimeError(f"No posts loaded from {path}")

    return posts


def load_predictions_for_run(run_row: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """
    Load predictions CSV for a single run from the path in the run index row.
    """
    predictions_path = Path(run_row["predictions_path"])
    if not predictions_path.is_file():
        raise FileNotFoundError(f"Predictions file not found at {predictions_path}")

    with predictions_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {
                "post_id": row["post_id"],
                "course_code_pred": row.get("course_code") or "",
                "true_contains_painpoint": (row.get("true_contains_painpoint") or "").strip().lower(),
                "pred_contains_painpoint": (row.get("pred_contains_painpoint") or "").strip().lower(),
                "root_cause_summary_pred": row.get("root_cause_summary_pred") or "",
                "pain_point_snippet_pred": row.get("pain_point_snippet_pred") or "",
                "confidence_pred": row.get("confidence_pred") or "",
                "parse_error": row.get("parse_error", "False"),
                "schema_error": row.get("schema_error", "False"),
                "used_fallback": row.get("used_fallback", "False"),
                "llm_failure": row.get("llm_failure", "False"),
            }


def bool_from_str(val: str | bool) -> bool:
    """
    Normalize various string representations of boolean values.
    """
    if isinstance(val, bool):
        return val
    v = (val or "").strip().lower()
    return v in {"1", "true", "t", "yes", "y"}


def compute_error_type(gold_label: str, pred_label: str) -> str:
    """
    Compute error type for a single prediction.
    """
    if gold_label not in {"y", "n"}:
        return "unknown"

    if gold_label == "y":
        if pred_label == "y":
            return "tp"
        else:
            return "fn"

    if pred_label == "y":
        return "fp"
    else:
        return "tn"


def build_panel(
    split: str,
    run_index_rows: List[Dict[str, Any]],
    gold: Dict[str, Dict[str, Any]],
    posts: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build the panel rows by joining runs with gold labels and post text.
    """
    panel: List[Dict[str, Any]] = []

    for run_row in run_index_rows:
        model_name = run_row["model_name"]
        provider = run_row["provider"]
        prompt_name = run_row.get("prompt_name") or run_row.get("prompt") or ""
        run_slug = run_row.get("run_slug", "")
        run_dir = run_row["run_dir"]
        started_at = run_row.get("started_at_epoch", "")
        finished_at = run_row.get("finished_at_epoch", "")
        avg_sec = run_row.get("avg_elapsed_sec_per_example", "")
        total_cost = run_row.get("total_cost_usd", "")

        for pred_row in load_predictions_for_run(run_row):
            pid = pred_row["post_id"]

            if pid not in gold:
                raise RuntimeError(f"Prediction post_id {pid} has no gold label (split={split}).")

            if pid not in posts:
                raise RuntimeError(f"Prediction post_id {pid} has no post text in candidates (split={split}).")

            gold_row = gold[pid]
            post_row = posts[pid]

            gold_label = gold_row["gold_contains_painpoint"]
            pred_label = pred_row["pred_contains_painpoint"]

            error_type = compute_error_type(gold_label, pred_label)
            is_correct = (
                gold_label in {"y", "n"} and pred_label in {"y", "n"} and gold_label == pred_label
            )

            panel.append(
                {
                    "split": split,
                    "post_id": pid,
                    "course_code": gold_row.get("course_code") or post_row.get("course_code") or "",
                    "model_name": model_name,
                    "provider": provider,
                    "prompt": prompt_name,
                    "run_slug": run_slug,
                    "run_dir": run_dir,
                    "post_title": post_row.get("post_title", ""),
                    "post_selftext": post_row.get("post_selftext", ""),
                    "combined_text": post_row.get("combined_text", ""),
                    "gold_contains_painpoint": gold_label,
                    "gold_root_cause_summary": gold_row.get("gold_root_cause_summary", ""),
                    "gold_ambiguity_flag": gold_row.get("gold_ambiguity_flag", ""),
                    "gold_labeler_id": gold_row.get("gold_labeler_id", ""),
                    "gold_notes": gold_row.get("gold_notes", ""),
                    "true_contains_painpoint": pred_row["true_contains_painpoint"],
                    "pred_contains_painpoint": pred_label,
                    "root_cause_summary_pred": pred_row["root_cause_summary_pred"],
                    "pain_point_snippet_pred": pred_row["pain_point_snippet_pred"],
                    "confidence_pred": pred_row["confidence_pred"],
                    "parse_error": bool_from_str(pred_row["parse_error"]),
                    "schema_error": bool_from_str(pred_row["schema_error"]),
                    "used_fallback": bool_from_str(pred_row["used_fallback"]),
                    "llm_failure": bool_from_str(pred_row["llm_failure"]),
                    "is_correct": is_correct,
                    "error_type": error_type,
                    "run_started_at_epoch": started_at,
                    "run_finished_at_epoch": finished_at,
                    "avg_elapsed_sec_per_example": avg_sec,
                    "total_cost_usd": total_cost,
                }
            )

    return panel


def write_panel_csv(panel_rows: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write the panel rows to a CSV file.
    """
    if not panel_rows:
        raise RuntimeError("No panel rows to write.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(panel_rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(panel_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Stage 1 post-level panel for a split."
    )
    parser.add_argument(
        "--split",
        default="DEV",
        choices=["DEV", "TEST"],
        help="Data split to build panel for.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. Default: artifacts/benchmark/stage1_panel_<split>.csv",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Optional list of model names to include (default: all in run index).",
    )
    parser.add_argument(
        "--prompts",
        nargs="*",
        default=None,
        help="Optional list of prompt filenames to include (e.g. s1_zero.txt). Default: all.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    split = args.split
    output = (
        Path(args.output)
        if args.output
        else Path(f"artifacts/benchmark/stage1_panel_{split}.csv")
    )

    run_rows = load_run_index(split=split, models=args.models, prompts=args.prompts)
    gold = load_gold_labels_full(split=split)
    posts = load_posts(split=split)

    panel = build_panel(split=split, run_index_rows=run_rows, gold=gold, posts=posts)
    write_panel_csv(panel, output)

    print(f"Wrote {len(panel)} panel rows to {output}")


if __name__ == "__main__":
    main()