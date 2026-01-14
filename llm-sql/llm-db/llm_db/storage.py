from __future__ import annotations

import sqlite3
from typing import Any, List, Sequence, Tuple

_FORBIDDEN = (
    "insert ",
    "update ",
    "delete ",
    "drop ",
    "alter ",
    "create ",
    "attach ",
    "detach ",
    "pragma ",
    "reindex ",
    "vacuum ",
    "replace ",
)


def execute_readonly(
    db_path: str,
    sql: str,
    params: Sequence[Any],
    max_rows: int,
) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    s = sql.strip().lower()
    if not s.startswith("select"):
        raise ValueError("Only SELECT statements allowed")
    if ";" in sql:
        raise ValueError("Multi-statement SQL not allowed")
    for kw in _FORBIDDEN:
        if kw in s:
            raise ValueError(f"Forbidden keyword: {kw.strip()}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = conn.execute(sql, tuple(params))
        cols = [d[0] for d in cur.description]
        rows = []
        for i, row in enumerate(cur.fetchall()):
            if i >= max_rows:
                break
            rows.append(row)
        return cols, rows
    finally:
        conn.close()