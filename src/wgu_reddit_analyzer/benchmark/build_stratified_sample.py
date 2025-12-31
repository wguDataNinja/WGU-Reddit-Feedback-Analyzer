"""
Stage 1B — Stratified Sampling

Purpose:
    Build a small, deterministic, auditable DEV/TEST sample from the locked
    Stage 0 dataset for manual labeling and benchmark evaluation.

Inputs:
    - artifacts/stage0_filtered_posts.jsonl
    - Optional: artifacts/analysis/length_profile.json for length bounds.

Outputs:
    - artifacts/benchmark/DEV_candidates.jsonl
    - artifacts/benchmark/TEST_candidates.jsonl
    - artifacts/benchmark/DEV_candidates.csv
    - artifacts/benchmark/TEST_candidates.csv
    - artifacts/runs/sample_<timestamp>/sampling.log
    - artifacts/runs/sample_<timestamp>/manifest.json

Usage:
    From the repository root:
        PYTHONPATH=src python -m wgu_reddit_analyzer.benchmark.build_stratified_sample

    Overwrite existing outputs:
        PYTHONPATH=src python -m wgu_reddit_analyzer.benchmark.build_stratified_sample --force

Notes:
    - Applies fixed short/medium/long buckets (20–149, 150–299, 300–600 tokens).
    - Keeps all qualifying focus-course posts (D335) unconditionally.
    - Fills remaining capacity via deterministic round-robin across
      (course_code, length_bucket) up to a global target size.
    - Applies a deterministic 70/30 DEV/TEST split on the final pool.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.utils.token_utils import count_tokens
from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION

SEED = 20251107
DEFAULT_MIN_TOKENS = 20
DEFAULT_MAX_TOKENS = 600

FOCUS_COURSE = "D335"
TARGET_TOTAL = 200

BUCKET_BOUNDS: Dict[str, Tuple[int, int]] = {
    "short": (20, 149),
    "medium": (150, 299),
    "long": (300, 600),
}

OUTPUT_FIELDS = [
    "post_id",
    "course_code",
    "length_tokens",
    "length_bucket",
    "title",
    "selftext",
    "subreddit_name",
    "created_utc",
    "score",
    "num_comments",
    "permalink",
    "url",
    "vader_compound",
]

LOGGER = get_logger("build_stratified_sample")


@dataclass
class Candidate:
    """
    Sample candidate row derived from Stage 0.

    Attributes:
        is_focus: Indicates whether the candidate is in the focus course.
    """

    post_id: str
    course_code: str
    length_tokens: int
    length_bucket: str
    title: str
    selftext: str
    subreddit_name: Optional[str]
    created_utc: Optional[float]
    score: Optional[int]
    num_comments: Optional[int]
    permalink: Optional[str]
    url: Optional[str]
    vader_compound: Optional[float]
    is_focus: bool

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize candidate for output files.

        Returns:
            Dictionary without the internal is_focus flag.
        """
        return {
            "post_id": self.post_id,
            "course_code": self.course_code,
            "length_tokens": self.length_tokens,
            "length_bucket": self.length_bucket,
            "title": self.title,
            "selftext": self.selftext,
            "subreddit_name": self.subreddit_name,
            "created_utc": self.created_utc,
            "score": self.score,
            "num_comments": self.num_comments,
            "permalink": self.permalink,
            "url": self.url,
            "vader_compound": self.vader_compound,
        }


def infer_bucket(length_tokens: int) -> Optional[str]:
    """
    Map a token length to a configured length bucket.

    Args:
        length_tokens: Token length for a post.

    Returns:
        Bucket name if within bounds, otherwise None.
    """
    for name, (lower, upper) in BUCKET_BOUNDS.items():
        if lower <= length_tokens <= upper:
            return name
    return None


def load_length_bounds(length_profile_path: Path) -> Tuple[int, int]:
    """
    Load min/max token bounds from length_profile.json when available.

    Args:
        length_profile_path: Path to length_profile.json.

    Returns:
        Tuple of (min_tokens, max_tokens).
    """
    min_tokens = DEFAULT_MIN_TOKENS
    max_tokens = DEFAULT_MAX_TOKENS

    if not length_profile_path.exists():
        return min_tokens, max_tokens

    try:
        with length_profile_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        LOGGER.warning(
            "Failed to read length profile at %s, using defaults (%s-%s).",
            length_profile_path,
            min_tokens,
            max_tokens,
        )
        return min_tokens, max_tokens

    if isinstance(data, dict) and "bounds" in data:
        bounds = data["bounds"]
        if isinstance(bounds, dict):
            min_tokens = int(bounds.get("min_tokens", min_tokens))
            max_tokens = int(bounds.get("max_tokens", max_tokens))

    LOGGER.info(
        "Using length bounds: min_tokens=%s, max_tokens=%s.",
        min_tokens,
        max_tokens,
    )
    return min_tokens, max_tokens


def read_stage0_candidates(
    stage0_path: Path,
    min_tokens: int,
    max_tokens: int,
) -> Tuple[List[Candidate], int]:
    """
    Load Stage 0 records and filter to sampling candidates.

    Args:
        stage0_path: Path to Stage 0 JSONL.
        min_tokens: Minimum allowed token length.
        max_tokens: Maximum allowed token length.

    Returns:
        Tuple of:
            - List of Candidate objects.
            - Total Stage 0 records scanned.
    """
    candidates: List[Candidate] = []
    stage0_total = 0

    if not stage0_path.exists():
        raise FileNotFoundError(f"Stage 0 file not found: {stage0_path}")

    with stage0_path.open("r", encoding="utf-8") as handle:
        for raw_index, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            stage0_total += 1

            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.warning(
                    "Skipping invalid JSON line at index %s.",
                    raw_index,
                )
                continue

            course_code = rec.get("course_code")
            if not course_code:
                continue

            title = (rec.get("title") or "").strip()
            selftext = (rec.get("selftext") or "").strip()
            text = (title + "\n\n" + selftext).strip()
            length_tokens = count_tokens(text)

            if length_tokens < min_tokens or length_tokens > max_tokens:
                continue

            bucket = infer_bucket(length_tokens)
            if bucket is None:
                continue

            post_id = str(rec.get("post_id") or rec.get("id") or "").strip()
            if not post_id:
                continue

            candidates.append(
                Candidate(
                    post_id=post_id,
                    course_code=str(course_code),
                    length_tokens=length_tokens,
                    length_bucket=bucket,
                    title=title,
                    selftext=selftext,
                    subreddit_name=rec.get("subreddit_name"),
                    created_utc=rec.get("created_utc"),
                    score=rec.get("score"),
                    num_comments=rec.get("num_comments"),
                    permalink=rec.get("permalink"),
                    url=rec.get("url"),
                    vader_compound=rec.get("vader_compound"),
                    is_focus=(str(course_code) == FOCUS_COURSE),
                )
            )

    LOGGER.info(
        "Loaded %s records from Stage 0; %s after length filter.",
        stage0_total,
        len(candidates),
    )
    return candidates, stage0_total


def sample_with_global_target(
    candidates: List[Candidate],
    rng: random.Random,
    target_total: int,
) -> List[Candidate]:
    """
    Build a final candidate pool with a global target and focus-course guarantee.

    Args:
        candidates: All filtered Candidate objects.
        rng: Random instance seeded for determinism.
        target_total: Desired total size for DEV+TEST pool.

    Returns:
        Final list of selected candidates.
    """
    focus = [c for c in candidates if c.is_focus]
    non_focus = [c for c in candidates if not c.is_focus]

    target_non_focus = max(0, target_total - len(focus))

    if target_non_focus == 0 or not non_focus:
        LOGGER.info(
            "Global target satisfied by focus-course only or no non-focus "
            "available. Focus=%s, Non-focus_used=0.",
            len(focus),
        )
        final_pool = list(focus)
        if len(final_pool) < target_total:
            LOGGER.info(
                "Target not met; using all %s available candidates.",
                len(final_pool),
            )
        return final_pool

    by_stratum: Dict[Tuple[str, str], List[Candidate]] = {}
    for candidate in non_focus:
        key = (candidate.course_code, candidate.length_bucket)
        by_stratum.setdefault(key, []).append(candidate)

    for items in by_stratum.values():
        rng.shuffle(items)

    selected_non_focus: List[Candidate] = []
    while len(selected_non_focus) < target_non_focus:
        progressed = False
        for items in by_stratum.values():
            if not items:
                continue
            if len(selected_non_focus) >= target_non_focus:
                break
            selected_non_focus.append(items.pop())
            progressed = True
        if not progressed:
            break

    LOGGER.info(
        "Focus candidates kept: %s; Non-focus selected: %s (requested up to %s; "
        "non-focus available=%s).",
        len(focus),
        len(selected_non_focus),
        target_non_focus,
        len(non_focus),
    )

    final_pool = focus + selected_non_focus
    LOGGER.info(
        "Final candidate pool size: %s (target_total=%s).",
        len(final_pool),
        target_total,
    )
    if len(final_pool) < target_total:
        LOGGER.info(
            "Target not met; using all %s available candidates.",
            len(final_pool),
        )

    return final_pool


def stratified_dev_test_split(
    candidates: List[Candidate],
    rng: random.Random,
) -> Tuple[List[Candidate], List[Candidate]]:
    """
    Apply a global 70/30 DEV/TEST split to the final candidate pool.

    Args:
        candidates: Final candidate pool.
        rng: Random instance seeded for determinism.

    Returns:
        Tuple of (DEV_candidates, TEST_candidates).
    """
    items = list(candidates)
    rng.shuffle(items)

    n = len(items)
    if n == 0:
        return [], []

    dev_n = round(0.7 * n)
    dev_n = max(1, min(dev_n, n - 1))

    dev = items[:dev_n]
    test = items[dev_n:]

    LOGGER.info(
        "DEV count: %s; TEST count: %s (total=%s).",
        len(dev),
        len(test),
        n,
    )
    return dev, test


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """
    Write rows to a JSONL file.

    Args:
        path: Output file path.
        rows: Iterable of dict-like rows.
    """
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """
    Write rows to a CSV file with a fixed schema.

    Args:
        path: Output CSV path.
        rows: Iterable of dict-like rows.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in OUTPUT_FIELDS})


def build_manifest(
    run_id: str,
    stage0_path: Path,
    length_profile_path: Path,
    dev_path_jsonl: Path,
    test_path_jsonl: Path,
    dev_path_csv: Path,
    test_path_csv: Path,
    min_tokens: int,
    max_tokens: int,
    stage0_total: int,
    after_length_filter: int,
    dev_count: int,
    test_count: int,
    final_pool_count: int,
    target_total: int,
) -> Dict[str, Any]:
    """
    Build a manifest describing the Stage 1B sampling run.

    Returns:
        Manifest dictionary for serialization to JSON.
    """
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "stage1b_sampling",
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "script_name": Path(__file__).name,
        "git_commit": "uncommitted-local",
        "inputs": {
            "stage0_path": str(stage0_path),
            "length_profile_path": str(length_profile_path),
            "min_tokens": min_tokens,
            "max_tokens": max_tokens,
        },
        "outputs": {
            "dev_candidates_jsonl": str(dev_path_jsonl),
            "test_candidates_jsonl": str(test_path_jsonl),
            "dev_candidates_csv": str(dev_path_csv),
            "test_candidates_csv": str(test_path_csv),
        },
        "params": {
            "seed": SEED,
            "focus_course": FOCUS_COURSE,
            "target_total": target_total,
            "bucket_bounds": {
                name: {"min": lower, "max": upper}
                for name, (lower, upper) in BUCKET_BOUNDS.items()
            },
        },
        "counts": {
            "stage0_total": stage0_total,
            "after_length_filter": after_length_filter,
            "final_pool_count": final_pool_count,
            "dev_count": dev_count,
            "test_count": test_count,
        },
        "notes": (
            "Stratified sample within configured length bounds. All qualifying "
            "D335 posts retained. Non-focus posts selected via deterministic "
            "round-robin under a global target. Final pool split 70/30 into "
            "DEV/TEST."
        ),
    }


def configure_logging(log_path: Path) -> None:
    """
    Configure file and stdout logging for this script.

    Args:
        log_path: Path to the log file.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)

    LOGGER.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    LOGGER.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    LOGGER.addHandler(stream_handler)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse CLI arguments.

    Args:
        argv: Optional argument list.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Stage 1B: Build stratified DEV/TEST samples from Stage 0 "
            f"(~{TARGET_TOTAL} posts by default)."
        ),
    )
    parser.add_argument(
        "--stage0-path",
        default="artifacts/stage0_filtered_posts.jsonl",
        help="Path to Stage 0 filtered posts JSONL.",
    )
    parser.add_argument(
        "--length-profile-path",
        default="artifacts/analysis/length_profile.json",
        help="Path to length profile JSON (optional).",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/benchmark",
        help="Directory for DEV/TEST candidate outputs.",
    )
    parser.add_argument(
        "--runs-dir",
        default="artifacts/runs",
        help="Directory for run manifests and logs.",
    )
    parser.add_argument(
        "--target-total",
        type=int,
        default=TARGET_TOTAL,
        help=(
            "Global target for DEV+TEST candidates, including all focus-course "
            f"posts. Default: {TARGET_TOTAL}."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwrite of existing DEV/TEST candidate files.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint for Stage 1B stratified sampling.

    Args:
        argv: Optional argument list.

    Returns:
        Exit code: 0 on success, non-zero on failure.
    """
    args = parse_args(argv)

    stage0_path = Path(args.stage0_path)
    length_profile_path = Path(args.length_profile_path)
    out_dir = Path(args.out_dir)
    runs_dir = Path(args.runs_dir)
    target_total = int(args.target_total)

    dev_jsonl = out_dir / "DEV_candidates.jsonl"
    test_jsonl = out_dir / "TEST_candidates.jsonl"
    dev_csv = out_dir / "DEV_candidates.csv"
    test_csv = out_dir / "TEST_candidates.csv"

    existing = [
        path
        for path in (dev_jsonl, test_jsonl, dev_csv, test_csv)
        if path.exists()
    ]
    if existing and not args.force:
        message = (
            "DEV/TEST candidate files already exist. Use --force to overwrite:"
            "\n" + "\n".join(str(path) for path in existing)
        )
        print(message, file=sys.stderr)
        LOGGER.error("%s", message)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"sample_{timestamp}"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "sampling.log"
    configure_logging(log_path)

    LOGGER.info("Stage 1B sampling started.")
    LOGGER.info("Run directory: %s", run_dir)

    min_tokens, max_tokens = load_length_bounds(length_profile_path)
    candidates, stage0_total = read_stage0_candidates(
        stage0_path=stage0_path,
        min_tokens=min_tokens,
        max_tokens=max_tokens,
    )
    after_length_filter = len(candidates)

    rng = random.Random(SEED)
    final_pool = sample_with_global_target(
        candidates=candidates,
        rng=rng,
        target_total=target_total,
    )
    dev_candidates, test_candidates = stratified_dev_test_split(
        candidates=final_pool,
        rng=rng,
    )

    if len(dev_candidates) + len(test_candidates) != len(final_pool):
        LOGGER.warning(
            "DEV+TEST size (%s) does not match final pool size (%s).",
            len(dev_candidates) + len(test_candidates),
            len(final_pool),
        )

    dev_ids = {c.post_id for c in dev_candidates}
    test_ids = {c.post_id for c in test_candidates}
    overlap = dev_ids & test_ids
    if overlap:
        LOGGER.warning(
            "DEV/TEST sets share %s overlapping post_id(s); this should not "
            "happen.",
            len(overlap),
        )

    dev_rows = [c.to_dict() for c in dev_candidates]
    test_rows = [c.to_dict() for c in test_candidates]

    write_jsonl(dev_jsonl, dev_rows)
    write_jsonl(test_jsonl, test_rows)
    write_csv(dev_csv, dev_rows)
    write_csv(test_csv, test_rows)

    manifest = build_manifest(
        run_id=run_id,
        stage0_path=stage0_path,
        length_profile_path=length_profile_path,
        dev_path_jsonl=dev_jsonl,
        test_path_jsonl=test_jsonl,
        dev_path_csv=dev_csv,
        test_path_csv=test_csv,
        min_tokens=min_tokens,
        max_tokens=max_tokens,
        stage0_total=stage0_total,
        after_length_filter=after_length_filter,
        dev_count=len(dev_candidates),
        test_count=len(test_candidates),
        final_pool_count=len(final_pool),
        target_total=target_total,
    )

    manifest_path = run_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)

    LOGGER.info("Wrote manifest to %s.", manifest_path)
    LOGGER.info("Stage 1B sampling completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())