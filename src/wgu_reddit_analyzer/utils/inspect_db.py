#!/usr/bin/env python3
"""Quick SQLite inspector for WGU Reddit Analyzer"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import List, Set

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "db" / "WGU-Reddit.db"
ALLOWLIST_PATH = REPO_ROOT / "data" / "wgu_subreddits.txt"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def load_allowlist(path: Path) -> Set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def placeholders(n: int) -> str:
    return ",".join(["?"] * n)


def get_posts_columns(conn: sqlite3.Connection) -> List[str]:
    cols = conn.execute("PRAGMA table_info(posts);").fetchall()
    return [c["name"] if isinstance(c, sqlite3.Row) else c[1] for c in cols]


def print_overview(conn: sqlite3.Connection, allow: Set[str]) -> None:
    ph = placeholders(len(allow))
    params = tuple(sorted(allow))

    (post_count,) = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM posts p
        JOIN subreddits s ON s.subreddit_id = p.subreddit_id
        WHERE s.name IN ({ph})
        """,
        params,
    ).fetchone()

    (subreddit_count,) = conn.execute(
        f"""
        SELECT COUNT(DISTINCT s.name)
        FROM posts p
        JOIN subreddits s ON s.subreddit_id = p.subreddit_id
        WHERE s.name IN ({ph})
        """,
        params,
    ).fetchone()

    print("DB Snapshot Overview")
    print("====================")
    print(f"Database: {DB_PATH}")

    print("Core Content Tables")
    print("---------------------------------------")
    print(f"posts{'':16s}{post_count} rows\n")

    print("Coverage")
    print("-----------------------------")
    print(f"unique subreddits{'':7s}{subreddit_count}\n")

    print("Posts Table Schema")
    print("------------------")
    print("posts:")
    for name in get_posts_columns(conn):
        print(f"  - {name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect WGU-Reddit SQLite database (walkthrough-focused: allowlist-filtered posts/subreddits)."
    )
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Path to SQLite DB.")
    parser.add_argument(
        "--allowlist",
        type=str,
        default=str(ALLOWLIST_PATH),
        help="Path to subreddit allowlist (one subreddit name per line).",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        raise SystemExit(1)

    allowlist_path = Path(args.allowlist)
    if not allowlist_path.exists():
        print(f"ERROR: Allowlist not found at {allowlist_path}")
        raise SystemExit(1)

    allow = load_allowlist(allowlist_path)
    if not allow:
        print(f"ERROR: Allowlist is empty: {allowlist_path}")
        raise SystemExit(1)

    conn = get_connection(db_path)
    try:
        print_overview(conn, allow)
    finally:
        conn.close()


if __name__ == "__main__":
    main()