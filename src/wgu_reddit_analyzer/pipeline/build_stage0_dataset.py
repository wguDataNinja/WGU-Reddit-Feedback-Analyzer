"""
Stage 0 Dataset Builder (Historical / Artifact-Generating)

This module documents the exact logic used to produce the authoritative Stage 0
Reddit corpus used in the WGU Reddit Analyzer paper.

Stage 0 constructs a fixed, complaint-focused dataset from the project’s historical
SQLite database by applying strictly defined structural, course-matching, and
sentiment filters. The resulting JSONL file is treated as immutable ground truth
for all downstream stages.

Important:
- The Stage 0 artifact (artifacts/stage0_filtered_posts.jsonl) is committed to the
  repository and is the version used for all reported results.
- External users are NOT expected to run this script.
- Re-running Stage 0 requires access to the original database and will produce a
  different corpus, invalidating downstream counts.

This script is retained for auditability and methodological transparency only.

Entrypoint (historical):
    python -m wgu_reddit_analyzer.pipeline.build_stage0_dataset

Artifact:
    artifacts/stage0_filtered_posts.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from wgu_reddit_analyzer.utils import filters
from wgu_reddit_analyzer.utils.db import get_db_connection
from wgu_reddit_analyzer.utils.sentiment_vader import calculate_vader_sentiment

try:
    from wgu_reddit_analyzer.utils.logging_utils import get_logger  # type: ignore

    logger = get_logger(__name__)
except Exception:  # noqa: BLE001
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)


STAGE0_FILENAME = "stage0_filtered_posts.jsonl"

BASE_QUERY = """
SELECT
    p.post_id,
    p.subreddit_id,
    s.name AS subreddit_name,
    p.title,
    p.selftext,
    p.created_utc,
    p.score,
    p.upvote_ratio,
    p.flair,
    p.post_type,
    p.num_comments,
    p.url,
    p.permalink,
    p.is_promotional,
    p.is_removed,
    p.is_deleted,
    p.extra_metadata,
    p.captured_at,
    p.vader_compound
FROM posts AS p
LEFT JOIN subreddits AS s
    ON p.subreddit_id = s.subreddit_id
WHERE
    COALESCE(p.is_deleted, 0) = 0
    AND COALESCE(p.is_removed, 0) = 0
    AND COALESCE(p.is_promotional, 0) = 0
    AND length(trim(COALESCE(p.title, '') || ' ' || COALESCE(p.selftext, ''))) > 0
;
"""


def _project_root() -> Path:
    """
    Infer the repository root from this module's location.

    This repository ships runnable pipeline scripts under src/. The Stage 0 builder is
    expected to be invoked from a cloned repository without user-specific paths.

    Returns:
        Absolute path to the inferred repository root.
    """
    return Path(__file__).resolve().parents[3]


def _artifacts_dir() -> Path:
    """
    Create (if needed) and return the repository artifacts directory.

    Returns:
        Path to artifacts/ under the inferred repository root.
    """
    directory = _project_root() / "artifacts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _load_course_codes() -> List[str]:
    """
    Load normalized course codes from the configured course list CSV.

    The CSV path is defined by wgu_reddit_analyzer.utils.filters.COURSE_CSV. Codes are
    read from the "CourseCode" column and normalized via string conversion and strip.

    Returns:
        List of non-empty course codes. Returns an empty list if the file is missing
        or cannot be read.
    """
    csv_path = filters.COURSE_CSV
    if not csv_path.exists():
        logger.error("Course list CSV not found at %s", csv_path)
        return []

    try:
        df_codes = pd.read_csv(csv_path, usecols=["CourseCode"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read course list CSV at %s: %s", csv_path, exc)
        return []

    codes = df_codes["CourseCode"].dropna().astype(str).str.strip().tolist()
    codes = [code for code in codes if code]

    logger.info("Loaded %d course codes from %s", len(codes), csv_path)
    if not codes:
        logger.error("No valid course codes loaded from %s", csv_path)

    return codes


def _ensure_vader(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the DataFrame has a numeric vader_compound score for each row.

    If vader_compound is missing or not castable to float, the score is recomputed
    using calculate_vader_sentiment over the combined title and selftext.

    Args:
        df: DataFrame containing at least title and selftext columns.

    Returns:
        The same DataFrame with a vader_compound column present and best-effort
        cast to float.
    """
    if "vader_compound" not in df.columns:
        df["vader_compound"] = None

    def needs_vader(value: Any) -> bool:
        if value is None:
            return True
        try:
            float(value)
            return False
        except (TypeError, ValueError):
            return True

    mask = df["vader_compound"].apply(needs_vader)
    missing_count = int(mask.sum())

    if missing_count > 0:
        logger.info(
            "Recomputing VADER sentiment for %d posts with missing/invalid scores.",
            missing_count,
        )

        def combined_text(row: Dict[str, Any]) -> str:
            title = row.get("title") or ""
            body = row.get("selftext") or ""
            if not isinstance(title, str):
                title = ""
            if not isinstance(body, str):
                body = ""
            return f"{title.strip()} {body.strip()}".strip()

        texts = df.loc[mask].apply(combined_text, axis=1)
        df.loc[mask, "vader_compound"] = texts.apply(calculate_vader_sentiment)

    try:
        df["vader_compound"] = df["vader_compound"].astype(float)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not cast all vader_compound values to float: %s", exc)

    return df


def build_stage0_dataset(output_path: Path) -> int:
    """
    Build and write the Stage 0 dataset to a JSON Lines file.

    The selection and filtering behavior is defined by PIPELINE_SPEC.md and must be
    consistent across runs. This function preserves the required filtering rules and
    output fields.

    Args:
        output_path: Destination path for the JSONL output file.

    Returns:
        Number of records written to output_path. If no eligible records are found,
        an empty file is written and 0 is returned.
    """
    conn = get_db_connection()
    try:
        logger.info("Loading base posts from DB with structural filters.")
        df = pd.read_sql_query(BASE_QUERY, conn)
    finally:
        conn.close()

    logger.info("Base query returned %d rows.", len(df))
    if df.empty:
        output_path.write_text("", encoding="utf-8")
        return 0

    course_codes = _load_course_codes()
    if not course_codes:
        output_path.write_text("", encoding="utf-8")
        return 0

    logger.info(
        "Applying course code filter with exact_match_count=1 using "
        "utils.filters.filter_posts_by_course_code.",
    )
    before_filter = len(df)
    df = filters.filter_posts_by_course_code(
        df=df,
        course_codes=course_codes,
        exact_match_count=1,
        title_col="title",
        text_col="selftext",
        out_col="matched_course_codes",
    )
    after_filter = len(df)
    logger.info(
        "Course filter complete. %d -> %d posts matched exactly one course code.",
        before_filter,
        after_filter,
    )
    if df.empty:
        output_path.write_text("", encoding="utf-8")
        return 0

    df["course_code_count"] = df["matched_course_codes"].apply(len)
    df["course_code"] = df["matched_course_codes"].apply(
        lambda values: values[0] if values else None,
    )

    before_exact = len(df)
    df = df[df["course_code_count"] == 1].copy()
    logger.info(
        "Enforced course_code_count == 1: %d -> %d posts.",
        before_exact,
        len(df),
    )
    if df.empty:
        output_path.write_text("", encoding="utf-8")
        return 0

    df = _ensure_vader(df)

    before_sent = len(df)
    df = df[df["vader_compound"] < -0.2].copy()
    logger.info(
        "Applied negative sentiment filter (vader_compound < -0.2): %d -> %d posts.",
        before_sent,
        len(df),
    )
    if df.empty:
        output_path.write_text("", encoding="utf-8")
        return 0

    cols = [
        "post_id",
        "subreddit_id",
        "subreddit_name",
        "title",
        "selftext",
        "created_utc",
        "score",
        "upvote_ratio",
        "flair",
        "post_type",
        "num_comments",
        "url",
        "permalink",
        "matched_course_codes",
        "course_code",
        "course_code_count",
        "vader_compound",
        "is_promotional",
        "is_removed",
        "is_deleted",
        "extra_metadata",
        "captured_at",
    ]
    for col in ("is_promotional", "is_removed", "is_deleted"):
        if col not in df.columns:
            df[col] = 0

    cols = [col for col in cols if col in df.columns]
    df = df[cols]

    count = 0
    with output_path.open("w", encoding="utf-8") as file:
        for _, row in df.iterrows():
            json.dump(row.to_dict(), file, ensure_ascii=False)
            file.write("\n")
            count += 1

    logger.info("Stage 0 export complete: %d records written to %s", count, output_path)
    return count


def main() -> None:
    """
    Build the Stage 0 dataset using the default artifacts location.

    Writes artifacts/stage0_filtered_posts.jsonl under the inferred repository root.
    """
    artifacts_dir = _artifacts_dir()
    output_path = artifacts_dir / STAGE0_FILENAME
    build_stage0_dataset(output_path)


if __name__ == "__main__":
    main()