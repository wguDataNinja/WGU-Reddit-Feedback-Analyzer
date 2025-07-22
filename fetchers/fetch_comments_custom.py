from utils.db_connection import get_db_connection
# filename: fetchers/fetch_comments_custom.py

import praw

import pandas as pd
from time import time, sleep
from config import REDDIT_CREDENTIALS
from utils.paths import project_path

POSTS_LIST_PATH = project_path / 'data/posts_without_comments.csv'
SLEEP_SECONDS = 2

reddit = praw.Reddit(
    client_id=REDDIT_CREDENTIALS['client_id'],
    client_secret=REDDIT_CREDENTIALS['client_secret'],
    user_agent=REDDIT_CREDENTIALS['user_agent'],
    username=REDDIT_CREDENTIALS['username'],
    password=REDDIT_CREDENTIALS['password']
)

def fetch_comments():
    start_time = time()
    total_inserted, total_failures = 0, 0
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        post_ids = pd.read_csv(POSTS_LIST_PATH, header=None)[0].tolist()
    except Exception as e:
        print(f"❌ Failed to load posts: {e}")
        conn.close()
        return

    print(f"🔍 {len(post_ids)} posts to fetch...")

    for i, post_id in enumerate(post_ids, 1):
        try:
            print(f"[{i}/{len(post_ids)}] {post_id}")
            submission = reddit.submission(id=post_id)
            submission.comments.replace_more(limit=None)
            inserted = 0
            for comment in submission.comments.list():
                cursor.execute('''
                    INSERT OR IGNORE INTO comments (
                        comment_id, post_id, parent_comment_id, username, body, created_utc,
                        score, is_removed, is_deleted, captured_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    comment.id,
                    post_id,
                    comment.parent_id,
                    comment.author.name if comment.author else None,
                    comment.body,
                    int(comment.created_utc),
                    comment.score,
                    0,
                    int(comment.author is None),
                    int(time())
                ))
                inserted += 1
            conn.commit()
            total_inserted += inserted
            print(f"   ✅ {inserted} comments inserted.")
            sleep(SLEEP_SECONDS)
        except Exception as e:
            print(f"❌ Error: {e}")
            total_failures += 1

    conn.close()
    print(f"\n🎯 Done: {total_inserted} comments, {total_failures} failures, {round(time() - start_time, 2)}s")

if __name__ == "__main__":
    fetch_comments()