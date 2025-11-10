from __future__ import annotations

"""
Daily Posts Fetcher

Retrieves recent posts from all target subreddits and inserts them
into the posts table, supporting incremental updates via frontier logic.

Inputs:
    - Subreddit list from data/wgu_subreddits.txt
    - Valid Reddit API credentials
    - Existing posts table (for frontier detection)

Outputs:
    - New rows in posts table
    - Structured run summary dict for orchestrator / logging
"""

import time
from pathlib import Path
from typing import Dict, Any, List
import prawcore

from wgu_reddit_analyzer.utils.reddit_client import make_reddit
from wgu_reddit_analyzer.utils.db import get_db_connection, get_table_columns
from wgu_reddit_analyzer.utils.logging_utils import get_logger

logger = get_logger("fetch_posts_daily")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUBREDDIT_LIST_PATH = PROJECT_ROOT / "data" / "wgu_subreddits.txt"

MAX_POSTS_PER_SUB = 1000


def _read_subreddit_list() -> List[str]:
    if not SUBREDDIT_LIST_PATH.exists():
        logger.error("Subreddit config file not found: %s", SUBREDDIT_LIST_PATH)
        return []

    subs: List[str] = []
    with SUBREDDIT_LIST_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("r/"):
                line = line[2:]
            if line:
                subs.append(line)

    if not subs:
        logger.error("No subreddits loaded from %s", SUBREDDIT_LIST_PATH)
    return subs


def _get_posts_columns(conn) -> List[str]:
    cols = get_table_columns(conn, "posts")
    if not cols:
        logger.error("Posts table not found or no columns detected.")
    return cols


def _get_frontier_for_sub(cur, name: str) -> float:
    """Return latest captured timestamp for posts under /r/{name}/."""
    pattern = f"%/r/{name}/%"
    cur.execute(
        """
        SELECT MAX(created_utc)
        FROM posts
        WHERE permalink LIKE ?
        """,
        (pattern,),
    )
    row = cur.fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def fetch_posts(limit_per_sub: int = MAX_POSTS_PER_SUB) -> Dict[str, Any]:
    start = time.time()
    failures = 0
    total_new = 0

    reddit = make_reddit()
    subs = _read_subreddit_list()
    if not subs:
        return {"stage": "posts", "posts_fetched": 0, "failures": 1, "duration_sec": 0.0}

    conn = get_db_connection()
    post_cols = set(_get_posts_columns(conn))
    if not post_cols:
        conn.close()
        return {"stage": "posts", "posts_fetched": 0, "failures": 1, "duration_sec": 0.0}

    cur = conn.cursor()

    for name in subs:
        scanned = new_for_sub = 0

        try:
            subreddit = reddit.subreddit(name)

            # Validate access
            try:
                _ = subreddit.id
            except prawcore.exceptions.NotFound:
                logger.warning("Skipping subreddit '%s' — not found or banned (404).", name)
                continue
            except prawcore.exceptions.Forbidden:
                logger.warning("Skipping subreddit '%s' — access forbidden/private (403).", name)
                continue
            except Exception as exc:
                failures += 1
                logger.warning("Error initializing subreddit '%s': %s: %s", name, type(exc).__name__, exc)
                continue

            frontier = _get_frontier_for_sub(cur, name)

            for submission in subreddit.new(limit=limit_per_sub):
                scanned += 1
                created_utc = float(getattr(submission, "created_utc", 0.0) or 0.0)
                if frontier and created_utc <= frontier:
                    break  # reached known territory

                edited = getattr(submission, "edited", False)
                edited_utc = float(edited) if isinstance(edited, (int, float)) else None

                author = getattr(submission, "author", None)
                author_name = getattr(author, "name", None) if author else None

                data = {
                    "post_id": getattr(submission, "id", None),
                    "subreddit_id": getattr(submission, "subreddit_id", None),
                    "username": author_name,
                    "title": getattr(submission, "title", None),
                    "selftext": getattr(submission, "selftext", None),
                    "created_utc": created_utc,
                    "edited_utc": edited_utc,
                    "score": int(getattr(submission, "score", 0) or 0),
                    "upvote_ratio": float(getattr(submission, "upvote_ratio", 0) or 0),
                    "is_promotional": int(not bool(getattr(submission, "is_self", False))),
                    "is_removed": int(getattr(submission, "removed_by_category", None) is not None),
                    "is_deleted": int(author is None),
                    "flair": getattr(submission, "link_flair_text", None),
                    "post_type": "self" if bool(getattr(submission, "is_self", False)) else "link",
                    "num_comments": int(getattr(submission, "num_comments", 0) or 0),
                    "url": getattr(submission, "url", None),
                    "permalink": f"https://www.reddit.com{getattr(submission, 'permalink', '')}",
                    "extra_metadata": None,
                    "captured_at": time.time(),
                }

                row = {k: v for k, v in data.items() if k in post_cols}
                if not row.get("post_id"):
                    continue

                cols = ", ".join(row.keys())
                qs = ", ".join(["?"] * len(row))
                cur.execute(f"INSERT OR IGNORE INTO posts ({cols}) VALUES ({qs})", list(row.values()))
                if cur.rowcount > 0:
                    new_for_sub += 1
                    total_new += 1

            logger.info(
                "Subreddit %s: scanned=%s new=%s frontier=%s",
                name,
                scanned,
                new_for_sub,
                f"{frontier:.2f}" if frontier else "NONE",
            )

        except Exception as exc:
            failures += 1
            logger.warning("Error fetching posts for /r/%s: %s: %s", name, type(exc).__name__, exc)

    conn.commit()
    conn.close()

    duration = round(time.time() - start, 2)
    logger.info("New Posts Inserted=%s Failures=%s Duration=%.2fs", total_new, failures, duration)

    return {
        "stage": "posts",
        "posts_fetched": total_new,
        "failures": failures,
        "duration_sec": duration,
    }


if __name__ == "__main__":
    summary = fetch_posts()
    logger.info("Standalone fetch_posts run summary: %s", summary)