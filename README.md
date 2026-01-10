
WGU Reddit Analyzer Pipeline

Last updated: 2025-12-14

⸻

Purpose

The WGU Reddit Analyzer is a reproducible, auditable pipeline for extracting actionable student pain points from Reddit discussions about Western Governors University (WGU).

Its goal is not sentiment monitoring, but structured issue discovery:
	•	identifying whether a post describes a real, course-side problem
	•	grouping similar issues
	•	producing clean, traceable data for analysis, reporting, and research

The system is designed to balance:
	•	methodological rigor
	•	transparency and auditability
	•	practical cost and performance constraints

It is suitable both for internal analysis and for academic or external review.

⸻

What the System Does (At a High Level)

The analyzer takes Reddit posts and transforms them into structured insights through a multi-stage process:
	1.	Collect and clean relevant Reddit posts
	2.	Detect whether each post contains a genuine, actionable pain point
	3.	Group similar pain points within courses
	4.	Normalize those groups into a global issue taxonomy
	5.	Produce clean tables for reporting and downstream use

At every step, the system writes explicit artifacts so results can be inspected, reproduced, or challenged.

⸻

System Architecture Overview

The pipeline is organized into four main analytical stages, all operating on a shared, frozen dataset.

Stage 0 — Data Collection and Filtering
	•	Ingests Reddit posts from WGU-related subreddits
	•	Removes spam, deleted, or empty content
	•	Detects valid WGU course codes
	•	Retains posts with strong negative sentiment
	•	Produces a stable, frozen dataset used by all later stages

Key output:
artifacts/stage0_filtered_posts.jsonl

⸻

Stage 1 — Pain Point Classification

Stage 1 determines whether a post contains a fixable, course-side pain point.

Each post is classified into one of three labels:
	•	y — contains a clear pain point
	•	n — does not contain a pain point
	•	u — unclear or unusable (ambiguous, parsing failure, or invalid output)

If a pain point is detected, the model also produces:
	•	a short root-cause summary
	•	a concise text snippet anchored in the post

Stage 1 operates in two modes:

Benchmark Mode (DEV / TEST)
Used to evaluate prompts and models against human-labeled data.

Measures include:
	•	precision, recall, F1, and accuracy
	•	handling of ambiguous outputs
	•	cost and latency
	•	error modes and parsing behavior

All benchmark runs produce:
	•	prediction tables
	•	metrics summaries
	•	alignment diagnostics (confusion matrices)
	•	full run manifests with provenance

Full-Corpus Mode
Once a model and prompt are selected, Stage 1 runs across the entire dataset to produce inputs for later stages.

Only posts confidently labeled as pain points are passed downstream.

⸻

Stage 2 — Course-Level Clustering

Stage 2 groups individual pain points within each course into coherent themes.

For each course, the system:
	•	collects pain-point posts
	•	clusters them using an LLM
	•	produces summaries and membership lists

The result is a set of course-specific issue clusters, each backed by explicit artifacts and manifests.

⸻

Stage 3 — Global Issue Normalization

Stage 3 merges course-level clusters into a shared global issue taxonomy.

This step:
	•	aligns similar issues across different courses
	•	assigns global issue identifiers
	•	ensures full coverage or explicit exclusion

It produces mappings from posts and course clusters to global issue types, enabling cross-course analysis.

⸻

Stage 4 — Report Data Layer

Stage 4 produces clean, deterministic tables for reporting and analysis.

Outputs include:
	•	post-level master tables
	•	course summaries
	•	global issue summaries
	•	issue-by-course matrices

All outputs are deterministic joins and aggregations of prior stages.

⸻

Evaluation, Benchmarking, and Validation

Explicit Benchmarking

Stage 1 is the only stage with full empirical benchmarking against gold labels.

Benchmark artifacts include:
	•	3×3 confusion matrices over {y, n, u}
	•	binary metrics computed under a strict policy
	•	per-run cost and latency summaries
	•	post-level inspection panels for false positives and false negatives

Ambiguous outputs are never silently dropped; exclusions are explicitly counted.

⸻

Statistical Validation of Prompt Improvements

Prompt updates are evaluated using paired statistical tests, not just headline metrics.

For each prompt comparison on the same DEV set, the system computes:
	•	paired correctness differences
	•	McNemar’s exact test to assess whether improvements are statistically meaningful
	•	class-distribution chi-square tests to detect large behavioral shifts

A new prompt is accepted only if:
	•	F1 score does not regress
	•	McNemar’s test shows a statistically significant improvement
	•	distribution shifts are reviewed and acknowledged

This ensures that prompt iteration is grounded in evidence, not anecdotal improvements.

⸻

Reproducibility and Provenance

The pipeline enforces reproducibility through:
	•	a frozen Stage 0 dataset
	•	fixed DEV/TEST benchmark splits
	•	versioned prompts stored alongside outputs
	•	per-run manifests recording configuration and hashes
	•	explicit schema_version fields on all major artifacts
	•	raw model input and output logs for audits

Any run can be recreated or independently inspected.

⸻

Repository Structure (High Level)

src/wgu_reddit_analyzer/
├── fetchers/        Reddit ingestion
├── pipeline/        Stage 0 dataset build
├── benchmark/       Stage 1 benchmarking and evaluation
├── stage1/          Full-corpus Stage 1 classification
├── stage2/          Course-level clustering
├── stage3/          Global issue normalization
├── report_data/     Final report tables
├── refinement/      Refinement and iteration logging
└── utils/           Shared helpers and logging

Supporting folders:
	•	prompts/ — versioned prompt templates
	•	artifacts/ — generated data and run outputs
	•	docs/ — technical and methodological documentation
	•	dev/ — internal development and alignment logs
	•	archive_legacy/ — deprecated experiments

⸻

Methodological Alignment

The design of the WGU Reddit Analyzer aligns with the framework described in:

LLM-as-classifier: Semi-Supervised, Iterative Framework for Hierarchical Text Classification using Large Language Models (2025)

That framework emphasizes:
	•	domain-driven schemas
	•	semi-supervised topic discovery
	•	explicit iterative refinement
	•	statistical validation of updates
	•	robustness and drift awareness

The analyzer already satisfies many of these principles through its frozen corpus, hierarchical stages, versioned prompts, deterministic artifacts, and strong provenance guarantees.

A focused three-step alignment plan brings the system to a defensible level of methodological rigor:
	1.	Explicit schema and hierarchy documentation
	2.	Alignment matrices and visible refinement loops
	3.	Statistical gating of Stage 1 prompt updates

Together, these steps support transparent, auditable iteration without requiring major architectural changes.

⸻

Status
	•	Stage 0 dataset locked
	•	Stage 1 benchmarking and statistical validation complete
	•	Stage 2–4 fully operational
	•	Prompt refinement loop active and documented

The system is production-ready for analysis and suitable for external review.

⸻

References
	•	Rao et al. (2025). QuaLLM Framework for Reddit Feedback Extraction
	•	De Santis et al. (2025). LLM Robustness on Noisy Social Text
	•	LLM-as-classifier: Semi-Supervised, Iterative Framework for Hierarchical Text Classification using Large Language Models (2025)

⸻
