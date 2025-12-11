from __future__ import annotations
"""
Combine multiple Stage 1 benchmark runs into a single analysis table and
produce post-centric chunks for LLM-assisted error analysis.

For each selected run directory, this script:

1. Loads manifest.json to get:
   - model_name, provider, split
   - prompt filename/path (if present)
   - predictions CSV path

2. Loads predictions_<split>.csv and joins each row with:
   - gold label from gold_labels.csv
   - full post text from DEV/TEST_candidates.jsonl

3. Computes an error_type per example:
   - TP, FP, FN, TN (treats "u" as "not predicted positive")

4. Writes a combined CSV with one row per
   (run × post_id × model × prompt).

5. Splits the combined table into post-centric chunks with a fixed
   number of posts per chunk (default 5). Each chunk file contains
   all models and prompts for its subset of posts, which makes it
   convenient to paste into an LLM for human-in-the-loop analysis.

Typical usage (25-post DEV subset, zero vs few-shot runs):

PYTHONPATH=src python -m wgu_reddit_analyzer.benchmark.combine_runs_for_analysis \
  --runs-dir artifacts/benchmark/runs/stage1_ \
  --glob "*_DEV_20251118_*" \
  --glob "*_DEV_20251119_*" \
  --gold-path artifacts/benchmark/gold/gold_labels.csv \
  --candidates-path artifacts/benchmark/DEV_candidates.jsonl \
  --out-dir artifacts/analysis \
  --combined-name combined_zero_vs_few_25dev.csv \
  --posts-per-chunk 5
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def load_gold_labels(gold_path: Path, split: str) -> Dict[str, Dict]:
    """
    Load gold_labels.csv and return mapping:
        post_id -> {
            "contains_painpoint": "y"/"n"/"u",
            "root_cause_summary": str,
            "ambiguity_flag": str,
            "notes": str,
            "split": str,
        }

    We do not filter by split here; the caller may choose to.
    """
    labels: Dict[str, Dict] = {}
    with gold_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_id = row.get("post_id")
            if not post_id:
                continue
            labels[post_id] = {
                "contains_painpoint": (row.get("contains_painpoint") or "").strip().lower(),
                "root_cause_summary": row.get("root_cause_summary") or "",
                "ambiguity_flag": row.get("ambiguity_flag") or "",
                "notes": row.get("notes") or "",
                "split": row.get("split") or "",
            }
    if not labels:
        raise RuntimeError(f"No gold labels loaded from {gold_path}")
    return labels


def load_candidates(candidates_path: Path) -> Dict[str, Dict]:
    """
    Load DEV/TEST_candidates.jsonl and return mapping:
        post_id -> {
            "course_code": str,
            "full_post_text": str,
        }
    """
    import json as _json

    candidates: Dict[str, Dict] = {}
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

            candidates[post_id] = {
                "course_code": course_code,
                "full_post_text": text,
            }

    if not candidates:
        raise RuntimeError(f"No candidates loaded from {candidates_path}")
    return candidates


def determine_error_type(true_label: str, pred_label: str) -> str:
    """
    Compute TP/FP/FN/TN given:
        true_label in {"y","n"} (gold)
        pred_label in {"y","n","u"} (prediction)
    We treat "u" as "not predicted positive".
    """
    true_label = (true_label or "").lower()
    pred_label = (pred_label or "").lower()

    if true_label not in {"y", "n"}:
        return "IGNORE"

    if true_label == "y":
        if pred_label == "y":
            return "TP"
        return "FN"
    else:  # true_label == "n"
        if pred_label == "y":
            return "FP"
        return "TN"


def collect_rows_for_run(
    run_dir: Path,
    gold_by_post: Dict[str, Dict],
    candidates_by_post: Dict[str, Dict],
    split_filter: str | None = None,
) -> List[Dict]:
    """
    Load manifest + predictions for a single run directory and
    return a list of normalized rows ready for the combined CSV.

    Each row includes:
        run_name, run_dir, model_name, provider, split,
        prompt_filename, prompt_copied_path,
        post_id, course_code, full_post_text,
        gold_* fields,
        prediction fields,
        error_type.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    model_name = manifest.get("model_name", "")
    provider = manifest.get("provider", "")
    split = manifest.get("split", "")

    if split_filter and split != split_filter:
        # Skip runs for other splits (e.g., TEST if we only want DEV)
        return []

    # Prompt info; handle older manifests that may not have new keys
    prompt_template_path = manifest.get("prompt_template_path", "")
    prompt_filename = manifest.get("prompt_filename") or (
        Path(prompt_template_path).name if prompt_template_path else ""
    )
    prompt_copied_path = manifest.get("prompt_copied_path", "")

    # Build a human-readable run_name
    base_run_name = f"{model_name}_{split}" if model_name and split else run_dir.name
    run_name = base_run_name
    if prompt_filename:
        run_name = f"{base_run_name}_{prompt_filename}"

    # Predictions CSV
    predictions_path_str = manifest.get("predictions_path")
    if predictions_path_str:
        predictions_path = Path(predictions_path_str)
    else:
        predictions_path = run_dir / f"predictions_{split}.csv"

    if not predictions_path.is_file():
        raise FileNotFoundError(f"Predictions not found: {predictions_path}")

    rows: List[Dict] = []
    with predictions_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_id = row.get("post_id")
            if not post_id:
                continue

            gold = gold_by_post.get(post_id)
            if not gold:
                # Post not in gold; skip
                continue

            if split_filter and gold.get("split") != split_filter:
                continue

            cand = candidates_by_post.get(post_id)
            if not cand:
                # Candidate missing; skip
                continue

            gold_label = gold.get("contains_painpoint", "")
            pred_label = row.get("pred_contains_painpoint", "")

            error_type = determine_error_type(gold_label, pred_label)
            if error_type == "IGNORE":
                continue

            rows.append(
                {
                    "run_name": run_name,
                    "run_dir": str(run_dir),
                    "model_name": model_name,
                    "provider": provider,
                    "split": split,
                    "prompt_filename": prompt_filename,
                    "prompt_copied_path": prompt_copied_path,
                    "post_id": post_id,
                    "course_code": cand.get("course_code") or "",
                    "full_post_text": cand.get("full_post_text") or "",
                    "gold_contains_painpoint": gold_label,
                    "gold_root_cause_summary": gold.get("root_cause_summary") or "",
                    "gold_ambiguity_flag": gold.get("ambiguity_flag") or "",
                    "gold_notes": gold.get("notes") or "",
                    "pred_contains_painpoint": pred_label,
                    "root_cause_summary_pred": row.get("root_cause_summary_pred") or "",
                    "pain_point_snippet_pred": row.get("pain_point_snippet_pred") or "",
                    "confidence_pred": row.get("confidence_pred") or "",
                    "error_type": error_type,
                }
            )
    return rows


def write_combined_csv(all_rows: List[Dict], out_path: Path) -> None:
    """
    Write the combined analysis table to a single CSV file.
    """
    if not all_rows:
        raise RuntimeError("No rows to write in combined CSV.")

    fieldnames = [
        "run_name",
        "run_dir",
        "model_name",
        "provider",
        "split",
        "prompt_filename",
        "prompt_copied_path",
        "post_id",
        "course_code",
        "full_post_text",
        "gold_contains_painpoint",
        "gold_root_cause_summary",
        "gold_ambiguity_flag",
        "gold_notes",
        "pred_contains_painpoint",
        "root_cause_summary_pred",
        "pain_point_snippet_pred",
        "confidence_pred",
        "error_type",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)


def write_post_chunks(
    all_rows: List[Dict],
    out_dir: Path,
    combined_basename: str,
    posts_per_chunk: int,
) -> None:
    """
    Split the combined rows into post-centric chunks.

    Each chunk contains all models/prompts for a fixed number of posts,
    ordered by post_id. Files are named:

        <stem>_chunk1.csv
        <stem>_chunk2.csv
        ...

    where <stem> is the combined_basename without extension.
    """
    if not all_rows:
        raise RuntimeError("No rows available to split into chunks.")

    by_post = defaultdict(list)
    for row in all_rows:
        by_post[row["post_id"]].append(row)

    post_ids = sorted(by_post.keys())
    total_posts = len(post_ids)
    if total_posts == 0:
        raise RuntimeError("No post_ids found in combined rows.")

    stem = Path(combined_basename).stem
    chunks = []
    for i in range(0, total_posts, posts_per_chunk):
        chunk_ids = post_ids[i : i + posts_per_chunk]
        chunk_rows = [r for pid in chunk_ids for r in by_post[pid]]
        chunks.append((chunk_ids, chunk_rows))

    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(all_rows[0].keys())

    for idx, (chunk_ids, chunk_rows) in enumerate(chunks, start=1):
        out_path = out_dir / f"{stem}_chunk{idx}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(chunk_rows)
        print(
            f"wrote {out_path}  posts={len(chunk_ids)}  rows={len(chunk_rows)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Combine multiple Stage 1 benchmark runs into a single analysis CSV "
            "and produce post-centric chunks for LLM review."
        )
    )
    parser.add_argument(
        "--runs-dir",
        required=True,
        help="Base directory containing stage1_ run folders.",
    )
    parser.add_argument(
        "--glob",
        action="append",
        required=True,
        help=(
            "Glob pattern(s) under --runs-dir selecting which run directories to include. "
            "May be provided multiple times."
        ),
    )
    parser.add_argument(
        "--gold-path",
        default="artifacts/benchmark/gold/gold_labels.csv",
        help="Path to gold_labels.csv.",
    )
    parser.add_argument(
        "--candidates-path",
        default="artifacts/benchmark/DEV_candidates.jsonl",
        help="Path to DEV/TEST_candidates.jsonl (used for full_post_text).",
    )
    parser.add_argument(
        "--split",
        default="DEV",
        help="Split to include from gold/runs (e.g., DEV or TEST).",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/analysis",
        help="Directory where combined and chunked CSVs will be written.",
    )
    parser.add_argument(
        "--combined-name",
        default="combined_zero_vs_few_25dev.csv",
        help="Filename for the combined CSV.",
    )
    parser.add_argument(
        "--posts-per-chunk",
        type=int,
        default=5,
        help="Number of posts per chunk CSV (default 5).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    runs_base = Path(args.runs_dir)
    if not runs_base.is_dir():
        raise FileNotFoundError(f"Runs dir not found: {runs_base}")

    # Collect run directories from all glob patterns
    run_dirs = []
    for pattern in args.glob:
        run_dirs.extend(sorted(runs_base.glob(pattern)))

    # Deduplicate while preserving order
    seen = set()
    unique_run_dirs = []
    for rd in run_dirs:
        if rd not in seen:
            seen.add(rd)
            unique_run_dirs.append(rd)

    if not unique_run_dirs:
        raise RuntimeError("No run directories matched the provided glob patterns.")

    gold_by_post = load_gold_labels(Path(args.gold_path), split=args.split)
    candidates_by_post = load_candidates(Path(args.candidates_path))

    all_rows: List[Dict] = []
    for run_dir in unique_run_dirs:
        rows = collect_rows_for_run(
            run_dir=run_dir,
            gold_by_post=gold_by_post,
            candidates_by_post=candidates_by_post,
            split_filter=args.split,
        )
        if not rows:
            continue
        all_rows.extend(rows)

    if not all_rows:
        raise RuntimeError("No rows collected from the selected runs.")

    out_dir = Path(args.out_dir)
    combined_path = out_dir / args.combined_name

    write_combined_csv(all_rows, combined_path)
    print(f"Wrote combined CSV: {combined_path} (rows={len(all_rows)})")

    write_post_chunks(
        all_rows=all_rows,
        out_dir=out_dir,
        combined_basename=args.combined_name,
        posts_per_chunk=args.posts_per_chunk,
    )


if __name__ == "__main__":
    main()