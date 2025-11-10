from __future__ import annotations

"""
Daily Comments Fetcher

Fetches a bounded tree of comments for recent target posts and upserts into
the comments table, supporting both bootstrap and incremental modes.

Inputs:
    - Existing posts table (targets)
    - Reddit API client via make_reddit()
    - comments table schema (via get_table_columns)

Outputs:
    - New rows in comments table
    - Structured run summary dict for orchestrator / logging
"""

import time
from typing import Dict, Any, List, Optional

import prawcore

from wgu_reddit_analyzer.utils.reddit_client import make_reddit
from wgu_reddit_analyzer.utils.db import get_db_connection, get_table_columns
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("fetch_comments_daily")

# Tunables (aligned with Stage 0 design)
INITIAL_LOOKBACK_DAYS = 3          # when no comments have been captured yet
LOOKBACK_SECONDS = 6 * 60 * 60     # incremental window: 6 hours back from last captured
MAX_POSTS_BOOTSTRAP = 100
MAX_POSTS_INCREMENTAL = 100
MAX_COMMENTS_PER_LEVEL = 3
MAX_DEPTH = 2
SLEEP_SECONDS = 0.0


def _get_comment_table_cols(conn) -> List[str]:
    cols = get_table_columns(conn, "comments")
    if not cols:
        logger.error("Comments table not found or no columns detected.")
    return cols


def _get_last_comment_captured_at(conn) -> Optional[float]:
    cur = conn.cursor()
    cur.execute("SELECT MAX(captured_at) FROM comments")
    row = cur.fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _select_bootstrap_posts(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT post_id
        FROM posts
        WHERE created_utc >= strftime('%s','now') - ? * 86400
        ORDER BY created_utc DESC
        LIMIT ?
        """,
        (INITIAL_LOOKBACK_DAYS, MAX_POSTS_BOOTSTRAP),
    )
    rows = cur.fetchall()
    post_ids = [str(r[0]) for r in rows if r[0]]

    logger.info(
        "Comments mode=bootstrap CandidatePosts=%d LookbackDays=%d",
        len(post_ids),
        INITIAL_LOOKBACK_DAYS,
    )
    return post_ids


def _select_incremental_posts(conn, last_captured: float) -> List[str]:
    window_start = max(0.0, last_captured - LOOKBACK_SECONDS)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT post_id
        FROM posts
        WHERE created_utc >= ?
        ORDER BY created_utc DESC
        LIMIT ?
        """,
        (window_start, MAX_POSTS_INCREMENTAL),
    )
    rows = cur.fetchall()
    post_ids = [str(r[0]) for r in rows if r[0]]

    logger.info(
        (
            "Comments mode=incremental CandidatePosts=%d "
            "LastCaptured=%.2f WindowStart=%.2f Lookback=%ds"
        ),
        len(post_ids),
        last_captured,
        window_start,
        LOOKBACK_SECONDS,
    )
    return post_ids


def _make_submission(reddit, post_id: str):
    if post_id.startswith("t3_"):
        return reddit.submission(fullname=post_id)
    return reddit.submission(id=post_id)


def _insert_comment_tree(
    cur,
    comment_cols: List[str],
    comment,
    post_id: str,
    parent_comment_id: Optional[str],
    depth: int,
    inserted_counter: Dict[str, int],
) -> None:
    if depth > MAX_DEPTH:
        return

    comment_id = getattr(comment, "id", None)
    if not comment_id:
        return

    author = getattr(comment, "author", None)
    author_name = getattr(author, "name", None) if author else None

    edited = getattr(comment, "edited", False)
    edited_utc = float(edited) if isinstance(edited, (int, float)) else None

    data = {
        "comment_id": comment_id,
        "post_id": post_id,
        "username": author_name,
        "parent_comment_id": parent_comment_id,
        "body": getattr(comment, "body", None),
        "created_utc": float(getattr(comment, "created_utc", time.time())),
        "edited_utc": edited_utc,
        "score": int(getattr(comment, "score", 0)),
        "is_promotional": 0,
        "is_removed": 0,
        "is_deleted": int(author_name is None),
        "extra_metadata": None,
        "captured_at": time.time(),
    }

    row = {k: v for k, v in data.items() if k in comment_cols}
    if row.get("comment_id") and row.get("post_id"):
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        cur.execute(
            f"INSERT OR IGNORE INTO comments ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        if cur.rowcount:
            inserted_counter["n"] += 1

    if depth < MAX_DEPTH:
        replies = list(getattr(comment, "replies", []))[:MAX_COMMENTS_PER_LEVEL]
        for reply in replies:
            _insert_comment_tree(
                cur,
                comment_cols,
                reply,
                post_id,
                parent_comment_id=comment_id,
                depth=depth + 1,
                inserted_counter=inserted_counter,
            )


def fetch_comments() -> Dict[str, Any]:
    start = time.time()
    failures = 0

    reddit = make_reddit()
    conn = get_db_connection()
    comment_cols = _get_comment_table_cols(conn)

    if not comment_cols:
        conn.close()
        return {
            "stage": "comments",
            "target_posts": 0,
            "comments_inserted": 0,
            "failures": 1,
            "duration_sec": 0.0,
        }

    last_captured = _get_last_comment_captured_at(conn)

    if last_captured is None:
        mode = "bootstrap"
        post_ids = _select_bootstrap_posts(conn)
    else:
        mode = "incremental"
        post_ids = _select_incremental_posts(conn, last_captured)

    if not post_ids:
        logger.info("No posts selected for comments (mode=%s). Skipping.", mode)
        conn.close()
        return {
            "stage": "comments",
            "target_posts": 0,
            "comments_inserted": 0,
            "failures": 0,
            "duration_sec": round(time.time() - start, 2),
        }

    cur = conn.cursor()
    inserted_counter = {"n": 0}

    for post_id in post_ids:
        try:
            submission = _make_submission(reddit, post_id)

            try:
                submission.comments.replace_more(limit=0)
            except prawcore.exceptions.NotFound:
                logger.warning(
                    "Skipping post '%s' (404 when fetching comments).",
                    post_id,
                )
                continue
            except prawcore.exceptions.Forbidden:
                logger.warning(
                    "Skipping post '%s' (403 when fetching comments).",
                    post_id,
                )
                continue
            except Exception as exc:
                failures += 1
                logger.warning(
                    "Error loading comments for post '%s': %s: %s",
                    post_id,
                    exc.__class__.__name__,
                    exc,
                )
                continue

            top_level = list(submission.comments)[:MAX_COMMENTS_PER_LEVEL]
            for tl in top_level:
                _insert_comment_tree(
                    cur,
                    comment_cols,
                    tl,
                    post_id,
                    parent_comment_id=submission.id,
                    depth=1,
                    inserted_counter=inserted_counter,
                )

            conn.commit()
            if SLEEP_SECONDS:
                time.sleep(SLEEP_SECONDS)

        except prawcore.exceptions.NotFound:
            logger.warning(
                "Skipping post '%s' (404 when creating submission).",
                post_id,
            )
            continue
        except prawcore.exceptions.Forbidden:
            logger.warning(
                "Skipping post '%s' (403 when creating submission).",
                post_id,
            )
            continue
        except Exception as exc:
            failures += 1
            logger.warning(
                "Error fetching comments for post '%s': %s: %s",
                post_id,
                exc.__class__.__name__,
                exc,
            )
            continue

    conn.commit()
    conn.close()

    duration = round(time.time() - start, 2)
    inserted = inserted_counter["n"]

    logger.info(
        "Comments Inserted=%s Failures=%s Duration=%.2fs Mode=%s TargetPosts=%s",
        inserted,
        failures,
        duration,
        mode,
        len(post_ids),
    )

    return {
        "stage": "comments",
        "target_posts": len(post_ids),
        "comments_inserted": inserted,
        "failures": failures,
        "duration_sec": duration,
    }


if __name__ == "__main__":
    summary = fetch_comments()
    logger.info("Standalone fetch_comments run summary: %s", summary)