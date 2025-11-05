# filename: daily_update.py

import time
import logging
import sys
import os
from datetime import datetime

from fetchers.fetch_posts_daily import fetch_posts
from fetchers.fetch_comments_daily import fetch_comments
from fetchers.fetch_users_daily import fetch_users
from fetchers.fetch_user_stats import fetch_user_stats
from fetchers.fetch_subreddits_daily import fetch_subreddits
from utils.db_connection import get_db_connection

#!/usr/bin/env python3

from datetime import datetime
print(f"auto daily_update.py started at {datetime.now()}", flush=True)

import sys
import os

# This script is in: /Users/buddy/Desktop/WGU-Reddit/scripts
# So its parent is your project root: /Users/buddy/Desktop/WGU-Reddit
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))

# Make sure project root is first in sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("sys.path:", sys.path)

# === Logging Setup ===
logger = logging.getLogger("daily_update")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, "daily_update.log")

    file_handler = logging.FileHandler(log_file_path)
    file_formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="[%Y-%m-%d %H:%M:%S]")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)

def log_update(message):
    logger.info(message)

def log_run_start():
    logger.info("\n\n" + "=" * 60)
    logger.info(f"New Daily Update Run - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60 + "\n")

def log_run_summary(overall_start, posts_fetched, comments_inserted, users_updated, new_users_inserted, subreddit_stats_fetched, failures):
    duration = round(time.time() - overall_start, 2)
    logger.info("\n" + "-" * 50)
    logger.info(f"SUMMARY")
    logger.info(f"Total Duration: {duration}s")
    logger.info(f"Posts Fetched: {posts_fetched}")
    logger.info(f"Comments Inserted: {comments_inserted}")
    logger.info(f"Users Updated: {users_updated}")
    logger.info(f"New Users Inserted: {new_users_inserted}")
    logger.info(f"Subreddit Stats Fetched: {subreddit_stats_fetched}")
    logger.info(f"Failures: {failures}")
    logger.info("-" * 50 + "\n")

# === Main Execution ===
def main():
    overall_start = time.time()
    log_run_start()

    total_posts_fetched = 0
    total_comments_inserted = 0
    total_users_updated = 0
    total_new_users_inserted = 0
    total_subreddit_stats_fetched = 0
    total_failures = 0

    log_update("Starting daily update process...")

    # Fetch posts
    log_update("Fetching posts...")
    try:
        result = fetch_posts() or {}
        posts = result.get("posts", [])
        posts_fetched = len(posts)
        duration = result.get("duration", "N/A")
        failures = result.get("failures", 0)
        log_update(f"Fetched {posts_fetched} posts in {duration}s")
        if failures:
            log_update(f"Post fetching failures: {failures}")
        total_posts_fetched += posts_fetched
        total_failures += failures
        post_ids = [post["id"] for post in posts]
    except Exception as e:
        log_update(f"Post fetching failed: {str(e)}")
        post_ids = []

    # Fetch comments
    log_update("Fetching comments...")
    try:
        result = fetch_comments(post_ids) or {}
        comments_inserted = result.get("comments_inserted", 0)
        duration = result.get("duration", "N/A")
        failures = result.get("failures", 0)
        log_update(f"Inserted {comments_inserted} comments in {duration}s")
        if failures:
            log_update(f"Comment fetching failures: {failures}")
        total_comments_inserted += comments_inserted
        total_failures += failures
    except Exception as e:
        log_update(f"Comment fetching failed: {str(e)}")

    # Fetch users and user stats
    if total_posts_fetched > 0 or total_comments_inserted > 0:
        log_update("Fetching users...")
        try:
            result = fetch_users() or {}
            active_users_found = result.get("active_users_found", "N/A")
            new_users_inserted = result.get("new_users_inserted", 0)
            users_updated = result.get("users_updated", 0)
            duration = result.get("duration", "N/A")
            failures = result.get("failures", 0)
            log_update(f"Active Users Found: {active_users_found}, New Users Inserted: {new_users_inserted}, Users Updated: {users_updated} in {duration}s")
            if failures:
                log_update(f"User fetching failures: {failures}")
            total_new_users_inserted += new_users_inserted
            total_users_updated += users_updated
            total_failures += failures
        except Exception as e:
            log_update(f"User fetching failed: {str(e)}")

        log_update("Fetching user stats...")
        try:
            fetch_user_stats()
            log_update("User stats fetching completed.")
        except Exception as e:
            log_update(f"User stats fetching failed: {str(e)}")
    else:
        log_update("No new posts or comments. Skipping user fetching.")

    # Fetch subreddits
    log_update("Fetching subreddit stats...")
    try:
        result = fetch_subreddits() or {}
        subreddit_stats_fetched = result.get("subreddit_stats_fetched", 0)
        duration = result.get("duration", "N/A")
        failures = result.get("failures", 0)
        log_update(f"Fetched {subreddit_stats_fetched} subreddit stats in {duration}s")
        if failures:
            log_update(f"Subreddit fetching failures: {failures}")
        total_subreddit_stats_fetched += subreddit_stats_fetched
        total_failures += failures
    except Exception as e:
        log_update(f"Subreddit fetching failed: {str(e)}")

    # Log final summary
    log_run_summary(
        overall_start,
        total_posts_fetched,
        total_comments_inserted,
        total_users_updated,
        total_new_users_inserted,
        total_subreddit_stats_fetched,
        total_failures
    )

if __name__ == "__main__":
    main()