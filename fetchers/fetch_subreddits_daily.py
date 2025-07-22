# filename: fetchers/fetch_subreddits_daily.py

import praw
import json
import pandas as pd
from time import time, sleep
from config import REDDIT_CREDENTIALS
from utils.db_connection import get_db_connection
from utils.paths import project_path

# === CONFIG ===
SUBREDDITS_CSV_PATH = project_path / 'data/wgu_subreddits.csv'
SLEEP_SECONDS = 2
# === END CONFIG ===

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

def fetch_subreddits():
    start_time = time()
    fetched_stats = 0
    failures = 0

    subreddits = load_subreddits(SUBREDDITS_CSV_PATH)
    conn = get_db_connection()
    cursor = conn.cursor()

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)

            # Upsert subreddit metadata
            rules_json = json.dumps([
                {'short_name': rule.short_name, 'description': rule.description}
                for rule in subreddit.rules
            ])
            cursor.execute(
                '''
                INSERT OR REPLACE INTO subreddits (
                    subreddit_id, name, description, is_nsfw, created_utc, rules, sidebar_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    subreddit.id,
                    subreddit.display_name,
                    subreddit.public_description,
                    subreddit.over18,
                    int(subreddit.created_utc),
                    rules_json,
                    subreddit.description
                )
            )

            # Insert subscriber stats
            cursor.execute(
                '''
                INSERT INTO subreddit_stats (
                    subreddit_id, captured_at, subscriber_count, active_users, posts_per_day, total_posts
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    subreddit.id,
                    int(time()),
                    subreddit.subscribers,
                    subreddit.accounts_active or 0,
                    None,
                    None
                )
            )
            conn.commit()
            fetched_stats += 1
            sleep(SLEEP_SECONDS)
        except Exception as e:
            print(f"❌ Error fetching subreddit {subreddit_name}: {e}")
            failures += 1

    conn.close()
    return {
        "subreddit_stats_fetched": fetched_stats,
        "duration": round(time() - start_time, 2),
        "failures": failures
    }

if __name__ == '__main__':
    result = fetch_subreddits()
    print(result)
