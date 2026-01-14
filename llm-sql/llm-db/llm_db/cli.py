from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple

from .query_translate_stub import translate_nl_to_plan
from .sql_selector import compile_plan
from .storage import execute_readonly


def _print_rows(cols: List[str], rows: List[Tuple[Any, ...]]) -> None:
    print("\t".join(cols))
    for r in rows:
        print("\t".join("" if v is None else str(v) for v in r))


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="llm-db")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="Run a natural language query against posts (read-only)")
    q.add_argument("--db", required=True, help="Path to sqlite database")
    q.add_argument("nl", help="Natural language query")

    a = p.parse_args(argv)

    if a.cmd == "query":
        plan = translate_nl_to_plan(a.nl)
        compiled = compile_plan(plan)
        cols, rows = execute_readonly(a.db, compiled.sql, compiled.params, compiled.max_rows)

        meta: Dict[str, Any] = {
            "template_id": compiled.template_id.value,
            "params": list(compiled.params),
            "row_count": len(rows),
        }
        print(json.dumps(meta, indent=2))
        _print_rows(cols, rows)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())