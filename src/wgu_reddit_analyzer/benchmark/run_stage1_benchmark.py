"""
Stage 1 Benchmark Runner

Runs the Stage 1 LLM classifier against gold labels using a fixed,
deterministic subset (via --limit) or the full DEV/TEST split.
Writes predictions, metrics, manifest, and raw IO logs into a
timestamped run directory. Used for prompt iteration, model comparison,
and final benchmark runs.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any

from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.stage1_types import (
    Stage1PredictionInput,
    Stage1PredictionOutput,
    LlmCallResult,
)
from wgu_reddit_analyzer.benchmark.stage1_classifier import classify_post, build_prompt
from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION

logger = get_logger(__name__)

# Global run index CSV (one row per run, auto-appended after every run)
RUN_INDEX_CSV = Path("artifacts/benchmark/stage1_run_index.csv")


def load_prompt(prompt_path: Path) -> str:
    """Load the prompt template text from disk."""
    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()


def load_gold_labels(gold_path: Path, split: str) -> Dict[str, Dict]:
    """
    Returns mapping: post_id -> {"true_contains_painpoint": "y"/"n", "course_code": str}

    Only includes rows where:
      - split matches
      - contains_painpoint in {"y", "n"}
    """
    labels: Dict[str, Dict] = {}
    with gold_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") != split:
                continue

            cp = (row.get("contains_painpoint") or "").strip().lower()
            if cp not in {"y", "n"}:
                continue

            post_id = row["post_id"]
            labels[post_id] = {
                "true_contains_painpoint": cp,
                "course_code": row.get("course_code") or "",
            }

    if not labels:
        raise RuntimeError(f"No eligible gold labels found in {gold_path} for split={split}")

    logger.info("Loaded %d gold labels for split %s", len(labels), split)
    return labels


def load_candidates(candidates_path: Path) -> Dict[str, Stage1PredictionInput]:
    """
    Reads DEV/TEST_candidates.jsonl and returns mapping:
      post_id -> Stage1PredictionInput
    """
    import json as _json

    candidates: Dict[str, Stage1PredictionInput] = {}
    with candidates_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = _json.loads(line)
            post_id = obj["post_id"]
            course_code = obj.get("course_code") or ""
            title = obj.get("title") or ""
            selftext = obj.get("selftext") or ""
            if selftext:
                text = f"{title}\n\n{selftext}" if title else selftext
            else:
                text = title

            candidates[post_id] = Stage1PredictionInput(
                post_id=post_id,
                course_code=course_code,
                text=text,
            )

    if not candidates:
        raise RuntimeError(f"No candidates loaded from {candidates_path}")

    logger.info("Loaded %d candidate posts from %s", len(candidates), candidates_path)
    return candidates


def compute_metrics(
    gold_and_preds: List[Tuple[str, str]]
) -> Dict[str, float]:
    """
    Compute Stage 1 classification metrics.

    gold_and_preds: list of (true, pred) with true in {"y","n"}, pred in {"y","n","u"}.
    "u" is treated as "not predicted positive":
        - if true == "y" and pred != "y": FN
        - if true == "n" and pred != "y": TN
    """
    tp = fp = fn = tn = 0

    for true_label, pred_label in gold_and_preds:
        if true_label == "y":
            if pred_label == "y":
                tp += 1
            else:
                fn += 1
        else:
            if pred_label == "y":
                fp += 1
            else:
                tn += 1

    total = tp + fp + fn + tn

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "num_examples": total,
    }


def ensure_run_dir(run_slug: str) -> Path:
    """
    Create a new run directory for this benchmark.

    The directory name includes the run slug and a timestamp to keep
    artifacts self-contained and reproducible.
    """
    from datetime import datetime

    base = Path("artifacts/benchmark/stage1/runs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base / f"{run_slug}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def append_run_index_row(index_path: Path, row: Dict[str, object]) -> None:
    """
    Append a single row to the global Stage 1 run index CSV.

    Creates the file and header if it does not exist. If a row for the
    same run_dir already exists, it is not duplicated. When new columns
    are added, the entire file is rewritten with a unified header.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "run_slug",
        "model_name",
        "provider",
        "split",
        "prompt_name",
        "prompt",
        "num_examples",
        "tp",
        "fp",
        "fn",
        "tn",
        "precision",
        "recall",
        "f1",
        "accuracy",
        "total_cost_usd",
        "avg_elapsed_sec_per_example",
        "num_parse_errors",
        "num_schema_errors",
        "num_llm_failures",
        "num_fallbacks",
        "is_official",
        "run_tag",
        "run_dir",
        "metrics_path",
        "predictions_path",
        "started_at_epoch",
        "finished_at_epoch",
    ]

    existing_rows: List[Dict[str, Any]] = []
    existing_run_dirs: set[str] = set()

    if index_path.is_file():
        with index_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                existing_rows.append(r)
                existing_run_dirs.add(r.get("run_dir"))

    if str(row["run_dir"]) in existing_run_dirs:
        return

    existing_rows.append(row)

    with index_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing_rows:
            writer.writerow(r)


def append_raw_io_record(raw_io_path: Path, record: Dict[str, Any]) -> None:
    """
    Append a single raw IO record to the JSONL log for this run.

    Each line is a standalone JSON object.
    """
    raw_io_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_io_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")


def run_stage1_benchmark(
    model_name: str,
    prompt_path: Path,
    split: str,
    gold_path: Path,
    candidates_path: Path,
    limit: int | None = None,
    debug: bool = False,
) -> None:
    """
    Execute a Stage 1 benchmark run for the given model, prompt, and split.
    """
    logger.info("Starting Stage 1 benchmark: model=%s split=%s", model_name, split)

    info = get_model_info(model_name)
    prompt_template = load_prompt(prompt_path)
    gold_labels = load_gold_labels(gold_path, split)
    candidates = load_candidates(candidates_path)

    all_labeled_ids_in_order = list(gold_labels.keys())
    available_ids = [pid for pid in all_labeled_ids_in_order if pid in candidates]
    missing_ids = [pid for pid in all_labeled_ids_in_order if pid not in candidates]

    if missing_ids:
        logger.warning(
            "Skipping %d labeled post_ids not present in candidates: %s...",
            len(missing_ids),
            missing_ids[:5],
        )

    if not available_ids:
        raise RuntimeError(
            "No labeled post_ids found in candidates; check that *_candidates.jsonl "
            "was built from the same underlying dataset as gold_labels.csv"
        )

    if limit is not None:
        available_ids = available_ids[:limit]
        logger.info("Applying limit=%d; evaluating on %d examples", limit, len(available_ids))

    logger.info("Evaluating on %d labeled examples present in candidates", len(available_ids))

    if limit is not None:
        size_tag = f"{limit}{split.lower()}"
    else:
        size_tag = f"full{split.lower()}"

    run_slug = f"{model_name}_{prompt_path.stem}_{size_tag}"

    run_dir = ensure_run_dir(run_slug)
    predictions_path = run_dir / f"predictions_{split}.csv"
    metrics_path = run_dir / f"metrics_{split}.json"
    manifest_path = run_dir / "manifest.json"
    raw_io_path = run_dir / f"raw_io_{split}.jsonl"

    prompt_copy_path = run_dir / prompt_path.name
    shutil.copy2(prompt_path, prompt_copy_path)

    rows_for_csv: List[Dict] = []
    gold_and_preds: List[Tuple[str, str]] = []
    predictions: List[Stage1PredictionOutput] = []
    call_results: List[LlmCallResult] = []

    total_cost = 0.0
    total_elapsed = 0.0

    start_time = time.time()
    call_index = 0

    for post_id in available_ids:
        gold = gold_labels[post_id]
        example = candidates[post_id]

        prompt_text = build_prompt(prompt_template, example)

        pred_obj, llm_result = classify_post(
            model_name=model_name,
            example=example,
            prompt_template=prompt_template,
            debug=debug,
        )

        predictions.append(pred_obj)
        call_results.append(llm_result)

        true_label = gold["true_contains_painpoint"]
        pred_label = (pred_obj.contains_painpoint or "").lower()
        gold_and_preds.append((true_label, pred_label))

        total_cost += llm_result.total_cost_usd or 0.0
        total_elapsed += llm_result.elapsed_sec or 0.0

        rows_for_csv.append(
            {
                "post_id": example.post_id,
                "course_code": example.course_code,
                "true_contains_painpoint": true_label,
                "pred_contains_painpoint": pred_label,
                "root_cause_summary_pred": pred_obj.root_cause_summary or "",
                "pain_point_snippet_pred": pred_obj.pain_point_snippet or "",
                "confidence_pred": pred_obj.confidence,
                "parse_error": getattr(pred_obj, "parse_error", False),
                "schema_error": getattr(pred_obj, "schema_error", False),
                "used_fallback": getattr(pred_obj, "used_fallback", False),
                "llm_failure": getattr(llm_result, "llm_failure", False),
            }
        )

        raw_record: Dict[str, Any] = {
            "post_id": example.post_id,
            "course_code": example.course_code,
            "model_name": model_name,
            "provider": info.provider,
            "split": split,
            "prompt_name": prompt_path.name,
            "call_index": call_index,
            "prompt_text": prompt_text,
            "raw_response_text": llm_result.raw_text,
            "started_at": llm_result.started_at,
            "finished_at": llm_result.finished_at,
            "parse_error": getattr(pred_obj, "parse_error", False),
            "schema_error": getattr(pred_obj, "schema_error", False),
            "used_fallback": getattr(pred_obj, "used_fallback", False),
            "llm_failure": getattr(llm_result, "llm_failure", False),
        }
        append_raw_io_record(raw_io_path, raw_record)
        call_index += 1

    end_time = time.time()
    wallclock = end_time - start_time

    metrics = compute_metrics(gold_and_preds)

    num_parse_errors = sum(1 for p in predictions if getattr(p, "parse_error", False))
    num_schema_errors = sum(1 for p in predictions if getattr(p, "schema_error", False))
    num_fallbacks = sum(1 for p in predictions if getattr(p, "used_fallback", False))
    num_llm_failures = sum(1 for r in call_results if getattr(r, "llm_failure", False))

    metrics.update(
        {
            "model_name": model_name,
            "provider": info.provider,
            "split": split,
            "total_cost_usd": total_cost,
            "total_elapsed_sec_model_calls": total_elapsed,
            "wallclock_sec": wallclock,
            "avg_elapsed_sec_per_example": total_elapsed / metrics["num_examples"]
            if metrics["num_examples"] > 0
            else 0.0,
            "num_parse_errors": num_parse_errors,
            "num_schema_errors": num_schema_errors,
            "num_llm_failures": num_llm_failures,
            "num_fallbacks": num_fallbacks,
        }
    )

    with predictions_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "post_id",
                "course_code",
                "true_contains_painpoint",
                "pred_contains_painpoint",
                "root_cause_summary_pred",
                "pain_point_snippet_pred",
                "confidence_pred",
                "parse_error",
                "schema_error",
                "used_fallback",
                "llm_failure",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_for_csv)

    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "model_name": model_name,
        "provider": info.provider,
        "run_slug": run_slug,
        "prompt_template_path": str(prompt_path),
        "prompt_filename": prompt_path.name,
        "prompt_copied_path": str(prompt_copy_path),
        "split": split,
        "gold_path": str(gold_path),
        "candidates_path": str(candidates_path),
        "num_examples": metrics["num_examples"],
        "metrics_path": str(metrics_path),
        "predictions_path": str(predictions_path),
        "raw_io_path": str(raw_io_path),
        "run_dir": str(run_dir),
        "started_at_epoch": start_time,
        "finished_at_epoch": end_time,
    }
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    index_row = {
        "run_slug": run_slug,
        "model_name": model_name,
        "provider": info.provider,
        "split": split,
        "prompt_name": prompt_path.name,
        "prompt": prompt_path.name,
        "num_examples": metrics["num_examples"],
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "fn": metrics["fn"],
        "tn": metrics["tn"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "accuracy": metrics["accuracy"],
        "total_cost_usd": metrics.get("total_cost_usd", 0.0),
        "avg_elapsed_sec_per_example": metrics.get("avg_elapsed_sec_per_example", 0.0),
        "num_parse_errors": metrics.get("num_parse_errors", 0),
        "num_schema_errors": metrics.get("num_schema_errors", 0),
        "num_llm_failures": metrics.get("num_llm_failures", 0),
        "num_fallbacks": metrics.get("num_fallbacks", 0),
        "is_official": False,
        "run_tag": "dev",
        "run_dir": str(run_dir),
        "metrics_path": str(metrics_path),
        "predictions_path": str(predictions_path),
        "started_at_epoch": start_time,
        "finished_at_epoch": end_time,
    }
    append_run_index_row(RUN_INDEX_CSV, index_row)

    logger.info("Stage 1 benchmark complete. Metrics: %s", json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    print(f"\nRun artifacts written to: {run_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1 LLM benchmark against gold labels."
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name (must exist in MODEL_REGISTRY).",
    )
    parser.add_argument(
        "--prompt",
        default="prompts/s1_optimal.txt",
        help="Path to prompt template text file.",
    )
    parser.add_argument(
        "--split",
        default="DEV",
        choices=["DEV", "TEST"],
        help="Data split to evaluate.",
    )
    parser.add_argument(
        "--gold-path",
        default="artifacts/benchmark/gold/gold_labels.csv",
        help="Path to gold_labels.csv.",
    )
    parser.add_argument(
        "--candidates-path",
        default=None,
        help=(
            "Override path to *_candidates.jsonl. "
            "If not set, chooses DEV/TEST_candidates.jsonl based on split."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of labeled examples to evaluate.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging of prompts and model outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    gold_path = Path(args.gold_path)
    if not gold_path.is_file():
        raise FileNotFoundError(f"Gold labels not found at {gold_path}")

    if args.candidates_path:
        candidates_path = Path(args.candidates_path)
    else:
        if args.split == "DEV":
            candidates_path = Path("artifacts/benchmark/DEV_candidates.jsonl")
        else:
            candidates_path = Path("artifacts/benchmark/TEST_candidates.jsonl")

    if not candidates_path.is_file():
        raise FileNotFoundError(f"Candidates file not found at {candidates_path}")

    prompt_path = Path(args.prompt)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")

    run_stage1_benchmark(
        model_name=args.model,
        prompt_path=prompt_path,
        split=args.split,
        gold_path=gold_path,
        candidates_path=candidates_path,
        limit=args.limit,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()