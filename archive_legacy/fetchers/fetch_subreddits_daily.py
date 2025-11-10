# filename: fetchers/fetch_subreddits_daily.py
import praw
import json
import pandas as pd
from time import time, sleep
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from utils.db_connection import get_db_connection

# === Load environment and config ===
load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "config.yaml"
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

reddit_cfg = config["reddit"]
paths_cfg = config["paths"]

# === Resolve paths ===
PROJECT_ROOT = Path(paths_cfg["project_root"]).resolve()
DATA_DIR = PROJECT_ROOT / paths_cfg["data_dir"]
OUTPUT_DIR = PROJECT_ROOT / paths_cfg["output_dir"]
LOGS_DIR = PROJECT_ROOT / paths_cfg["logs_dir"]
SUBREDDITS_CSV_PATH = DATA_DIR / "wgu_subreddits.csv"

# === Reddit client ===
reddit = praw.Reddit(
    client_id=os.getenv(reddit_cfg["client_id_env"]),
    client_secret=os.getenv(reddit_cfg["client_secret_env"]),
    user_agent=os.getenv(reddit_cfg["user_agent_env"]),
    username=os.getenv(reddit_cfg["username_env"]),
    password=os.getenv(reddit_cfg["password_env"])
)

# === CONFIG ===
SLEEP_SECONDS = 2
# === END CONFIG ===

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

            cursor.execute('''
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
            ))

            # Insert subscriber stats
            cursor.execute('''
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
            ))

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