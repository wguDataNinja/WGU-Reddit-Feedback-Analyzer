# filename: fetch_users_daily.py

from utils.db_connection import get_db_connection
from time import time, sleep
import praw
from config import REDDIT_CREDENTIALS
from utils.paths import project_path
from datetime import datetime, timezone

USER_FETCH_LIMIT = 1000
SLEEP_SECONDS = 2

reddit = praw.Reddit(
    client_id=REDDIT_CREDENTIALS["client_id"],
    client_secret=REDDIT_CREDENTIALS["client_secret"],
    user_agent=REDDIT_CREDENTIALS["user_agent"],
    username=REDDIT_CREDENTIALS["username"],
    password=REDDIT_CREDENTIALS["password"]
)

def fetch_users():
    start_time = time()
    active_users_found = 0
    new_users_inserted = 0
    users_updated = 0
    failures = 0

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get today's start time in UTC
    today_start_utc = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

    # Get distinct usernames from today's posts and comments
    cursor.execute("""
        SELECT DISTINCT username FROM (
            SELECT username FROM posts WHERE username IS NOT NULL AND created_utc >= ?
            UNION
            SELECT username FROM comments WHERE username IS NOT NULL AND created_utc >= ?
        ) ORDER BY RANDOM() LIMIT ?
    """, (today_start_utc, today_start_utc, USER_FETCH_LIMIT))

    usernames = [row[0] for row in cursor.fetchall()]
    active_usernames = []

    print("Distinct usernames found today:", len(usernames))

    for username in usernames:
        try:
            redditor = reddit.redditor(username)
            now = int(time())

            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            user_exists = cursor.fetchone() is not None

            if user_exists:
                cursor.execute('''
                    UPDATE users SET 
                        karma_comment = ?, 
                        karma_post = ?,
                        last_seen_at = ?
                    WHERE username = ?
                ''', (
                    redditor.comment_karma,
                    redditor.link_karma,
                    now,
                    redditor.name
                ))
                users_updated += 1
            else:
                cursor.execute('''
                    INSERT INTO users (
                        username, karma_comment, karma_post, created_utc, first_captured_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    redditor.name,
                    redditor.comment_karma,
                    redditor.link_karma,
                    int(redditor.created_utc),
                    now,
                    now
                ))
                new_users_inserted += 1

            active_users_found += 1
            active_usernames.append(redditor.name)
            conn.commit()
            sleep(SLEEP_SECONDS)
        except Exception:
            print(f"Skipped banned/suspended user: {username}")
            failures += 1

    conn.close()

    print("Users already in database:", users_updated)
    print(f"New users inserted: {active_users_found - users_updated}")
    print("Existing users updated:", users_updated)
    print("Users info not available (banned/suspended):", failures)

    return {
        "active_users_found": active_users_found,
        "new_users_inserted": new_users_inserted,
        "users_updated": users_updated,
        "duration": round(time() - start_time, 2),
        "failures": failures,
        "usernames": active_usernames
    }

if __name__ == "__main__":
    fetch_users()