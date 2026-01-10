Stage 4 — Report Data Layer Specification
Last updated: 2025-12-11

Purpose

Stage 4 builds the report data layer, a clean, merged set of tables used for dashboards, PDFs, future web interfaces, and institutional analysis.

Stage 4:
	•	performs no LLM calls
	•	makes no analytical decisions
	•	applies no thresholds or filters
	•	only joins, reshapes, and standardizes outputs from Stages 0–3

Outputs reflect the final, authoritative global issue assignments from Stage 3 and are fully deterministic.

All canonical Stage 4 tables include a schema_version column (currently 1.0.0).

Inputs

Stage 4 consumes only these artifacts:

Stage	Input File	Purpose
Stage 0	artifacts/stage0_filtered_posts.jsonl	Locked Reddit corpus (negative WGU-course posts)
Stage 1	artifacts/stage1/full_corpus/<run_slug>/predictions_FULL.csv	Full-corpus painpoint predictions + metadata
Stage 2	artifacts/stage2/painpoints_llm_friendly.csv	Per-post LLM-extracted painpoints
Stage 3A	artifacts/stage3/preprocessed/<stage2_run_slug>/clusters_llm.csv	Flattened cluster summaries
Stage 3B	artifacts/stage3/runs/<stage3_run_slug>/cluster_global_index.csv	cluster_id → global_cluster_id mapping
Stage 3B	artifacts/stage3/runs/<stage3_run_slug>/post_global_index.csv	post_id → cluster_id → global_cluster_id
Stage 3B	artifacts/stage3/runs/<stage3_run_slug>/global_clusters.json	canonical global-cluster definitions
Stage 3B	artifacts/stage3/runs/<stage3_run_slug>/manifest.json	provenance (includes source_stage2_run)
Metadata	data/course_list_with_college.csv	course titles + college info

Notes
	•	global_clusters.json is the authoritative Stage 3 semantic definition.
	•	global_clusters_summary.csv may exist but Stage 4 does not consume it.
	•	Stage 4 prefers Stage 2 provenance taken from Stage 3 manifest:
“source_stage2_run”: {
“run_id”: “<stage2_run_id>”,
“stage2_run_dir”: “artifacts/stage2/runs/<stage2_run_slug>”,
“stage2_run_slug”: “<stage2_run_slug>”,
“manifest_path”: “artifacts/stage2/runs/<stage2_run_slug>/manifest.json”
}

Outputs (under artifacts/report_data/)
	1.	post_master.csv

One row per Stage 0 post (full corpus).

Contains:
	•	Stage 0 metadata (title, body/selftext, course_code, timestamps, permalinks)
	•	Stage 1 predictions (pred_contains_painpoint / is_pain_point, error flags)
	•	Stage 2 painpoint summaries/snippets for posts with pain points
	•	Multi-membership collapsed as semicolon-joined fields:
	•	cluster_id
	•	global_cluster_id
	•	normalized_issue_label
	•	provisional_label
	•	Course metadata (course_title, college info)
	•	schema_version

Multi-membership behavior

Stage 4 builds a post×cluster intermediate from post_global_index.csv.
If a post belongs to multiple Stage 2 clusters, all cluster-level and global-level fields are joined via semicolons.

Posts with no pain points (pred_contains_painpoint != “y”) will have empty cluster/global fields. This is expected and not an error.

Grain: 1 row per post_id.
	2.	course_summary.csv

Per-course rollup.

Fields (non-exhaustive):
	•	course_code
	•	course_title
	•	college_name (or equivalent)
	•	total_negative_posts (from Stage 0)
	•	total_painpoint_posts (Stage 1 y)
	•	num_clusters (distinct Stage 2 clusters for that course)
	•	top normalized_issue_labels (e.g., top 3, semicolon-joined)
	•	schema_version

Grain: 1 row per course_code.
	3.	course_cluster_detail.jsonl

Cluster-level detail per course.

Fields:
	•	course_code, course_title
	•	cluster_id
	•	cluster issue_summary (from Stage 2)
	•	normalized_issue_label (from Stage 3)
	•	num_posts_in_cluster
	•	percent_of_course_painpoints
	•	1–3 sample post_ids and snippets
	•	schema_version (per record)

Grain: 1 row per (course_code, cluster_id).
	4.	global_issues.csv

Flattened global issue dictionary built from Stage 3 artifacts.

Fields:
	•	global_cluster_id
	•	normalized_issue_label
	•	provisional_label
	•	short_description
	•	total_num_posts
	•	num_courses
	•	num_clusters
	•	schema_version

Grain: 1 row per global_cluster_id.

Clarification:
	•	global_clusters.json is the canonical semantic definition.
	•	global_issues.csv is a normalized analytic summary.

	5.	issue_course_matrix.csv

Cross-course distribution of issues.

Fields:
	•	normalized_issue_label
	•	course_code
	•	num_posts (distinct posts for that issue × course)
	•	num_clusters (distinct Stage 2 clusters that roll into that pair)
	•	schema_version

Definitions:
	•	num_posts: count of distinct post_ids in clusters mapping to that normalized_issue_label and course_code.
	•	num_clusters: count of distinct Stage 2 clusters contributing to that (normalized_issue_label, course_code).

Grain: 1 row per (normalized_issue_label, course_code).

Processing logic

Script:
wgu_reddit_analyzer.report_data.build_analytics

Steps:
	1.	Load Stage 0 posts.
	2.	Join Stage 1 predictions onto posts.
	3.	Join Stage 2 painpoints.
	4.	Join Stage 3 post and cluster indices.
	5.	Join course metadata.
	6.	Build post×cluster intermediate from post_global_index.csv.
	7.	Collapse to post_master.csv with semicolon joins for multi-membership fields.
	8.	From post_master + intermediate tables, build:
	•	course_summary.csv
	•	course_cluster_detail.jsonl
	•	global_issues.csv
	•	issue_course_matrix.csv
	9.	Add schema_version column to each CSV output.

No LLMs, no filtering, no thresholds. All transformations are deterministic joins, reshapes, and aggregations.

Stage 4B (optional overviews)

Script:
wgu_reddit_analyzer.report_data.build_reports

Outputs:
	•	courses_overview.csv
	•	issues_overview.csv

Both include schema_version and are informational only; they are not part of the core analytic dataset.

Pipeline Data Volumes

Stage 4 also produces a small set of pipeline-volume summaries that show how many posts, pain points, clusters, and global issues each course and college contributes to the dataset. These outputs provide a transparent view of how the Reddit corpus flows through Stages 0–3.

These summaries do not introduce new LLM calls.
They are built entirely from existing Stage 4 artifacts.

Artifacts (under artifacts/report_data/):
	•	pipeline_counts_by_course.csv
	•	pipeline_counts_by_college.csv
	•	pipeline_counts_overview.md

They are generated by:

python -m wgu_reddit_analyzer.report_data.build_pipeline_counts

and rely only on:
	•	post_master.csv
	•	course_cluster_detail.jsonl
	•	issue_course_matrix.csv
	•	global_issues.csv
	•	course_summary.csv

For interpretation guidelines—including:
	•	how to read stage-by-stage attrition
	•	how to understand multi-college courses
	•	why Stage 1 parse-error rows appear as zero-painpoint posts

see:

docs/PIPELINE_COUNTS_OVERVIEW.md

Downstream consumers
	•	Per-course PDFs and course dashboards:
	•	post_master.csv
	•	course_summary.csv
	•	course_cluster_detail.jsonl
	•	Global maps and institution-level reports:
	•	global_issues.csv
	•	issue_course_matrix.csv
	•	pipeline_counts_by_course.csv
	•	pipeline_counts_by_college.csv
	•	Future web explorer:
	•	JSON exports derived from all Stage 4 tables

Reliability and provenance

Deterministic if:
	•	Stage 0 corpus is fixed
	•	Stage 1 predictions are fixed
	•	Stage 2 painpoints are fixed
	•	Stage 3 run directory is fixed
	•	course metadata is fixed

Provenance chain:
	•	Stage 4 knows which Stage 3 run it used (via run_id and stage3_run_dir).
	•	Stage 3 manifest records which Stage 2 run it came from (source_stage2_run).
	•	Stage 2 manifest links back to Stage 1 and Stage 0 artifacts via paths and run_ids.

This chain is the authoritative lineage for all Stage 4 outputs.