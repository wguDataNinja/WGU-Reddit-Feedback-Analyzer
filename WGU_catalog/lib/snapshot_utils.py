# lib/snapshot_utils.py
import json
from pathlib import Path
from .config import SNAPSHOT_COLLEGES_PATH

def load_snapshot_dict(path: Path) -> dict:
    """
    Load a JSON snapshot file into a dict.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def pick_snapshot(date_str: str, snapshots: dict) -> list:
    """
    Given a catalog date (YYYY-MM) and a dict of snapshots keyed by version,
    return the snapshot list for the greatest version <= date_str.
    """
    versions = sorted(snapshots.keys())
    chosen = None
    for version in versions:
        if version <= date_str:
            chosen = version
    if chosen is None:
        raise ValueError(f"[FAIL] No snapshot version found for {date_str}")
    return snapshots[chosen]

def pick_degree_snapshot(catalog_date: str) -> str:
    """
    Return the snapshot version string (key) for the greatest college snapshot
    version <= catalog_date, using the master colleges snapshots file.
    """
    college_snapshots = load_snapshot_dict(SNAPSHOT_COLLEGES_PATH)
    versions = sorted(college_snapshots.keys())
    chosen = None
    for version in versions:
        if version <= catalog_date:
            chosen = version
    if chosen is None:
        raise ValueError(f"[FAIL] No valid College snapshot found for {catalog_date}")
    return chosen