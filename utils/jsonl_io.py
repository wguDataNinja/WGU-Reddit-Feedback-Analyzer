# utils/jsonl_io.py

"""Simple JSONL read/write helpers."""

import json
import os
from pathlib import Path
from typing import Iterator, Dict, Any, Iterable

def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    """Overwrite the file with the given records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    """Read a JSONL file line by line."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def append_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> int:
    """
    Append records to a JSONL file, creating the file if it doesn't exist.
    Returns the number of records appended.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
        # Flush and fsync to avoid data loss in crashes
        f.flush()
        os.fsync(f.fileno())
    return count