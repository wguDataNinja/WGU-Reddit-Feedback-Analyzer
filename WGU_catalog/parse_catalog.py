# parse_catalog.py

from pathlib import Path
import os
import re
import json
import csv
from collections import defaultdict

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
from lib.anchors import ANCHORS, COURSE_PATTERNS, FILTERS
from lib.snapshot_utils import load_snapshot_dict, pick_snapshot, pick_degree_snapshot

# Anchors for degree titles and faculty lines
DEGREE_HEADER = re.compile(r"^(Bachelor|Master|Certificate|Post|Endorsement|MBA|MS,|BS,)", re.IGNORECASE)
FACULTY_LINE = re.compile(r"^[A-Z][a-z]+,\s+[A-Z][a-z]+;")

# Ensure output directories exist
for d in (PROGRAM_NAMES_DIR, HELPERS_DIR, RAW_ROWS_OUTPUT_DIR, ANOMALY_DIR):
    Path(d).mkdir(parents=True, exist_ok=True)

# Load trusted college snapshots
college_snapshots = load_snapshot_dict(SNAPSHOT_COLLEGES_PATH)

# ------------------------------------------------------------------------------
# STEP 0: Extract program names per catalog
# ------------------------------------------------------------------------------
for txt_path in sorted(Path(TEXT_DIR).glob("*.txt")):
    parts = txt_path.stem.split("_")  # ["catalog","YYYY","MM"]
    date = f"{parts[1]}-{parts[2]}"
    valid_cols = pick_snapshot(date, college_snapshots)

    with open(txt_path, encoding="utf-8") as f:
        lines = [l.strip() for l in f]

    first_ccn = next((i for i,l in enumerate(lines) if ANCHORS["CCN_HEADER"].search(l)), None)
    if first_ccn is None:
        continue

    progs = defaultdict(list)
    cur_col = None
    for i in range(first_ccn):
        line = lines[i]
        if line in valid_cols:
            cur_col = line
            continue
        if not cur_col:
            continue
        if (DEGREE_HEADER.match(line)
            and not FILTERS["PROGRAM_TITLE_EXCLUDE_PATTERNS"].match(line)
            and ";" not in line):
            progs[cur_col].append(line)

    out = Path(PROGRAM_NAMES_DIR)/f"{parts[1]}_{parts[2]}_program_names_v10.json"
    with open(out,"w",encoding="utf-8") as f:
        json.dump(progs, f, indent=2)

# ------------------------------------------------------------------------------
# STEP 1: Extract raw rows and anomalies
# ------------------------------------------------------------------------------
for txt_path in sorted(Path(TEXT_DIR).glob("*.txt")):
    parts = txt_path.stem.split("_")
    date = f"{parts[1]}-{parts[2]}"
    valid_cols = pick_snapshot(date, college_snapshots)

    with open(txt_path,encoding="utf-8") as f:
        lines = [l.strip() for l in f]

    first_ccn = next((i for i,l in enumerate(lines) if ANCHORS["CCN_HEADER"].search(l)),None)
    if first_ccn is None:
        continue
    start = None
    for j in range(first_ccn,-1,-1):
        if lines[j] in valid_cols:
            start=j; break
    if start is None: continue

    scan=lines[start:]
    anchors=[i for i,l in enumerate(scan) if ANCHORS["CCN_HEADER"].search(l)]

    raw=[]
    for idx,a in enumerate(anchors):
        bstart=a+1
        bend=anchors[idx+1] if idx+1<len(anchors) else len(scan)
        for k in range(bstart,bend):
            if (ANCHORS["FOOTER_COPYRIGHT"].search(scan[k])
                or ANCHORS["FOOTER_TOTAL_CUS"].search(scan[k])):
                bend=k; break
        for k in range(bstart,bend):
            if scan[k].strip(): raw.append(scan[k].strip())

    out_raw=Path(RAW_ROWS_OUTPUT_DIR)/f"{parts[1]}_{parts[2]}_raw_course_rows.json"
    with open(out_raw,"w",encoding="utf-8") as f:
        json.dump(raw,f,indent=2)

    anomalies=[r for r in raw if not any(p.match(r) for p in COURSE_PATTERNS.values())]
    out_an=Path(ANOMALY_DIR)/f"anomalies_{parts[1]}_{parts[2]}.json"
    with open(out_an,"w",encoding="utf-8") as f:
        json.dump(anomalies,f,indent=2)

# ------------------------------------------------------------------------------
# STEP 2: Build sections_index
# ------------------------------------------------------------------------------
sections_index={}
for txt_path in sorted(Path(TEXT_DIR).glob("*.txt")):
    parts=txt_path.stem.split("_")
    date=f"{parts[1]}-{parts[2]}"
    prog_file=Path(PROGRAM_NAMES_DIR)/f"{parts[1]}_{parts[2]}_program_names_v10.json"
    if not prog_file.exists(): continue

    with open(prog_file,encoding="utf-8") as f:
        degs=json.load(f)
    with open(txt_path,encoding="utf-8") as f:
        lines=[l.strip() for l in f]

    sections_index[date]={}
    for col,progs in degs.items():
        sections_index[date][col] = {}
        for prog in progs:
            if prog not in lines: continue
            hi = lines.index(prog)
            start = next((j for j in range(hi,len(lines))
                          if ANCHORS["CCN_HEADER"].search(lines[j])),None)
            if start is None: continue
            stop=len(lines)
            for k in range(start+1,len(lines)):
                nl=lines[k].strip()
                if nl in progs and nl!=prog: stop=k; break
                if nl in degs.keys(): stop=k; break
                if (ANCHORS["FOOTER_COPYRIGHT"].search(nl)
                    or ANCHORS["FOOTER_TOTAL_CUS"].search(nl)): stop=k; break
            sections_index[date][col][prog]=[start,stop]

with open(SECTION_INDEX_PATH,"w",encoding="utf-8") as f:
    json.dump(sections_index,f,indent=2)
# ------------------------------------------------------------------------------
# STEP 3: Build degree_snapshots
# ------------------------------------------------------------------------------
with open(DEGREE_DUPLICATES_FILE, encoding="utf-8") as f:
    raw_dupes = json.load(f)

# Normalize into: raw_degree_name → resolved_name
if isinstance(raw_dupes, list) and all("raw_degree_name" in d and "resolved_name" in d for d in raw_dupes):
    degree_duplicates = {
        d["raw_degree_name"].strip(): d["resolved_name"].strip()
        for d in raw_dupes
    }
else:
    raise ValueError("Unrecognized degree_duplicates format: expected list of dicts with 'raw_degree_name' and 'resolved_name'.")

degree_snapshots = {}

for date, fences in sections_index.items():
    version = pick_degree_snapshot(date)
    canonical_colleges = college_snapshots[version]

    unresolved = {}
    embedded_certificates = set()
    trailing_certificates = []

    for college, degrees in fences.items():
        resolved = [degree_duplicates.get(name, name).strip() for name in degrees.keys()]

        if college == "Certificates - Standard Paths":
            trailing_certificates.extend(resolved)
        else:
            unique = sorted(set(resolved))
            unresolved[college] = unique
            embedded_certificates.update(d for d in unique if "Certificate" in d)

    if trailing_certificates:
        trailing_certificates = sorted(set(trailing_certificates))
        overlap = embedded_certificates & set(trailing_certificates)
        if overlap:
            raise ValueError(f"[FAIL] Overlapping Certificates in {date}: {overlap}")
        unresolved["Certificates - Standard Paths"] = trailing_certificates

    # Enforce canonical College order
    ordered_snapshot = {}
    for college in canonical_colleges:
        if college in unresolved:
            ordered_snapshot[college] = unresolved[college]
        elif college == "Certificates - Standard Paths":
            continue
        else:
            raise ValueError(f"[FAIL] Missing expected College '{college}' in {date}")

    degree_snapshots[date] = ordered_snapshot

with open(DEGREE_SNAPSHOTS_OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(degree_snapshots, f, indent=2, ensure_ascii=False)
# ------------------------------------------------------------------------------
# STEP 4: Build course_index
# ------------------------------------------------------------------------------
course_index={}
with open(SECTION_INDEX_PATH,encoding="utf-8") as f:
    secs=json.load(f)

for txt_path in sorted(Path(TEXT_DIR).glob("*.txt")):
    parts=txt_path.stem.split("_")
    date=f"{parts[1]}-{parts[2]}"
    if date not in secs: continue

    with open(txt_path,encoding="utf-8") as f:
        lines=[l.strip() for l in f]

    for col,progs in secs[date].items():
        for prog,(s,t) in progs.items():
            block=lines[s:t]
            anchs=[i for i,l in enumerate(block) if ANCHORS["CCN_HEADER"].search(l)]
            for idx in anchs:
                for line in block[idx+1:]:
                    if not line: continue
                    if (ANCHORS["FOOTER_COPYRIGHT"].search(line)
                        or ANCHORS["FOOTER_TOTAL_CUS"].search(line)): break
                    m_info=None
                    for nm,pt in COURSE_PATTERNS.items():
                        m=pt.match(line)
                        if m: m_info=(nm,m.groups()); break
                    if not m_info: continue
                    nm,gr=m_info
                    if nm=="CCN_FULL":
                        dept,num,code,title,cus,term=gr
                    elif nm=="CODE_ONLY": code,title,cus,term=gr; dept=num=None
                    else: title,cus,term=gr; dept=num=code=None
                    ent=course_index.setdefault(code,{"canonical_title":title,"canonical_cus":int(cus),"instances":[]})
                    ent["instances"].append({"catalog_date":date,"college":col,"degree":prog,"pattern":nm,"raw":line})

with open(COURSE_INDEX_PATH,"w",encoding="utf-8") as f:
    json.dump(course_index,f,indent=2)

# ------------------------------------------------------------------------------
# STEP 5: Write CSVs
# ------------------------------------------------------------------------------
with open(COURSES_FLAT_CSV,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,["CourseCode","CourseName"]); w.writeheader()
    for c,i in course_index.items(): w.writerow({"CourseCode":c,"CourseName":i["canonical_title"]})
with open(COURSES_WITH_COLLEGE_CSV,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,["CourseCode","CourseName","Colleges"]); w.writeheader()
    for c,i in course_index.items():
        cols={inst["college"] for inst in i["instances"] if inst.get("college")}
        w.writerow({"CourseCode":c,"CourseName":i["canonical_title"],"Colleges":"; ".join(sorted(cols))})