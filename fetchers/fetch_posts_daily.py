# fetchers/fetch_posts_daily.py

import praw
import pandas as pd
from datetime import datetime
from time import time
from config import REDDIT_CREDENTIALS
from utils.paths import project_path
from utils.db_connection import get_db_connection

# === CONFIG ===
SORT_METHOD = 'new'
MAX_POSTS = 1000
SUBREDDITS_CSV_PATH = project_path / 'data/wgu_subreddits.csv'

reddit = praw.Reddit(
    client_id=REDDIT_CREDENTIALS['client_id'],
    client_secret=REDDIT_CREDENTIALS['client_secret'],
    user_agent=REDDIT_CREDENTIALS['user_agent'],
    username=REDDIT_CREDENTIALS['username'],
    password=REDDIT_CREDENTIALS['password']
)


def load_subreddits(csv_path):
    df = pd.read_csv(csv_path, header=None)
    return df[0].dropna().unique().tolist()


def normalize_subreddit_id(subreddit_id):
    return subreddit_id.removeprefix('t5_')


def fetch_latest_post_time(cursor, subreddit_id):
    subreddit_id = normalize_subreddit_id(subreddit_id)
    cursor.execute('''
        SELECT MAX(created_utc) FROM posts WHERE subreddit_id = ?
    ''', (subreddit_id,))
    result = cursor.fetchone()
    return result[0] if result and result[0] else 0


def fetch_posts():
    start_time = time()
    fetched_total = 0
    failures = 0
    new_posts = []

    subreddits = load_subreddits(SUBREDDITS_CSV_PATH)
    conn = get_db_connection()
    cursor = conn.cursor()

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            subreddit_id = normalize_subreddit_id(subreddit.id)
            latest_known_post_time = fetch_latest_post_time(cursor, subreddit_id)

            fetch_func = getattr(subreddit, SORT_METHOD, subreddit.new)
            count = 0
            for post in fetch_func(limit=MAX_POSTS):
                if post.created_utc <= latest_known_post_time:
                    break

                cursor.execute('''
                    INSERT OR IGNORE INTO posts (
                        post_id, subreddit_id, username, title, selftext, created_utc,
                        edited_utc, score, upvote_ratio, is_promotional, is_removed,
                        is_deleted, flair, post_type, num_comments, url, permalink, extra_metadata, captured_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post.id,
                    normalize_subreddit_id(post.subreddit_id),
                    post.author.name if post.author else None,
                    post.title,
                    post.selftext,
                    int(post.created_utc),
                    int(post.edited) if post.edited else None,
                    post.score,
                    post.upvote_ratio,
                    0,
                    int(post.removed_by_category is not None),
                    int(post.author is None),
                    post.link_flair_text,
                    'text' if post.is_self else 'image' if post.url.endswith(
                        ('.jpg', '.png', '.gif')) else 'video' if post.is_video else 'link',
                    post.num_comments,
                    post.url,
                    post.permalink,
                    None,
                    int(time())
                ))

                if cursor.rowcount > 0:
                    new_posts.append({
                        "id": post.id,
                        "subreddit_id": normalize_subreddit_id(post.subreddit_id),
                        "created_utc": int(post.created_utc)
                    })

                count += 1
                fetched_total += 1

            conn.commit()

            subreddit_display = f"r/{subreddit_name}".ljust(20)
            if count > 0:
                print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {subreddit_display} {count} new posts")
            else:
                print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {subreddit_display} No new posts")

        except Exception as e:
            subreddit_display = f"r/{subreddit_name}".ljust(20)
            print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {subreddit_display} Error: {e}")
            failures += 1

    conn.close()
    return {
        "posts_fetched": fetched_total,
        "duration": round(time() - start_time, 2),
        "failures": failures,
        "posts": new_posts
    }