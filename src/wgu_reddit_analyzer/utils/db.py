"""SQLite connection helpers for the WGU Reddit Analyzer."""

from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import List, Union

from .logging_utils import get_logger

logger = get_logger("db")

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_DIR = REPO_ROOT / "db"
DB_PATH = DB_DIR / "WGU-Reddit.db"
DB_DIR.mkdir(parents=True, exist_ok=True)


def get_db_connection(db_path: Union[Path, str, None] = None) -> sqlite3.Connection:
    """Return SQLite connection; default is db/WGU-Reddit.db."""
    raw = db_path or DB_PATH
    path = Path(os.path.expanduser(str(raw))).resolve()

    if not path.parent.exists():
        logger.error("DB directory missing: %s", path.parent)
        raise sqlite3.OperationalError(f"DB directory missing: {path.parent}")

    logger.info("Opening DB at: %s", path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Return list of column names for a given table."""
    cur = conn.execute(f"PRAGMA table_info({table});")
    return [r[1] for r in cur.fetchall()]