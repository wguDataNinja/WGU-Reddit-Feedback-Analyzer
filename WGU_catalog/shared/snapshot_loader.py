# snapshot_loader.py

import json
from pathlib import Path

# Set project root (assumes this file is in shared/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_REFS_DIR = PROJECT_ROOT / "shared"

def load_snapshot_json(rel_path: str) -> dict:
    """Load a trusted snapshot JSON from shared/catalog_refs/."""
    full_path = CATALOG_REFS_DIR / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"[FAIL] Snapshot not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_snapshot(date_str: str, snapshot_dict: dict) -> dict | list:
    """Select the most recent snapshot <= catalog date."""
    versions = sorted(snapshot_dict.keys())
    chosen = None
    for version in versions:
        if version <= date_str:
            chosen = version
    if not chosen:
        raise ValueError(f"[FAIL] No snapshot version found for {date_str}")
    return snapshot_dict[chosen]
def load_snapshot_json(rel_path: str) -> dict:
    """
    Load a trusted snapshot JSON from shared/catalog_refs/.

    Args:
        rel_path (str): e.g. "colleges/college_snapshots.json"

    Returns:
        dict: Loaded snapshot content
    """
    full_path = CATALOG_REFS_DIR / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"[FAIL] Snapshot not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_snapshot(date_str: str, snapshot_dict: dict) -> dict | list:
    """
    Selects the most recent snapshot ≤ catalog date.

    Args:
        date_str (str): Catalog date in YYYY-MM format
        snapshot_dict (dict): Snapshots keyed by version (e.g. '2017-01')

    Returns:
        dict | list: The snapshot corresponding to the chosen version
    """
    versions = sorted(snapshot_dict.keys())
    chosen = None
    for version in versions:
        if version <= date_str:
            chosen = version
    if not chosen:
        raise ValueError(f"[FAIL] No snapshot version found for {date_str}")
    return snapshot_dict[chosen]


if __name__ == "__main__":
    print("Test: Load and pick from college_snapshots.json")
    snapshots = load_snapshot_json("colleges/college_snapshots.json")
    result = pick_snapshot("2017-01", snapshots)
    print("Snapshot selected:", result)