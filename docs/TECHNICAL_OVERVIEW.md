
WGU Reddit Analyzer – Technical Overview
Architecture Guide
Last updated: 2025-12-14

Purpose

This document explains how the WGU Reddit Analyzer works at a high level.

It describes:
	•	how data moves through the system
	•	what each stage is responsible for
	•	how the project maintains clarity, traceability, and reproducible results

It is meant for stakeholders, reviewers, and collaborators who want to understand the architecture without diving into implementation details.

All core artifacts carry a schema_version field (currently 1.0.0) so that future schema changes can be tracked precisely.

⸻

	1.	System Summary

The WGU Reddit Analyzer processes Reddit posts about WGU courses to identify course-related pain points, group similar issues, and produce structured tables used for insights and reports.

The system has four main stages:
	1.	Stage 1 – Pain Point Classification
Identifies whether a post contains a fixable, course-side issue and summarizes it.
	2.	Stage 2 – Course-Level Clustering
Groups similar pain points within each course.
	3.	Stage 3 – Global Issue Normalization
Merges course-level clusters across all courses into a shared set of global issue types.
	4.	Stage 4 – Report Data Layer
Produces clean tables for reports, dashboards, and future tools.

All stages read from the same frozen Stage 0 dataset to keep results stable and repeatable.

The system emphasizes:
	•	transparent data transformations
	•	explicit artifacts at every step
	•	strict provenance and traceability
	•	reproducible evaluation and refinement

⸻

	2.	Repository Structure (High-Level)

src/wgu_reddit_analyzer/
fetchers/        Reddit ingestion (source of Stage 0 data)
pipeline/        Stage 0 filtering and dataset building
benchmark/       Stage 1 benchmarking, alignment, eval tables, sampling
stage1/          Full-corpus Stage 1 classification
stage2/          Stage 2 course-level clustering
stage3/          Stage 3 global normalization and evaluation
report_data/     Stage 4 merged tables and analytics
refinement/      Refinement-loop logging utilities
utils/           Logging, token counting, shared helpers

Supporting folders:
	•	prompts/ – versioned prompt templates
	•	artifacts/ – generated datasets and run folders
	•	docs/ – project documentation
	•	dev/ – developer logs and alignment notes
	•	archive_legacy/ – older experiments and unused code

⸻

	3.	Stage 0 – Dataset Build (Inputs to All Stages)

Stage 0 collects Reddit posts and produces a clean, stable dataset.

It:
	•	ingests posts from WGU-related subreddits
	•	removes spam, deleted content, and empty posts
	•	detects valid WGU course codes
	•	computes sentiment and retains strongly negative posts
	•	normalizes IDs, titles, text, and timestamps

Key artifact:
	•	artifacts/stage0_filtered_posts.jsonl

This dataset is treated as frozen so all downstream results are repeatable.

⸻

	4.	Stage 1 – Pain Point Classification

Goal

Determine whether each post contains a fixable course-side pain point and, if so, generate:
	•	a short root-cause summary
	•	a concise snippet anchored in the post

Stage 1 uses a strict tri-state label:
	•	y = contains a fixable pain point
	•	n = does not contain a fixable pain point
	•	u = unclear, invalid, or unparseable

All labels are explicitly normalized into {y, n, u}. No rows are silently dropped.

Stage 1 has two modes.

⸻

4.1 Benchmark Mode (DEV / TEST)

Benchmark mode evaluates prompts and models against fixed gold labels.

It focuses on:
	•	binary precision, recall, F1, and accuracy
	•	explicit handling of ambiguous or invalid outputs
	•	cost per post and latency
	•	schema stability and parsing behavior
	•	prompt and model comparison

This logic lives under src/wgu_reddit_analyzer/benchmark/.

Per-run outputs include:
	•	predictions_.csv
	•	metrics_.json
	•	manifest.json
	•	raw_io_.jsonl

Alignment and evaluation artifacts:
	1.	Deterministic alignment diagnostics
Stored under artifacts/benchmark/alignment/<run_id>/:

	•	confusion_matrix__<run_id>.csv
	•	confusion_heatmap__<run_id>.png

These use a fixed 3×3 matrix over ordered labels {y, n, u}.
	2.	Eval tables
Stored under artifacts/benchmark/eval/<run_slug>/:

	•	stage1_confusion_long.csv
	•	stage1_confusion_matrix.csv

Metrics policy

Binary metrics are computed using the policy binary_excluding_u:
	•	rows where gold == u or pred == u are excluded
	•	excluded rows are explicitly counted as num_excluded_due_to_u
	•	no implicit relabeling occurs

metrics_.json includes:
	•	metrics_policy = “binary_excluding_u”
	•	num_excluded_due_to_u

Provenance guarantees
	•	The exact rendered prompt sent to the model is logged
	•	prompt_sha256 is recorded in both manifest.json and stage1_run_index.csv
	•	The prompt file itself is copied into the run directory
	•	Prompt text logged in raw IO is byte-identical to the model input

Global run index

All Stage 1 benchmark runs append one row to:
	•	artifacts/benchmark/stage1_run_index.csv

This index records:
	•	model, provider, split
	•	prompt_name and prompt_sha256
	•	metrics and counts
	•	paths to predictions, metrics, and alignment artifacts
	•	run_dir and timestamps

This file is an index only, not an artifact store.

⸻

4.2 Full-Corpus Mode

Once a model and prompt are selected, Stage 1 runs over the entire Stage 0 dataset.

Each output row includes:
	•	pred_contains_painpoint (y, n, or u)
	•	root_cause_summary and pain_point_snippet when y
	•	confidence_pred normalized to [0, 1]
	•	parse_error, schema_error, used_fallback, llm_failure
	•	model, provider, run_id, schema_version

Important semantics:
	•	confidence scores are not used for filtering
	•	Stage 2 consumes only rows where:
	•	pred_contains_painpoint == “y”
	•	no error flags are set

Key downstream artifact:
	•	artifacts/stage2/painpoints_llm_friendly.csv

⸻

	5.	Stage 2 – Course-Level Clustering

Goal

Transform individual pain points into course-specific themes.

Inputs:
	•	Stage 1 pain-point rows
	•	course metadata
	•	clustering prompt per course

Process:
	1.	Load valid pain-point rows
	2.	Attach course metadata
	3.	Group by course_code
	4.	Cluster pain points using an LLM
	5.	Validate outputs against strict schemas
	6.	Store prompts, inputs, outputs, and manifests

Clusters include:
	•	cluster_id
	•	issue_summary
	•	num_posts
	•	member post_ids

Posts may belong to multiple clusters within a course.

Key outputs:
	•	course-level cluster JSON files
	•	clusters_llm.csv
	•	artifacts/stage3/preprocessed/<stage2_run_slug>/clusters_llm.csv
	•	Stage 2 manifest with schema_version and counts

5.1 Stage 2 Evaluation

Deterministic diagnostics under:
	•	artifacts/stage2/eval/<stage2_run_slug>/

Includes:
	•	cluster_size_summary
	•	course_cluster_coverage

These do not affect clustering behavior.

⸻

	6.	Stage 3 – Global Issue Normalization

Goal

Merge course-level clusters into a shared taxonomy of global issue types.

Inputs:
	•	Stage 2 cluster outputs
	•	Stage 2 manifest

Process:
	•	batch clusters by impact
	•	normalize cluster meanings via LLM
	•	assign global_cluster_id
	•	ensure one-to-one coverage or explicit unassignment
	•	merge batches
	•	map results back to posts

Key artifacts:
	•	global_clusters.json
	•	cluster_global_index.csv
	•	post_global_index.csv

Stage 3 manifest records full provenance.

6.1 Stage 3 Evaluation

Diagnostics under:
	•	artifacts/stage3/eval/<stage3_run_slug>/

Includes:
	•	cluster_global_alignment_long.csv
	•	global_issue_coverage.csv
	•	cluster_issue_coverage.csv

Used for inspection only.

⸻

	7.	Stage 4 – Report Data Layer

Goal

Produce clean, merged tables for reporting and analysis.

Implementation:
	•	src/wgu_reddit_analyzer/report_data/build_analytics.py
	•	outputs under artifacts/report_data/

Inputs:
	•	Stage 0 posts
	•	Stage 1 full-corpus predictions
	•	Stage 2 cluster tables
	•	Stage 3 global mappings
	•	course metadata

Main outputs:
	•	post_master.csv
	•	course_summary.csv
	•	course_cluster_detail.jsonl
	•	global_issues.csv
	•	issue_course_matrix.csv

All transformations are deterministic joins and aggregations.

7.1 Overviews and Pipeline Counts

Optional summaries:
	•	courses_overview.csv
	•	issues_overview.csv
	•	pipeline_counts_by_course.csv
	•	pipeline_counts_by_college.csv
	•	pipeline_counts_overview.md

⸻

	8.	Model Registry and LLM Client

All LLM calls go through a shared client that handles:
	•	provider selection
	•	retries and failures
	•	token counting and cost
	•	raw prompt and response logging

Each call emits a structured LlmCallResult.

⸻

	9.	Prompts and Versioning

	•	All prompts live under prompts/
	•	Prompt files are copied into run directories
	•	prompt_sha256 is recorded for change detection
	•	Manifests record full configuration and provenance

⸻

	10.	Reproducibility

Reproducibility is enforced through:
	•	frozen Stage 0 data
	•	fixed DEV/TEST gold labels
	•	deterministic evaluation logic
	•	explicit schema_version everywhere
	•	per-run manifests and raw logs

Any run can be recreated exactly.

⸻

	11.	Evaluation and Refinement Logging

The system maintains explicit evaluation layers:
	•	Stage 1 alignment and confusion diagnostics
	•	Stage 2 cluster diagnostics
	•	Stage 3 coverage and purity diagnostics

Refinement decisions are logged separately with structured rationale and references to inspected artifacts.

⸻

Below is a clean, drop-in update to the technical overview.
Nothing else in the document needs to change.

You should add one new subsection under Stage 1, and a small update to Sections 10–11.
This keeps the document professional, stable, and paper-ready.

⸻

Add this new subsection under Stage 1

Insert after 4.1 Benchmark Mode and before 4.2 Full-Corpus Mode.

⸻

4.1.1 Statistical Validation and Prompt Gating

Benchmark metrics alone (precision, recall, F1) are not sufficient to justify prompt updates, because they do not measure whether improvements are statistically meaningful or driven by paired error correction.

To address this, the system includes a formal statistical gating layer for Stage 1 prompt refinement.

This layer compares two benchmark runs of the same model and split (old prompt vs new prompt) using only gold-labeled DEV or TEST data.

The gating process performs three analyses:
	1.	Paired error analysis (McNemar test)
For each post_id shared between the two runs:
	•	Was the old prompt correct?
	•	Was the new prompt correct?
From these paired outcomes, the system computes:
	•	b: old correct, new wrong
	•	c: old wrong, new correct
An exact two-sided McNemar test is applied using a Binomial(b+c, 0.5) distribution.
This determines whether the new prompt fixes significantly more errors than it introduces.
	2.	Binary metric comparison
Precision, recall, F1, and accuracy are computed for both runs using the existing
binary_excluding_u policy:
	•	rows with gold == u or pred == u are excluded
	•	excluded rows are explicitly counted
Metrics are computed only on the joined set of examples to ensure fairness.
	3.	Prediction distribution shift diagnostic
The system compares predicted label counts (y, n, u) between the two runs using a
2×3 chi-square test.
Significant shifts are flagged for review but do not automatically veto adoption.

Prompt adoption rule
A prompt update is accepted only if:
	•	New F1 is not lower than old F1, and
	•	McNemar p-value < 0.05, and
	•	c > b (more errors fixed than introduced)

Otherwise, the update is rejected.

Gating artifacts
Each comparison writes deterministic artifacts under:

artifacts/benchmark/gating/<comparison_slug>/

Including:
	•	gating_summary.json
(metrics, McNemar results, distribution shift, final decision)
	•	paired_rows.csv
(per-example audit trail with eligibility and correctness flags)

This gating layer converts Stage 1 prompt iteration from qualitative experimentation into statistically validated model refinement.

⸻

Update Section 10 (Reproducibility)

Add one bullet at the end:
	•	deterministic statistical gating artifacts for Stage 1 prompt adoption decisions

⸻

Update Section 11 (Evaluation and Refinement Logging)

Replace the final paragraph with this clarified version:

⸻

The system maintains explicit evaluation layers:
	•	Stage 1 alignment diagnostics (confusion matrices and heatmaps)
	•	Stage 1 statistical gating for prompt updates (McNemar and distribution shift tests)
	•	Stage 2 cluster diagnostics
	•	Stage 3 coverage and normalization diagnostics

Refinement decisions are logged separately with structured rationale and direct references to the underlying evaluation and gating artifacts. Prompt updates are adopted only when statistically justified.

⸻
