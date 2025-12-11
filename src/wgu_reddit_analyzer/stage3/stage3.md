
Updated Stage 3 Developer Guide

1. Inputs and preprocessing

Inputs required for a Stage 3 run
	•	Stage 2 run directory:
	•	artifacts/stage2/runs/<stage2_run_slug>/clusters/*.json
	•	artifacts/stage2/runs/<stage2_run_slug>/manifest.json
	•	Optional:
	•	data/course_list_with_college.csv for metadata

Preprocessing script

Location:
src/wgu_reddit_analyzer/stage3/preprocess_clusters.py

Responsibilities

1. Load Stage 2 clusters
From each clusters/<course_code>.json file:
	•	courses (list)
	•	course_code
	•	course_title
	•	clusters:
	•	cluster_id
	•	issue_summary
	•	num_posts
	•	post_ids

2. Flatten
One row per Stage 2 cluster.

3. Optional metadata join
Join on course_code to add:
	•	college_name
	•	program_name

4. Outputs
Written under:
artifacts/stage3/preprocessed/<stage2_run_slug>/

a) LLM-friendly cluster table – JSONL
clusters_llm_friendly.jsonl

Each row contains:

{
  "cluster_id": "C200_3",
  "course_code": "C200",
  "course_title": "...",
  "issue_summary": "...",
  "num_posts": 1,
  "college_name": "College of Business",
  "program_name": "MBA",
  "cluster_size_bucket": "1-3"
}

b) Cluster→post map (never sent to LLM)
cluster_post_ids.jsonl

{ "cluster_id": "C200_3", "post_id": "1k73poq" }

c) Flat CSV for analytics
clusters_flat.csv
Columns:
	•	cluster_id
	•	course_code
	•	course_title
	•	issue_summary
	•	num_posts
	•	college_name
	•	program_name
	•	cluster_size_bucket

⸻

2. LLM interaction and Stage 3 schema

Prompt file

Location:
prompts/s3_global_clusters.txt
Copied into run dir as stage3_prompt.txt.

Input JSON passed to LLM

{
  "clusters": [
    {
      "cluster_id": "C200_2",
      "course_code": "C200",
      "course_title": "Managing Organizations and Leading People",
      "issue_summary": "AI-detection tool false positives ...",
      "num_posts": 3,
      "college_name": "...",
      "program_name": "...",
      "cluster_size_bucket": "1-3"
    }
  ]
}

LLM responsibilities (short version)
	•	Merge course-level clusters into global issues by root cause.
	•	Use seeded labels when a meaning matches.
	•	Each input cluster_id must appear once:
	•	In exactly one global issue’s member_cluster_ids, or
	•	In unassigned_clusters.
	•	Do NOT output course_code or course_title.
	•	Output valid JSON only.
	•	Sort global issues by total num_posts descending.

Global cluster naming fields

Each global issue must include:

provisional_label          # machine-friendly, underscores, stable
normalized_issue_label     # human-readable concise label
short_description          # one-sentence root-cause statement
member_cluster_ids         # list of cluster_id strings

Output schema (strict)

{
  "global_clusters": [
    {
      "provisional_label": "ai_detection_confusion_and_false_flags",
      "normalized_issue_label": "AI-detection confusion and false flags",
      "short_description": "AI tools generate unclear or incorrect similarity flags without guidance.",
      "member_cluster_ids": ["C200_2", "D300_1"]
    }
  ],
  "unassigned_clusters": ["C300_5"]
}

This replaces the older Stage 3 schema using member_clusters objects.
Stage 3 now outputs only cluster_ids (not metadata).

⸻

3. Batching strategy

Cluster universe

Source: clusters_llm_friendly.jsonl

Sorted by:
	1.	num_posts (desc)
	2.	course_code
	3.	cluster_id

Batch configuration
	•	--max-clusters-per-batch (default 60)
	•	Optional truncation: --max-issue-summary-chars (default 300)

Creating batches
	•	Slice sorted clusters into batches of max size.
	•	Render the JSON input for each batch.
	•	Send to LLM.

Cross-batch merging

After all batches complete:
	1.	Group results by provisional_label (lowercase, trimmed).
	2.	Merge all member_cluster_ids from batches.
	3.	Keep normalized_issue_label and short_description from the group with highest total posts.
	4.	Sort global clusters by total_num_posts descending.
	5.	Assign deterministic IDs:
	•	G001, G002, …

(No change needed for cross-batch merge logic.)

⸻

4. Stage 3 run driver

Location:
src/wgu_reddit_analyzer/stage3/run_stage3_global_clusters.py

CLI args:
	•	--stage2-run-dir
	•	--model
	•	--prompt-path
	•	Optional:
	•	--out-root
	•	--max-clusters-per-batch
	•	--max-issue-summary-chars
	•	--dry-run
	•	--reuse-preprocessed

Run slug

<model>_s3_global_<YYYYMMDD>_<HHMMSS>

Run directory contents
	•	global_clusters.json (canonical Stage 3 output)
	•	cluster_global_index.csv
	•	global_clusters_summary.csv
	•	post_global_index.csv
	•	batch request/response files
	•	prompt snapshot
	•	manifest with metrics

Final canonical file structure example

{
  "global_clusters": [
    {
      "global_cluster_id": "G001",
      "provisional_label": "ai_detection_confusion_and_false_flags",
      "normalized_issue_label": "AI-detection confusion and false flags",
      "short_description": "...",
      "source_clusters": [...],
      "total_num_posts": 8,
      "num_courses": 2
    }
  ],
  "unassigned_clusters": ["C300_5"]
}


⸻

5. Metrics and analytics

In manifest or summary files:
	•	num_input_clusters
	•	num_global_clusters
	•	num_unassigned_clusters
	•	total_input_posts
	•	total_assigned_posts
	•	cluster_coverage_fraction
	•	post_coverage_fraction

Major CSV tables:
	•	cluster_global_index.csv
	•	global_clusters_summary.csv
	•	post_global_index.csv

⸻

6. Validation and failure modes

Validator

Location:
src/wgu_reddit_analyzer/stage3/validate_global_clusters.py

Checks:
	•	JSON structure
	•	All cluster_id reference valid Stage 2 clusters
	•	Exclusive assignment (each cluster_id appears once)
	•	Total_num_posts matches sum of source clusters
	•	global_cluster_id uniqueness

Batch failure handling:
	•	Write failure to batch_XXX_error.txt
	•	Optionally retry once
	•	If still failing: mark all clusters in that batch unassigned

⸻

7. Repository integration & documentation

Key modules under:
src/wgu_reddit_analyzer/stage3/

Documentation:
docs/STAGE3_SPEC.md

Should contain:
	•	Overview of Stage 3
	•	Input/output schemas
	•	Prompt contract
	•	Runner usage
	•	Validation rules

⸻

8. Roadmap alignment
	•	Stage 1 v2 (painpoint_ids)
	•	Stage 2.5 (course insights synthesis)
	•	Optional embedding-assisted Stage 3 refinement

⸻

