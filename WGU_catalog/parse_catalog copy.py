# parse_catalog.py
import argparse
from pathlib import Path
import os
import json
import csv
import re

from WGU_catalog.lib.config import (
    TEXT_DIR,
    PROGRAM_NAMES_DIR,
    SNAPSHOT_COLLEGES_PATH,
    SECTION_INDEX_PATH,
    DEGREE_DUPLICATES_FILE,
    DEGREE_SNAPSHOTS_OUT_FILE,
    COURSE_INDEX_PATH,
    RAW_ROWS_OUTPUT_DIR,
    ANOMALY_DIR,
    COURSES_FLAT_CSV,
    COURSES_WITH_COLLEGE_CSV,
    HELPERS_DIR,
)

from lib.anchors import ANCHORS, COURSE_PATTERNS
from lib.snapshot_utils import load_snapshot_dict, pick_snapshot, pick_degree_snapshot

# Add debug flag
parser = argparse.ArgumentParser(description="Parse catalog with optional debug output")
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()
DEBUG = args.debug

# Simple wrappers for printing
print_info = print
def print_debug(msg):
    if DEBUG:
        print(msg)

# Ensure all output directories exist
for path in [HELPERS_DIR, PROGRAM_NAMES_DIR, RAW_ROWS_OUTPUT_DIR, ANOMALY_DIR]:
    path.mkdir(parents=True, exist_ok=True)

def match_course_row(row: str) -> dict:
    for pattern_name, pattern in COURSE_PATTERNS.items():
        match = pattern.match(row)
        if match:
            return {"matched_pattern": pattern_name, "groups": match.groups()}
    return None

def get_program_section_start(lines: list, valid_colleges: list) -> int:
    first_ccn_idx = None
    for i, line in enumerate(lines):
        if ANCHORS["CCN_HEADER"].search(line):
            first_ccn_idx = i
            break
    if first_ccn_idx is None:
        raise ValueError("[FAIL] No CCN header found")
    for j in range(first_ccn_idx, -1, -1):
        if lines[j].strip() in valid_colleges:
            return j
    raise ValueError("[FAIL] No College header found above first CCN")

def parse_catalog():
    outputs = []
    sections_index = {}

    # Load college snapshots for date-based filtering
    college_snapshots = load_snapshot_dict(SNAPSHOT_COLLEGES_PATH)

    catalog_files = sorted([f for f in os.listdir(TEXT_DIR) if f.endswith('.txt')])

    # Phase 1: Section index (degree boundaries)
    for FILE_NAME in catalog_files:
        FILE_PATH = Path(TEXT_DIR) / FILE_NAME
        parts = FILE_NAME.replace('.txt', '').split('_')[1:]
        CATALOG_DATE = f"{parts[0]}-{parts[1]}"
        print_info(f"\n📅 {CATALOG_DATE}")

        degree_names_path = Path(PROGRAM_NAMES_DIR) / f"{parts[0]}_{parts[1]}_program_names_v10.json"
        if not degree_names_path.exists():
            print_info(f"⚠️  Extracting program names...")
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                raw_lines = [line.strip() for line in f if line.strip()]

            result = {}
            current_college = None
            buffer = []
            collecting = False

            for line in raw_lines:
                if ANCHORS["SCHOOL_OF"].match(line):
                    if current_college and buffer:
                        result[current_college] = buffer
                    current_college = line
                    buffer = []
                    collecting = True
                    continue

                if any(pat.match(line) for pat in [
                    ANCHORS["COURSES_SECTION_BREAK"],
                    ANCHORS["PROGRAM_OUTCOMES"],
                    ANCHORS["FOOTER_COPYRIGHT"],
                    ANCHORS["FOOTER_TOTAL_CUS"],
                    ANCHORS["SCHOOL_OF"]
                ]):
                    if current_college and buffer:
                        result[current_college] = buffer
                    current_college = None
                    buffer = []
                    collecting = False
                    continue

                if collecting and not re.match(r"^(Steps|[0-9]|[•\-])", line):
                    buffer.append(line)

            if current_college and buffer:
                result[current_college] = buffer

            with open(degree_names_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print_info(f"✅ Program names saved")

        with open(degree_names_path, 'r', encoding='utf-8') as f:
            degree_names = json.load(f)
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f]

        sections_index.setdefault(CATALOG_DATE, {})
        found_count, fail_count = 0, 0
        print_info(f"🔍 Colleges: {len(degree_names)}")

        for college, programs in degree_names.items():
            print_info(f"  🎓 {college}")
            sections_index[CATALOG_DATE].setdefault(college, {})

            for degree_name in programs:
                start_idx = None
                stop_idx = len(lines)
                degree_heading_idx = next((i for i, line in enumerate(lines) if line == degree_name), None)

                if degree_heading_idx is None:
                    print_info(f"    ⚠️ Heading not found: {degree_name}")
                    fail_count += 1
                    continue

                for j in range(degree_heading_idx, len(lines)):
                    if ANCHORS['CCN_HEADER'].search(lines[j]):
                        start_idx = j
                        break
                else:
                    print_info(f"    ⚠️ CCN not found: {degree_name}")
                    fail_count += 1
                    continue

                # Tight stop-fence logic
                for k in range(start_idx + 1, len(lines)):
                    next_line = lines[k].strip()
                    if next_line in programs and next_line != degree_name:
                        stop_idx = k
                        break
                    if ANCHORS['SCHOOL_OF'].match(next_line):
                        stop_idx = k
                        break
                    if ANCHORS['FOOTER_TOTAL_CUS'].search(next_line) or ANCHORS['FOOTER_COPYRIGHT'].search(next_line):
                        stop_idx = k
                        break

                sections_index[CATALOG_DATE][college][degree_name] = [start_idx, stop_idx]
                print_debug(f"    ✅ {degree_name} at lines {start_idx}-{stop_idx}")
                found_count += 1

        print_info(f"📊 Summary: {found_count} ok / {fail_count} issues")

    # Save section index
    with open(SECTION_INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(sections_index, f, indent=2)
    print_info(f"📁 Saved: {SECTION_INDEX_PATH}")
    outputs.append(str(SECTION_INDEX_PATH))

    # Phase 2: Degree snapshots
    with open(SNAPSHOT_COLLEGES_PATH, 'r', encoding='utf-8') as f:
        college_snapshots = json.load(f)
    with open(DEGREE_DUPLICATES_FILE, 'r', encoding='utf-8') as f:
        degree_duplicates = json.load(f)

    degree_snapshots = {}
    for program_file in sorted(Path(PROGRAM_NAMES_DIR).glob('*_program_names_v10.json')):
        catalog_date = program_file.stem.split('_program_names_v10')[0].replace('_', '-')
        with open(program_file, 'r', encoding='utf-8') as f:
            program_names = json.load(f)

        snapshot_version = pick_degree_snapshot(catalog_date)
        canonical_order = college_snapshots[snapshot_version]

        snapshot_unsorted = {}
        embedded_certificates = set()
        trailing_certificates = []

        for college_name, degrees in program_names.items():
            resolved_degrees = [degree_duplicates.get(d.strip(), d.strip()) for d in degrees]

            if college_name == "Certificates - Standard Paths":
                trailing_certificates.extend(resolved_degrees)
            else:
                unique_sorted = sorted(set(resolved_degrees))
                snapshot_unsorted[college_name] = unique_sorted
                embedded_certificates.update(d for d in unique_sorted if "Certificate" in d)

        if trailing_certificates:
            trailing_certificates = sorted(set(trailing_certificates))
            overlap = embedded_certificates.intersection(trailing_certificates)
            if overlap:
                raise ValueError(f"[FAIL] Duplicate Certificates: {overlap}")
            snapshot_unsorted["Certificates - Standard Paths"] = trailing_certificates

        ordered = {}
        for college in canonical_order:
            if college in snapshot_unsorted:
                ordered[college] = snapshot_unsorted[college]
            elif college != "Certificates - Standard Paths":
                raise ValueError(f"[FAIL] College missing: {college} in {catalog_date}")

        degree_snapshots[catalog_date] = ordered

    with open(DEGREE_SNAPSHOTS_OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(degree_snapshots, f, indent=4, ensure_ascii=False)
    print_info(f"📁 Saved: {DEGREE_SNAPSHOTS_OUT_FILE}")
    outputs.append(str(DEGREE_SNAPSHOTS_OUT_FILE))

    # Phase 3: Raw course row extraction
    for FILE_NAME in sorted(os.listdir(TEXT_DIR)):
        if not FILE_NAME.endswith('.txt'):
            continue

        FILE_PATH = Path(TEXT_DIR) / FILE_NAME
        parts = FILE_NAME.replace('.txt', '').split('_')[1:]
        date_prefix = f"{parts[0]}_{parts[1]}"
        catalog_date = f"{parts[0]}-{parts[1]}"
        print_info(f"\n📘 Courses: {catalog_date}")

        valid_colleges = pick_snapshot(catalog_date, college_snapshots)
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f]

        try:
            start_idx = get_program_section_start(lines, valid_colleges)
        except ValueError as e:
            print_info(f"⚠️ {e}")
            continue

        scan_lines = lines[start_idx:]
        ccn_indices = [i for i, l in enumerate(scan_lines) if ANCHORS['CCN_HEADER'].search(l)]

        raw_course_rows = []
        for idx, ai in enumerate(ccn_indices):
            block_start = ai + 1
            block_end = ccn_indices[idx + 1] if idx + 1 < len(ccn_indices) else len(scan_lines)
            for i in range(block_start, block_end):
                if ANCHORS['FOOTER_TOTAL_CUS'].search(scan_lines[i]) or ANCHORS['FOOTER_COPYRIGHT'].search(scan_lines[i]):
                    block_end = i
                    break
            for i in range(block_start, block_end):
                line = scan_lines[i].strip()
                if line:
                    raw_course_rows.append(line)

        valid_rows = [r for r in raw_course_rows if match_course_row(r)]
        anomalies = [r for r in raw_course_rows if not match_course_row(r)]

        raw_out = RAW_ROWS_OUTPUT_DIR / f"{date_prefix}_raw_course_rows_v10.json"
        anomaly_out = ANOMALY_DIR / f"anomalies_{date_prefix}_v10.json"
        with open(raw_out, 'w', encoding='utf-8') as f:
            json.dump(raw_course_rows, f, indent=2)
        with open(anomaly_out, 'w', encoding='utf-8') as f:
            json.dump(anomalies, f, indent=2)
        print_info(f"  ✅ Saved raw + anomalies ({len(valid_rows)} valid, {len(anomalies)} anomalies)")
        outputs.extend([str(raw_out), str(anomaly_out)])

    # Phase 4: Write course indexes
    with open(COURSE_INDEX_PATH, 'r', encoding='utf-8') as f:
        course_index = json.load(f)

    with open(COURSES_FLAT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["CourseCode", "CourseName"])
        writer.writeheader()
        for ccn, details in course_index.items():
            writer.writerow({
                "CourseCode": ccn.strip(),
                "CourseName": details.get("canonical_title", "").strip()
            })
    print_info(f"📁 Saved: {COURSES_FLAT_CSV}")
    outputs.append(str(COURSES_FLAT_CSV))

    with open(COURSES_WITH_COLLEGE_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["CourseCode", "CourseName", "Colleges"])
        writer.writeheader()
        for ccn, details in course_index.items():
            colleges = {inst.get("college", "").strip() for inst in details.get("instances", []) if inst.get("college")}
            writer.writerow({
                "CourseCode": ccn.strip(),
                "CourseName": details.get("canonical_title", "").strip(),
                "Colleges": "; ".join(sorted(colleges))
            })
    print_info(f"📁 Saved: {COURSES_WITH_COLLEGE_CSV}")
    outputs.append(str(COURSES_WITH_COLLEGE_CSV))

    return {"success": True, "outputs": outputs}

if __name__ == '__main__':
    parse_catalog()
