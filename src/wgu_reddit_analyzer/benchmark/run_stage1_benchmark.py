"""
Stage 1 Benchmark Runner

Runs the Stage 1 pain-point classifier against gold-labeled DEV or TEST data.
This script is used for prompt iteration, model comparison, and reported
benchmark results.

Behavior:
- Evaluates labeled examples in deterministic order (as listed in the gold CSV).
- Optional --limit evaluates the first N eligible examples only.
- Executes a single LLM pass per example (no retries, no ensembling).

Artifacts (per run):
- predictions.csv   : per-example predictions and error flags
- metrics.json       : aggregate classification metrics
- raw_io.jsonl       : prompt / response logs for each call
- manifest.json      : full provenance (inputs, selection, environment, git)

Design goals:
- Reproducible and auditable benchmarks
- Clear, stable CLI for external users
- No hidden corrective logic

Usage:
python src/wgu_reddit_analyzer/stage1/run_stage1_full_corpus.py --model llama3 --limit 5 --output-dir .
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wgu_reddit_analyzer.benchmark.model_registry import get_model_info
from wgu_reddit_analyzer.benchmark.stage1_classifier import build_prompt, classify_post
from wgu_reddit_analyzer.benchmark.stage1_types import (
    LlmCallResult,
    Stage1PredictionInput,
    Stage1PredictionOutput,
)
from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION

# Logger fallback: prefer project logger; fallback to stdlib logging.
try:
    from wgu_reddit_analyzer.utils.logging_utils import get_logger  # type: ignore
    logger = get_logger(__name__)
except Exception:  # noqa: BLE001
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger(__name__)


DEFAULT_OUT_ROOT = Path("artifacts/benchmark/stage1/runs")
DEFAULT_RUN_INDEX = Path("artifacts/benchmark/stage1_run_index.csv")


@dataclass(frozen=True)
class GitInfo:
    commit: Optional[str]
    is_dirty: Optional[bool]
    describe: Optional[str]


def _utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_sha256_bytes(data: bytes) -> str:
    h = sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def load_prompt(prompt_path: Path) -> str:
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    return _read_text(prompt_path)


def load_gold_labels(gold_path: Path, split: str) -> Dict[str, Dict[str, str]]:
    """
    Returns mapping: post_id -> {"true_contains_painpoint": "y"/"n", "course_code": str}
    Preserves the CSV order via later list(gold.keys()) usage.
    """
    if not gold_path.is_file():
        raise FileNotFoundError(f"Gold labels not found at {gold_path}")

    labels: Dict[str, Dict[str, str]] = {}
    with gold_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "post_id" not in (reader.fieldnames or []):
            raise RuntimeError(f"gold_labels missing required column post_id: {gold_path}")
        for row in reader:
            if (row.get("split") or "").strip().upper() != split:
                continue

            cp = (row.get("contains_painpoint") or "").strip().lower()
            if cp not in {"y", "n"}:
                continue

            post_id = (row.get("post_id") or "").strip()
            if not post_id:
                continue

            labels[post_id] = {
                "true_contains_painpoint": cp,
                "course_code": (row.get("course_code") or "").strip(),
            }

    if not labels:
        raise RuntimeError(f"No eligible gold labels found in {gold_path} for split={split}")

    logger.info("Loaded %d gold labels for split %s", len(labels), split)
    return labels


def load_candidates(candidates_path: Path) -> Dict[str, Stage1PredictionInput]:
    """
    Reads *_candidates.jsonl and returns mapping: post_id -> Stage1PredictionInput
    """
    if not candidates_path.is_file():
        raise FileNotFoundError(f"Candidates file not found at {candidates_path}")

    candidates: Dict[str, Stage1PredictionInput] = {}
    with candidates_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
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


def compute_metrics(gold_and_preds: Iterable[Tuple[str, str]]) -> Dict[str, float]:
    """
    gold_and_preds: (true, pred) with true in {"y","n"}, pred in {"y","n","u"}.
    "u" treated as not predicted positive.
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
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "accuracy": float(accuracy),
        "num_examples": float(total),
    }


def ensure_run_dir(out_root: Path, run_slug: str, run_id: str) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = _utc_timestamp_compact()
    run_dir = out_root / f"{run_slug}_{stamp}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def _write_jsonl_append(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")


def append_run_index_row(index_path: Path, row: Dict[str, Any]) -> None:
    """
    Appends a row; if header needs expansion, rewrites file with union header.
    De-dupes by run_dir.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)

    existing_rows: List[Dict[str, Any]] = []
    existing_header: List[str] = []
    existing_run_dirs: set[str] = set()

    if index_path.is_file():
        with index_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            existing_header = list(reader.fieldnames or [])
            for r in reader:
                existing_rows.append(dict(r))
                if r.get("run_dir"):
                    existing_run_dirs.add(str(r.get("run_dir")))

    run_dir = str(row.get("run_dir", ""))
    if run_dir and run_dir in existing_run_dirs:
        return

    # Build union header
    keys = set(existing_header)
    keys.update(row.keys())
    # Stable order preference: keep existing header first, then append new keys sorted.
    new_keys = sorted(k for k in keys if k not in existing_header)
    header = existing_header + new_keys if existing_header else sorted(keys)

    existing_rows.append(row)

    with index_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in existing_rows:
            writer.writerow({k: r.get(k, "") for k in header})


def _repo_root_from_cwd() -> Path:
    # Best-effort: assume run from repo root; fallback to cwd.
    return Path(os.getcwd()).resolve()


def run_stage1_benchmark(
    model_name: str,
    prompt_path: Path,
    split: str,
    gold_path: Path,
    candidates_path: Path,
    out_root: Path,
    prompt_name_override: Optional[str],
    run_tag: str,
    limit: Optional[int],
    debug: bool,
    dry_run: bool,
    seed: Optional[int],
    write_run_index: bool,
    run_index_path: Path,
) -> None:
    if seed is not None:
        # No sampling today; we log the seed for standardization.
        os.environ["WGU_BENCHMARK_SEED"] = str(seed)

    info = get_model_info(model_name)
    prompt_template = load_prompt(prompt_path)
    prompt_sha = _sha256_file(prompt_path)
    gold_labels = load_gold_labels(gold_path, split)
    candidates = load_candidates(candidates_path)

    gold_ids_in_order = list(gold_labels.keys())
    available_ids = [pid for pid in gold_ids_in_order if pid in candidates]
    missing_ids = [pid for pid in gold_ids_in_order if pid not in candidates]

    if not available_ids:
        raise RuntimeError(
            "No labeled post_ids found in candidates; check that candidates were built from "
            "the same underlying dataset as gold_labels.csv"
        )

    if limit is not None:
        available_ids = available_ids[:limit]

    prompt_name = prompt_name_override or prompt_path.name

    size_tag = f"{limit}{split.lower()}" if limit is not None else f"full{split.lower()}"
    run_slug = f"{model_name}_{Path(prompt_name).stem}_{size_tag}"

    run_id = f"b1_{_utc_timestamp_compact()}"
    run_dir = ensure_run_dir(out_root=out_root, run_slug=run_slug, run_id=run_id)

    predictions_path = run_dir / "predictions.csv"
    metrics_path = run_dir / "metrics.json"
    manifest_path = run_dir / "manifest.json"
    raw_io_path = run_dir / "raw_io.jsonl"
    prompt_copy_path = run_dir / "prompt_used.txt"

    if dry_run:
        print("DRY RUN")
        print(f"model_name: {model_name}")
        print(f"provider: {info.provider}")
        print(f"split: {split}")
        print(f"limit: {limit}")
        print(f"gold_path: {gold_path}")
        print(f"candidates_path: {candidates_path}")
        print(f"prompt_path: {prompt_path}")
        print(f"out_root: {out_root}")
        print(f"run_dir: {run_dir}")
        print(f"num_gold_labels: {len(gold_ids_in_order)}")
        print(f"num_available: {len(available_ids)}")
        print(f"num_missing: {len(missing_ids)}")
        return

    # Copy prompt used
    shutil.copy2(prompt_path, prompt_copy_path)

    repo_root = _repo_root_from_cwd()
    git = _get_git_info(repo_root)

    # One-screen start summary
    logger.info("Stage1 benchmark starting")
    logger.info("model=%s provider=%s split=%s limit=%s", model_name, info.provider, split, str(limit))
    logger.info("prompt=%s (sha256=%s)", str(prompt_path), prompt_sha)
    logger.info("gold=%s candidates=%s", str(gold_path), str(candidates_path))
    logger.info("run_dir=%s", str(run_dir))
    if missing_ids:
        logger.warning("Missing %d labeled ids from candidates (first 5): %s", len(missing_ids), missing_ids[:5])

    rows_for_csv: List[Dict[str, Any]] = []
    gold_and_preds: List[Tuple[str, str]] = []
    predictions: List[Stage1PredictionOutput] = []
    call_results: List[LlmCallResult] = []

    total_cost = 0.0
    total_elapsed = 0.0
    had_failures = False

    started_at = time.time()

    for call_index, post_id in enumerate(available_ids):
        gold = gold_labels[post_id]
        example = candidates[post_id]
        prompt_text = build_prompt(prompt_template, example)
        input_text_hash = _safe_sha256_bytes((example.text or "").encode("utf-8", errors="replace"))

        call_started = time.time()
        exc_text = None

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
                confidence=None,
                parse_error=False,
                schema_error=False,
                used_fallback=False,
            )

        predictions.append(pred_obj)
        call_results.append(llm_result)

        true_label = (gold.get("true_contains_painpoint") or "").lower()
        pred_label = (getattr(pred_obj, "contains_painpoint", "") or "").lower() or "u"
        if pred_label not in {"y", "n", "u"}:
            pred_label = "u"

        gold_and_preds.append((true_label, pred_label))

        total_cost += float(getattr(llm_result, "total_cost_usd", 0.0) or 0.0)
        total_elapsed += float(getattr(llm_result, "elapsed_sec", 0.0) or 0.0)

        row = {
            "post_id": example.post_id,
            "course_code": example.course_code,
            "true_contains_painpoint": true_label,
            "pred_contains_painpoint": pred_label,
            "root_cause_summary_pred": getattr(pred_obj, "root_cause_summary", "") or "",
            "pain_point_snippet_pred": getattr(pred_obj, "pain_point_snippet", "") or "",
            "confidence_pred": getattr(pred_obj, "confidence", None),
            "parse_error": bool(getattr(pred_obj, "parse_error", False)),
            "schema_error": bool(getattr(pred_obj, "schema_error", False)),
            "used_fallback": bool(getattr(pred_obj, "used_fallback", False)),
            "llm_failure": bool(getattr(llm_result, "llm_failure", False)),
        }
        rows_for_csv.append(row)

        raw_record: Dict[str, Any] = {
            "run_id": run_id,
            "run_slug": run_slug,
            "run_tag": run_tag,
            "call_index": call_index,
            "post_id": example.post_id,
            "course_code": example.course_code,
            "model_name": model_name,
            "provider": getattr(info, "provider", ""),
            "split": split,
            "prompt_name": prompt_name,
            "prompt_sha256": prompt_sha,
            "input_text_sha256": input_text_hash,
            "prompt_text": prompt_text,
            "raw_response_text": getattr(llm_result, "raw_text", "") or "",
            "started_at_epoch": float(getattr(llm_result, "started_at", call_started) or call_started),
            "finished_at_epoch": float(getattr(llm_result, "finished_at", time.time()) or time.time()),
            "elapsed_sec": float(getattr(llm_result, "elapsed_sec", 0.0) or 0.0),
            "total_cost_usd": float(getattr(llm_result, "total_cost_usd", 0.0) or 0.0),
            "parse_error": bool(getattr(pred_obj, "parse_error", False)),
            "schema_error": bool(getattr(pred_obj, "schema_error", False)),
            "used_fallback": bool(getattr(pred_obj, "used_fallback", False)),
            "llm_failure": bool(getattr(llm_result, "llm_failure", False)),
        }
        if exc_text:
            raw_record["exception"] = exc_text
            raw_record["exception_traceback"] = traceback.format_exc(limit=50)

        _write_jsonl_append(raw_io_path, raw_record)

    finished_at = time.time()
    wallclock = finished_at - started_at

    metrics = compute_metrics(gold_and_preds)
    num_examples = int(metrics["num_examples"])

    num_parse_errors = sum(1 for p in predictions if bool(getattr(p, "parse_error", False)))
    num_schema_errors = sum(1 for p in predictions if bool(getattr(p, "schema_error", False)))
    num_fallbacks = sum(1 for p in predictions if bool(getattr(p, "used_fallback", False)))
    num_llm_failures = sum(1 for r in call_results if bool(getattr(r, "llm_failure", False)))

    metrics_obj: Dict[str, Any] = dict(metrics)
    metrics_obj.update(
        {
            "schema_version": SCHEMA_VERSION,
            "model_name": model_name,
            "provider": getattr(info, "provider", ""),
            "split": split,
            "run_id": run_id,
            "run_slug": run_slug,
            "run_tag": run_tag,
            "prompt_name": prompt_name,
            "prompt_sha256": prompt_sha,
            "num_examples": num_examples,
            "total_cost_usd": float(total_cost),
            "total_elapsed_sec_model_calls": float(total_elapsed),
            "wallclock_sec": float(wallclock),
            "avg_elapsed_sec_per_example": (float(total_elapsed) / num_examples) if num_examples > 0 else 0.0,
            "num_parse_errors": int(num_parse_errors),
            "num_schema_errors": int(num_schema_errors),
            "num_llm_failures": int(num_llm_failures),
            "num_fallbacks": int(num_fallbacks),
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

    _write_json(metrics_path, metrics_obj)

    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stage": "benchmark_stage1",
        "run_id": run_id,
        "run_slug": run_slug,
        "run_tag": run_tag,
        "mode": "benchmark",
        "model_name": model_name,
        "provider": getattr(info, "provider", ""),
        "prompt_name": prompt_name,
        "prompt_template_path": str(prompt_path),
        "prompt_sha256": prompt_sha,
        "prompt_copied_path": str(prompt_copy_path),
        "split": split,
        "limit": limit,
        "seed": seed,
        "inputs": {
            "gold_path": str(gold_path),
            "gold_sha256": _sha256_file(gold_path),
            "candidates_path": str(candidates_path),
            "candidates_sha256": _sha256_file(candidates_path),
        },
        "selection": {
            "gold_label_post_ids_total": len(gold_ids_in_order),
            "post_ids_missing_from_candidates": missing_ids,
            "post_ids_evaluated_in_order": available_ids,
            "limit_applied": limit is not None,
            "limit_rule": "first_n_in_gold_order" if limit is not None else None,
        },
        "outputs": {
            "run_dir": str(run_dir),
            "predictions_path": str(predictions_path),
            "metrics_path": str(metrics_path),
            "raw_io_path": str(raw_io_path),
        },
        "timing": {
            "started_at_epoch": float(started_at),
            "finished_at_epoch": float(finished_at),
            "wallclock_sec": float(wallclock),
            "total_elapsed_sec_model_calls": float(total_elapsed),
        },
        "counts": {
            "num_examples": int(num_examples),
            "num_parse_errors": int(num_parse_errors),
            "num_schema_errors": int(num_schema_errors),
            "num_llm_failures": int(num_llm_failures),
            "num_fallbacks": int(num_fallbacks),
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

    if write_run_index:
        index_row: Dict[str, Any] = {
            "run_id": run_id,
            "run_slug": run_slug,
            "run_tag": run_tag,
            "model_name": model_name,
            "provider": getattr(info, "provider", ""),
            "split": split,
            "prompt_name": prompt_name,
            "prompt_sha256": prompt_sha,
            "limit": limit if limit is not None else "",
            "seed": seed if seed is not None else "",
            "num_examples": num_examples,
            "tp": int(metrics_obj.get("tp", 0)),
            "fp": int(metrics_obj.get("fp", 0)),
            "fn": int(metrics_obj.get("fn", 0)),
            "tn": int(metrics_obj.get("tn", 0)),
            "precision": float(metrics_obj.get("precision", 0.0)),
            "recall": float(metrics_obj.get("recall", 0.0)),
            "f1": float(metrics_obj.get("f1", 0.0)),
            "accuracy": float(metrics_obj.get("accuracy", 0.0)),
            "total_cost_usd": float(total_cost),
            "avg_elapsed_sec_per_example": float(metrics_obj.get("avg_elapsed_sec_per_example", 0.0)),
            "num_parse_errors": int(num_parse_errors),
            "num_schema_errors": int(num_schema_errors),
            "num_llm_failures": int(num_llm_failures),
            "num_fallbacks": int(num_fallbacks),
            "run_dir": str(run_dir),
            "metrics_path": str(metrics_path),
            "predictions_path": str(predictions_path),
            "raw_io_path": str(raw_io_path),
            "started_at_epoch": float(started_at),
            "finished_at_epoch": float(finished_at),
            "git_commit": git.commit or "",
            "git_describe": git.describe or "",
            "git_is_dirty": git.is_dirty if git.is_dirty is not None else "",
        }
        append_run_index_row(run_index_path, index_row)

    # Always print metrics + run dir to stdout for convenience.
    print(json.dumps(metrics_obj, indent=2))
    print(f"\nRun artifacts written to: {run_dir}")

    # Exit nonzero if anything failed, but only after writing artifacts.
    if had_failures or num_llm_failures > 0:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 1 LLM benchmark against gold labels.")
    parser.add_argument("--model", required=True, help="Model name (must exist in MODEL_REGISTRY).")
    parser.add_argument("--prompt", default="prompts/s1_refined.txt", help="Path to prompt template text file.")
    parser.add_argument("--prompt-name", default=None, help="Optional name label for the prompt in artifacts.")
    parser.add_argument("--split", default="DEV", choices=["DEV", "TEST"], help="Data split to evaluate.")
    parser.add_argument("--gold-path", default="artifacts/benchmark/gold/gold_labels.csv", help="Path to gold_labels.csv.")
    parser.add_argument(
        "--candidates-path",
        default=None,
        help="Override path to *_candidates.jsonl. If not set, chooses DEV/TEST_candidates.jsonl based on split.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of labeled examples (first N in gold order).")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Output root directory for run folders.")
    parser.add_argument("--run-tag", default="dev", help="Run tag label (e.g., dev, final).")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed (logged only unless future sampling is added).")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging of prompts and model outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print planned run without LLM calls or writes.")
    parser.add_argument("--no-run-index", action="store_true", help="Do not append this run to the global run index CSV.")
    parser.add_argument("--run-index-path", default=str(DEFAULT_RUN_INDEX), help="Path to global run index CSV.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    gold_path = Path(args.gold_path)

    if args.candidates_path:
        candidates_path = Path(args.candidates_path)
    else:
        candidates_path = Path("artifacts/benchmark/DEV_candidates.jsonl") if args.split == "DEV" else Path("artifacts/benchmark/TEST_candidates.jsonl")

    run_stage1_benchmark(
        model_name=args.model,
        prompt_path=Path(args.prompt),
        split=args.split,
        gold_path=gold_path,
        candidates_path=candidates_path,
        out_root=Path(args.out_root),
        prompt_name_override=args.prompt_name,
        run_tag=args.run_tag,
        limit=args.limit,
        debug=args.debug,
        dry_run=args.dry_run,
        seed=args.seed,
        write_run_index=(not args.no_run_index),
        run_index_path=Path(args.run_index_path),
    )


if __name__ == "__main__":
    main()