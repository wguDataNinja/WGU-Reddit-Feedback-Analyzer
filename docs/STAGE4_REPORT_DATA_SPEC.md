Stage 4 — Report Data Layer Specification  
Last updated: 2025-11-30

---

# Purpose

Stage 4 builds the **report data layer**, a clean, merged set of tables used for dashboards, PDFs, future web interfaces, and institutional analysis.

Stage 4:

- performs **no LLM calls**
- makes **no analytical decisions**
- applies **no thresholds or filters**
- simply **joins, reshapes, and standardizes** outputs from Stages 0–3

Outputs reflect the final, authoritative global issue assignments from Stage 3.

Stage 4 is fully deterministic.

---

# Inputs

Stage 4 consumes only these artifacts:

| Stage   | Input File                                                                                     | Purpose |
|---------|------------------------------------------------------------------------------------------------|---------|
| Stage 0 | `artifacts/stage0_filtered_posts.jsonl`                                                       | Locked Reddit corpus (negative WGU-course posts) |
| Stage 1 | `artifacts/stage1/full_corpus/<run_slug>/predictions_FULL.csv`                                | Full-corpus painpoint predictions + metadata |
| Stage 2 | `artifacts/stage2/painpoints_llm_friendly.csv`                                                | Per-post LLM-extracted painpoints |
| Stage 3A| `artifacts/stage3/preprocessed/<stage2_run_slug>/clusters_llm.csv`                            | Flattened cluster summaries |
| Stage 3B| `artifacts/stage3/runs/<stage3_run_id>/cluster_global_index.csv`                              | cluster_id → global_cluster_id mapping |
| Stage 3B| `artifacts/stage3/runs/<stage3_run_id>/post_global_index.csv`                                 | post_id → cluster_id → global_cluster_id |
| Stage 3B| `artifacts/stage3/runs/<stage3_run_id>/global_clusters.json`                                  | canonical global-cluster definitions |
| Stage 3B| `artifacts/stage3/runs/<stage3_run_id>/manifest.json`                                         | provenance (includes `source_stage2_run`) |
| Metadata| `data/course_list_with_college.csv`                                                           | course titles + college info |

Important notes:

- `global_clusters.json` is the **authoritative** Stage-3 output.  
- `global_clusters_summary.csv` exists but **Stage 4 never consumes it**.  
- Stage 4 **prefers** Stage-2 provenance from the Stage-3 manifest’s block:

```json
"source_stage2_run": {
  "run_id": "<stage2_run_id>",
  "stage2_run_dir": "artifacts/stage2/runs/<stage2_run_slug>",
  "stage2_run_slug": "<stage2_run_slug>",
  "manifest_path": "artifacts/stage2/runs/<stage2_run_slug>/manifest.json"
}
```

This ensures correct, reproducible lineage.

---

# Outputs (under `artifacts/report_data/`)

## 1. post_master.csv

One row **per Stage-0 post** (all 1103).

Contains:

- Stage-0 metadata (title, selftext fields, course_code)  
- Stage-1 predictions (`pred_contains_painpoint`, `is_pain_point`, flags)  
- Stage-2 summaries/snippets for painpoints  
- Multi-membership collapsed as semicolon-joined fields:

  - `cluster_id`  
  - `global_cluster_id`  
  - `normalized_issue_label`  
  - `provisional_label`

- Course metadata (title, colleges)  
- Permalinks, timestamps

**Multi-membership behavior (must be explicit):**

Stage 4 builds a post×cluster intermediate from `post_global_index.csv`.  
If a post belongs to **multiple Stage-2 clusters**, all cluster-level and global-level fields are joined via semicolons.

**Missing labels are expected for non-painpoint posts** (e.g., 713/1103).  
These are not errors—they are normal non-painpoint posts.

Grain:  
**1 row per `post_id`**.

---

## 2. course_summary.csv

Per-course rollup.

Fields:

- total negative posts  
- total painpoint posts  
- number of distinct clusters  
- top normalized issue labels (e.g., top 3)  
- course title + colleges

Grain:  
**1 row per course_code**.

---

## 3. course_cluster_detail.jsonl

Cluster-level detail for each course.

Fields:

- course_code, course_title  
- cluster_id  
- cluster `issue_summary`  
- normalized_issue_label  
- number of posts in cluster  
- percent of the course’s painpoints  
- 1–3 sample post_ids + snippets

Grain:  
**1 row per (course_code, cluster_id)**.

---

## 4. global_issues.csv

Flattened global issue dictionary built from Stage-3 artifacts.

Fields:

- `global_cluster_id`  
- `normalized_issue_label`  
- `provisional_label`  
- `short_description`  
- `total_num_posts`  
- `num_courses`  
- `num_clusters`

Grain:  
**1 row per global_cluster_id**.

Clarification:

- `global_clusters.json` = canonical definition  
- `global_issues.csv` = analytic summary  
They are **complementary**, not redundant.

---

## 5. issue_course_matrix.csv

Cross-course distribution of issues.

Fields:

- `normalized_issue_label`  
- `course_code`  
- `num_posts` (distinct posts for that issue × course)  
- `num_clusters` (# Stage-2 clusters contributing to that pair)

Grain:  
**1 row per (normalized_issue_label, course_code)**.

Definitions:

- `num_posts`: count of distinct post_ids in clusters that map to the given normalized_issue_label  
- `num_clusters`: count of distinct Stage-2 clusters that roll into that (issue, course)

---

# Processing Logic

Script:  
`wgu_reddit_analyzer.report_data.build_analytics`

Steps:

1. Load Stage 0 posts  
2. Join Stage-1 predictions  
3. Join Stage-2 painpoints  
4. Join Stage-3 post and cluster indices  
5. Join metadata  
6. Build post×cluster intermediate  
7. Collapse to true post-level `post_master.csv` (semicolon joins for multi-membership)  
8. Build:

   - `course_summary.csv`  
   - `course_cluster_detail.jsonl`  
   - `global_issues.csv`  
   - `issue_course_matrix.csv`

No LLMs, no filtering, no thresholds.

---

# Stage 4B (optional overviews)

Script:  
`wgu_reddit_analyzer.report_data.build_reports`

Outputs:

- `courses_overview.csv`  
- `issues_overview.csv`

These are informational and not part of the canonical dataset.

---

# Downstream Consumers

- Per-course PDFs → use `post_master.csv`, `course_summary.csv`, `course_cluster_detail.jsonl`  
- Global maps → use `global_issues.csv`, `issue_course_matrix.csv`  
- Future web explorer → JSON exports from all stage-4 tables

---

# Example Terminal Commands

To build Stage 4 for your latest run:

```bash
python -m wgu_reddit_analyzer.report_data.build_analytics \
  --stage3-preprocessed-dir artifacts/stage3/preprocessed/gpt-5-mini_s2_cluster_full_20251126_080011 \
  --stage3-run-dir artifacts/stage3/runs/gpt-5-mini_s3_global_gpt-5-mini_s2_cluster_full_20251130_084422
```

To build the optional overview tables:

```bash
python -m wgu_reddit_analyzer.report_data.build_reports --artifacts-dir artifacts
```

---

# Reliability

Deterministic if:

- Stage-0 corpus unchanged  
- Stage-1 predictions unchanged  
- Stage-2 painpoints unchanged  
- Stage-3 run directory fixed  
- course metadata fixed

Provenance:

- Stage-4 records which Stage-3 run it used (`run_id`)  
- Stage-3 manifest records which Stage-2 run it came from (`source_stage2_run`)  
- This chain is the authoritative lineage for all reports

___


update with this section:

## Pipeline Data Volumes

Stage 4 also produces a small set of pipeline volume summaries that describe how many posts, pain points, clusters, and global issues exist per course and per college.

Key artifacts (all under `artifacts/report_data/`):

- `pipeline_counts_by_course.csv`
- `pipeline_counts_by_college.csv`
- `pipeline_counts_overview.md`

These are built by `wgu_reddit_analyzer.report_data.build_pipeline_counts` and rely only on existing Stage 4 tables (no additional model calls). See `docs/PIPELINE_COUNTS_OVERVIEW.md` for details and interpretation guidelines.

## Pipeline Data Volumes

Stage 4 also produces a small set of **pipeline-volume summaries** that show how many posts, pain points, clusters, and global issues each course and college contributes to the dataset. These outputs provide transparent counts of how the Reddit corpus flows through Stages 0–3.

These summaries do **not** introduce new LLM calls.  
They are built entirely from existing Stage-4 artifacts.

Artifacts (all under `artifacts/report_data/`):

- `pipeline_counts_by_course.csv`  
- `pipeline_counts_by_college.csv`  
- `pipeline_counts_overview.md`

These files are generated by:

```bash
python -m wgu_reddit_analyzer.report_data.build_pipeline_counts
```

and rely only on:

- `post_master.csv`  
- `course_cluster_detail.jsonl`  
- `issue_course_matrix.csv`  
- `global_issues.csv`  
- `course_summary.csv`

For interpretation guidelines—including how to read stage-by-stage attrition, how to understand multi-college courses, and why Stage-1 parse-error rows appear as zero-painpoint posts—see:

```
docs/PIPELINE_COUNTS_OVERVIEW.md
```