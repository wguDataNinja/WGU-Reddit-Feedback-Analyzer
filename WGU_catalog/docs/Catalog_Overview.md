#docs/Catalog_Overview.md.


# 📚 WGU Catalog Overview

📅 Last Updated: 2025-07-04  
🛠 Maintainer: [Buddy]  
🔒 Status: V10 Locked — Clean Baseline

---

## 🎯 Project Purpose

This module extracts structured academic data from WGU's institutional catalogs (2017–2025) for use in downstream NLP, classification, and time-series analysis. It powers course code lookup, college-level classification, and institutional growth tracking within the broader **WGU Reddit Monitoring Capstone** project.

---

## 📥 Catalog Download + Parse Pipeline

This pipeline downloads and processes all WGU catalogs from 2017–2025 using a versioned, patchable system.

### 🗂️ Source Collection

- **`institutional-catalog.html`**  
  ⤷ Manual snapshot of the WGU Institutional Catalog page  
- **`extract_catalog_links.py`**  
  ⤷ Parses snapshot → outputs `catalog_links.txt`

### 📦 Download Plan & Validation

- **`parse_and_rename_catalogs.py`**  
  ⤷ Builds `catalog_download_plan.csv` from URLs using regex + normalized naming  
- **`catalog_download_patch.csv`**  
  ⤷ Optional manual patching for missed or malformed files  
- **`download_from_plan.py`**  
  ⤷ Downloads PDFs → `raw/`, normalized as `catalog_YYYY_MM.pdf`  
- **`verify_catalog_downloads.py`**  
  ⤷ Checks for expected catalogs by month → flags gaps

### 🧾 Parsing PDFs to Text

- **`plumber_parse_all_pdfs.py`**  
  ⤷ Uses `pdfplumber` to convert PDFs → `.txt` in `plumber_parsed/`  
- **`plumber_parse_single_pdf.py`**  
  ⤷ Used for debugging individual catalogs  

---

## 🧠 Scraper Architecture — V10 Baseline

All scraping logic is built from scratch under V10. No legacy PyPDF2 outputs or mixed helpers are used. Parsing is clean, testable, and versioned.

### ✅ Key Guarantees

- Trusted input: only `.txt` from `pdfplumber`
- No legacy merges (v5–v9 ignored)
- All schema quirks and fixes logged in `catalog_schema_notes_v10.md`
- All regex patterns explicitly reviewed
- Fails on ambiguity — never guesses College/Degree headers

### 📂 Folder Structure

WGU_catalog/
├── catalogs/
│   ├── raw/                  # PDFs
│   ├── plumber_parsed/       # Clean .txt
├── helpers/
│   ├── college_snapshots_v10_seed.json
│   ├── degree_snapshots_v10.json
│   ├── catalog_schema_notes_v10.md
│   └── …
├── scripts/                  # Only _v10 scripts
├── notebooks/                # Only _v10 notebooks
├── outputs/
│   ├── program_names/
│   ├── raw_course_rows/
│   ├── mappings/
│   ├── flat/
│   └── …
└── docs/
└── Catalog_Overview.md

---

## 📊 Capstone Integration — NLP & Classification

### Use Case

This catalog module supports the capstone project:

**“WGU Reddit Monitoring Pipeline with Sentiment Analysis and NLP”**

### Connected Pipeline Steps

1. **Extract course codes** from post text using `Cxxxx` identifiers  
2. **Map course codes** to College and Degree using the parsed catalog JSONs  
3. **Classify posts** by College (e.g., IT, Health) based on course mapping  
4. **Detect drift** in program names and catalog structure using time-series

### Example: Institutional Growth Tracking

You can visualize department expansion using parsed snapshots.

```python
# program_counts_by_year.csv → output from snapshot extract

year,college,num_programs
2020,College of IT,12
2021,College of IT,15
...

Use this to create plots of College growth, track naming changes, or describe structural drift in your final paper.

⸻

📌 Standing Truths
	•	Course rows only parsed inside valid Degree blocks
	•	Program Outcomes and trailing Certificates are fenced and isolated
	•	Spillover text (e.g., Observations, Assessment Notes) is not merged
	•	All anomalies logged separately
	•	College/Degree changes across time tracked in snapshots

⸻

🚧 Future Work
	•	Build course_index_v10.json with full College → Degree → Course chains
	•	Normalize Course Codes to detect duplicate rows (by CU / Term)
	•	Add visualization of catalog-level shifts (e.g., name changes, program churn)
	•	Possibly integrate claude_catalog_tracking_system.md if schema expansion is needed

⸻

✅ Status

V10 is locked and verified. Parsing is ready.
All helpers are versioned. Drift is logged. Output is auditable.

🔐 Trusted Input: plumber_parsed/*.txt  
🧠 Clean JSON: helpers/ + outputs/  
📘 Notes: docs/Catalog_Overview.md, helpers/catalog_schema_notes_v10.md


⸻


