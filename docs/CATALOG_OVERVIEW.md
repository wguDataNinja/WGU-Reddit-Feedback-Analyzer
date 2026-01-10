# WGU Reddit Analyzer – Catalog Overview

_Last updated: 2025-11-08_

---

## 1. Purpose
Provides background on how course and college data were extracted from Western Governors University’s public academic catalogs (2017–2025).  
These structured datasets enable accurate course-level filtering and aggregation in the Reddit pain-point analysis pipeline.

---

## 2. Catalog Data Source
The catalog pipeline ingested WGU’s publicly available institutional catalogs.  
From these PDFs, course codes, titles, and college affiliations were parsed and normalized into a canonical format.

**Outputs used by the Reddit Analyzer:**
- `data/course_list_with_college.csv` — current mapping of course codes to colleges  
- `data/college_snapshots.json` — record of historical college naming changes  

All data originated from verified, public WGU catalog files.

---

## 3. Processing Overview
1. **Collection** – Catalog PDFs downloaded from WGU’s public catalog index.  
2. **Parsing** – Text extracted using consistent PDF-to-text conversion.  
3. **Normalization** – Course and college information standardized under a unified schema.  
4. **Export** – Clean CSV and JSON files written to the `data/` directory for use in downstream NLP and classification tasks.  

Each phase is versioned and reproducible. Intermediate data are retained for validation but not publicly distributed.

---

## 4. Integration with Reddit Pipeline
Catalog outputs link Reddit posts to official academic units:

- Posts must reference a valid course code.  
- Each post inherits its college label from the catalog mapping.  
- Enables aggregation by course or college and consistent benchmarking over time.  

This linkage ensures model outputs align with WGU’s institutional structure at the time of analysis.

---

## 5. Sample Data Preview

**course_list_with_college.csv**

| CourseCode | Title | Colleges |
|-------------|--------|-----------|
| C715 | Organizational Behavior | Leavitt School of Health; School of Business; School of Technology |
| D072 | Fundamentals for Success in Business | School of Business |

**college_snapshots.json**

```json
{
  "2024-04": [
    "School of Business",
    "Leavitt School of Health",
    "School of Technology",
    "School of Education"
  ]
}
```

*(Full files available under `/data/` in the repository.)*

---

## 6. Limitations & Maintenance
Catalog data represent a fixed institutional snapshot (2017–2025).  
As WGU updates courses and programs, mappings may drift.  
To maintain accuracy, catalog parsing should be rerun periodically with new public catalogs.

---

## 7. Deliverables
- `course_list_with_college.csv` — canonical course–college mapping  
- `college_snapshots.json` — reference for historical naming  

---

## 8. Attribution
**Source data:** publicly available WGU academic catalogs (2017–2025).  
No proprietary or student data were used.  

---

