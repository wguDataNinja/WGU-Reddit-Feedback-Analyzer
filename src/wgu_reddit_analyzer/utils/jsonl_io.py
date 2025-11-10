"""JSONL read/write helpers for WGU Reddit Analyzer."""

from pathlib import Path
import json, os


def write_jsonl(records, path: Path) -> int:
    """Write list of records to a JSONL file (overwrite)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records or []:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def append_jsonl(records, path: Path) -> int:
    """Append list of records to a JSONL file (syncs to disk)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for r in records or []:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
        f.flush()
        os.fsync(f.fileno())
    return n


def read_jsonl(path: Path):
    """Read JSONL file into list of dicts."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]