"""
Create a clustering-ready painpoints table from Stage 1 full-corpus predictions.

Inputs (relative to repo root)
  Default:
    artifacts/stage1/full_corpus/LATEST/predictions_FULL.csv
  Optional override:
    --input-predictions PATH

Outputs (relative to repo root)
  artifacts/stage2/painpoints_llm_friendly.csv
  artifacts/stage2/manifest.json

Filtering rules
  Keep a row only if:
    - pred_contains_painpoint == "y"
    - parse_error, schema_error, used_fallback, llm_failure are all false
    - root_cause_summary_pred is non-empty after stripping whitespace
    - pain_point_snippet_pred is non-empty after stripping whitespace

Output ordering (deterministic)
  - primary: number of posts per course (descending)
  - tie-breakers: course_code, then post_id
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_INPUT_REL = Path("artifacts/stage1/full_corpus/LATEST/predictions_FULL.csv")
DEFAULT_OUTPUT_REL = Path("artifacts/stage2/painpoints_llm_friendly.csv")
DEFAULT_MANIFEST_REL = Path("artifacts/stage2/manifest.json")

_REQUIRED_COLUMNS = [
    "post_id",
    "course_code",
    "pred_contains_painpoint",
    "root_cause_summary_pred",
    "pain_point_snippet_pred",
    "parse_error",
    "schema_error",
    "used_fallback",
    "llm_failure",
]

_TRUE_VALUES = {"true", "1", "y", "yes"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _make_run_id() -> str:
    return f"stage2_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def _git_info(repo_root: Path) -> Dict[str, Any]:
    head = repo_root / ".git" / "HEAD"
    if not head.exists():
        return {"present": False}
    try:
        head_txt = head.read_text(encoding="utf-8").strip()
        if head_txt.startswith("ref:"):
            ref = head_txt.split(" ", 1)[1].strip()
            ref_path = repo_root / ".git" / ref
            sha = ref_path.read_text(encoding="utf-8").strip() if ref_path.exists() else None
            return {"present": True, "head": sha, "ref": ref}
        return {"present": True, "head": head_txt, "ref": None}
    except Exception as e:
        return {"present": True, "error": str(e)}


def _require_relpath(p: Path, arg_name: str) -> Path:
    """
    Enforce repo-relative paths for CLI arguments.
    Returns an absolute path resolved under REPO_ROOT.
    """
    if p.is_absolute():
        raise SystemExit(f"{arg_name} must be a relative path (relative to repo root), got: {p}")
    return (REPO_ROOT / p).resolve()


def _flag_is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUE_VALUES


def _validate_header(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise SystemExit("Input CSV appears to have no header row.")
    missing = [c for c in _REQUIRED_COLUMNS if c not in fieldnames]
    if missing:
        raise SystemExit(f"Input CSV is missing required columns: {', '.join(missing)}")


def prepare_painpoints(input_csv: Path, output_csv: Path) -> Dict[str, Any]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    painpoints: list[dict[str, str]] = []
    total = 0
    drop_reasons: dict[str, int] = defaultdict(int)

    with input_csv.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        _validate_header(reader.fieldnames)

        for row in reader:
            total += 1

            if row.get("pred_contains_painpoint") != "y":
                drop_reasons["not_painpoint"] += 1
                continue

            if any(_flag_is_true(row.get(flag)) for flag in ("parse_error", "schema_error", "used_fallback", "llm_failure")):
                drop_reasons["error_flagged"] += 1
                continue

            root_cause = (row.get("root_cause_summary_pred") or "").strip()
            snippet = (row.get("pain_point_snippet_pred") or "").strip()

            if not root_cause:
                drop_reasons["empty_root_cause_summary"] += 1
                continue
            if not snippet:
                drop_reasons["empty_pain_point_snippet"] += 1
                continue

            painpoints.append(
                {
                    "post_id": row["post_id"],
                    "course_code": row["course_code"],
                    "root_cause_summary": root_cause,
                    "pain_point_snippet": snippet,
                }
            )

    course_post_ids: dict[str, set[str]] = defaultdict(set)
    for p in painpoints:
        course_post_ids[p["course_code"]].add(p["post_id"])

    painpoints.sort(
        key=lambda r: (
            -len(course_post_ids[r["course_code"]]),
            r["course_code"],
            r["post_id"],
        )
    )

    with output_csv.open("w", newline="", encoding="utf-8") as f_out:
        fieldnames = ["post_id", "course_code", "root_cause_summary", "pain_point_snippet"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(painpoints)

    return {
        "total_rows_read": total,
        "rows_written": len(painpoints),
        "drop_reasons": dict(drop_reasons),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Stage 2: preprocess Stage 1 predictions into a clustering-ready painpoints CSV."
    )
    p.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_REL,
        help="Relative path to Stage 1 predictions_FULL.csv (default uses LATEST).",
    )
    p.add_argument(
        "--input-predictions",
        type=Path,
        default=None,
        help="Explicit relative path to Stage 1 predictions_FULL.csv (overrides --input).",
    )
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_REL, help="Relative path to write painpoints CSV")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_REL, help="Relative path to write manifest.json")
    args = p.parse_args()

    input_rel: Path = args.input_predictions if args.input_predictions is not None else args.input
    output_rel: Path = args.output
    manifest_rel: Path = args.manifest

    input_csv = _require_relpath(input_rel, "--input-predictions" if args.input_predictions is not None else "--input")
    output_csv = _require_relpath(output_rel, "--output")
    manifest_path = _require_relpath(manifest_rel, "--manifest")

    if not input_csv.exists():
        raise SystemExit(f"Input not found: {input_rel}")

    started_at = _utc_now()
    run_id = _make_run_id()

    summary = prepare_painpoints(input_csv=input_csv, output_csv=output_csv)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "stage": "stage2",
        "run_id": run_id,
        "created_at_utc": started_at,
        "command": " ".join([os.path.basename(__file__)] + [a for a in os.sys.argv[1:]]),
        "inputs": {
            "predictions_full_csv": {
                "path": str(input_rel),
                "bytes": input_csv.stat().st_size,
            }
        },
        "outputs": {
            "painpoints_llm_friendly_csv": {
                "path": str(output_rel),
                "bytes": output_csv.stat().st_size,
            }
        },
        "counts": summary,
        "git": _git_info(REPO_ROOT),
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Done. Kept {summary['rows_written']} painpoints out of {summary['total_rows_read']} rows read.")
    print(f"Written CSV: {output_rel}")
    print(f"Written manifest: {manifest_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())