WGU Reddit Analyzer – Stage 1 Specification
Pain-Point Detection, Benchmarking, Statistical Gating, and Full-Corpus Classification
Last updated: 2025-12-14

⸻

	1.	Purpose and Scope

Stage 1 decides whether a Reddit post contains a course-side, actionable pain point and, if so, extracts:
	•	a root-cause summary
	•	a short snippet anchored in the post
	•	a model confidence score (metadata only, never used for filtering)

Stage 1 has two modes:
	1.	Benchmark mode (DEV/TEST)
Used for model and prompt selection, cost and latency measurement, behavior evaluation, and statistically validated prompt adoption decisions.
	2.	Full-corpus mode
Applies a chosen model and prompt to the entire Stage 0 dataset to produce inputs for Stage 2 clustering.

Stage 1 is the only stage with comprehensive empirical benchmarking and formal prompt gating. All outputs follow one stable normalized schema. Stage 1 uses run_id as canonical provenance.

⸻

	2.	Inputs and Dependencies

From Stage 0:
	•	artifacts/stage0_filtered_posts.jsonl
Frozen cleaned Reddit posts.

Benchmark sampling inputs:
	•	artifacts/benchmark/DEV_candidates.jsonl
	•	artifacts/benchmark/TEST_candidates.jsonl
	•	artifacts/benchmark/gold/gold_labels.csv

Prompts:
	•	prompts/s1_zero.txt
	•	prompts/s1_few.txt
	•	prompts/s1_optimal.txt

Model system:
	•	src/wgu_reddit_analyzer/benchmark/model_registry.py
	•	src/wgu_reddit_analyzer/benchmark/model_client.py

Statistical gating inputs:
	•	two Stage 1 benchmark run directories containing split-specific predictions CSVs
	•	gold-labeled DEV or TEST data (required for paired statistical tests)

⸻

	3.	Stage 1 Responsibilities

Stage 1:
	1.	Runs LLM classifiers with different prompts and models (benchmark mode)
	2.	Parses JSON, normalizes outputs, enforces schema safety
	3.	Emits deterministic benchmark artifacts suitable for statistical comparison
	4.	Computes metrics, cost, and latency under explicit semantics
	5.	Supports FP and FN analysis via post-level panels and raw IO logs
	6.	Supports statistically validated prompt adoption via paired tests (gating)
	7.	Runs the chosen model and prompt on all Stage 0 posts (full-corpus mode)
	8.	Produces stable per-post predictions consumed by Stage 2
	9.	Records run_id and schema_version in run manifests and outputs

Removed:
	•	no confidence thresholds
	•	no heuristic filtering
	•	no silent drops

⸻

	4.	Labels and Semantics

Stage 1 uses a strict tri-state label:
	•	y = contains a fixable course-side pain point
	•	n = does not contain a fixable course-side pain point
	•	u = unknown or unusable due to parsing, schema, or ambiguous output

Normalization rule:
	•	both gold and predicted labels are canonicalized into {y, n, u}
	•	invalid or missing labels normalize to u
	•	this applies to all alignment, metrics, and gating logic

⸻

	5.	Datasets and Sampling (DEV / TEST)

5.1 Base
	•	source: artifacts/stage0_filtered_posts.jsonl

Sampling code under src/wgu_reddit_analyzer/benchmark/ produces:
	•	artifacts/benchmark/DEV_candidates.jsonl
	•	artifacts/benchmark/TEST_candidates.jsonl

Sampling rules and exact counts are defined by the sampling scripts and their manifests.

5.2 Gold labels
Stored in artifacts/benchmark/gold/gold_labels.csv

Fields commonly include:
	•	post_id
	•	split
	•	course_code
	•	contains_painpoint in {y, n, u}
	•	root_cause_summary
	•	ambiguity_flag
	•	labeler_id
	•	notes

Gold labels are treated as immutable.

If ambiguity filtering is applied, it must be explicit in code and documented in the run manifest or metrics policy.

⸻

	6.	Stage 1 Prediction Schema (Authoritative)

Benchmark predictions file includes, per post:
	•	post_id
	•	course_code
	•	true_contains_painpoint in {y, n, u}
	•	pred_contains_painpoint in {y, n, u}
	•	root_cause_summary_pred
	•	pain_point_snippet_pred
	•	confidence_pred in [0.0, 1.0]
	•	parse_error (bool)
	•	schema_error (bool)
	•	used_fallback (bool)
	•	llm_failure (bool)

Rules:
	•	if pred == y, summary and snippet are populated (derived from model output)
	•	if pred in {n, u}, summary and snippet are empty
	•	invalid or missing confidence is coerced to 0.0
	•	any parse or schema error yields pred_contains_painpoint == u, with flags set, unless safely recovered by an explicit fallback parser

Downstream stages never use confidence for filtering.

⸻

	7.	Benchmark Code Layout

Under src/wgu_reddit_analyzer/benchmark/:

Core Stage 1:
	•	stage1_classifier.py
Prompt rendering, model call, parsing, normalization, safe fallback behavior.
	•	stage1_types.py
Pydantic models for Stage 1 inputs, outputs, and call metadata.
	•	model_client.py
Provider-neutral call wrapper with retries, timing, token counting, cost estimation.
	•	model_registry.py
Model metadata and pricing configuration.
	•	run_stage1_benchmark.py
Benchmark runner (DEV/TEST) that writes run artifacts and indexes the run.

Benchmark evaluation:
	•	eval_types.py
Pydantic models for Stage 1 eval outputs (confusion tables).
	•	eval_builders.py
Deterministic builders for stage1_confusion_long and stage1_confusion_matrix.

Alignment diagnostics:
	•	benchmark/alignment/label_utils.py
Label normalization and metrics policy helpers.
	•	benchmark/alignment/confusion_matrix.py
Deterministic 3x3 confusion matrix builder over ordered {y, n, u}.
	•	benchmark/alignment/heatmap.py
Matplotlib writer for confusion matrix heatmaps.

Statistical gating:
	•	stage1_stat_tests.py
Pure statistical utilities (McNemar exact p-value; chi-square for 2xK contingency).
	•	stage1_stat_gating.py
Loads two run dirs, joins by post_id, computes paired tests and metrics, writes gating artifacts.
	•	cli_stage1_gating.py
CLI wrapper for gating comparisons.

Analysis helpers:
	•	build_stage1_panel.py
Builds post-level panels for FP and FN analysis.
	•	combine_runs_for_analysis.py
Optional collation of multiple runs for comparisons.
	•	update_run_index.py
Utilities for summarizing run index into markdown.

Artifacts:
	•	artifacts/benchmark/stage1/runs/<run_slug>/
	•	artifacts/benchmark/stage1_run_index.csv
	•	artifacts/benchmark/eval/<run_slug>/
	•	artifacts/benchmark/alignment/<run_id>/
	•	artifacts/benchmark/gating/<comparison_slug>/

⸻

	8.	Prompt Benchmarking and Provenance

Prompts:
	•	prompts/s1_zero.txt
	•	prompts/s1_few.txt
	•	prompts/s1_optimal.txt

Each run:
	•	copies the prompt file into the run directory
	•	records prompt_filename and prompt_template_path in manifest.json
	•	records prompt_sha256 in manifest.json and stage1_run_index.csv

Prompt provenance guarantee:
	•	the prompt logged in raw_io_.jsonl is byte-identical to the prompt sent to the model
	•	the runner constructs prompt_text deterministically and passes it into classify_post for the model call

⸻

	9.	LLM Call Logic

Stage 1 uses model_client.generate():
	•	provider-neutral
	•	supports retries and timeouts
	•	returns LlmCallResult with raw text, token usage, cost, and latency
	•	sets llm_failure and retry metadata

Runs are not strictly deterministic due to provider behavior, but the pipeline logs enough provenance to reproduce and audit exact run conditions.

⸻

	10.	Benchmark Runner Flow

run_stage1_benchmark.py performs:
	1.	Load gold labels and candidate inputs for the split
	2.	Load prompt template and compute prompt_sha256
	3.	For each eligible post in a fixed order:
	•	build prompt_text deterministically
	•	call classify_post with prompt_text to guarantee provenance
	•	append raw IO record to raw_io_.jsonl
	•	record normalized prediction row
	4.	Write predictions_.csv
	5.	Compute and write metrics_.json
	6.	Write evaluation tables under artifacts/benchmark/eval/<run_slug>/
	7.	Write alignment artifacts under artifacts/benchmark/alignment/<run_id>/
	8.	Write manifest.json
	9.	Append one row to artifacts/benchmark/stage1_run_index.csv

Run directory shape:

artifacts/benchmark/stage1/runs/<run_slug>/
	•	predictions_.csv
	•	metrics_.json
	•	raw_io_.jsonl
	•	manifest.json
	•	copied prompt file

⸻

	11.	Metrics and Explicit Policy

Stage 1 benchmark metrics use an explicit policy.

Current policy:
	•	metrics_policy = binary_excluding_u

Meaning:
	•	binary metrics are computed only over rows where gold in {y, n} and pred in {y, n}
	•	any row where gold == u or pred == u is excluded from binary precision, recall, F1, and accuracy
	•	the number of excluded rows is recorded as num_excluded_due_to_u

The 3x3 confusion matrix over {y, n, u} is still computed and saved as alignment artifacts.

⸻

	12.	Alignment Artifacts

Alignment artifacts are written per run_id:

artifacts/benchmark/alignment/<run_id>/
	•	confusion_matrix__<run_id>.csv
	•	confusion_heatmap__<run_id>.png

Properties:
	•	deterministic label ordering: y, n, u
	•	invalid labels are normalized to u

These artifacts are diagnostics-only and do not change classifier behavior.

⸻

	13.	Statistical Gating for Prompt Updates

Stage 1 includes a formal statistical gate for adopting prompt changes. This gate compares two benchmark runs on the same split and model.

Inputs:
	•	old_run_dir (Stage 1 benchmark run directory)
	•	new_run_dir (Stage 1 benchmark run directory)
	•	split in {DEV, TEST}

Predictions file resolution (legacy-safe):
	1.	If manifest.json exists and manifest.predictions_path exists on disk, use it.
	2.	Otherwise fall back to run_dir/predictions_{split}.csv.
	3.	Error if neither exists.

Join rule:
	•	inner join by post_id
	•	gating aborts if the join produces zero matched rows
	•	gating aborts if gold labels disagree across runs after normalization

Measured quantities:
	1.	Paired correctness outcomes for McNemar eligibility

	•	eligibility: gold, pred_old, pred_new all in {y, n}
	•	b: old correct, new wrong
	•	c: old wrong, new correct
	•	exact two-sided McNemar p-value using Binomial(b+c, 0.5)

	2.	Binary metrics for each run under binary_excluding_u

	•	computed on the joined set only
	•	reported for old and new with excluded counts

	3.	Prediction distribution shift (diagnostic)

	•	counts of predicted y, n, u on joined rows for old and new
	•	chi-square test on a 2x3 contingency table
	•	significant shifts are flagged but do not automatically veto adoption

Decision rule:
	•	reject if new F1 is strictly lower than old F1
	•	otherwise accept only if McNemar p-value < alpha and c > b
	•	otherwise reject

Gating artifacts:

artifacts/benchmark/gating/<comparison_slug>/
	•	gating_summary.json
	•	paired_rows.csv

These artifacts are deterministic and provide a full audit trail for prompt adoption decisions.

⸻

	14.	Run Index

The global Stage 1 run index is:
	•	artifacts/benchmark/stage1_run_index.csv

It contains one row per run and split, including:
	•	run_slug, model_name, provider, split
	•	prompt_name and prompt_sha256
	•	metrics and counts
	•	num_excluded_due_to_u
	•	cost and latency summaries
	•	paths to run_dir, metrics, predictions, and alignment artifacts
	•	timestamps

This file is an index, not an artifact store.

⸻

	15.	Raw IO Logging

Every model call appends one JSONL record to raw_io_.jsonl including:
	•	post_id, course_code
	•	model_name, provider
	•	split
	•	prompt_name
	•	prompt_text (exact model input)
	•	raw_response_text
	•	timestamps
	•	parse_error, schema_error, used_fallback, llm_failure

Used for debugging, audits, and post-hoc analyses.

⸻

	16.	Unified Post-Level Panel

build_stage1_panel.py produces:
	•	artifacts/benchmark/stage1_panel_DEV.csv
	•	artifacts/benchmark/stage1_panel_TEST.csv

Typical contents:
	•	post text
	•	gold labels
	•	predictions and flags
	•	confidence
	•	error categorization (tp fp fn tn) under the active metrics policy
	•	run metadata (model, prompt, run_slug, run_id)

Used for qualitative FP and FN inspection and refinement.

⸻

	17.	Prompt Iteration and Refinement Workflow

Prompt iteration is performed in benchmark mode and adopts prompts via statistical gating.

Typical workflow:
	1.	Run benchmark on DEV (and TEST when available)
	2.	Inspect panels for FP and FN patterns
	3.	Propose prompt update
	4.	Run benchmark again on the same split and model
	5.	Run statistical gating (old vs new) on the paired benchmark runs
	6.	Adopt the prompt only if gating accepts
	7.	Record refinement iteration notes referencing gating artifacts and inspected panels

⸻

	18.	Full-Corpus Mode

Full-corpus Stage 1 applies the selected model and prompt across all Stage 0 posts.

Outputs are written as a run directory with:
	•	full-corpus predictions CSV (or equivalent)
	•	raw IO logs
	•	manifest.json containing run_id, prompt provenance, and schema_version
	•	prompt copy

Stage 2 reads pain-point rows from the full-corpus output, filtering only by:
	•	pred_contains_painpoint == y
	•	no failure flags

No thresholds are introduced.

⸻

	19.	Model Requirements

Models must:
	•	produce parseable output under the Stage 1 schema contract
	•	behave stably under retry policy
	•	expose token usage (or be handled consistently when unavailable)
	•	set llm_failure correctly on call failures

Registry commonly includes:
	•	llama3
	•	gpt-5-nano
	•	gpt-5-mini
	•	gpt-5
	•	gpt-4o-mini

⸻

	20.	Reproducibility

Stage 1 reproducibility is supported by:
	•	frozen Stage 0 dataset
	•	fixed DEV/TEST candidates and gold labels
	•	deterministic prompt rendering and fixed iteration order
	•	per-run prompt copy and prompt_sha256
	•	per-run manifests capturing configuration and paths
	•	raw IO logs for every model call
	•	explicit schema_version on artifacts
	•	deterministic eval, alignment, and gating outputs

Downstream systems should key provenance on run_id, with prompt_sha256 used to detect prompt changes cleanly.

⸻

