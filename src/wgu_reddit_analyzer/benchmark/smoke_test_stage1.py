from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.stage1_types import Stage1PredictionInput, Stage1PredictionOutput
from wgu_reddit_analyzer.benchmark.stage1_classifier import classify_post
from wgu_reddit_analyzer.utils.logging_utils import get_logger


logger = get_logger(__name__)


def load_prompt(prompt_path: Path) -> str:
    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()


def load_gold_labels(gold_path: Path, split: str) -> Dict[str, Dict]:
    """
    Returns mapping: post_id -> {"true_contains_painpoint": "y"/"n", "course_code": str}
    Only includes rows where:
      - split matches
      - ambiguity_flag != "1"
      - contains_painpoint in {"y", "n"}
    """
    labels: Dict[str, Dict] = {}
    with gold_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") != split:
                continue

            if row.get("ambiguity_flag") == "1":
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
    gold_and_preds: list of (true, pred) with true in {"y","n"}, pred in {"y","n","u"}.
    We treat "u" as "not predicted positive":
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
        else:  # true_label == "n"
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


def ensure_run_dir(model_name: str, split: str) -> Path:
    from datetime import datetime

    base = Path("artifacts/benchmark/runs/stage1_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base / f"{model_name}_{split}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_smoke_test(
    model_name: str,
    prompt_path: Path,
    split: str,
    gold_path: Path,
    candidates_path: Path,
) -> None:
    logger.info("Starting Stage 1 smoke test: model=%s split=%s", model_name, split)

    info = get_model_info(model_name)
    prompt_template = load_prompt(prompt_path)
    gold_labels = load_gold_labels(gold_path, split)
    candidates = load_candidates(candidates_path)

    # Use only intersection of labeled posts and candidates
    all_labeled_ids = set(gold_labels.keys())
    available_ids = [pid for pid in all_labeled_ids if pid in candidates]
    missing_ids = [pid for pid in all_labeled_ids if pid not in candidates]

    if missing_ids:
        logger.warning(
            "Skipping %d labeled post_ids not present in candidates: %s...",
            len(missing_ids),
            missing_ids[:5],
        )

    if not available_ids:
        raise RuntimeError(
            "No labeled post_ids found in candidates; check that DEV_candidates.jsonl "
            "was built from the same underlying dataset as gold_labels.csv"
        )

    logger.info("Evaluating on %d labeled examples present in candidates", len(available_ids))

    run_dir = ensure_run_dir(model_name, split)
    predictions_path = run_dir / f"predictions_{split}.csv"
    metrics_path = run_dir / f"metrics_{split}.json"
    manifest_path = run_dir / "manifest.json"

    rows_for_csv: List[Dict] = []
    gold_and_preds: List[Tuple[str, str]] = []

    total_cost = 0.0
    total_elapsed = 0.0

    start_time = time.time()

    for post_id in available_ids:
        gold = gold_labels[post_id]
        example = candidates[post_id]
        pred_obj, llm_result = classify_post(
            model_name=model_name,
            example=example,
            prompt_template=prompt_template,
        )

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
                "ambiguity_flag_pred": pred_obj.ambiguity_flag,
            }
        )

    end_time = time.time()
    wallclock = end_time - start_time

    metrics = compute_metrics(gold_and_preds)
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
        }
    )

    # Write predictions CSV
    with predictions_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "post_id",
                "course_code",
                "true_contains_painpoint",
                "pred_contains_painpoint",
                "root_cause_summary_pred",
                "ambiguity_flag_pred",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_for_csv)

    # Write metrics JSON
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Write manifest
    manifest = {
        "model_name": model_name,
        "provider": info.provider,
        "prompt_template_path": str(prompt_path),
        "split": split,
        "gold_path": str(gold_path),
        "candidates_path": str(candidates_path),
        "num_examples": metrics["num_examples"],
        "metrics_path": str(metrics_path),
        "predictions_path": str(predictions_path),
        "run_dir": str(run_dir),
        "started_at_epoch": start_time,
        "finished_at_epoch": end_time,
    }
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Smoke test complete. Metrics: %s", json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    print(f"\nRun artifacts written to: {run_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1 LLM smoke test against gold labels."
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
        help="Data split to evaluate (gold is currently DEV).",
    )
    parser.add_argument(
        "--gold-path",
        default="artifacts/benchmark/gold/gold_labels.csv",
        help="Path to gold_labels.csv.",
    )
    parser.add_argument(
        "--candidates-path",
        default=None,
        help="Override path to *_candidates.jsonl. "
             "If not set, chooses DEV/TEST_candidates.jsonl based on split.",
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

    run_smoke_test(
        model_name=args.model,
        prompt_path=prompt_path,
        split=args.split,
        gold_path=gold_path,
        candidates_path=candidates_path,
    )


if __name__ == "__main__":
    main()