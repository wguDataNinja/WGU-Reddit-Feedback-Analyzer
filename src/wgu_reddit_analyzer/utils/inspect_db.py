#!/usr/bin/env python3
"""Quick SQLite inspector for WGU Reddit Analyzer."""

from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "db" / "WGU-Reddit.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return SQLite connection with Row factory."""
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_schema(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    """Return {table: [columns]} for the connected database."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    schema: Dict[str, List[str]] = {}
    for t in tables:
        cols = conn.execute(f"PRAGMA table_info({t});").fetchall()
        schema[t] = [c["name"] if isinstance(c, sqlite3.Row) else c[1] for c in cols]
    return schema


def print_overview(conn: sqlite3.Connection) -> None:
    """Print all tables with row counts and column names."""
    print(f"DB Path: {DB_PATH}\n")
    schema = get_schema(conn)
    if not schema:
        print("No tables found.")
        return

    print("Tables & Row Counts")
    print("-------------------")
    for t in sorted(schema):
        (cnt,) = conn.execute(f"SELECT COUNT(*) FROM {t};").fetchone()
        print(f"{t:20s} {cnt:10d}")
    print("\nSchema")
    print("------")
    for t, cols in sorted(schema.items()):
        print(f"{t}:")
        for c in cols:
            print(f"  - {c}")
        print("")


def print_samples(conn: sqlite3.Connection, limit: int) -> None:
    """Print up to N sample rows from each table."""
    schema = get_schema(conn)
    if not schema:
        return

    print(f"Sample rows (up to {limit} per table)")
    print("-----------------------------------")
    for t in sorted(schema):
        print(f"\nTable: {t}")
        rows = conn.execute(f"SELECT * FROM {t} LIMIT {limit};").fetchall()
        if not rows:
            print("  (no rows)")
            continue
        cols = rows[0].keys()
        print("  Columns:", ", ".join(cols))
        for r in rows:
            preview = ", ".join(f"{k}={r[k]!r}" for k in cols)
            if len(preview) > 240:
                preview = preview[:237] + "..."
            print("  ", preview)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect WGU-Reddit SQLite database (schema, counts, samples)."
    )
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Path to SQLite DB.")
    parser.add_argument("--samples", type=int, default=0, help="Print N sample rows per table.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        raise SystemExit(1)

    conn = get_connection(db_path)
    try:
        print_overview(conn)
        if args.samples > 0:
            print_samples(conn, args.samples)
    finally:
        conn.close()


if __name__ == "__main__":
    main()