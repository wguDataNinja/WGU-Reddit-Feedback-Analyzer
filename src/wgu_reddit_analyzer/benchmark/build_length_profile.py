"""
Length Profile Builder — Stage 1A

Purpose:
    Analyze token-length distributions in the authoritative Stage 0 dataset
    to inform a defensible MAX_TOKENS cutoff for sampling and LLM benchmarking.

Inputs:
    - artifacts/stage0_filtered_posts.jsonl

Outputs:
    - artifacts/analysis/length_profile.csv
        One row per post_id with token length.
    - artifacts/analysis/length_histogram.csv
        Bucketed token-length counts for quick plotting.
    - artifacts/analysis/length_profile.json
        Summary statistics (no cutoff enforced).
    - artifacts/runs/length_profile_<run_id>/manifest.json
    - artifacts/runs/length_profile_<run_id>/length_profile.log

Usage:
    # Basic analysis run (fails if outputs already exist)
    python -m wgu_reddit_analyzer.benchmark.build_length_profile

    # Force re-run and overwrite previous analysis files
    python -m wgu_reddit_analyzer.benchmark.build_length_profile --force

Notes:
    - Analysis-only: does not modify Stage 0.
    - suggested_max_tokens is NOT set here; choose it manually after reviewing
      the histogram and extremes, then feed that into the sampling stage.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.utils.token_utils import count_tokens

logger = get_logger("length_profile")


def project_root() -> Path:
    """
    Repository root.

    File is at:
        src/wgu_reddit_analyzer/benchmark/build_length_profile.py
    Root is three levels up.
    """
    return Path(__file__).resolve().parents[3]


def default_stage0_path() -> Path:
    return project_root() / "artifacts" / "stage0_filtered_posts.jsonl"


def default_analysis_dir() -> Path:
    return project_root() / "artifacts" / "analysis"


def default_runs_dir() -> Path:
    return project_root() / "artifacts" / "runs"


@dataclass
class LengthStats:
    total_records: int
    nonempty_text_records: int
    min_tokens: int
    max_tokens: int
    mean_tokens: float
    median_tokens: int
    p90_tokens: int
    p95_tokens: int
    p99_tokens: int


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quantile(sorted_vals: List[int], q: float) -> int:
    if not sorted_vals:
        return 0
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]

    idx = (len(sorted_vals) - 1) * q
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]

    frac = idx - lo
    return int(round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac))


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _open_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSON line")
                continue


def compute_lengths(stage0_path: Path) -> Tuple[List[Tuple[str, str, int]], LengthStats]:
    lengths: List[int] = []
    rows: List[Tuple[str, str, int]] = []

    total_records = 0
    nonempty_text_records = 0

    for rec in _open_jsonl(stage0_path):
        total_records += 1

        post_id = str(rec.get("post_id", "")).strip()
        course_code = str(rec.get("course_code", "")).strip()

        title = str(rec.get("title", "") or "").strip()
        selftext = str(rec.get("selftext", "") or "").strip()
        text = f"{title}\n\n{selftext}".strip()

        if not post_id:
            continue
        if not text:
            continue

        length_tokens = count_tokens(text)
        if length_tokens <= 0:
            continue

        nonempty_text_records += 1
        rows.append((post_id, course_code, length_tokens))
        lengths.append(length_tokens)

    logger.info("Stage 0 records seen: %d", total_records)
    logger.info("Records with non-empty text: %d", nonempty_text_records)

    if not lengths:
        raise SystemExit("No valid records with non-empty text found in Stage 0.")

    lengths.sort()

    min_tokens = lengths[0]
    max_tokens = lengths[-1]
    mean_tokens = sum(lengths) / len(lengths)
    median_tokens = _quantile(lengths, 0.5)
    p90_tokens = _quantile(lengths, 0.9)
    p95_tokens = _quantile(lengths, 0.95)
    p99_tokens = _quantile(lengths, 0.99)

    stats = LengthStats(
        total_records=total_records,
        nonempty_text_records=nonempty_text_records,
        min_tokens=min_tokens,
        max_tokens=max_tokens,
        mean_tokens=mean_tokens,
        median_tokens=median_tokens,
        p90_tokens=p90_tokens,
        p95_tokens=p95_tokens,
        p99_tokens=p99_tokens,
    )

    return rows, stats


def write_length_profile_csv(rows: List[Tuple[str, str, int]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["post_id", "course_code", "length_tokens"])
        writer.writerows(rows)


def write_histogram_csv(
    rows: List[Tuple[str, str, int]],
    path: Path,
    bin_size: int = 50,
) -> None:
    if not rows:
        return

    max_len = max(length_tokens for _, _, length_tokens in rows)
    num_bins = max(1, (max_len // bin_size) + 1)

    counts = [0] * num_bins
    for _, _, length_tokens in rows:
        idx = min(length_tokens // bin_size, num_bins - 1)
        counts[idx] += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bucket_start_tokens", "bucket_end_tokens", "count"])
        for i, count in enumerate(counts):
            start = i * bin_size
            end = start + bin_size - 1
            writer.writerow([start, end, count])


def write_summary_json(
    stats: LengthStats,
    stage0_path: Path,
    json_path: Path,
    suggested_max_tokens: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    payload = {
        "input_path": str(stage0_path),
        "generated_utc": _now_utc_iso(),
        "total_records": stats.total_records,
        "nonempty_text_records": stats.nonempty_text_records,
        "min_tokens": stats.min_tokens,
        "max_tokens": stats.max_tokens,
        "mean_tokens": stats.mean_tokens,
        "median_tokens": stats.median_tokens,
        "p90_tokens": stats.p90_tokens,
        "p95_tokens": stats.p95_tokens,
        "p99_tokens": stats.p99_tokens,
    }

    if suggested_max_tokens is not None:
        payload["suggested_max_tokens"] = suggested_max_tokens
    if note:
        payload["note"] = note

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_run_manifest(
    run_dir: Path,
    stats: LengthStats,
    stage0_path: Path,
    profile_csv: Path,
    hist_csv: Path,
    summary_json: Path,
) -> None:
    manifest = {
        "stage": "length_profile",
        "run_id": run_dir.name,
        "timestamp_utc": _now_utc_iso(),
        "script_name": "wgu_reddit_analyzer/benchmark/build_length_profile.py",
        "inputs": {
            "stage0_path": str(stage0_path),
        },
        "outputs": {
            "length_profile_csv": str(profile_csv),
            "length_histogram_csv": str(hist_csv),
            "length_profile_json": str(summary_json),
        },
        "stats": asdict(stats),
        "params": {
            "bin_size_tokens": 50,
            "suggested_max_tokens": None,
        },
        "notes": (
            "Analysis-only Stage 1A run. Inspect histogram and extremes before "
            "choosing MAX_TOKENS for sampling."
        ),
    }

    with (run_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def write_run_log(run_dir: Path, stats: LengthStats, stage0_path: Path) -> None:
    lines = [
        f"Length profile run (tokens): {run_dir.name}",
        f"Input: {stage0_path}",
        f"Total Stage 0 records seen: {stats.total_records}",
        f"Records with non-empty text: {stats.nonempty_text_records}",
        f"Min tokens: {stats.min_tokens}",
        f"Max tokens: {stats.max_tokens}",
        f"Mean tokens: {stats.mean_tokens:.2f}",
        f"Median tokens: {stats.median_tokens}",
        f"P90 tokens: {stats.p90_tokens}",
        f"P95 tokens: {stats.p95_tokens}",
        f"P99 tokens: {stats.p99_tokens}",
        "",
        "Note: suggested_max_tokens not set in this analysis run.",
        "Decide final cutoff after inspecting histogram and spot-checking extremes.",
    ]
    with (run_dir / "length_profile.log").open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1A: Build token-based length profile from Stage 0 (analysis only)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_stage0_path(),
        help="Path to Stage 0 JSONL (default: artifacts/stage0_filtered_posts.jsonl)",
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=default_analysis_dir(),
        help="Directory for analysis outputs (default: artifacts/analysis)",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=default_runs_dir(),
        help="Directory for run manifests/logs (default: artifacts/runs)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing analysis outputs.",
    )

    args = parser.parse_args()

    stage0_path: Path = args.input
    analysis_dir: Path = args.analysis_dir
    runs_dir: Path = args.runs_dir

    if not stage0_path.exists():
        raise SystemExit(f"Stage 0 file not found: {stage0_path}")

    _ensure_dir(analysis_dir)
    _ensure_dir(runs_dir)

    profile_csv = analysis_dir / "length_profile.csv"
    hist_csv = analysis_dir / "length_histogram.csv"
    summary_json = analysis_dir / "length_profile.json"

    if not args.force:
        for p in (profile_csv, hist_csv, summary_json):
            if p.exists():
                raise SystemExit(
                    f"Output file already exists: {p} (use --force to overwrite)"
                )

    logger.info("Reading Stage 0 from: %s", stage0_path)
    rows, stats = compute_lengths(stage0_path)

    logger.info("Writing length_profile.csv (token lengths)")
    write_length_profile_csv(rows, profile_csv)

    logger.info("Writing length_histogram.csv (token lengths)")
    write_histogram_csv(rows, hist_csv)

    logger.info("Writing length_profile.json (summary, no cutoff yet)")
    write_summary_json(stats, stage0_path, summary_json)

    run_dir = runs_dir / f"length_profile_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    _ensure_dir(run_dir)

    logger.info("Writing run manifest and log under: %s", run_dir)
    write_run_manifest(run_dir, stats, stage0_path, profile_csv, hist_csv, summary_json)
    write_run_log(run_dir, stats, stage0_path)

    logger.info("Done. Inspect histogram and extremes before choosing MAX_TOKENS.")


if __name__ == "__main__":
    main()