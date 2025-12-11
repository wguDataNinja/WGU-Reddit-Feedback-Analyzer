WGU Reddit Analyzer – Technical Overview  
Public-Facing Architecture Guide  
Last updated: 2025-11-30

---

# Purpose

This document explains how the WGU Reddit Analyzer works at a high level.

It describes:

- how data moves through the system  
- what each stage is responsible for  
- how the project maintains clarity, traceability, and reproducible results  

It is meant for stakeholders, reviewers, and collaborators who want to understand the architecture without diving into implementation details.

---

# 1. System Summary

The WGU Reddit Analyzer processes Reddit posts about WGU courses to identify course-related pain points, group similar issues, and produce structured tables used for insights and reports.

The system has four main stages:

1. **Stage 1 – Pain Point Classification**  
   Identifies whether a post contains a fixable, course-side issue, and if so, summarizes it.

2. **Stage 2 – Course-Level Clustering**  
   Groups similar pain points within each course.

3. **Stage 3 – Global Issue Normalization**  
   Merges course-level clusters across all courses into a shared set of global issue types.

4. **Stage 4 – Report Data Layer**  
   Produces clean tables for reports, dashboards, and future web tools.

All stages read from the same frozen Stage 0 dataset to keep results stable and repeatable.

The system values:

- transparent data transformations  
- clear artifacts at every step  
- the ability to reproduce results exactly  

---

# 2. Repository Structure (High-Level)

```
src/wgu_reddit_analyzer/
    fetchers/        # Reddit ingestion (source of Stage 0 data)
    pipeline/        # Stage 0 filtering and dataset building
    benchmark/       # Stage 1 benchmarking and sampling
    stage1/          # Full-corpus Stage 1 classification
    stage2/          # Stage 2 course-level clustering
    stage3/          # Stage 3 global normalization
    report_data/     # Stage 4 merged tables for reporting
    utils/           # Logging, token counting, helpers
```

Supporting folders:

- `prompts/` – all versioned prompts  
- `artifacts/` – all generated datasets and run folders  
- `docs/` – project documentation  
- `archive_legacy/` – older experiments and unused code  

---

# 3. Stage 0 – Dataset Build (Inputs to All Stages)

Stage 0 collects Reddit posts and turns them into a clean, consistent dataset.

It:

- reads posts from WGU-related subreddits  
- removes spam, deleted content, and empty posts  
- detects valid WGU course codes  
- computes sentiment (e.g., VADER) and keeps only strongly negative posts  
- normalizes all fields (IDs, titles, text, timestamps)

Key file:

- `artifacts/stage0_filtered_posts.jsonl` – the fixed dataset used by all later stages  

This file is treated as unchanging so that results stay consistent.

---

# 4. Stage 1 – Pain Point Classification

## Goal
Decide whether each post contains a **fixable course-side pain point** and, if so, generate:

- a short root-cause summary  
- a concise snippet anchored in the post  

Stage 1 has two modes:

1. **Benchmark Mode (DEV/TEST)**  
   Tests different prompts and models, compares accuracy, and measures cost.

2. **Full-Corpus Mode**  
   Runs the selected model/prompt on the full Stage 0 dataset.

### 4.1 Benchmark Mode

Stage 1 benchmarking focuses on:

- precision, recall, F1  
- cost per post  
- latency  
- behavior on noisy writing  
- schema stability  
- prompt and model comparison  

This work lives in `src/wgu_reddit_analyzer/benchmark/`.

### 4.2 Full-Corpus Mode

Once a model/prompt combination is chosen, Stage 1 is run across all Stage 0 posts.

Each output row includes:

- whether the post contains a pain point  
- a root-cause summary  
- a snippet  
- flags for parser or model errors  
- basic metadata such as model name and run ID

Important:

- Stage 2 **does not** filter using confidence scores.  
- Stage 2 simply keeps rows where:
  - `pred_contains_painpoint == "y"`  
  - no parse/schema/LLM error occurred  

Key reshaped output:

- `artifacts/stage2/painpoints_llm_friendly.csv`

---

# 5. Stage 2 – Course-Level Clustering

## Goal
Turn individual pain points into course-level themes that instructors or curriculum teams can act on.

Inputs:

- Stage 1 pain-point rows  
- course metadata  
- an LLM clustering prompt for each course  

Process:

1. Load all pain points.  
2. Add course titles and college information.  
3. Group posts by `course_code`.  
4. For each course, send its pain points to an LLM to create meaningful clusters.  
5. Validate each cluster file with strict schema rules.  
6. Store prompts, inputs, and outputs to guarantee consistency.

Typical cluster fields:

- `cluster_id` (e.g., `C214_1`)  
- a short `issue_summary`  
- number of posts  
- the list of member `post_id` values  

Stage 2 allows posts to appear in more than one cluster for the same course.

Key outputs:

- `artifacts/stage3/preprocessed/<run_id>/clusters_llm.csv`  
- per-course cluster JSON files  
- a Stage 2 manifest describing the run  

---

# 6. Stage 3 – Global Issue Normalization

## Goal
Merge course-level clusters into a shared set of **global issue types** so that problems can be compared across courses and colleges.

Inputs:

- `clusters_llm.csv` from Stage 2  
- all cluster JSON files  
- Stage 2 run metadata  

Process:

1. Load all course-level cluster summaries.  
2. Use an LLM to group similar clusters together across courses.  
3. Assign each cluster a `global_cluster_id` and `normalized_issue_label`.  
4. Map these normalized labels back to the post level.

Key outputs:

- `cluster_global_index.csv` – maps cluster → global issue  
- `post_global_index.csv` – maps post → cluster → global issue  
- `global_clusters.json` – list of global issues with labels, descriptions, and membership

Examples of normalized issue labels:

- `assessment_material_misalignment`  
- `unclear_or_ambiguous_instructions`  
- `evaluator_inconsistency_or_poor_feedback`  

These labels allow stakeholders to track problems that appear across multiple courses.

---

# 7. Stage 4 – Report Data Layer

## Goal
Produce a clean set of merged tables that pull together everything from the earlier stages.

These files are used for:

- course-level PDF reports  
- cross-course comparisons  
- future web dashboards  

Implementation:

- `src/wgu_reddit_analyzer/report_data/build_analytics.py`  
- outputs stored under `artifacts/report_data/`

Inputs:

- Stage 0 posts  
- Stage 2 pain-point CSV  
- Stage 3 cluster + global files  
- course metadata  

Main outputs:

1. **post_master.csv**  
   - one row per post  
   - includes pain-point flags, summaries, snippets, cluster IDs, global labels, course metadata  

2. **course_summary.csv**  
   - one row per course  
   - includes negative post counts, pain-point counts, top issues, course title, college  

3. **course_cluster_detail.jsonl**  
   - one record per cluster per course  
   - includes cluster summaries, normalized labels, post counts, and examples  

4. **global_issues.csv**  
   - one row per global issue type  
   - includes labels, descriptions, and counts  

5. **issue_course_matrix.csv**  
   - one row per (issue, course) pair  
   - includes number of posts and clusters contributing to that issue in that course  

These tables are the working dataset for all human-facing outputs.

---

# 8. Model Registry and LLM Client

The system uses a shared LLM client and model registry.

This layer handles:

- choosing the right model provider  
- setting up retry and timeout rules  
- logging input/output token usage  
- tracking per-call cost and latency  
- offering a consistent interface across stages  

This keeps behavior consistent whether you're benchmarking, clustering, or normalizing.

---

# 9. Prompts and Versioning

All prompt templates live under `prompts/`.

During any run (Stage 1, 2, or 3):

- the exact prompt is copied into the run folder  
- a manifest.json records the model, settings, and important paths  
- raw LLM responses are saved where relevant  

This ensures that a run’s results can be recreated later.

---

# 10. Reproducibility

The pipeline maintains repeatable results through:

- a frozen Stage 0 dataset  
- fixed DEV/TEST samples and gold labels for Stage 1 benchmarking  
- versioned prompts copied into run directories  
- run manifests describing configuration  
- raw LLM logs for stages that involve model calls  
- strict validation of IDs and schema in Stages 2 and 3  
- deterministic logic in Stage 4 (no randomness, no LLMs)

Because each run stores its own inputs and metadata, any full-corpus result or report can be recreated—down to the exact posts, clusters, and issue labels involved.