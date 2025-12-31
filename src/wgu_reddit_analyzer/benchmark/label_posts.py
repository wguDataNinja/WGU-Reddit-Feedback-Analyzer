from __future__ import annotations
"""
Stage 1C — Manual Labeling Tool

Interactive console tool to assign gold labels to Stage 1B DEV/TEST
candidates for the benchmark.

Run from repo root:

    PYTHONPATH=src python -m wgu_reddit_analyzer.benchmark.label_posts

Defaults:
  - Reads DEV/TEST candidates from artifacts/benchmark/*.jsonl
  - Writes labels to artifacts/benchmark/gold/gold_labels.csv
  - Creates run logs and manifest under artifacts/runs/

Label commands:
  y = actionable painpoint present
  n = no actionable painpoint
  u = ambiguous / unsure (mark ambiguous only)
  Enter = skip (no label; will show again later)
  q = quit

Ambiguous rows (u) are kept for transparency but excluded from scoring.
"""

import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.core.schema_definitions import SCHEMA_VERSION

LOGGER = get_logger("label_posts")

# Default repo-aware paths for typical layout usage
REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
BENCHMARK_DIR = ARTIFACTS_DIR / "benchmark"
GOLD_DIR = BENCHMARK_DIR / "gold"

DEV_PATH = BENCHMARK_DIR / "DEV_candidates.jsonl"
TEST_PATH = BENCHMARK_DIR / "TEST_candidates.jsonl"
GOLD_CSV = GOLD_DIR / "gold_labels.csv"

LABEL_COLUMNS = [
    "post_id",
    "split",
    "course_code",
    "contains_painpoint",   # "y" / "n" / "" (blank if ambiguous)
    "root_cause_summary",   # short free text (only for "y")
    "ambiguity_flag",       # "0" / "1" (1 iff command "u")
    "labeler_id",           # e.g. "AI1"
    "notes",                # optional free text
]

DEFAULT_LABELER_ID = "AI1"


@dataclass
class Candidate:
    post_id: str
    split: str
    course_code: str
    title: str
    selftext: str

    def key(self) -> Tuple[int, str, str]:
        # DEV before TEST, then by course_code, then post_id
        return (0 if self.split == "DEV" else 1, self.course_code, self.post_id)


def safe_clear() -> None:
    if os.name == "nt":
        os.system("cls")
    elif os.getenv("TERM"):
        os.system("clear")


def read_jsonl_candidates(path: Path, split: str) -> List[Candidate]:
    if not path.exists():
        raise FileNotFoundError(f"Missing candidate file: {path}")
    out: List[Candidate] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            post_id = (rec.get("post_id") or "").strip()
            if not post_id:
                continue
            course_code = (rec.get("course_code") or "").strip()
            title = (rec.get("title") or "").strip()
            selftext = (rec.get("selftext") or "").strip()
            out.append(Candidate(post_id, split, course_code, title, selftext))
    return out


def load_candidates(dev_path: Path, test_path: Path) -> List[Candidate]:
    dev = read_jsonl_candidates(dev_path, "DEV")
    test = read_jsonl_candidates(test_path, "TEST")
    all_c = dev + test

    # Deduplicate by post_id; DEV wins on conflict
    seen: Dict[str, Candidate] = {}
    for c in sorted(all_c, key=Candidate.key):
        if c.post_id not in seen:
            seen[c.post_id] = c

    candidates = list(seen.values())
    candidates.sort(key=Candidate.key)
    return candidates


def load_existing_labels(path: Path) -> Dict[str, Dict[str, str]]:
    labels: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return labels
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("post_id")
            if pid:
                labels[pid] = row
    return labels


def write_labels(path: Path, labels: Dict[str, Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        labels.values(),
        key=lambda r: (
            0 if r.get("split") == "DEV" else 1,
            r.get("course_code", ""),
            r.get("post_id", ""),
        ),
    )
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in LABEL_COLUMNS})


def create_run_context() -> Tuple[Path, str]:
    runs_dir = ARTIFACTS_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"label_{ts}"
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, run_id


def configure_logging(log_path: Path) -> None:
    # Reset handlers for clean per-run logging
    for h in list(LOGGER.handlers):
        LOGGER.removeHandler(h)
    LOGGER.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)
    LOGGER.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    LOGGER.addHandler(sh)


def write_manifest(
    run_dir: Path,
    run_id: str,
    dev_path: Path,
    test_path: Path,
    gold_csv: Path,
    labeler_id: str,
    total: int,
    labeled: int,
) -> None:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "stage1c_labeling",
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "script_name": Path(__file__).name,
        "inputs": {
            "dev_candidates": str(dev_path),
            "test_candidates": str(test_path),
        },
        "outputs": {
            "gold_labels_csv": str(gold_csv),
        },
        "params": {
            "labeler_id_default": labeler_id,
            "schema_columns": LABEL_COLUMNS,
        },
        "counts": {
            "total_candidates": total,
            "labeled_rows": labeled,
        },
        "notes": "Manual gold labels for Stage 1B candidates; resume-safe.",
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def prompt_label(c: Candidate, labeler_id: str) -> Optional[Dict[str, str]]:
    safe_clear()
    print(f"[{c.split}] {c.course_code}  post_id={c.post_id}")
    print("-" * 60)
    print("Title:")
    print(c.title or "(no title)")
    print("\nSelftext:")
    body = c.selftext or "(no selftext)"
    width = 100
    for i in range(0, len(body), width):
        print(body[i : i + width])
    print("-" * 60)
    print("Commands: y = painpoint, n = no painpoint, u = ambiguous, q = quit, Enter = skip")

    cmd = input("contains_painpoint [y/n/u]: ").strip().lower()

    if cmd == "q":
        return None

    if cmd == "":
        # skip: no label saved; will reappear next run
        return {}

    if cmd not in ("y", "n", "u"):
        print("Invalid input, skipping.")
        return {}

    contains_painpoint = ""
    root_cause_summary = ""
    notes = ""
    ambiguity_flag = "0"

    if cmd == "y":
        contains_painpoint = "y"
        root_cause_summary = input("root_cause_summary (short, optional): ").strip()
        notes = input("notes (optional, Enter to skip): ").strip()
        ambiguity_flag = "0"

    elif cmd == "n":
        contains_painpoint = "n"
        notes = input("notes (optional, Enter to skip): ").strip()
        ambiguity_flag = "0"

    elif cmd == "u":
        # Mark ambiguous; do not assert a painpoint label
        contains_painpoint = ""
        notes = input("notes (optional, Enter to skip): ").strip()
        ambiguity_flag = "1"

    return {
        "post_id": c.post_id,
        "split": c.split,
        "course_code": c.course_code,
        "contains_painpoint": contains_painpoint,
        "root_cause_summary": root_cause_summary,
        "ambiguity_flag": ambiguity_flag,
        "labeler_id": labeler_id,
        "notes": notes,
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 1C: Manual labeling tool for Stage 1B DEV/TEST candidates "
            "to create gold_labels.csv."
        )
    )
    parser.add_argument(
        "--dev-path",
        default=str(DEV_PATH),
        help="Path to DEV_candidates.jsonl (default: artifacts/benchmark/DEV_candidates.jsonl).",
    )
    parser.add_argument(
        "--test-path",
        default=str(TEST_PATH),
        help="Path to TEST_candidates.jsonl (default: artifacts/benchmark/TEST_candidates.jsonl).",
    )
    parser.add_argument(
        "--gold-csv",
        default=str(GOLD_CSV),
        help="Output CSV for gold labels (default: artifacts/benchmark/gold/gold_labels.csv).",
    )
    parser.add_argument(
        "--labeler-id",
        default=DEFAULT_LABELER_ID,
        help=f"Labeler ID to record in outputs (default: {DEFAULT_LABELER_ID}).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    dev_path = Path(args.dev_path)
    test_path = Path(args.test_path)
    gold_csv = Path(args.gold_csv)
    labeler_id = args.labeler_id

    run_dir, run_id = create_run_context()
    configure_logging(run_dir / "labeling.log")

    LOGGER.info("Stage 1C labeling started. Run directory: %s", run_dir)
    LOGGER.info("Using DEV candidates: %s", dev_path)
    LOGGER.info("Using TEST candidates: %s", test_path)
    LOGGER.info("Gold CSV path: %s", gold_csv)
    LOGGER.info("Labeler ID: %s", labeler_id)

    candidates = load_candidates(dev_path, test_path)
    LOGGER.info("Loaded %s candidates (DEV+TEST).", len(candidates))

    labels = load_existing_labels(gold_csv)
    LOGGER.info("Existing labels loaded: %s", len(labels))

    labeled_this_run = 0

    for idx, c in enumerate(candidates, start=1):
        if c.post_id in labels:
            continue

        print(f"\nPost {idx}/{len(candidates)} (unlabeled)")
        res = prompt_label(c, labeler_id=labeler_id)

        if res is None:
            LOGGER.info("Quit requested. Stopping.")
            break

        if not res:
            continue

        labels[c.post_id] = res
        write_labels(gold_csv, labels)
        labeled_this_run += 1
        LOGGER.info(
            "Labeled post_id=%s split=%s contains_painpoint='%s' ambiguity_flag=%s",
            c.post_id,
            c.split,
            res["contains_painpoint"],
            res["ambiguity_flag"],
        )

    write_manifest(
        run_dir=run_dir,
        run_id=run_id,
        dev_path=dev_path,
        test_path=test_path,
        gold_csv=gold_csv,
        labeler_id=labeler_id,
        total=len(candidates),
        labeled=len(labels),
    )

    LOGGER.info(
        "Stage 1C labeling complete. Total labeled: %s (this run: %s).",
        len(labels),
        labeled_this_run,
    )
    LOGGER.info("Gold labels CSV: %s", gold_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())