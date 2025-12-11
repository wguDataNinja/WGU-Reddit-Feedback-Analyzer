
1. Smallest easiest path to ~90% alignment

Starting from about 60–65% aligned.

Step 1 – Make schema and hierarchy explicit (Phase 1)
	•	Write a short schema doc:
	•	Top-level classes (pain point vs not pain point).
	•	Global normalized issue labels with definitions and examples.
	•	The hierarchy: post → pain point → course cluster → global issue.
	•	Record schema version in run manifests.

Effort: easy
Alignment gain: about +5%
Running total: ~65–70%

⸻

Step 2 – Add alignment matrices and a visible refinement loop (Phase 2)
	•	Stage 1:
	•	On DEV/TEST, build confusion matrices between gold pain-point labels and Stage 1 predictions.
	•	Save a simple heatmap per prompt/model.
	•	Stage 2 / 3:
	•	Build alignment tables between discovered clusters and final global issue labels.
	•	For each iteration, log a short “what to change next” note in a manifest or markdown file (classes to merge, drop, or rewrite).
	•	Treat each change as an iteration (t → t+1) with an iteration ID.

Effort: medium
Alignment gain: about +10%
Running total: ~75–80%

⸻

Step 3 – Add statistical gating for Stage 1 prompts (core of Phase 3)
	•	Implement McNemar’s test for Stage 1:
	•	Fixed DEV/TEST set.
	•	Old prompt vs new prompt on same examples.
	•	Compute b, c, chi-square, p-value.
	•	Only adopt a new prompt if F1 improves and p < threshold.
	•	Add a chi-square test for class distributions:
	•	Compare vector of class counts (pain point vs non) between prompts on same dataset.
	•	If distribution shifts significantly, inspect before adoption.

Effort: medium
Alignment gain: strong, about +10–15%
Running total: roughly 85–90%

This step is high leverage: it covers most of the paper’s “Validation Gate” logic without changing the overall architecture.

You can stop here for a lean, realistic ~90% alignment, and leave preference-based few-shots, sequence invariance, adversarial defenses, and drift monitoring as “Phase 2” work.

⸻

2. Alignment Document

WGU Reddit Analyzer – Alignment with “LLM-as-classifier” Framework

Last updated: 2025-12-10

1. Purpose
This document explains how the WGU Reddit Analyzer relates to the framework described in “LLM-as-classifier: Semi-Supervised, Iterative Framework for Hierarchical Text Classification using Large Language Models.”

It focuses on:
	•	How the current pipeline maps to the paper’s phases.
	•	Where the system is already aligned in spirit and mechanics.
	•	A minimal, high-impact path to reach roughly 90% methodological alignment.

⸻

2. Current pipeline overview
The WGU Reddit Analyzer processes Reddit posts about WGU courses to identify course-side pain points and aggregate them into actionable issue types.

It has four stages:
	•	Stage 0 – Dataset build
	•	Collects WGU-related Reddit posts.
	•	Removes spam and invalid content.
	•	Filters to strongly negative posts.
	•	Writes a frozen stage0_filtered_posts.jsonl used by all later stages.
	•	Stage 1 – Pain point classification
	•	Decides whether a post contains a fixable course-side pain point.
	•	Produces a short root-cause summary and a grounded snippet.
	•	Has DEV/TEST benchmarking and a full-corpus mode.
	•	Stage 2 – Course-level clustering
	•	Takes pain-point posts and groups them into course-specific themes using an LLM.
	•	Produces clusters per course with cluster IDs, summaries, and member post IDs.
	•	Stage 3 – Global issue normalization
	•	Merges course clusters into a shared set of global issue types.
	•	Produces a mapping from post → course cluster → global issue label.
	•	Stage 4 – Report data layer
	•	Joins all prior outputs to produce stable tables for reports, dashboards, and analysis.
	•	Is deterministic and does not use LLMs.

Prompts are versioned, all LLM calls log inputs and outputs, and run manifests capture models and parameters. Stage 0 is frozen for reproducibility.

⸻

3. Mapping to the paper’s framework
The paper proposes a four-phase lifecycle plus a validation suite and monitoring layer.
	1.	Phase 1 – Domain knowledge integration

	•	WGU Reddit Analyzer:
	•	Uses WGU course metadata and “fixable course-side pain point” as the core concept.
	•	Implicitly defines top-level classes (pain point vs non pain point) and a set of global issue labels such as assessment_material_misalignment and unclear_or_ambiguous_instructions.
	•	Stage 0 cleans and normalizes the corpus and freezes it as a stable dataset.
	•	Alignment:
	•	Strong on corpus preparation and domain-driven labeling.
	•	The missing piece is an explicit, documented schema describing all classes and the hierarchy.

	2.	Phase 2 – Iterative topic discovery and class refinement

	•	Paper:
	•	Use unconstrained topics or ground-truth classes.
	•	Build an alignment matrix between domain classes and discovered topics.
	•	Use this matrix to refine or drop classes.
	•	WGU Reddit Analyzer:
	•	Uses LLM clustering at the course level (Stage 2) and normalization at the global level (Stage 3) to discover themes.
	•	Already behaves like “LLM discovers structure; humans name the taxonomy.”
	•	Refinement is driven by manual inspection but not yet formalized into alignment matrices and logged iterations.
	•	Alignment:
	•	The mechanics are there (Stages 2 and 3), but the explicit analysis step (alignment matrix) and a visible refine loop are missing.

	3.	Phase 3 – Hierarchical expansion and prompt engineering

	•	Paper:
	•	Build a clean parent–child hierarchy.
	•	Optionally implement a chain-of-thought prompt to decide parent then child.
	•	Optimize prompt length subject to quality.
	•	Use McNemar’s test and chi-square tests to gate prompt changes.
	•	WGU Reddit Analyzer:
	•	Already enforces a hierarchy: post → pain point → course cluster → global issue.
	•	Prompts are versioned and copied into artifacts.
	•	Stage 1 benchmarking tracks metrics but does not yet use formal statistical tests when switching prompts.
	•	Alignment:
	•	Hierarchy and prompt versioning are strong.
	•	Missing the statistical gating that the paper treats as core: McNemar’s test, and distributional chi-square for prompt variants.

	4.	Phase 4 – Reinforced few-shots with human or AI feedback

	•	Paper:
	•	Build a preference dataset of ambiguous cases (winner vs loser labels).
	•	Use it to drive few-shot selection and possibly RLHF/DPO.
	•	WGU Reddit Analyzer:
	•	Has DEV/TEST with gold labels and error inspection.
	•	Few-shot examples exist but are not explicitly derived from a preference dataset.
	•	Alignment:
	•	Conceptually close but lacking a formal preference dataset and documented few-shot selection policy.

	5.	Validation and robustness

	•	Paper:
	•	Standard metrics on a golden set.
	•	Sequence invariance tests (batch order, truncation, few-shot order).
	•	Distributional tests for class balance.
	•	Adversarial robustness against prompt injection.
	•	WGU Reddit Analyzer:
	•	Computes precision, recall, F1 for Stage 1.
	•	Uses a frozen DEV/TEST set.
	•	Does not yet implement sequence invariance tests, adversarial checks, or statistical distribution tests for prompt changes.

	6.	Monitoring and drift

	•	Paper:
	•	Monitor class distributions over time with chi-square tests and control charts.
	•	Monitor embedding cohesion within classes.
	•	Detect novel topics and trigger a return to the refinement loop.
	•	WGU Reddit Analyzer:
	•	Stage 4 already produces per-post, per-course, per-issue tables that are ideal for monitoring.
	•	Currently used mainly for analytics and reporting, not as a formal drift detection system.

⸻

4. Current alignment summary
Today, the WGU Reddit Analyzer already implements:
	•	A frozen corpus and reproducible pipeline.
	•	A multi-level hierarchy from post to global issue.
	•	Semi-supervised use of LLMs for topic discovery and taxonomy construction.
	•	Prompt and model versioning.
	•	Quantitative benchmarking for Stage 1.
	•	Deterministic, audit-friendly reporting.

The main missing pieces relative to the paper are:
	•	Explicit written schema and hierarchy.
	•	Alignment matrices and logged prompt refinement iterations.
	•	Statistical gating for prompts (McNemar and class-distribution chi-square).
	•	Preference-based few-shot selection.
	•	Sequence invariance tests.
	•	Adversarial input handling.
	•	Drift monitoring linked to Stage 4 outputs.

This puts the system in the roughly 60–65% “aligned” range: strong on lifecycle and structure, weaker on the formal validation and robustness pieces.

⸻

5. Minimal path to ~90% alignment
The goal is to reach roughly 90% alignment with the least effort and disruption. The proposed path focuses on three areas:
	1.	Make schemas and hierarchy explicit (Phase 1)
	2.	Add alignment matrices and a visible refinement loop (Phase 2)
	3.	Add statistical gating for Stage 1 prompts (core Phase 3)

Together, these steps deliver most of the paper’s value without requiring major architectural changes.

⸻

Step 1: Explicit schema and hierarchy (easy)
Deliverables:
	•	A short markdown document in docs/, for example docs/schema_and_hierarchy.md, that includes:
	•	Parent class definitions for Stage 1 (pain point vs not pain point).
	•	The catalog of global normalized issue labels, each with a one-line description and 2–3 post examples.
	•	A diagram or bullet hierarchy:
	•	Post
	•	Pain point presence (yes/no)
	•	Course-level cluster (within a course)
	•	Global issue label (shared across courses)
	•	A schema version number recorded in:
	•	Stage 1, 2, and 3 run manifests.
	•	Stage 4 tables (as a simple column schema_version).

Impact:
	•	Fully covers the “Domain Knowledge Integration” formalism from the paper.
	•	Makes the taxonomy first-class and traceable across runs.

⸻

Step 2: Alignment matrices and refinement loop (medium)
Deliverables:
	•	Stage 1 alignment:
	•	On DEV/TEST, compute confusion matrices between gold labels and Stage 1 predictions for each prompt/model combination.
	•	Save them as tables and simple heatmaps in artifacts/benchmark/alignment/.
	•	Stage 2 and 3 alignment:
	•	Build an alignment table between discovered clusters and global issue labels. Examples:
	•	Rows: global issue labels.
	•	Columns: course-level unconstrained clusters or cluster types.
	•	Save per-run alignment matrices in artifacts/stage3/alignment/<run_id>.csv.
	•	Refinement loop:
	•	For each taxonomy or prompt update, create a short iteration log file that records:
	•	Iteration ID (t).
	•	Prompt or definition changes.
	•	Notable patterns in the alignment matrices (classes too broad, empty, overlapping).
	•	Planned next actions (merge, split, rename, or drop labels).

Impact:
	•	Brings Stage 2 and 3 into direct alignment with the paper’s “alignment matrix” and “Refine(P_class(t), A(t))” loop.
	•	Makes your semi-supervised discovery and taxonomy evolution explicit and auditable.

⸻

Step 3: Statistical gating for Stage 1 prompts (medium)
Deliverables:
	•	McNemar test implementation:
	•	A script or module under src/wgu_reddit_analyzer/benchmark/ that:
	•	Runs old and new prompts on the same DEV/TEST set.
	•	Compares per-example correctness vs gold labels.
	•	Computes b and c (old correct/new wrong vs old wrong/new correct).
	•	Computes chi-square and p-value.
	•	Outputs:
	•	Old and new F1 scores.
	•	McNemar p-value.
	•	Decision: accept or reject new prompt.
	•	Class-distribution chi-square:
	•	For each prompt comparison, compute class count vectors on the same dataset (pain point vs non pain point).
	•	Apply a chi-square test to detect significant distribution changes.
	•	Log results alongside McNemar output.
	•	Policy:
	•	In documentation, define a simple rule:
	•	A new prompt becomes the default only if:
	•	F1 is not worse than the current best, and
	•	McNemar p < threshold (for a meaningful improvement), and
	•	Any large class-distribution shift has been reviewed and accepted.

Impact:
	•	Implements the paper’s “Validation Gate” for prompt changes.
	•	Turns Stage 1 tuning from informal trial-and-error into a statistically grounded process.
	•	Provides a reusable pattern you can later extend to Stage 3 if desired.

⸻

6. What remains beyond 90%
After these three steps, the WGU Reddit Analyzer would:
	•	Have a clear, versioned schema and hierarchy.
	•	Use alignment matrices and logged iterations for taxonomy and prompt refinement.
	•	Genuinely implement the paper’s core validation gate for Stage 1.

That is enough for a defensible claim of “approximately 90% aligned with the framework’s end-to-end methodology.”

The remaining work to reach near-full alignment would be:
	•	Preference-based few-shot selection for ambiguous cases.
	•	Sequence invariance tests (batch order, truncation, example permutations).
	•	Adversarial input filtering for prompt injection phrases.
	•	Monitoring and drift detection based on Stage 4 outputs and embeddings.

Those can be added incrementally without changing the basic design.

⸻

Goal: reach approx 90% alignment and claim:

	•	“Operationalizes nearly all of the paper’s practical guidance, with explicit support for: frozen corpora, gold-set benchmarking, prompt versioning, semi-supervised topic discovery, hierarchical labels, and provenance-safe reporting.”
