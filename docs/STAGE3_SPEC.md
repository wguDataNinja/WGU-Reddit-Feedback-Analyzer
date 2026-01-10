STAGE 3 SPEC
Cross-Course Meta-Clustering and Global Pain-Point Themes
Last updated: 2025-12-11
	1.	Purpose

Stage 3 merges all course-level clusters (from Stage 2) into a smaller set of cross-course global issue themes.

It answers:
Which root-cause problems recur across WGU courses and programs?

Consumers include program chairs, curriculum designers, and leadership.
	2.	Inputs

From a specific Stage 2 run (identified by stage2_run_slug):
	•	Stage 2 manifest
artifacts/stage2/runs/<stage2_run_slug>/manifest.json
	•	Stage 2 cluster outputs (exact filenames may vary, but must be documented):
	•	artifacts/stage2/runs/<stage2_run_slug>/painpoint_clusters.csv
(or equivalent per-cluster CSV with cluster_id, course_code, num_posts, etc.)

From Stage 3 preprocessing:
	•	Flattened cluster summary CSV:
artifacts/stage3/preprocessed/<stage2_run_slug>/clusters_llm.csv
(LLM-ready summaries of Stage 2 clusters)

Stage 3 also consumes:
	•	The Stage 3 prompt template (copied to stage3_prompt.txt for each run)
	•	The Stage 2 run_id and metadata from the Stage 2 manifest

	3.	Responsibilities

Stage 3:
	1.	Loads Stage 2 cluster metadata and the preprocessed clusters_llm.csv.
	2.	Normalizes cluster summaries into LLM-friendly units.
	3.	Groups semantically similar clusters across courses.
	4.	Assigns each merged group:
	•	provisional_label
	•	normalized_issue_label
	•	short_description
	•	member_cluster_ids
	5.	Ensures coverage and exclusivity:
	•	every Stage 2 cluster_id appears exactly once in a global cluster or in unassigned_clusters
	•	no duplicates
	•	no silent drops
	•	if the LLM omits some cluster_ids in a batch, they are treated as unassigned (not errors)
	6.	Produces canonical global outputs (JSON + index CSVs).
	7.	Writes a Stage 3 manifest with:
	•	run_id (Stage 3)
	•	schema_version
	•	source_stage2_run provenance
	•	timing, cost, and simple counts

	4.	Global theme rules

provisional_label
	•	lowercase natural-language phrase
	•	describes the dominant, fixable root cause
	•	stable within a run; analysts may edit later

Examples:
	•	“practice and study materials misaligned with assessments”
	•	“ambiguous or incomplete instructions”
	•	“inconsistent or unhelpful evaluator feedback”

normalized_issue_label
	•	canonical machine-friendly tag
	•	must reuse the seeded taxonomy when possible (see schema document)
	•	typically fewer normalized labels than global clusters

Examples:
	•	assessment_material_misalignment
	•	unclear_or_ambiguous_instructions
	•	course_pacing_or_workload
	•	technology_or_platform_issues

short_description
	•	one sentence explaining the fixable mechanism

Example:
“Course practice materials do not match the OA’s content or difficulty, leaving students unprepared.”

member_cluster_ids
	•	list of Stage 2 cluster_id values that compose the global cluster

	5.	Assignment rules

	•	Each Stage 2 cluster_id appears once:
	•	inside a global cluster’s member_cluster_ids, or
	•	inside unassigned_clusters
	•	No duplicates
	•	No cluster in multiple themes

unassigned_clusters is used when:
	•	summary is too vague to infer a fixable cause
	•	issue is not actionable (pure emotion only)
	•	the LLM batch response omits that cluster_id

Omitted cluster_ids must still be listed explicitly in unassigned_clusters.
Emotions like “confused” or “frustrated” are not root causes.
	6.	Output format (canonical global JSON)

File:
artifacts/stage3/runs/<stage3_run_slug>/global_clusters.json

Shape:

{
“global_clusters”: [
{
“provisional_label”: “string”,
“normalized_issue_label”: “string”,
“short_description”: “string”,
“member_cluster_ids”: [“C123_1”, “C456_2”]
}
],
“unassigned_clusters”: [“C789_3”]
}

Rules:
	•	global_clusters sorted by descending total_num_posts (computed later)
	•	no course_code or course_title in output
	•	a normalized_issue_label may appear on multiple global clusters
	•	unassigned_clusters collects vague, non-actionable, or LLM-omitted clusters

	7.	Index files and provenance

Stage 3 adds internal index files used by Stage 4 and eval:

cluster_global_index.csv
	•	one row per Stage 2 cluster_id
	•	columns include:
	•	schema_version
	•	stage3_run_id, stage3_run_slug, stage3_run_dir
	•	cluster_id
	•	global_cluster_id (or a reserved unassigned identifier)
	•	normalized_issue_label
	•	provisional_label
	•	total_num_posts
	•	num_courses
	•	ensures each Stage 2 cluster_id is accounted for exactly once

post_global_index.csv
	•	one row per (post_id, cluster_id, global_cluster_id)
	•	columns include:
	•	schema_version
	•	stage3_run_id, stage3_run_slug, stage3_run_dir
	•	post_id
	•	course_code
	•	cluster_id
	•	global_cluster_id
	•	normalized_issue_label
	•	preserves multi-cluster membership and supports Stage 4 joins

Stage 3 manifest

File:
artifacts/stage3/runs/<stage3_run_slug>/manifest.json

Fields include (non-exhaustive):
	•	schema_version
	•	run_id
	•	stage3_run_slug
	•	stage3_run_dir
	•	source_stage2_run:
	•	run_id (may be null for legacy Stage 2 runs)
	•	stage2_run_dir
	•	stage2_run_slug
	•	manifest_path
	•	model_name
	•	prompt_template_path
	•	counts (num_input_clusters, num_global_clusters, num_unassigned_clusters, total_input_posts)
	•	timing and cost fields

Downstream code should rely on run_id and manifest metadata instead of path guessing.
	8.	Workflow

	1.	Load Stage 2 manifest and cluster metadata.
	2.	Load Stage 3 preprocessed clusters_llm.csv.
	3.	Join Stage 2 metadata (course_code, num_posts, post_ids) for weighting.
	4.	Sort clusters by impact (e.g., num_posts descending).
	5.	Batch clusters (default around 60 per batch).
	6.	For each batch:
	•	build strict LLM prompt
	•	call model via model_client.generate()
	•	parse JSON output safely
	•	enforce exclusivity and coverage within the batch
	7.	Merge batch outputs:
	•	merge provisional labels and normalized labels
	•	unify member_cluster_ids
	8.	Compute aggregates:
	•	total_num_posts per global_cluster_id
	•	num_clusters and num_courses
	9.	Write:
	•	global_clusters.json
	•	cluster_global_index.csv
	•	post_global_index.csv
	•	optional global_clusters_summary.csv (auxiliary, not used by Stage 4)
	•	stage3_prompt.txt
	•	manifest.json

	9.	Evaluation outputs (diagnostics)

Stage 3 also produces diagnostics-only eval tables (do not affect pipeline behavior):

Location:
artifacts/stage3/eval/<stage3_run_slug>/

Files:
	•	cluster_global_alignment_long.csv
	•	long-format alignment: one row per (cluster_id, global_cluster_id, normalized_issue_label) with post_count
	•	global_issue_coverage.csv
	•	per normalized_issue_label and global_cluster_id:
	•	total_posts
	•	num_clusters
	•	cluster_issue_coverage.csv
	•	per cluster_id:
	•	dominant_global_cluster_id
	•	dominant_normalized_issue_label
	•	dominant_issue_post_count
	•	total_posts
	•	purity (dominant_issue_post_count / total_posts)

All three include:
	•	schema_version
	•	stage3_run_id, stage3_run_slug, stage3_run_dir

If post_global_index.csv is missing or malformed, Stage 3 writes empty, schema-correct eval tables and logs a warning.
	10.	Cost and runtime

For roughly 300–400 Stage 2 clusters:
	•	6–12 LLM batches
	•	cost ≈ $0.02–$0.15 depending on model
	•	wall time about 3–15 minutes
	•	batches may be processed in parallel

LLM calls may need long timeouts (around 90 seconds) for larger batches.
	11.	Deliverables per Stage 3 run

Required:
	•	global_clusters.json (canonical definition)
	•	cluster_global_index.csv (cluster → global mapping)
	•	post_global_index.csv (post → cluster → global)
	•	manifest.json (with run_id, schema_version, source_stage2_run)

Auxiliary:
	•	global_clusters_summary.csv (not consumed by Stage 4)
	•	stage3_prompt.txt
	•	LLM batch request/response logs
	•	eval tables under artifacts/stage3/eval/<stage3_run_slug>/:
	•	cluster_global_alignment_long.csv
	•	global_issue_coverage.csv
	•	cluster_issue_coverage.csv

These artifacts define the cross-course systemic instructional issues for WGU and provide the diagnostics used in the Phase 2 alignment and future refinement loops.