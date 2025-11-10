"""Bootstrap and maintain minimal SQLite schema for the WGU Reddit Analyzer."""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, List

# File path: src/wgu_reddit_analyzer/utils/db_bootstrap.py
REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "data" / "WGU-Reddit.db"


def _get_existing_schema(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    """Return a map of table -> column names."""
    cur = conn.cursor()
    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    out: Dict[str, List[str]] = {}
    for t in tables:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t});").fetchall()]
        out[t] = cols
    return out


def _ensure_table(conn: sqlite3.Connection, table: str, create_sql: str) -> None:
    """Create a table if it does not exist."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    )
    if cur.fetchone() is None:
        cur.execute(create_sql)


def _ensure_columns(conn: sqlite3.Connection, table: str, desired_cols: Dict[str, str]) -> None:
    """Add missing columns without dropping or altering existing ones."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    existing = {r[1] for r in cur.fetchall()}
    for col, decl in desired_cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def ensure_minimal_schema(db_path: Path | None = None) -> None:
    """
    Idempotently bootstrap the SQLite database:
    - Creates required tables if missing.
    - Adds missing columns as needed.
    - Never drops or modifies existing columns.
    """
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        schema = _get_existing_schema(conn)

        # Tables
        _ensure_table(conn, "subreddits", """
            CREATE TABLE IF NOT EXISTS subreddits (
              subreddit_id TEXT PRIMARY KEY,
              name TEXT,
              description TEXT,
              is_nsfw INTEGER,
              created_utc REAL,
              rules TEXT,
              sidebar_text TEXT
            );
        """)

        _ensure_table(conn, "subreddit_stats", """
            CREATE TABLE IF NOT EXISTS subreddit_stats (
              subreddit_id TEXT,
              captured_at REAL,
              subscriber_count INTEGER,
              active_users INTEGER,
              posts_per_day REAL,
              total_posts INTEGER
            );
        """)

        _ensure_table(conn, "users", """
            CREATE TABLE IF NOT EXISTS users (
              username TEXT PRIMARY KEY,
              karma_comment INTEGER,
              karma_post INTEGER,
              created_utc REAL,
              first_captured_at REAL,
              last_seen_at REAL
            );
        """)

        _ensure_table(conn, "users_backup", """
            CREATE TABLE IF NOT EXISTS users_backup (
              username TEXT,
              created_utc REAL,
              is_promotional INTEGER,
              karma_post INTEGER,
              karma_comment INTEGER,
              last_seen REAL,
              first_captured_at REAL,
              last_seen_at REAL
            );
        """)

        _ensure_table(conn, "posts", """
            CREATE TABLE IF NOT EXISTS posts (
              post_id TEXT PRIMARY KEY,
              subreddit_id TEXT,
              username TEXT,
              title TEXT,
              selftext TEXT,
              created_utc REAL,
              edited_utc REAL,
              score INTEGER,
              upvote_ratio REAL,
              is_promotional INTEGER,
              is_removed INTEGER,
              is_deleted INTEGER,
              flair TEXT,
              post_type TEXT,
              num_comments INTEGER,
              url TEXT,
              permalink TEXT,
              extra_metadata TEXT,
              captured_at REAL,
              matched_course_codes TEXT,
              course_code TEXT,
              course_code_count INTEGER,
              vader_compound REAL,
              processed_stage0_at REAL
            );
        """)

        _ensure_table(conn, "comments", """
            CREATE TABLE IF NOT EXISTS comments (
              comment_id TEXT PRIMARY KEY,
              post_id TEXT,
              username TEXT,
              parent_comment_id TEXT,
              body TEXT,
              created_utc REAL,
              edited_utc REAL,
              score INTEGER,
              is_promotional INTEGER,
              is_removed INTEGER,
              is_deleted INTEGER,
              extra_metadata TEXT,
              captured_at REAL
            );
        """)

        _ensure_table(conn, "posts_keyword", """
            CREATE TABLE IF NOT EXISTS posts_keyword (
              post_id TEXT,
              subreddit_id TEXT,
              username TEXT,
              title TEXT,
              selftext TEXT,
              created_utc REAL,
              edited_utc REAL,
              score INTEGER,
              upvote_ratio REAL,
              is_promotional INTEGER,
              is_removed INTEGER,
              is_deleted INTEGER,
              flair TEXT,
              post_type TEXT,
              num_comments INTEGER,
              url TEXT,
              permalink TEXT,
              search_terms TEXT,
              captured_at REAL
            );
        """)

        _ensure_table(conn, "comments_keyword", """
            CREATE TABLE IF NOT EXISTS comments_keyword (
              comment_id TEXT,
              post_id TEXT,
              subreddit_id TEXT,
              username TEXT,
              body TEXT,
              created_utc REAL,
              edited_utc REAL,
              score INTEGER,
              is_removed INTEGER,
              is_deleted INTEGER,
              parent_id TEXT,
              depth INTEGER,
              search_terms TEXT,
              captured_at REAL
            );
        """)

        _ensure_table(conn, "run_log", """
            CREATE TABLE IF NOT EXISTS run_log (
              run_id INTEGER PRIMARY KEY AUTOINCREMENT,
              started_at REAL,
              finished_at REAL,
              seeds_read INTEGER,
              posts_attempted INTEGER,
              comments_inserted INTEGER,
              failures INTEGER
            );
        """)

        _ensure_table(conn, "user_map", """
            CREATE TABLE IF NOT EXISTS user_map (
              user_id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT
            );
        """)

        # Columns (safe adds only)
        _ensure_columns(conn, "subreddits", {
            "subreddit_id": "TEXT",
            "name": "TEXT",
            "description": "TEXT",
            "is_nsfw": "INTEGER",
            "created_utc": "REAL",
            "rules": "TEXT",
            "sidebar_text": "TEXT",
        })

        _ensure_columns(conn, "subreddit_stats", {
            "subreddit_id": "TEXT",
            "captured_at": "REAL",
            "subscriber_count": "INTEGER",
            "active_users": "INTEGER",
            "posts_per_day": "REAL",
            "total_posts": "INTEGER",
        })

        _ensure_columns(conn, "users", {
            "username": "TEXT",
            "karma_comment": "INTEGER",
            "karma_post": "INTEGER",
            "created_utc": "REAL",
            "first_captured_at": "REAL",
            "last_seen_at": "REAL",
        })

        _ensure_columns(conn, "posts", {
            "matched_course_codes": "TEXT",
            "course_code": "TEXT",
            "course_code_count": "INTEGER",
            "vader_compound": "REAL",
            "processed_stage0_at": "REAL",
        })

        _ensure_columns(conn, "comments", {"parent_comment_id": "TEXT"})

        conn.commit()
    finally:
        conn.close()