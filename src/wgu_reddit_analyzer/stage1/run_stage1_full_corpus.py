"""
Stage 1 Full-Corpus Runner

Runs the Stage 1 pain-point classifier (selected model + prompt) over the
Stage 0 filtered corpus and writes a self-contained artifact directory.

Reads
- Stage 0 corpus JSONL (default: artifacts/stage0_filtered_posts.jsonl)
  Required fields: post_id, title, selftext
  Optional: course_code (defaults to empty)

Writes (single run directory)
- predictions_FULL.csv
  One row per post with pain-point decision and extracted fields
- raw_io_FULL.jsonl
  One record per model call (prompt, response, error flags)
- manifest.json
  Run provenance: inputs, counts, timing, cost, environment
- prompt_used.txt
  Exact prompt text used

Normal usage:
  python src/wgu_reddit_analyzer/stage1/run_stage1_full_corpus.py \
    --model <model_name> --output-dir <output_dir>

Demo usage:
  python src/wgu_reddit_analyzer/stage1/run_stage1_full_corpus.py \
    --model llama3 --limit 10 --output-dir _demo
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.stage1_classifier import build_prompt, classify_post, load_prompt_template
from wgu_reddit_analyzer.benchmark.stage1_types import LlmCallResult, Stage1PredictionInput, Stage1PredictionOutput
from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("stage1.run_stage1_full_corpus")

DEFAULT_STAGE0_JSONL = Path("artifacts/stage0_filtered_posts.jsonl")
DEFAULT_OUT_ROOT = Path("artifacts/stage1/full_corpus")
DEFAULT_PROMPT_PATH = Path("prompts/s1_optimal.txt")


@dataclass(frozen=True)
class GitInfo:
    commit: Optional[str]
    is_dirty: Optional[bool]
    describe: Optional[str]


def _utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_repo_root(start: Path) -> Path:
    """
    Best-effort repo root discovery.
    Walk upward looking for .git or pyproject.toml; fall back to cwd.
    """
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").is_file():
            return parent
    return Path(os.getcwd()).resolve()


def _get_git_info(repo_root: Path) -> GitInfo:
    def run(cmd: List[str]) -> Optional[str]:
        try:
            out = subprocess.check_output(cmd, cwd=str(repo_root), stderr=subprocess.DEVNULL)
            return out.decode("utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001
            return None

    commit = run(["git", "rev-parse", "HEAD"])
    describe = run(["git", "describe", "--always", "--dirty"])
    dirty_txt = run(["git", "status", "--porcelain"])
    is_dirty = None if dirty_txt is None else (dirty_txt.strip() != "")
    return GitInfo(commit=commit, is_dirty=is_dirty, describe=describe)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def _write_jsonl_append(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")


def _ensure_run_dir(out_root: Path, run_slug: str, run_id: str) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = _utc_timestamp_compact()
    run_dir = out_root / f"{run_slug}_{stamp}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _prepare_output_dir_explicit(path: Path, overwrite: bool) -> None:
    """
    If output_dir exists:
      - must be a directory
      - must be empty unless overwrite is set
    If output_dir does not exist:
      - create it
    """
    if path.exists():
        if not path.is_dir():
            raise RuntimeError(f"output_dir exists but is not a directory: {path}")
        existing = list(path.iterdir())
        if existing and not overwrite:
            raise RuntimeError(
                f"output_dir is not empty: {path}. Choose a new directory or pass --overwrite."
            )
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(parents=True, exist_ok=True)


def load_full_corpus_inputs(
    input_jsonl: Path,
    limit: int | None = None,
) -> Tuple[List[Stage1PredictionInput], List[str]]:
    """
    Load Stage 0 posts as Stage1PredictionInput objects.

    Determinism: preserves input file order. If limit is set, selects the first N
    eligible lines as they appear in the file.
    """
    if not input_jsonl.is_file():
        raise FileNotFoundError(f"Input JSONL not found at {input_jsonl}")

    items: List[Stage1PredictionInput] = []
    post_ids_in_order: List[str] = []

    with input_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)
            post_id = (obj.get("post_id") or "").strip()
            if not post_id:
                continue

            title = obj.get("title") or ""
            selftext = obj.get("selftext") or ""
            if selftext:
                text = f"{title}\n\n{selftext}" if title else selftext
            else:
                text = title

            items.append(
                Stage1PredictionInput(
                    post_id=post_id,
                    course_code=(obj.get("course_code") or "").strip(),
                    text=text,
                )
            )
            post_ids_in_order.append(post_id)

            if limit is not None and len(items) >= limit:
                break

    if not items:
        raise RuntimeError(f"No posts loaded from {input_jsonl}")

    logger.info("Loaded %d posts from %s", len(items), input_jsonl)
    return items, post_ids_in_order


def _normalize_confidence(value: Any) -> float:
    try:
        x = float(value)
    except Exception:  # noqa: BLE001
        return 0.0
    if not (x == x):  # NaN
        return 0.0
    if x == float("inf") or x == float("-inf"):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def run_stage1_full_corpus(
    model_name: str,
    prompt_path: Path,
    input_path: Path,
    out_root: Path,
    output_dir: Optional[Path],
    prompt_name_override: Optional[str],
    run_tag: str,
    limit: int | None = None,
    debug: bool = False,
    dry_run: bool = False,
    overwrite: bool = False,
) -> None:
    # Validate inputs early (fail fast)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    if not input_path.is_file():
        raise FileNotFoundError(f"Input JSONL not found at {input_path}")

    # Load model metadata and prompt; hash inputs for provenance
    info = get_model_info(model_name)
    prompt_template = load_prompt_template(prompt_path)
    prompt_sha256 = _sha256_file(prompt_path)
    input_sha256 = _sha256_file(input_path)

    # Load Stage 0 corpus (optional limit for smoke tests)
    examples, post_ids_in_order = load_full_corpus_inputs(input_path, limit=limit)

    # Compute run identifiers (human-readable + unique)
    prompt_name = prompt_name_override or prompt_path.name
    size_tag = f"{limit}full" if limit is not None else "fullcorpus"
    run_slug = f"{model_name}_{Path(prompt_name).stem}_{size_tag}"
    run_id = f"s1_{_utc_timestamp_compact()}"

    # Resolve output directory (explicit vs auto-generated)
    if output_dir is not None:
        _prepare_output_dir_explicit(output_dir, overwrite=overwrite)
        run_dir = output_dir
    else:
        run_dir = _ensure_run_dir(out_root=out_root, run_slug=run_slug, run_id=run_id)

    # Define run artifact paths
    predictions_path = run_dir / "predictions_FULL.csv"
    manifest_path = run_dir / "manifest.json"
    raw_io_path = run_dir / "raw_io_FULL.jsonl"
    prompt_copy_path = run_dir / "prompt_used.txt"

    # Dry run: print configuration only, no model calls
    if dry_run:
        print("DRY RUN")
        print(f"model_name: {model_name}")
        print(f"provider: {getattr(info, 'provider', '')}")
        print(f"prompt_path: {prompt_path} (sha256={prompt_sha256})")
        print(f"input_path: {input_path} (sha256={input_sha256})")
        print(f"num_posts: {len(examples)}")
        print(f"run_dir: {run_dir}")
        return

    # Create run directory and snapshot prompt for reproducibility
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_copy_path.write_text(prompt_path.read_text(encoding="utf-8"), encoding="utf-8")

    # Capture git state for traceability
    repo_root = _find_repo_root(Path(__file__).resolve())
    git = _get_git_info(repo_root)

    logger.info("Stage 1 full-corpus starting")
    logger.info("model=%s provider=%s", model_name, getattr(info, "provider", ""))
    logger.info("prompt=%s (sha256=%s)", str(prompt_path), prompt_sha256)
    logger.info("input=%s (sha256=%s) posts=%d", str(input_path), input_sha256, len(examples))
    logger.info("run_dir=%s", str(run_dir))

    # Initialize aggregates and error counters
    rows_for_csv: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_elapsed = 0.0
    had_failures = False

    num_parse_errors = 0
    num_schema_errors = 0
    num_fallbacks = 0
    num_llm_failures = 0

    started_at = time.time()

    # Main loop: one post → one model call
    for call_index, example in enumerate(examples):
        prompt_text = build_prompt(prompt_template, example)

        call_started = time.time()
        exc_text: Optional[str] = None
        exc_tb: Optional[str] = None

        # Call classifier; fail soft on exceptions
        try:
            pred_obj, llm_result = classify_post(
                model_name=model_name,
                example=example,
                prompt_template=prompt_template,
                debug=debug,
            )
        except Exception as exc:  # noqa: BLE001
            had_failures = True
            exc_text = f"{type(exc).__name__}: {exc}"
            exc_tb = traceback.format_exc(limit=50)

            llm_result = LlmCallResult(  # type: ignore[call-arg]
                model_name=model_name,
                provider=getattr(info, "provider", ""),
                raw_text="",
                total_cost_usd=0.0,
                elapsed_sec=(time.time() - call_started),
                started_at=call_started,
                finished_at=time.time(),
                llm_failure=True,
            )
            pred_obj = Stage1PredictionOutput(  # type: ignore[call-arg]
                post_id=example.post_id,
                course_code=example.course_code,
                contains_painpoint="u",
                root_cause_summary="",
                pain_point_snippet="",
                confidence=0.0,
                parse_error=False,
                schema_error=False,
                used_fallback=False,
            )
        # Timing, cost, and error counters
        total_cost += float(getattr(llm_result, "total_cost_usd", 0.0) or 0.0)
        total_elapsed += float(getattr(llm_result, "elapsed_sec", 0.0) or 0.0)

        if bool(getattr(pred_obj, "parse_error", False)):
            num_parse_errors += 1
        if bool(getattr(pred_obj, "schema_error", False)):
            num_schema_errors += 1
        if bool(getattr(pred_obj, "used_fallback", False)):
            num_fallbacks += 1
        if bool(getattr(llm_result, "llm_failure", False)):
            num_llm_failures += 1

        # Normalize label and confidence
        pred_label = (getattr(pred_obj, "contains_painpoint", "") or "").lower() or "u"
        if pred_label not in {"y", "n", "u"}:
            pred_label = "u"

        confidence_val = _normalize_confidence(getattr(pred_obj, "confidence", None))

        rows_for_csv.append(
            {
                "post_id": example.post_id,
                "course_code": example.course_code,
                "pred_contains_painpoint": pred_label,
                "root_cause_summary_pred": getattr(pred_obj, "root_cause_summary", "") or "",
                "pain_point_snippet_pred": getattr(pred_obj, "pain_point_snippet", "") or "",
                "confidence_pred": confidence_val,
                "parse_error": bool(getattr(pred_obj, "parse_error", False)),
                "schema_error": bool(getattr(pred_obj, "schema_error", False)),
                "used_fallback": bool(getattr(pred_obj, "used_fallback", False)),
                "llm_failure": bool(getattr(llm_result, "llm_failure", False)),
            }
        )

        raw_record: Dict[str, Any] = {
            "run_id": run_id,
            "run_slug": run_slug,
            "run_tag": run_tag,
            "call_index": call_index,
            "post_id": example.post_id,
            "course_code": example.course_code,
            "model_name": model_name,
            "provider": getattr(info, "provider", ""),
            "split": "FULL",
            "prompt_name": prompt_name,
            "prompt_sha256": prompt_sha256,
            "prompt_text": prompt_text,
            "raw_response_text": getattr(llm_result, "raw_text", "") or "",
            "started_at_epoch": float(getattr(llm_result, "started_at", call_started) or call_started),
            "finished_at_epoch": float(getattr(llm_result, "finished_at", time.time()) or time.time()),
            "elapsed_sec": float(getattr(llm_result, "elapsed_sec", 0.0) or 0.0),
            "total_cost_usd": float(getattr(llm_result, "total_cost_usd", 0.0) or 0.0),
            "confidence_pred": confidence_val,
            "parse_error": bool(getattr(pred_obj, "parse_error", False)),
            "schema_error": bool(getattr(pred_obj, "schema_error", False)),
            "used_fallback": bool(getattr(pred_obj, "used_fallback", False)),
            "llm_failure": bool(getattr(llm_result, "llm_failure", False)),
        }
        if exc_text:
            raw_record["exception"] = exc_text
        if exc_tb:
            raw_record["exception_traceback"] = exc_tb

        _write_jsonl_append(raw_io_path, raw_record)

    finished_at = time.time()
    wallclock = finished_at - started_at
    num_examples = len(examples)
    avg_elapsed_sec_per_example = (total_elapsed / num_examples) if num_examples > 0 else 0.0

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

    selection: Dict[str, Any] = {
        "limit": limit,
        "limit_rule": "first_n_in_file_order" if limit is not None else None,
    }
    if post_ids_in_order:
        selection["first_post_id"] = post_ids_in_order[0]
        selection["last_post_id"] = post_ids_in_order[-1]
    if limit is not None:
        selection["post_ids_evaluated_in_order"] = post_ids_in_order

    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stage": "stage1_full_corpus",
        "script": "src/wgu_reddit_analyzer/stage1/run_stage1_full_corpus.py",
        "mode": "full_corpus",
        "run_id": run_id,
        "run_slug": run_slug,
        "run_tag": run_tag,
        "model_name": model_name,
        "provider": getattr(info, "provider", ""),
        "prompt_name": prompt_name,
        "prompt_template_path": str(prompt_path),
        "prompt_sha256": prompt_sha256,
        "prompt_copied_path": str(prompt_copy_path),
        "inputs": {
            "stage0_filtered_posts_path": str(input_path),
            "stage0_filtered_posts_sha256": input_sha256,
        },
        "selection": selection,
        "outputs": {
            "run_dir": str(run_dir),
            "predictions_path": str(predictions_path),
            "raw_io_path": str(raw_io_path),
        },
        "counts": {
            "num_examples": int(num_examples),
            "num_parse_errors": int(num_parse_errors),
            "num_schema_errors": int(num_schema_errors),
            "num_llm_failures": int(num_llm_failures),
            "num_fallbacks": int(num_fallbacks),
        },
        "timing": {
            "started_at_epoch": float(started_at),
            "finished_at_epoch": float(finished_at),
            "wallclock_sec": float(wallclock),
            "total_elapsed_sec_model_calls": float(total_elapsed),
            "avg_elapsed_sec_per_example": float(avg_elapsed_sec_per_example),
        },
        "cost": {
            "total_cost_usd": float(total_cost),
            "avg_cost_usd_per_example": (float(total_cost) / num_examples) if num_examples > 0 else 0.0,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "git": {
            "commit": git.commit,
            "describe": git.describe,
            "is_dirty": git.is_dirty,
        },
    }
    _write_json(manifest_path, manifest)

    logger.info(
        "Stage 1 full-corpus complete. examples=%d total_cost_usd=%.6f wallclock_sec=%.2f",
        num_examples,
        total_cost,
        wallclock,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nRun artifacts written to: {run_dir}")

    if had_failures or num_llm_failures > 0:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 1 full-corpus classifier over the Stage 0 filtered posts.")
    parser.add_argument("--model", required=True, help="Model name (must exist in MODEL_REGISTRY).")
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT_PATH), help="Path to prompt template text file.")
    parser.add_argument("--prompt-name", default=None, help="Optional name label for the prompt in artifacts.")
    parser.add_argument("--input-jsonl", default=str(DEFAULT_STAGE0_JSONL), help="Path to Stage 0 filtered posts (JSONL).")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of posts to classify (for smoke tests).")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Output root directory for run folders.")
    parser.add_argument("--output-dir", default=None, help="Explicit output directory to write run artifacts into.")
    parser.add_argument("--overwrite", action="store_true", help="Allow writing into a non-empty --output-dir.")
    parser.add_argument("--run-tag", default="final", help="Run tag label (for provenance only).")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging of prompts and model outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print planned run without LLM calls or writes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_stage1_full_corpus(
        model_name=args.model,
        prompt_path=Path(args.prompt),
        input_path=Path(args.input_jsonl),
        out_root=Path(args.out_root),
        output_dir=(Path(args.output_dir) if args.output_dir else None),
        prompt_name_override=args.prompt_name,
        run_tag=args.run_tag,
        limit=args.limit,
        debug=args.debug,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()