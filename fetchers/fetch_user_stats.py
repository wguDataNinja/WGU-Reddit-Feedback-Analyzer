# filename: fetch_user_stats.py

from time import time
from datetime import datetime, timezone
from utils.db_connection import get_db_connection
import praw
from config import REDDIT_CREDENTIALS

reddit = praw.Reddit(
    client_id=REDDIT_CREDENTIALS["client_id"],
    client_secret=REDDIT_CREDENTIALS["client_secret"],
    user_agent=REDDIT_CREDENTIALS["user_agent"]
)

def fetch_user_stats(usernames=None):
    start_time = time()
    conn = get_db_connection()
    cursor = conn.cursor()

    if usernames is None:
        # fallback: get users from today's posts
        today_start_utc = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        cursor.execute("""
            SELECT DISTINCT username FROM (
                SELECT username FROM posts WHERE captured_at >= ?
                UNION
                SELECT username FROM comments WHERE captured_at >= ?
            )
        """, (today_start_utc, today_start_utc))
        usernames = [row[0] for row in cursor.fetchall()]

    print(f"Fetching stats for {len(usernames)} active users from today...")

    inserted = 0
    for username in usernames:
        try:
            redditor = reddit.redditor(username)
            captured_at = int(time())

            cursor.execute('''
                INSERT INTO user_stats (
                    username, captured_at, karma_post, karma_comment, total_posts, total_comments, is_banned
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                redditor.name,
                captured_at,
                redditor.link_karma,
                redditor.comment_karma,
                0,
                0,
                0
            ))
            inserted += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    print(f"✅ Inserted {inserted} user stats rows.")

if __name__ == "__main__":
    fetch_user_stats()