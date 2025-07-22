# scrape_catalog.py
import os
import sys

# Add the WGU_catalog directory to sys.path BEFORE importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.config import ANCHOR_COLLEGE, TEXT_DIR, SNAPSHOT_COLLEGES_PATH, DEGREE_DUPLICATES_FILE, ANCHOR_CCN_HEADER
import json

# Preload shared JSON inputs
with open(SNAPSHOT_COLLEGES_PATH, "r", encoding="utf-8") as f:
    COLLEGE_SNAPSHOTS = json.load(f)

with open(DEGREE_DUPLICATES_FILE, "r", encoding="utf-8") as f:
    DEGREE_DUPLICATES = json.load(f)

# 1. Load catalog
catalog_files = sorted(TEXT_DIR.glob("catalog_*.txt"), key=lambda p: p.name)
if not catalog_files:
    sys.exit(1)
file_path = catalog_files[0]
file_name = file_path.name

# 2. Extract date and snapshot
parts = file_name.replace(".txt", "").split("_")[1:]
catalog_date = f"{parts[0]}-{parts[1]}"

def pick_snapshot(date_str, snapshot_dict):
    versions = sorted(snapshot_dict.keys())
    chosen = None
    for v in versions:
        if v <= date_str:
            chosen = v
    if not chosen:
        raise ValueError(f"No snapshot for {date_str}")
    return snapshot_dict[chosen]

valid_colleges = pick_snapshot(catalog_date, COLLEGE_SNAPSHOTS)

# 3. Load lines
with open(file_path, "r", encoding="utf-8") as f:
    lines = [l.strip() for l in f]

# 4. Find first CCN header
first_ccn_idx = next((i for i, line in enumerate(lines) if ANCHOR_CCN_HEADER.search(line)), None)
if first_ccn_idx is None:
    print("[ERROR] No CCN header found.")
    sys.exit(1)
print(f"[DEBUG] CCN header at line {first_ccn_idx}: {lines[first_ccn_idx]}")


# 5. Walk upward to find enclosing college
first_college = None
actual_college_line = None
college_idx = None
for j in range(first_ccn_idx, -1, -1):
    line = lines[j].strip()
    if line in valid_colleges:
        first_college = line
        actual_college_line = line
        college_idx = j
        print(f"[DEBUG] Exact college match at {j}: '{line}'")
        break
    for college in valid_colleges:
        if line.startswith(college):
            first_college = college
            actual_college_line = line
            college_idx = j
            print(f"[DEBUG] Fuzzy college match at {j}: '{line}' → '{college}'")
            break
    if first_college:
        break

if not first_college:
    print("[ERROR] No valid college header found.")
    sys.exit(1)
print(f"[DEBUG] College found: '{first_college}' at line {college_idx}")
print(f"[DEBUG] Actual catalog line: '{actual_college_line}'")


# 6. Guess first degree by grabbing the next non-empty line
first_degree = None
degree_idx = None
for i in range(college_idx + 1, len(lines)):
    line = lines[i].strip()
    if line and not ANCHOR_COLLEGE.search(line):
        first_degree = line
        degree_idx = i
        print(f"[DEBUG] Guessed degree at line {i}: '{line}'")
        break

if not first_degree:
    print("[ERROR] Could not guess degree name.")
    sys.exit(1)










