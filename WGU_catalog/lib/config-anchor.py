# lib/config.py
from pathlib import Path
import json

# Project root: /Users/buddy/Desktop/WGU-Reddit/WGU_catalog
BASE_DIR = Path(__file__).parent.parent

# Inputs
TEXT_DIR = BASE_DIR / "data" / "raw_catalog_texts"
SHARED_DIR = BASE_DIR / "shared"

# Outputs (all under /WGU_catalog/outputs)
OUTPUTS_DIR = BASE_DIR / "outputs"
HELPERS_DIR = OUTPUTS_DIR / "helpers"
PROGRAM_NAMES_DIR = OUTPUTS_DIR / "program_names"
RAW_ROWS_OUTPUT_DIR = OUTPUTS_DIR / "raw_course_rows"
ANOMALY_DIR = OUTPUTS_DIR / "anomalies"

# Shared inputs
SNAPSHOT_COLLEGES_PATH = SHARED_DIR / "college_snapshots.json"
DEGREE_DUPLICATES_FILE = SHARED_DIR / "degree_duplicates_master.json"

# Generated outputs
SECTION_INDEX_PATH = HELPERS_DIR / "sections_index_v10.json"
DEGREE_SNAPSHOTS_OUT_FILE = HELPERS_DIR / "degree_snapshots_v10_seed.json"
COURSE_INDEX_PATH = HELPERS_DIR / "course_index_v10.json"

# Final CSV outputs
COURSES_FLAT_CSV = OUTPUTS_DIR / "courses_flat_v10.csv"
COURSES_WITH_COLLEGE_CSV = OUTPUTS_DIR / "courses_with_college_v10.csv"

# Default test file
TEST_FILE = TEXT_DIR / "catalog_2017_01.txt"

# Ensure required output directories exist
for d in [OUTPUTS_DIR, HELPERS_DIR, PROGRAM_NAMES_DIR, RAW_ROWS_OUTPUT_DIR, ANOMALY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Preload shared JSON inputs
with open(SNAPSHOT_COLLEGES_PATH, "r", encoding="utf-8") as f:
    COLLEGE_SNAPSHOTS = json.load(f)

with open(DEGREE_DUPLICATES_FILE, "r", encoding="utf-8") as f:
    DEGREE_DUPLICATES = json.load(f)