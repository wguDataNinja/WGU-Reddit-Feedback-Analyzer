# extract_first_degree_section.py

import re
import json
import sys
from WGU_catalog.lib.config import TEXT_DIR, COLLEGE_SNAPSHOTS

# Anchors
ANCHOR_CCN_HEADER  = re.compile(r"CCN.*Course Number", re.IGNORECASE)
ANCHOR_COLLEGE     = re.compile(r"College of ", re.IGNORECASE)
ANCHOR_TOTAL_CUS   = re.compile(r"Total CUs", re.IGNORECASE)
ANCHOR_COPYRIGHT   = re.compile(r"©")

# 1. Load catalog
catalog_files = sorted(TEXT_DIR.glob("catalog_*.txt"))
if not catalog_files:
    print("[ERROR] No catalog files found.")
    sys.exit(1)
file_path = catalog_files[0]
file_name = file_path.name
print(f"[DEBUG] Selected catalog: {file_name}")

# 2. Extract date and snapshot
parts = file_name.replace(".txt", "").split("_")[1:]
catalog_date = f"{parts[0]}-{parts[1]}"
print(f"[DEBUG] Catalog date: {catalog_date}")

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
print(f"[DEBUG] Valid colleges: {valid_colleges}")

# 3. Load lines
with open(file_path, "r", encoding="utf-8") as f:
    lines = [l.strip() for l in f]
print(f"[DEBUG] Loaded {len(lines)} lines")

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

# 7. Find CCN block start from degree
start_idx = next((k for k in range(degree_idx, len(lines)) if ANCHOR_CCN_HEADER.search(lines[k])), None)
if start_idx is None:
    print("[ERROR] No CCN block found after degree.")
    sys.exit(1)
print(f"[DEBUG] CCN block starts at line {start_idx}")

# 8. Find fence end
stop_idx = len(lines)
for k in range(start_idx + 1, len(lines)):
    line = lines[k].strip()
    if ANCHOR_COLLEGE.search(line) or ANCHOR_TOTAL_CUS.search(line) or ANCHOR_COPYRIGHT.search(line):
        stop_idx = k
        print(f"[DEBUG] Fence stop anchor at line {k}: '{line}'")
        break

# 9. Output draft section
sections_index = {
    catalog_date: {
        first_college: {
            first_degree: [start_idx, stop_idx]
        }
    }
}

print(json.dumps(sections_index, indent=2))