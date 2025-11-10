"""
Stage 0 Dataset Builder

Purpose:
    Build the authoritative Stage 0 dataset used for all downstream tasks.

Inputs:
    - db/WGU-Reddit.db (posts and subreddits tables).
    - wgu_reddit_analyzer.utils.filters.COURSE_CSV (course list).

Outputs:
    - artifacts/stage0_filtered_posts.jsonl

Usage:
    python -m wgu_reddit_analyzer.pipeline.build_stage0_dataset

Notes:
    - Each record has exactly one matched course_code.
    - Each record satisfies vader_compound < -0.2.
    - Only structurally valid, non-deleted, non-removed, non-promotional posts
      are included.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from wgu_reddit_analyzer.utils import filters
from wgu_reddit_analyzer.utils.db import get_db_connection
from wgu_reddit_analyzer.utils.logging_utils import get_logger
from wgu_reddit_analyzer.utils.sentiment_vader import calculate_vader_sentiment

logger = get_logger("build_stage0_dataset")

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
    Return the repository root inferred from this file location.

    Returns:
        Absolute path to the repository root.
    """
    return Path(__file__).resolve().parents[3]


def _artifacts_dir() -> Path:
    """
    Ensure and return the artifacts directory.

    Returns:
        Path to artifacts/ under the repository root.
    """
    directory = _project_root() / "artifacts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _load_course_codes() -> List[str]:
    """
    Load course codes from the configured COURSE_CSV file.

    Returns:
        List of normalized course codes. Empty list if load fails.
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

    codes = (
        df_codes["CourseCode"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
    codes = [code for code in codes if code]

    logger.info("Loaded %d course codes from %s", len(codes), csv_path)
    if not codes:
        logger.error("No valid course codes loaded from %s", csv_path)

    return codes


def _ensure_vader(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure each post has a valid numeric vader_compound score.

    Missing or invalid scores are recomputed using title + selftext.

    Args:
        df:
            DataFrame of posts including title and selftext.

    Returns:
        DataFrame with a float vader_compound column.
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
        logger.warning(
            "Could not cast all vader_compound values to float: %s",
            exc,
        )

    return df


def build_stage0_dataset(output_path: Path) -> int:
    """
    Build and write the authoritative Stage 0 dataset.

    Args:
        output_path:
            Destination path for the JSONL output file.

    Returns:
        Number of records written to output_path.
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

    logger.info(
        "Stage 0 export complete: %d records written to %s",
        count,
        output_path,
    )
    return count


def main() -> None:
    """
    CLI entrypoint for building the Stage 0 dataset.

    Uses the default artifacts directory and filename.
    """
    artifacts_dir = _artifacts_dir()
    output_path = artifacts_dir / STAGE0_FILENAME
    build_stage0_dataset(output_path)


if __name__ == "__main__":
    main()