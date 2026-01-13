# filename: fetchers/fetch_subreddits_daily.py

import os
import json
from time import time, sleep
from pathlib import Path

import praw
import yaml
from dotenv import load_dotenv

from wgu_reddit_analyzer.utils.db import get_db_connection

# === Load environment ===
load_dotenv()

# === Project paths ===
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"
SUBREDDIT_LIST_PATH = PROJECT_ROOT / "data" / "wgu_subreddits.txt"

# === Load config ===
with CONFIG_PATH.open("r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

reddit_cfg = config["reddit"]

# === Reddit client ===
reddit = praw.Reddit(
    client_id=os.getenv(reddit_cfg["client_id_env"]),
    client_secret=os.getenv(reddit_cfg["client_secret_env"]),
    user_agent=os.getenv(reddit_cfg["user_agent_env"]),
    username=os.getenv(reddit_cfg["username_env"]),
    password=os.getenv(reddit_cfg["password_env"]),
)

# === CONFIG ===
SLEEP_SECONDS = 2
# === END CONFIG ===


def load_subreddits(path: Path) -> list[str]:
    subs: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                subs.append(s)
    return subs


def fetch_subreddits():
    start_time = time()
    fetched_stats = 0
    failures = 0

    subreddits = load_subreddits(SUBREDDIT_LIST_PATH)

    conn = get_db_connection()
    cursor = conn.cursor()

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)

            rules_json = json.dumps(
                [
                    {"short_name": r.short_name, "description": r.description}
                    for r in subreddit.rules
                ]
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO subreddits (
                    subreddit_id,
                    name,
                    description,
                    is_nsfw,
                    created_utc,
                    rules,
                    sidebar_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subreddit.id,
                    subreddit.display_name,
                    subreddit.public_description,
                    subreddit.over18,
                    int(subreddit.created_utc),
                    rules_json,
                    subreddit.description,
                ),
            )

            cursor.execute(
                """
                INSERT INTO subreddit_stats (
                    subreddit_id,
                    captured_at,
                    subscriber_count,
                    active_users,
                    posts_per_day,
                    total_posts
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    subreddit.id,
                    int(time()),
                    subreddit.subscribers,
                    (getattr(subreddit, "active_user_count", None)
                     or getattr(subreddit, "accounts_active", None)
                     or 0),
                    None,
                    None,
                ),
            )

            conn.commit()
            fetched_stats += 1
            sleep(SLEEP_SECONDS)


        except Exception as e:

            msg = str(e)

            if "received 404" in msg or "404" in msg:
                print(f"Skipping subreddit '{subreddit_name}' (404).")

                continue

            print(f"Error fetching subreddit {subreddit_name}: {e}")

            failures += 1

    conn.close()

    return {
        "subreddit_stats_fetched": fetched_stats,
        "duration": round(time() - start_time, 2),
        "failures": failures,
    }


if __name__ == "__main__":
    print(fetch_subreddits())