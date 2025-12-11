"""
Stage 1 full-corpus runner.

Runs the Stage 1 classifier over the full Stage 0 filtered corpus
(stage0_filtered_posts.jsonl) using the same prompt and parsing logic
as DEV/TEST benchmarks.

Outputs a self-contained run directory under:
    artifacts/stage1/full_corpus/<run_slug>_<timestamp>/

Artifacts:
    - predictions_FULL.csv   (Stage-1 prediction schema, no gold labels)
    - raw_io_FULL.jsonl      (prompt/response log for each call)
    - manifest.json          (run-level metadata and cost/latency summary)
    - <prompt>.txt           (copy of the prompt used)
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.stage1_types import (
    Stage1PredictionInput,
    Stage1PredictionOutput,
    LlmCallResult,
)
from wgu_reddit_analyzer.benchmark.stage1_classifier import (
    classify_post,
    load_prompt_template,
    build_prompt,
)
from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION
logger = get_logger("stage1.run_stage1_full_corpus")

def ensure_full_corpus_run_dir(run_slug: str) -> Path:
    """
    Create a new full-corpus run directory under artifacts/stage1/full_corpus.
    """
    base = Path("artifacts/stage1/full_corpus")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base / f"{run_slug}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def append_raw_io_record(raw_io_path: Path, record: Dict[str, Any]) -> None:
    """
    Append a single raw IO record to the JSONL log for this full-corpus run.
    """
    raw_io_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_io_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")


def load_full_corpus_inputs(
    input_jsonl: Path,
    limit: int | None = None,
) -> List[Stage1PredictionInput]:
    """
    Load Stage 0 filtered posts as Stage1PredictionInput objects.

    Mirrors the title/selftext combination logic used in benchmark
    candidate loading to keep prompts consistent.
    """
    import json as _json

    items: List[Stage1PredictionInput] = []

    with input_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = _json.loads(line)

            title = obj.get("title") or ""
            selftext = obj.get("selftext") or ""
            if selftext:
                text = f"{title}\n\n{selftext}" if title else selftext
            else:
                text = title

            spi = Stage1PredictionInput(
                post_id=obj["post_id"],
                course_code=obj.get("course_code") or "",
                text=text,
            )
            items.append(spi)

            if limit is not None and len(items) >= limit:
                break

    if not items:
        raise RuntimeError(f"No posts loaded from {input_jsonl}")

    logger.info("Loaded %d posts from %s", len(items), input_jsonl)
    return items


def run_stage1_full_corpus(
    model_name: str,
    prompt_path: Path,
    input_path: Path,
    limit: int | None = None,
    debug: bool = False,
) -> None:
    """
    Execute a Stage 1 full-corpus run with the given model and prompt.
    """
    logger.info(
        "Starting Stage 1 full-corpus run: model=%s input=%s",
        model_name,
        input_path,
    )

    info = get_model_info(model_name)
    prompt_template = load_prompt_template(prompt_path)
    examples = load_full_corpus_inputs(input_path, limit=limit)

    if limit is not None:
        size_tag = f"{limit}full"
    else:
        size_tag = "fullcorpus"

    run_slug = f"{model_name}_{prompt_path.stem}_{size_tag}"

    run_dir = ensure_full_corpus_run_dir(run_slug)
    predictions_path = run_dir / "predictions_FULL.csv"
    manifest_path = run_dir / "manifest.json"
    raw_io_path = run_dir / "raw_io_FULL.jsonl"

    prompt_copy_path = run_dir / prompt_path.name
    shutil.copy2(prompt_path, prompt_copy_path)

    rows_for_csv: List[Dict[str, Any]] = []
    predictions: List[Stage1PredictionOutput] = []
    call_results: List[LlmCallResult] = []

    total_cost = 0.0
    total_elapsed = 0.0

    num_parse_errors = 0
    num_schema_errors = 0
    num_fallbacks = 0
    num_llm_failures = 0

    start_time = time.time()
    call_index = 0

    for example in examples:
        prompt_text = build_prompt(prompt_template, example)

        pred_obj, llm_result = classify_post(
            model_name=model_name,
            example=example,
            prompt_template=prompt_template,
            debug=debug,
        )

        predictions.append(pred_obj)
        call_results.append(llm_result)

        total_cost += llm_result.total_cost_usd or 0.0
        total_elapsed += llm_result.elapsed_sec or 0.0

        if getattr(pred_obj, "parse_error", False):
            num_parse_errors += 1
        if getattr(pred_obj, "schema_error", False):
            num_schema_errors += 1
        if getattr(pred_obj, "used_fallback", False):
            num_fallbacks += 1
        if getattr(llm_result, "llm_failure", False):
            num_llm_failures += 1

        rows_for_csv.append(
            {
                "post_id": example.post_id,
                "course_code": example.course_code,
                "pred_contains_painpoint": pred_obj.contains_painpoint,
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
            "split": "FULL",
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
    num_examples = len(examples)

    avg_elapsed_sec_per_example = (
        total_elapsed / num_examples if num_examples > 0 else 0.0
    )

    with predictions_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "post_id",
                "course_code",
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

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "model_name": model_name,
        "provider": info.provider,
        "run_slug": run_slug,
        "mode": "full_corpus",
        "prompt_template_path": str(prompt_path),
        "prompt_filename": prompt_path.name,
        "prompt_copied_path": str(prompt_copy_path),
        "input_path": str(input_path),
        "num_posts": num_examples,
        "predictions_path": str(predictions_path),
        "raw_io_path": str(raw_io_path),
        "run_dir": str(run_dir),
        "started_at_epoch": start_time,
        "finished_at_epoch": end_time,
        "total_cost_usd": total_cost,
        "total_elapsed_sec_model_calls": total_elapsed,
        "wallclock_sec": wallclock,
        "avg_elapsed_sec_per_example": avg_elapsed_sec_per_example,
        "num_parse_errors": num_parse_errors,
        "num_schema_errors": num_schema_errors,
        "num_llm_failures": num_llm_failures,
        "num_fallbacks": num_fallbacks,
    }

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        "Stage 1 full-corpus run complete. "
        "posts=%d total_cost_usd=%.6f wallclock_sec=%.2f",
        num_examples,
        total_cost,
        wallclock,
    )
    print(json.dumps(manifest, indent=2))
    print(f"\nRun artifacts written to: {run_dir}")


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments for the full-corpus runner.
    """
    parser = argparse.ArgumentParser(
        description="Stage 1 full-corpus classifier over Stage 0 filtered posts."
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
        "--input-jsonl",
        default="artifacts/stage0_filtered_posts.jsonl",
        help="Path to Stage 0 filtered posts (JSONL).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of posts to classify (for smoke tests).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging of prompts and model outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_jsonl)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input JSONL not found at {input_path}")

    prompt_path = Path(args.prompt)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")

    run_stage1_full_corpus(
        model_name=args.model,
        prompt_path=prompt_path,
        input_path=input_path,
        limit=args.limit,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()