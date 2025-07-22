# convert_degree_duplicates.py

import csv
import json
from pathlib import Path

# === Resolve paths ===
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]

INPUT_CSV = PROJECT_ROOT / "WGU_catalog" / "data" / "helpers" / "degree_duplicates_master.csv"
OUTPUT_JSON = PROJECT_ROOT / "WGU_catalog" / "helpers" / "degree_duplicates_master.json"

print(f"[DEBUG] Looking for input CSV at: {INPUT_CSV}")
print(f"[DEBUG] Will write JSON to: {OUTPUT_JSON}")

# === Check existence before opening ===
if not INPUT_CSV.exists():
    raise FileNotFoundError(f"[FAIL] Input CSV not found: {INPUT_CSV}")

duplicates_map = {}

with open(INPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        raw = row["raw_degree_name"].strip()
        resolved = row["resolved_name"].strip()
        if resolved:
            duplicates_map[raw] = resolved

# === Ensure output directory exists ===
OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(duplicates_map, f, indent=2)

print(f"Saved: {OUTPUT_JSON} ({len(duplicates_map)} entries)")