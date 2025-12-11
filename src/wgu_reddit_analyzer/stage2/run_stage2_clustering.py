
from __future__ import annotations

"""
Stage 2 cluster runner.

Reads Stage-1 painpoint summaries, groups them by course, and calls an LLM
to produce course-level painpoint clusters in a canonical JSON schema.

Inputs:
    - artifacts/stage2/painpoints_llm_friendly.csv
    - data/course_list_with_college.csv
    - prompts/s2_cluster_batch.txt

Outputs (per Stage-2 run):
    - artifacts/stage2/runs/<run_slug>_<timestamp>/:
        - clusters/<course_code>.json              (cluster JSON, Stage 2 schema)
        - painpoints_used_<course_code>.jsonl      (per-course inputs)
        - stage2_prompt.txt                        (copy of the prompt)
        - manifest.json                            (Stage 2 run manifest)
"""

from dataclasses import dataclass
import argparse
import csv
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.benchmark.model_client import generate
from wgu_reddit_analyzer.stage2.validate_clusters import validate_clusters_dict
from wgu_reddit_analyzer.stage2.stage2_types import (
    PainpointRecord,
    Stage2CourseClusterSummary,
    Stage2RunManifest,
)

logger = get_logger("stage2.run_clustering")


@dataclass
class Painpoint:
    post_id: str
    course_code: str
    root_cause_summary: str
    pain_point_snippet: str


def ensure_stage2_run_dir(run_slug: str, out_root: Path) -> Path:
    """
    Create a new Stage 2 run directory:

        <out_root>/runs/<run_slug>_<timestamp>/
    """
    base = out_root / "runs"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base / f"{run_slug}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_painpoints(csv_path: Path) -> List[Painpoint]:
    """
    Load preprocessed painpoints from CSV.

    Expected header:
        post_id,course_code,root_cause_summary,pain_point_snippet
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"Painpoints CSV not found at {csv_path}")

    items: List[Painpoint] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("post_id"):
                continue
            summary = (row.get("root_cause_summary") or "").strip()
            snippet = (row.get("pain_point_snippet") or "").strip()
            if not summary and not snippet:
                continue
            items.append(
                Painpoint(
                    post_id=row["post_id"],
                    course_code=row["course_code"],
                    root_cause_summary=summary,
                    pain_point_snippet=snippet,
                )
            )

    if not items:
        raise RuntimeError(f"No painpoints loaded from {csv_path}")

    logger.info("Loaded %d painpoints from %s", len(items), csv_path)
    return items


def load_course_titles(meta_csv: Path) -> Dict[str, str]:
    """
    Load course titles from course metadata CSV.

    Expected header:
        CourseCode,Title,Colleges
    """
    if not meta_csv.is_file():
        raise FileNotFoundError(f"Course metadata CSV not found at {meta_csv}")

    mapping: Dict[str, str] = {}
    with meta_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("CourseCode") or "").strip()
            title = (row.get("Title") or "").strip()
            if not code:
                continue
            mapping[code] = title or code

    if not mapping:
        raise RuntimeError(f"No course titles loaded from {meta_csv}")

    logger.info("Loaded %d course titles from %s", len(mapping), meta_csv)
    return mapping


def group_by_course(painpoints: Iterable[Painpoint]) -> Dict[str, List[Painpoint]]:
    """
    Group painpoints by course_code.
    """
    grouped: Dict[str, List[Painpoint]] = {}
    for p in painpoints:
        grouped.setdefault(p.course_code, []).append(p)
    return grouped


def load_prompt_template(prompt_path: Path) -> str:
    """
    Load the Stage-2 clustering prompt template.
    """
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Stage-2 prompt not found at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def build_cluster_prompt(
    template: str,
    course_code: str,
    course_title: str,
    posts: List[Mapping[str, Any]],
) -> str:
    """
    Build the concrete LLM prompt for one course.

    The template contains {course_code} and {course_title} placeholders.
    The posts list is appended as JSON.
    """
    prompt = (
        template.replace("{course_code}", course_code)
        .replace("{course_title}", course_title)
    )

    posts_json = json.dumps(posts, ensure_ascii=False, indent=2)
    prompt += "\n\nPOSTS:\n"
    prompt += posts_json
    return prompt


def extract_json_from_response(raw_text: str) -> Any:
    """
    Extract the outermost JSON object from the LLM response.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("Empty LLM response")

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON object in LLM response")

    json_str = raw_text[start : end + 1]
    return json.loads(json_str)


def write_per_course_inputs(
    out_dir: Path, course_code: str, posts: List[Mapping[str, Any]]
) -> None:
    """
    Archive the exact painpoint rows used for Stage-2 clustering per course.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"painpoints_used_{course_code}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for obj in posts:
            f.write(json.dumps(obj, ensure_ascii=False))
            f.write("\n")


def _convert_to_painpoint_records(
    painpoints: List[Painpoint],
) -> List[PainpointRecord]:
    """
    Convenience conversion to PainpointRecord models (for type safety elsewhere if needed).
    """
    return [
        PainpointRecord(
            post_id=p.post_id,
            course_code=p.course_code,
            root_cause_summary=p.root_cause_summary,
            pain_point_snippet=p.pain_point_snippet,
        )
        for p in painpoints
    ]


def run_stage2_clustering(
    model_name: str,
    prompt_path: Path,
    painpoints_csv: Path,
    course_meta_csv: Path,
    out_root: Path,
    limit_courses: int | None = None,
    debug: bool = False,
) -> None:
    """
    Execute Stage-2 clustering across all courses present in painpoints CSV.

    Creates a run directory under:
        out_root / "runs" / <run_slug>_<timestamp>/
    """
    logger.info(
        "Starting Stage 2 clustering: model=%s painpoints=%s",
        model_name,
        painpoints_csv,
    )

    # Load inputs
    painpoints = load_painpoints(painpoints_csv)
    course_titles = load_course_titles(course_meta_csv)
    grouped = group_by_course(painpoints)
    prompt_template = load_prompt_template(prompt_path)

    # Run identity (Stage-1 style: model + mode + corpus tag)
    if limit_courses is None:
        corpus_tag = "full"
    else:
        corpus_tag = f"{limit_courses}courses"

    run_slug = f"{model_name}_s2_cluster_{corpus_tag}"
    run_dir = ensure_stage2_run_dir(run_slug, out_root=out_root)
    clusters_dir = run_dir / "clusters"
    clusters_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Stage 2 run dir: %s", run_dir)

    # Archive the prompt for reproducibility.
    prompt_copy_path = run_dir / "stage2_prompt.txt"
    shutil.copy2(prompt_path, prompt_copy_path)

    # Optional: limit number of courses for smoke tests.
    course_codes = sorted(grouped.keys())
    if limit_courses is not None:
        course_codes = course_codes[:limit_courses]

    # Manifest accounting
    started_at = time.time()
    total_cost = 0.0
    total_elapsed = 0.0
    num_cluster_calls = 0
    total_painpoints = len(painpoints)
    per_course_summary: Dict[str, Stage2CourseClusterSummary] = {}

    for course_code in course_codes:
        posts_for_course = grouped[course_code]
        if not posts_for_course:
            continue

        course_title = course_titles.get(course_code, course_code)

        logger.info(
            "Clustering course %s (%s) with %d painpoints",
            course_code,
            course_title,
            len(posts_for_course),
        )

        # Build per-course input objects for the LLM.
        posts_payload: List[Dict[str, Any]] = [
            {
                "post_id": p.post_id,
                "root_cause_summary": p.root_cause_summary,
                "pain_point_snippet": p.pain_point_snippet,
            }
            for p in posts_for_course
        ]

        # Archive the exact inputs for this course.
        write_per_course_inputs(run_dir, course_code, posts_payload)

        # Build prompt and call LLM.
        llm_prompt = build_cluster_prompt(
            template=prompt_template,
            course_code=course_code,
            course_title=course_title,
            posts=posts_payload,
        )

        llm_result = generate(model_name=model_name, prompt=llm_prompt)  # type: ignore[arg-type]
        num_cluster_calls += 1

        raw_text = llm_result.raw_text or ""
        if debug:
            logger.debug("LLM raw response for %s:\n%s", course_code, raw_text)

        # Aggregate cost and time
        total_cost += llm_result.total_cost_usd or 0.0
        total_elapsed += llm_result.elapsed_sec or 0.0

        # Parse and validate JSON.
        clusters_obj = extract_json_from_response(raw_text)

        valid_post_ids = {p.post_id for p in posts_for_course}
        validate_clusters_dict(
            clusters_obj,
            course_code=course_code,
            valid_post_ids=valid_post_ids,
            expected_total_posts=len(posts_for_course),
        )

        # Write canonical cluster JSON.
        out_path = clusters_dir / f"{course_code}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(clusters_obj, f, ensure_ascii=False, indent=2)

        # Per-course summary for manifest
        per_course_summary[course_code] = Stage2CourseClusterSummary(
            course_code=course_code,
            num_clusters=len(clusters_obj.get("courses", [])[0].get("clusters", [])),
            num_painpoints=len(posts_for_course),
            cluster_file=str(out_path),
            llm_model_name=llm_result.model_name,
            llm_provider=llm_result.provider,
            llm_total_cost_usd=llm_result.total_cost_usd,
            llm_elapsed_sec=llm_result.elapsed_sec,
        )

        logger.info("Wrote clusters for %s to %s", course_code, out_path)

    finished_at = time.time()
    wallclock = finished_at - started_at

    # Build and write manifest
    manifest = Stage2RunManifest(
        stage2_run_dir=str(run_dir),
        stage2_run_slug=run_slug,
        painpoints_csv_path=str(painpoints_csv),
        course_meta_csv_path=str(course_meta_csv),
        cluster_model_name=model_name,
        cluster_prompt_path=str(prompt_path),
        num_courses=len(course_codes),
        total_painpoints=total_painpoints,
        num_cluster_calls=num_cluster_calls,
        started_at_epoch=started_at,
        finished_at_epoch=finished_at,
        wallclock_sec=wallclock,
        total_cost_usd=total_cost,
        total_elapsed_sec_model_calls=total_elapsed,
        per_course=per_course_summary,
    )

    manifest_path = run_dir / "manifest.json"
    manifest_json = manifest.model_dump_json(indent=2)
    manifest_path.write_text(manifest_json, encoding="utf-8")

    logger.info("Stage 2 clustering complete. Manifest: %s", manifest_path)
    print(manifest_json)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 2 clustering over Stage-1 painpoints."
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name for clustering (e.g., gpt-5-mini).",
    )
    parser.add_argument(
        "--prompt",
        default="prompts/s2_cluster_batch.txt",
        help="Path to Stage-2 clustering prompt template.",
    )
    parser.add_argument(
        "--painpoints-csv",
        default="artifacts/stage2/painpoints_llm_friendly.csv",
        help="Path to Stage-2 painpoints CSV.",
    )
    parser.add_argument(
        "--course-meta-csv",
        default="data/course_list_with_college.csv",
        help="Path to course metadata CSV.",
    )
    parser.add_argument(
        "--out-root",
        default="artifacts/stage2",
        help="Root directory for Stage-2 runs (run dirs go under out-root/runs/).",
    )
    parser.add_argument(
        "--limit-courses",
        type=int,
        default=None,
        help="Optional limit on number of courses to cluster (for smoke tests).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable extra logging for debugging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_stage2_clustering(
        model_name=args.model,
        prompt_path=Path(args.prompt),
        painpoints_csv=Path(args.painpoints_csv),
        course_meta_csv=Path(args.course_meta_csv),
        out_root=Path(args.out_root),
        limit_courses=args.limit_courses,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()