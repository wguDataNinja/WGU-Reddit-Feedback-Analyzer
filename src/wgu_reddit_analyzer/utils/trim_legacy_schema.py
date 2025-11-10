#!/usr/bin/env python3
from __future__ import annotations
import sqlite3
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DB = REPO_ROOT / "data" / "WGU-Reddit.db"
DEST_DB = REPO_ROOT / "data" / "WGU-Reddit.clean.db"

# Canonical tables we keep for the new pipeline
KEEP_TABLES = {
    "posts",
    "comments",
    "posts_keyword",
    "comments_keyword",
    "subreddits",
    "subreddit_stats",
    "run_log",
}


def _get_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    return [r[0] for r in cur.fetchall()]


def create_clean_copy(src: Path = SRC_DB, dest: Path = DEST_DB) -> None:
    if not src.exists():
        raise SystemExit(f"Source DB not found: {src}")

    if dest.exists():
        raise SystemExit(
            f"Refusing to overwrite existing clean DB: {dest}\n"
            "If you want to regenerate it, delete it manually and rerun."
        )

    src_conn = sqlite3.connect(src)
    src_conn.row_factory = sqlite3.Row
    dest_conn = sqlite3.connect(dest)

    try:
        src_tables = set(_get_tables(src_conn))

        # 1) Create schemas in dest cloned from src for kept tables
        for table in sorted(KEEP_TABLES & src_tables):
            cur = src_conn.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name=?;",
                (table,),
            )
            row = cur.fetchone()
            create_sql = row[0] if row and row[0] else None
            if not create_sql:
                print(f"[WARN] No CREATE TABLE SQL for {table}, skipping.")
                continue

            dest_conn.execute(create_sql)
            print(f"[OK] Created table {table} in clean DB.")

        dest_conn.commit()

        # 2) Copy rows
        for table in sorted(KEEP_TABLES & src_tables):
            cols = [
                r[1]
                for r in src_conn.execute(f"PRAGMA table_info({table});").fetchall()
            ]
            if not cols:
                continue

            cols_csv = ", ".join(cols)
            placeholders = ", ".join(["?"] * len(cols))

            rows = src_conn.execute(
                f"SELECT {cols_csv} FROM {table};"
            ).fetchall()

            if not rows:
                print(f"[OK] {table}: no rows to copy.")
                continue

            dest_conn.executemany(
                f"INSERT INTO {table} ({cols_csv}) VALUES ({placeholders})",
                ([row[c] for c in cols] for row in rows),
            )
            dest_conn.commit()
            print(f"[OK] {table}: copied {len(rows)} rows.")

        print(f"\nClean DB created at: {dest}")
        print("Tables included:")
        for t in sorted(KEEP_TABLES & src_tables):
            print(f"  - {t}")

    finally:
        src_conn.close()
        dest_conn.close()


def main() -> None:
    print(f"Source DB: {SRC_DB}")
    print(f"Target DB: {DEST_DB}")
    create_clean_copy()


if __name__ == "__main__":
    main()