# fence_builder_cutoff.py

import os
import re
import json

from WGU_catalog.lib.config import TEXT_DIR, PROGRAM_NAMES_DIR, SECTION_INDEX_PATH

# === Anchors ===
ANCHOR_CCN_HEADER = re.compile(r"CCN.*Course Number", re.IGNORECASE)
ANCHOR_COLLEGE = re.compile(r"College of ", re.IGNORECASE)
ANCHOR_TOTAL_CUS = re.compile(r"Total CUs", re.IGNORECASE)
ANCHOR_COPYRIGHT = re.compile(r"©")

sections_index = {}

catalog_files = sorted([f for f in TEXT_DIR.glob("catalog_*.txt")])

for file_path in catalog_files:
    FILE_NAME = file_path.name
    DATE_PART = FILE_NAME.replace(".txt", "").split("_")[1:]
    CATALOG_DATE = f"{DATE_PART[0]}-{DATE_PART[1]}"
    print(f"\n📅 Processing: {CATALOG_DATE}")

    # === Load Degree names ===
    degree_names_path = PROGRAM_NAMES_DIR / f"{DATE_PART[0]}_{DATE_PART[1]}_program_names_v10.json"
    if not degree_names_path.exists():
        print(f"❌ No Degree names JSON for {CATALOG_DATE} — skipping.")
        continue

    with open(degree_names_path, 'r') as f:
        degree_names = json.load(f)

    # === Load lines ===
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f]

    sections_index.setdefault(CATALOG_DATE, {})

    # ✅ Process only first college and first degree
    first_college = next(iter(degree_names))
    first_degree = degree_names[first_college][0]
    print(f"\n🔍 Processing first college: {first_college}")
    print(f"🔍 First degree: {first_degree}")

    sections_index[CATALOG_DATE].setdefault(first_college, {})

    # === 1. Find Degree heading ===
    degree_heading_idx = None
    for i, line in enumerate(lines):
        if line == first_degree:
            degree_heading_idx = i
            break
    if degree_heading_idx is None:
        print(f"⚠️  Degree name not found: {first_degree}")
        exit()

    # === 2. Forward scan to first CCN_HEADER ===
    start_idx = None
    for j in range(degree_heading_idx, len(lines)):
        if ANCHOR_CCN_HEADER.search(lines[j]):
            start_idx = j
            break
    if start_idx is None:
        print(f"⚠️  No CCN table found for: {first_degree}")
        exit()

    # === 3. Find stop fence ===
    stop_idx = len(lines)
    for k in range(start_idx + 1, len(lines)):
        next_line = lines[k].strip()
        if next_line in degree_names[first_college] and next_line != first_degree:
            stop_idx = k
            break
        if ANCHOR_COLLEGE.search(next_line) or ANCHOR_TOTAL_CUS.search(next_line) or ANCHOR_COPYRIGHT.search(next_line):
            stop_idx = k
            break

    sections_index[CATALOG_DATE][first_college][first_degree] = [start_idx, stop_idx]
    print(f"✅ Fenced: {first_degree} → lines {start_idx} to {stop_idx}")

    # ✅ Output preview
    print("\n🔎 Preview fenced lines:")
    for line in lines[start_idx:stop_idx][:10]:
        print("  ", line)

    print(f"\n🛑 Cutoff reached — first section fenced successfully.\n")
    exit()