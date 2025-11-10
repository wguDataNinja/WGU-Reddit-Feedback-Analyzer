# filename: fetchers/fetch_comments_daily.py
from utils.db_connection import get_db_connection
import praw
from time import time, sleep

from utils.config_loader import load_env, require_reddit_creds

# Load env vars (safe if already loaded elsewhere)
load_env()

# === CONFIG ===
SLEEP_SECONDS = 2
MAX_COMMENTS_PER_LEVEL = 3  # Width
MAX_DEPTH = 2               # Depth
# === END CONFIG ===

def _reddit() -> praw.Reddit:
    creds = require_reddit_creds()
    return praw.Reddit(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        user_agent=creds["user_agent"],
        username=creds["username"],
        password=creds["password"],
    )

def fetch_comments(post_ids):
    start_time = time()
    inserted_comments = 0
    failures = 0

    if not post_ids:
        print("[INFO] No posts provided. Skipping comment fetch.")
        return {
            "comments_inserted": 0,
            "duration": round(time() - start_time, 2),
            "failures": 0,
        }

    reddit = _reddit()
    conn = get_db_connection()
    cursor = conn.cursor()

    def insert_comment_tree(comment, parent_id, current_depth):
        nonlocal inserted_comments
        cursor.execute(
            '''
            INSERT OR IGNORE INTO comments (
                comment_id, post_id, parent_comment_id, username, body, created_utc,
                score, is_removed, is_deleted, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                comment.id,
                post_id,
                parent_id,
                comment.author.name if comment.author else None,
                comment.body,
                int(comment.created_utc),
                comment.score,
                0,
                int(comment.author is None),
                int(time()),
            ),
        )
        inserted_comments += 1

        if current_depth < MAX_DEPTH:
            replies = comment.replies[:MAX_COMMENTS_PER_LEVEL]
            for reply in replies:
                insert_comment_tree(reply, comment.id, current_depth + 1)

    for post_id in post_ids:
        try:
            submission = reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)

            top_level_comments = submission.comments[:MAX_COMMENTS_PER_LEVEL]
            for tl_comment in top_level_comments:
                insert_comment_tree(tl_comment, submission.id, current_depth=1)

            conn.commit()
            sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"[ERROR] fetching comments for post {post_id}: {e}")
            failures += 1

    conn.close()
    return {
        "comments_inserted": inserted_comments,
        "duration": round(time() - start_time, 2),
        "failures": failures,
    }