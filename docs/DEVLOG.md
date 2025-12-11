# DEVLOG.md

# 2025-10-12 — Stage 0 Dataset Build (Foundational Ingestion)
Implemented full ingestion pipeline for raw Reddit dumps and API pulls.  
Added cleaning rules:
- drop deleted/removed bodies  
- drop empty or non-English posts  
- collapse spam detected by simple heuristics + regex patterns  
- normalize whitespace, escape sequences, and legacy Markdown noise  

Field normalization:
- `post_id`, `subreddit`, `title`, `selftext`, `created_utc`  
- ensured `created_utc` is always UNIX seconds (int)  
- added `course_candidates` placeholder field (not used downstream yet)

Wrote final immutable artifact:
`artifacts/stage0/stage0_filtered_posts.jsonl`  
Included `manifest.json` (source hash, row count, filter counts, timestamp).  
This dataset is frozen permanently for reproducibility.

---

# 2025-10-14 — Stage 1 Benchmark Prep: Length Profiling
Parsed Stage 0 corpus and generated token counts using shared tokenization utilities.  
Computed:
- token histogram  
- deciles / quartiles  
- long-tail analysis  
Identified optimal stratification boundaries for sampling.

Logged plots + summaries into `artifacts/benchmark/length_profile/`.

---

# 2025-10-15 — Stage 1 Benchmark Prep: Deterministic Sampling
Created stratified DEV and TEST subsets.  
Sampling logic:
1. split by length bucket  
2. random sample within each using frozen seed  
3. enforce subreddit diversity quota  
4. write stable row order  

Artifacts:
- `dev_sample.jsonl`  
- `test_sample.jsonl`  
Each with its own manifest (buckets, counts, RNG state).

---

# 2025-10-17 — Stage 1 Manual Labeling: Gold Dataset Creation
Human-labeled final benchmark set.  
Label schema v1:
- `contains_painpoint` (y/n)  
- `painpoint_type` (enumerated)  
- optional short `root_cause_summary` (free text)  

Performed reconciliation on disagreements, removed ambiguous items.  
Gold dataset stored under `artifacts/benchmark/gold/`.

---

# 2025-10-19 — Stage 1 Zero-Shot Smoke Tests
Evaluated several models using a minimal instruction-only prompt.  
Captured:
- failure rate (malformed JSON, hallucinated fields)  
- FP/TP/FN counts  
- cost per 100 posts  
- latency averages  

Observed systematic false positives in general-purpose models lacking domain examples.  
JSON parsing failures prompted creation of stricter schema templates.

---

# 2025-10-21 — Stage 1 Few-Shot Prompt Engineering
Developed a structured few-shot prompt with domain-specific examples.  
Prompt improvements:
- explicit painpoint definition  
- one positive example, one negative example  
- schema-first design  
- explicit failure-handling instructions  
- strong guidance to avoid hallucinating course codes or dates  

Stored all versions in `prompts/stage1/`, each with semantic version tags.

---

# 2025-10-23 — Stage 1 Benchmarking Suite Execution
Ran full F1-driven benchmark across models + prompt variants.  

For each run:
- used unified model client (routing, retries, timeout handling)  
- logged raw request/response JSON  
- tracked token usage, cost, and latency per call  
- applied strict schema validator (`schema_v2.json`)  
- recorded failure categories: syntax error, field missing, partial JSON, non-actionable response  

Generated evaluation report:
- precision/recall/F1 for painpoint detection  
- confusion matrix  
- schema-adherence rate  
- response length distribution  
- cost per thousand posts  

Selected final configuration based on best F1 with lowest failure rate.

---

# 2025-10-27 — Stage 1 Full-Corpus Mode (Production Run)
Executed chosen model + prompt on entire Stage-0 dataset (~all posts).  
Pipeline steps:
1. chunk posts into batches  
2. call model with streaming disabled (more stable JSON)  
3. validate response schema  
4. retry if recoverable failure  
5. write raw IO (one line per LLM call)  

Artifacts:
- `predictions_FULL.csv`  
- `raw_io_FULL.jsonl`  
- `manifest.json` (model, prompt, sampling disabled, cost, total time)

Added a `llm_failure` flag per row for downstream filtering.  
Confidence values retained but ignored for filtering in later stages.

---

# 2025-10-29 — Stage 1 → Stage 2 Interface Finalization
Produced `painpoints_llm_friendly.csv`.

Filters:
- `pred_contains_painpoint == "y"`  
- `llm_failure == false`  
- no confidence thresholding applied  

Preprocessing:
- trimmed root-cause text  
- normalized course mentions  
- merged course metadata (via lookup tables)  

This file became the canonical Stage 2 input.

---

# 2025-11-01 — Stage 2 Clustering: Architecture & Validator Setup
Defined clustering workflow:
1. group painpoints by course  
2. pass descriptions to single LLM call per course  
3. enforce stable cluster ID format (`C001`, `C002`, ...)  
4. apply deterministic validator rules  

Validator rules include:
- unique cluster IDs  
- all painpoints mapped at least once  
- sorted cluster order (largest→smallest)  
- cross-check post IDs against Stage 1 source  
- forbid empty clusters  
- enforce structure: title, description, membership list  

Prepared `stage2_prompt_v1.txt`.

---

# 2025-11-03 — Stage 2 Clustering Runs (Production)
Ran clustering against all courses with sufficient painpoints.  
Captured:
- raw LLM input (one file per course)  
- raw LLM output (JSON)  
- validated final cluster sets  
- painpoints actually used for each course  

Artifacts stored in:
`artifacts/stage2/runs/<run_slug>/`  
Contents per course:
- `<course>.json` (clusters)  
- `painpoints_used_<course>.jsonl`  
- input prompt snapshot  
- run manifest with timing + cost  

---

# 2025-11-05 — Stage 2 Finalization & Stabilization
Integrated schema v2.1 with stricter cluster validation.  
Ensured multi-cluster membership allowed but verified against duplicates.  
Added deterministic ordering of cluster fields to reduce diff noise.  
Declared Stage 2 production-ready.

---

# 2025-11-07 — Repository Namespace Standardization
Refactored entire codebase into unified namespace:
`wgu_reddit_analyzer`

Changes:
- converted all relative imports to absolute  
- adjusted execution pattern: `python -m wgu_reddit_analyzer.<module>`  
- ensured package compatibility with `pip install -e .`  
- reorganized `src/` structure matching the multi-stage pipeline  

Improved maintainability and containerization.

---

# 2025-11-10 — Stage 3 Preliminary Architecture
Outlined future course insight document generator.  
Proposed components:
- course-level overview generation  
- narrative synthesis over clusters  
- representative example extraction  
- metadata propagation (source traceability)  
Pending implementation until Stage 2 schemas are fully stable.

---

# 2025-11-26 — Technical Overview Rewrite (Public-Facing)
Produced clean, external-facing architecture guide.  
Clarified:
- Stage 1 as the only empirically benchmarked stage  
- Stage 2 consumes all painpoints (`y`, no LLM failure) without confidence filtering  
- reproducibility guarantees across all stages  

Updated repo structure summary.  
Retired inconsistent legacy documentation.

---
# 2025-11-27 — Stage 4 Report Data Layer

Implemented the full Stage 4 report data layer.  
This stage merges all upstream artifacts (Stage 0, Stage 1, Stage 2, Stage 3, and course metadata) into a single, stable data mart for reports and downstream interfaces.

Key results:
- Added `report_data/` as the final structured output layer.
- Implemented `build_analytics.py` (core merge) and `build_reports.py` (overview sorting).
- Outputs now include:
  - `post_master.csv` — unified post-level table
  - `course_summary.csv` — per-course totals and top issue labels
  - `course_cluster_detail.jsonl` — detailed cluster info per course
  - `global_issues.csv` — normalized issue taxonomy
  - `issue_course_matrix.csv` — cross-course issue map

All outputs are full-fidelity: no filtering, no thresholds, no cutoffs.  
This layer is now the single source of truth for PDF reports and future GUI work.

---

# Current Status (2025-11-27)

- Stage 0 frozen.  
- Stage 1 complete (benchmarking + full-corpus predictions).  
- Stage 2 complete (course clustering).  
- Stage 3 complete (global normalization).  
- Stage 4 complete (report data layer operational).